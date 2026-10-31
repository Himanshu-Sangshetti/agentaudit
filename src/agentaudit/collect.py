"""Collect an Agent from a local repo, a JSON/YAML manifest, or a live MCP server.

Static collection never executes anything from the target. Live collection
(`collect_live`) starts the MCP server command the caller supplies, so it is
only used when the caller explicitly opts in.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import yaml

from .model import Agent, Artifact, Tool

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__", ".next", "vendor"}
SCRIPT_EXT = {".sh", ".bash", ".zsh", ".ps1", ".psm1", ".bat", ".cmd"}
INSTRUCTION_NAMES = {"skill.md", "agents.md", "claude.md", "system_prompt.md", "prompt.md", "instructions.md",
                     "gemini.md", ".cursorrules"}
MAX_FILE_CHARS = 60_000  # Guard/Protect admission limit
MAX_FILES = 400


def _iter_files(root: Path):
    count = 0
    for p in sorted(root.rglob("*")):
        if any(part in SKIP_DIRS for part in p.parts) or not p.is_file():
            continue
        if p.stat().st_size > 2_000_000:
            continue
        count += 1
        if count > MAX_FILES:
            return
        yield p


def _read(p: Path) -> str:
    try:
        return p.read_text(errors="replace")[:MAX_FILE_CHARS]
    except OSError:
        return ""


# --- Tool definitions -------------------------------------------------------

_STR = r'''(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)'|`((?:[^`\\]|\\.)*)`)'''
_TS_REGISTER = re.compile(r"(?:registerTool|\.tool)\(\s*" + _STR + r"\s*,\s*(?:\{[^{}]*?description\s*:\s*" + _STR + r"|" + _STR + r")", re.S)
_OBJ_TOOL = re.compile(r"\bname\s*[:=]\s*" + _STR + r"\s*,\s*(?:title\s*[:=]\s*" + _STR + r"\s*,\s*)?description\s*[:=]\s*" + _STR, re.S)
_PY_DECORATED = re.compile(r"@(?:\w+\.)?tool\b[^\n]*\n(?:\s*@[^\n]*\n)*\s*(?:async\s+)?def\s+(\w+)\([^)]*\)[^:]*:\s*(?:\"\"\"(.*?)\"\"\"|'''(.*?)''')", re.S)


def _first(groups) -> str:
    return next((g for g in groups if g), "")


def _unescape(s: str) -> str:
    return s.replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'").strip()


def static_tools(path: Path, text: str) -> list[Tool]:
    tools: list[Tool] = []
    if path.suffix in {".ts", ".js", ".mjs", ".cjs", ".tsx"}:
        for m in _TS_REGISTER.finditer(text):
            g = m.groups()
            name, desc = _first(g[0:3]), _first(g[3:9])
            if name and desc and "${" not in name:
                tools.append(Tool(name, _unescape(desc), source=str(path)))
    if path.suffix == ".py":
        for m in _PY_DECORATED.finditer(text):
            tools.append(Tool(m.group(1), _unescape(m.group(2) or m.group(3) or ""), source=str(path)))
    if path.suffix in {".ts", ".js", ".py", ".json", ".mjs"}:
        for m in _OBJ_TOOL.finditer(text):
            g = m.groups()
            name, desc = _first(g[0:3]), _first(g[6:9])
            if name and desc and len(desc) > 15 and not any(t.name == name for t in tools):
                tools.append(Tool(name, _unescape(desc), source=str(path)))
    return tools


# --- Repo collection --------------------------------------------------------

def _package_scripts(text: str) -> str:
    try:
        scripts = json.loads(text).get("scripts", {})
    except (json.JSONDecodeError, AttributeError):
        return ""
    # Lifecycle hooks run on install; they are the classic supply-chain vector.
    return "\n".join(f"# npm {k}\n{v}" for k, v in scripts.items())


def _fenced_shell(md: str, untagged: bool = False) -> str:
    """Shell code blocks from Markdown. Skill files often leave the language off, so untagged=True keeps those too."""
    lang = r"(?:bash|sh|shell|console|powershell|ps1|zsh|cmd)" + ("?" if untagged else "")
    return "\n".join(re.findall(r"```" + lang + r"\n(.*?)```", md, re.S))


def collect_repo(root: str | Path, name: str | None = None) -> Agent:
    root = Path(root).resolve()
    agent = Agent(name=name or root.name, origin=str(root))
    for p in _iter_files(root):
        rel = str(p.relative_to(root))
        low = p.name.lower()
        if p.suffix in {".ts", ".js", ".mjs", ".cjs", ".py", ".json", ".tsx"} and "test" not in rel.lower():
            text = _read(p)
            agent.tools.extend(static_tools(p.relative_to(root), text))
            if low == "package.json":
                s = _package_scripts(text)
                if s:
                    agent.artifacts.append(Artifact("script", rel + "#scripts", s))
        if low in INSTRUCTION_NAMES or (p.suffix in {".prompt", ".txt"} and "prompt" in low):
            text = _read(p)
            agent.artifacts.append(Artifact("instructions", rel, text))
            code = _fenced_shell(text, untagged=True)
            if code.strip():  # commands a skill tells the agent to run are scripts too
                agent.artifacts.append(Artifact("script", rel + "#code", code))
        elif low.startswith("readme") and p.parent == root:
            md = _read(p)
            agent.artifacts.append(Artifact("readme", rel, md))
            sh = _fenced_shell(md)
            if sh:
                agent.artifacts.append(Artifact("script", rel + "#install", sh))
        elif p.suffix in SCRIPT_EXT or low == "dockerfile" or (p.suffix == ".py" and "scripts" in p.parts):
            agent.artifacts.append(Artifact("script", rel, _read(p)))
        elif low in {"mcp.json", "claude_desktop_config.json", "smithery.yaml", "server.json"}:
            agent.artifacts.append(Artifact("config", rel, _read(p)))
    for t in agent.tools:
        agent.artifacts.append(Artifact("tool_description", f"{t.source}::{t.name}", t.description))
    return agent


# --- Manifest (platform integration path) -----------------------------------

def collect_manifest(path: str | Path) -> Agent:
    """A minimal, platform-neutral agent definition:

    name, owner?, builder?, purpose?, instructions, tools: [{name, description, input_schema?}],
    scripts: [{path, text}]
    """
    path = Path(path)
    data = yaml.safe_load(path.read_text())
    agent = Agent(name=data.get("name", path.stem), origin=str(path),
                  declared={k: data[k] for k in ("owner", "builder", "purpose", "users") if k in data})
    if data.get("instructions"):
        agent.artifacts.append(Artifact("instructions", "instructions", data["instructions"]))
    for t in data.get("tools", []):
        tool = Tool(t["name"], t.get("description", ""), t.get("input_schema"), source="manifest")
        agent.tools.append(tool)
        agent.artifacts.append(Artifact("tool_description", f"manifest::{tool.name}", tool.description))
    for s in data.get("scripts", []):
        agent.artifacts.append(Artifact("script", s.get("path", "script"), s["text"]))
    if data.get("readme"):
        agent.artifacts.append(Artifact("readme", "readme", data["readme"]))
    return agent


# --- Live MCP (opt-in: runs the given command) ------------------------------

def collect_live(command: list[str], name: str, timeout: float = 30.0) -> Agent:
    """Ask a running MCP server for exactly what an agent would see via tools/list."""
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    def send(msg):
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
    def recv(want_id):
        while True:
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError("MCP server closed the connection")
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == want_id:
                return msg
    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "agentaudit", "version": "0.1"}}})
        init = recv(1)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        listed = recv(2)
    finally:
        proc.kill()
    agent = Agent(name=name, origin="live:" + " ".join(command))
    server_instr = init.get("result", {}).get("instructions")
    if server_instr:
        agent.artifacts.append(Artifact("instructions", "live:initialize.instructions", server_instr))
    for t in listed.get("result", {}).get("tools", []):
        tool = Tool(t["name"], t.get("description", ""), t.get("inputSchema"), source="live:tools/list")
        agent.tools.append(tool)
        agent.artifacts.append(Artifact("tool_description", f"live::{tool.name}", tool.description))
    return agent
