"""AgentAudit web service: the REST pre-deploy hook plus the single-page UI.

  POST /api/audit     {"github_url": "..."} or {"manifest_yaml": "..."}  -> report payload
  GET  /api/examples  precomputed reports for judge mode (no credits spent)
  GET  /api/health

Run:  uv run uvicorn agentaudit.server:app --port 8000
Build judge-mode examples once:  uv run python -m agentaudit.server --build-examples
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from collections import defaultdict, deque
from datetime import date
from pathlib import Path

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .audit import Auditor, Report, capability_facts
from .clocked import Clocked
from .collect import collect_manifest, collect_repo
from .model import Agent
from .render import to_markdown, verdict_of

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
REPORTS = ROOT / "examples" / "reports"
REGISTRY = ROOT / "examples" / "demo_registry"
GITHUB = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(?:\.git)?/?$")

PER_REQUEST_CREDITS = min(60.0, float(os.environ.get("AGENTAUDIT_REQUEST_CREDITS", 60)))
DAILY_CREDITS = float(os.environ.get("AGENTAUDIT_DAILY_CREDITS", 1500))
RATE_LIMIT = int(os.environ.get("AGENTAUDIT_RATE_PER_HOUR", 6))  # live audits per IP per hour
MAX_MANIFEST_CHARS = 60_000

# Which Clocked endpoint produced each kind of output, for the UI's provenance tags.
ENDPOINT_OF = {"guard": "Guard /injection", "inspect": "Inspect /script", "protect": "Protect /pii",
               "verify": "Verify /grounding", "compare": "Compare /compare", "rerank": "Rerank /rerank",
               "extract": "Extract /extract", "fill": "Fill /fill", "decide": "Decide /decide"}
GROUP_OF = {"guard": "safety", "inspect": "safety", "protect": "safety", "verify": "facts"}


# --- Payload ---------------------------------------------------------------

def _mask_artifacts(agent: Agent, report: Report, limit: int = 12_000) -> list[dict]:
    """Artifact texts for in-context highlighting, with every Protect span masked."""
    spans = defaultdict(list)
    for f in report.findings:
        if f.check == "protect":
            for e in f.evidence:
                if e.get("start", -1) >= 0:
                    spans[f.path].append((e["start"], e["end"]))
    out = []
    for a in agent.artifacts:
        text = a.text
        for s, e in sorted(spans.get(a.path, []), reverse=True):
            text = text[:s] + "•" * min(e - s, 12) + text[e:]
        out.append({"path": a.path, "kind": a.kind, "text": text[:limit], "truncated": len(text) > limit})
    return out


def _sensitive_values(agent: Agent, report: Report) -> set[str]:
    """The raw strings behind every Protect span, recovered from the artifact texts."""
    texts = {a.path: a.text for a in agent.artifacts}
    vals = set()
    for f in report.findings:
        if f.check != "protect" or f.path not in texts:
            continue
        for e in f.evidence:
            s, t = e.get("start", -1), e.get("end", -1)
            if 0 <= s < t:
                v = texts[f.path][s:t].strip()
                if len(v) >= 4:
                    vals.add(v)
    return vals


def _scrub(obj, vals: set[str]):
    if isinstance(obj, str):
        for v in vals:
            obj = obj.replace(v, "•" * min(len(v), 12))
        return obj
    if isinstance(obj, list):
        return [_scrub(x, vals) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub(v, vals) for k, v in obj.items()}
    return obj


def build_payload(agent: Agent, report: Report) -> dict:
    """Report plus what the UI needs. Every value Protect found is scrubbed from the whole payload
    (including Extract output and the Markdown), so the API never returns a secret."""
    payload = _build_payload(agent, report)
    return _scrub(payload, _sensitive_values(agent, report))


def _build_payload(agent: Agent, report: Report) -> dict:
    d = report.to_dict()
    for f in d["findings"]:
        f["endpoint"] = ENDPOINT_OF.get(f["check"], f["check"])
        f["group"] = GROUP_OF.get(f["check"], "other")
    d["verdict_label"] = verdict_of(report)
    d["artifacts"] = _mask_artifacts(agent, report)
    d["tools"] = [{"name": t.name, "description": t.description[:400], "source": t.source} for t in agent.tools]
    d["declared"] = agent.declared
    d["markdown"] = to_markdown(report)
    d["endpoints_used"] = sorted({ENDPOINT_OF[k] for k in ("guard", "inspect", "protect", "extract", "fill",
                                                           "verify", "compare", "rerank", "decide")})
    return d


def load_registry() -> list[Agent]:
    return [collect_manifest(p) for p in sorted(REGISTRY.glob("*.yaml"))] if REGISTRY.exists() else []


# --- Limits ----------------------------------------------------------------

class Limits:
    def __init__(self):
        self.lock = threading.Lock()
        self.day = date.today()
        self.spent = 0.0
        self.hits: dict[str, deque] = defaultdict(deque)

    def admit(self, ip: str) -> None:
        with self.lock:
            if date.today() != self.day:
                self.day, self.spent = date.today(), 0.0
            if self.spent + PER_REQUEST_CREDITS > DAILY_CREDITS:
                raise HTTPException(429, "Daily live-audit budget reached. Judge mode examples are still available.")
            q, now = self.hits[ip], time.time()
            while q and now - q[0] > 3600:
                q.popleft()
            if len(q) >= RATE_LIMIT:
                raise HTTPException(429, f"Rate limit: {RATE_LIMIT} live audits per hour. Try judge mode.")
            q.append(now)

    def charge(self, credits: float) -> None:
        with self.lock:
            self.spent += credits


limits = Limits()


# --- App -------------------------------------------------------------------

class AuditRequest(BaseModel):
    github_url: str | None = None
    manifest_yaml: str | None = None


app = FastAPI(title="AgentAudit", version="0.1.0",
              description="Pre-deployment audit for AI agents, built on all nine Clocked endpoints.")


@app.get("/api/health")
def health():
    return {"ok": True, "live": bool(os.environ.get("CLOCKED_API_KEY") or (ROOT / ".env").exists()),
            "daily_budget": DAILY_CREDITS, "spent_today": round(limits.spent, 1)}


@app.get("/api/examples")
def examples():
    items = []
    order = {name: i for i, (name, *_rest) in enumerate(EXAMPLES)}
    for p in sorted(REPORTS.glob("*.json"), key=lambda p: (order.get(p.stem, 99), p.stem)):
        d = json.loads(p.read_text())
        items.append({"id": p.stem, "agent": d["agent"], "verdict": d.get("verdict_label"),
                      "findings": len(d.get("findings", [])), "blurb": d.get("blurb", "")})
    return {"examples": items}


@app.get("/api/examples/{name}")
def example(name: str):
    p = REPORTS / f"{name}.json"
    if not re.fullmatch(r"[\w.-]+", name) or not p.exists():
        raise HTTPException(404, "No such example")
    return JSONResponse(json.loads(p.read_text()))


def _agent_from_request(req: AuditRequest) -> Agent:
    if req.manifest_yaml:
        if len(req.manifest_yaml) > MAX_MANIFEST_CHARS:
            raise HTTPException(413, "Manifest too large")
        try:
            data = yaml.safe_load(req.manifest_yaml)
        except yaml.YAMLError as e:
            raise HTTPException(400, f"Invalid YAML: {e}") from e
        if not isinstance(data, dict) or "name" not in data:
            raise HTTPException(400, "Manifest must be a mapping with at least a 'name'")
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
            fh.write(req.manifest_yaml)
        return collect_manifest(fh.name)
    if req.github_url:
        url = req.github_url.strip()
        if not GITHUB.match(url):
            raise HTTPException(400, "Expected https://github.com/<owner>/<repo>")
        tmp = tempfile.mkdtemp(prefix="agentaudit-")
        try:
            # Shallow clone only; nothing from the repo is executed.
            subprocess.run(["git", "clone", "--depth", "1", "--quiet", url, tmp], check=True, timeout=60,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise HTTPException(400, "Could not clone that repository (is it public?)") from e
        agent = collect_repo(tmp, name=url.rstrip("/").split("/")[-1].removesuffix(".git"))
        if not agent.artifacts:
            raise HTTPException(422, "No agent artifacts (tools, prompts, scripts, README) found in that repo")
        return agent
    raise HTTPException(400, "Send github_url or manifest_yaml")


@app.post("/api/audit")
def audit(req: AuditRequest, request: Request):
    agent = _agent_from_request(req)
    limits.admit(request.client.host if request.client else "unknown")
    registry = load_registry()
    reg = [(a.name, capability_facts(a)) for a in registry + [agent]]
    try:
        with Clocked(tag="web-live", budget=PER_REQUEST_CREDITS) as c:
            rep = Auditor(c).run(agent, reg)
            limits.charge(c.usage.credits)
    except RuntimeError as e:
        raise HTTPException(503, str(e)) from e
    return JSONResponse(build_payload(agent, rep))


if WEB.exists():
    app.mount("/static", StaticFiles(directory=WEB), name="static")

    @app.get("/")
    def index():
        return FileResponse(WEB / "index.html")


# --- Judge-mode example builder (spends credits once; cached afterwards) ----

EXAMPLES = [
    ("payroll-helper", "examples/payroll-helper.yaml", "manifest",
     "A payroll agent with a poisoned tool, an exfiltrating cleanup script, an embedded token and false README claims."),
    ("leave-balance-bot", "examples/demo_registry/leave-balance-bot.yaml", "manifest",
     "Safe, but it duplicates the approved HR Policy Assistant already in the registry."),
    ("password-reset-agent", "examples/demo_registry/password-reset-agent.yaml", "manifest",
     "An IT agent whose admin script passes Inspect, but Guard flags its own system instructions as an override (a known false-positive pattern on 'instructions' artifacts)."),
    ("expense-summarizer", "examples/demo_registry/expense-summarizer.yaml", "manifest",
     "A clean, read-only agent with no named owner."),
    ("mcp-memory", "data/raw/mcp/official-servers/src/memory", "repo",
     "Anthropic's reference Memory MCP server, scanned straight from its repository."),
]


def build_examples(budget: float = 230) -> None:
    registry = load_registry()
    targets = []
    for name, path, kind, blurb in EXAMPLES:
        p = ROOT / path
        if not p.exists():
            print(f"skip {name}: {path} missing")
            continue
        targets.append((name, collect_manifest(p) if kind == "manifest" else collect_repo(p, name=name), blurb))
    reg = [(a.name, capability_facts(a)) for a in registry] + \
          [(a.name, capability_facts(a)) for _, a, _ in targets if a.name not in {r.name for r in registry}]
    REPORTS.mkdir(parents=True, exist_ok=True)
    with Clocked(tag="webdev", budget=budget) as c:
        auditor = Auditor(c)
        for name, agent, blurb in targets:
            before = c.usage.credits
            rep = auditor.run(agent, reg)
            d = build_payload(agent, rep)
            d["blurb"] = blurb
            d["usage"] = {**d["usage"], "credits_this_report": c.usage.credits - before}
            (REPORTS / f"{name}.json").write_text(json.dumps(d, indent=1))
            print(f"{name}: {verdict_of(rep)}, {len(rep.findings)} findings, {c.usage.credits - before:.0f} credits")
        print("total credits", c.usage.credits)


if __name__ == "__main__":
    if "--build-examples" in sys.argv:
        build_examples()
    else:
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8000)))
