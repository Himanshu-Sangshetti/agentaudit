"""agentaudit command line.

  agentaudit scan PATH|GITHUB_URL|MANIFEST ... [--registry DIR] [--format md|json|sarif] [--precision]
  agentaudit estimate PATH|GITHUB_URL|MANIFEST ... [--registry DIR] [--precision]   (no API calls)
  agentaudit demo [NAME]                                                             (offline, no key)
  agentaudit usage
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from .audit import MAX_PROTECT, Auditor, Report, capability_facts
from .clocked import Clocked, ClockedError
from .collect import collect_manifest, collect_repo
from .model import Agent
from .render import exit_code, to_json, to_markdown, to_sarif, verdict_of

app = typer.Typer(add_completion=False, no_args_is_help=True,
                  help="Pre-deployment audit for AI agents, built on Clocked.")
console = Console(stderr=True)
GITHUB = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?/?$")
REPORTS = Path(__file__).resolve().parents[2] / "examples" / "reports"


class CliError(Exception):
    """An error with a message meant for the person at the terminal."""


def _load(target: str, manifest: bool) -> Agent:
    if manifest or target.endswith((".yaml", ".yml", ".agent.json")):
        if not Path(target).exists():
            raise CliError(f"Manifest not found: {target}")
        return collect_manifest(target)
    if GITHUB.match(target):
        # Shallow clone into a temp dir. Nothing from the repo is executed.
        tmp = tempfile.mkdtemp(prefix="agentaudit-")
        try:
            subprocess.run(["git", "clone", "--depth", "1", "--quiet", target, tmp], check=True, timeout=120,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise CliError(f"Could not clone {target}. Is it a public repository?") from e
        return collect_repo(tmp, name=target.rstrip("/").split("/")[-1].removesuffix(".git"))
    if not Path(target).exists():
        raise CliError(f"Not found: {target} (expected a directory, a GitHub URL or an agent manifest)")
    return collect_repo(target)


def _registry(registry: Path | None) -> list[Agent]:
    if not registry:
        return []
    if not registry.is_dir():
        raise CliError(f"--registry must be a directory: {registry}")
    out = []
    for p in sorted(registry.iterdir()):
        if p.is_dir():
            out.append(collect_repo(p))
        elif p.suffix in (".yaml", ".yml"):
            out.append(collect_manifest(p))
    return out


def _render(reports: list[Report], fmt: str) -> str:
    if fmt == "sarif":
        return json.dumps(to_sarif(reports), indent=2)
    if fmt == "json":
        return "[" + ",\n".join(to_json(r) for r in reports) + "]"
    return "\n\n---\n\n".join(to_markdown(r) for r in reports)


def explain(err: Exception, budget: float | None = None) -> str:
    """Turn a client or budget error into one actionable sentence."""
    if isinstance(err, ClockedError):
        if err.status in (401, 403):
            return ("Clocked rejected the API key (HTTP %d). Check CLOCKED_API_KEY, or create a new key in your "
                    "Clocked account settings." % err.status)
        if err.status == 402:
            return "Your Clocked account is out of credits (HTTP 402). Add credits or a plan, then re-run."
        if err.status == 422:
            try:
                detail = json.loads(err.body).get("detail", err.body)
            except (ValueError, AttributeError):
                detail = err.body
            return f"Clocked could not process one request (HTTP 422): {str(detail)[:400]}"
        if err.status == 429:
            return "Clocked is rate-limiting this account (HTTP 429). Wait a minute and re-run; results so far are cached."
        return f"Clocked returned HTTP {err.status}: {err.body[:300]}"
    msg = str(err)
    if "hit its budget" in msg:
        return (f"Stopped at the scan budget of {budget:.0f} credits. Everything already called is cached, so "
                f"re-running with a larger --budget (see `agentaudit estimate`) only pays for the rest.")
    if "ceiling" in msg:
        return f"Account credit ceiling reached: {msg}. Raise AGENTAUDIT_CREDIT_CEILING if that is intended."
    if "CLOCKED_API_KEY" in msg:
        return ("No Clocked API key found. Create one at https://clocked.rezolve.ai/account, then either "
                "`export CLOCKED_API_KEY=clk_...` or add `CLOCKED_API_KEY=clk_...` to a .env file here. "
                "To try AgentAudit without a key, run `agentaudit demo`.")
    return msg


class _Recorder:
    """Keeps the findings of each stage as it finishes, so a stopped scan can still show partial results."""

    STAGES = ("guard", "inspect", "protect", "verify")

    def __init__(self, auditor: Auditor):
        self.findings: list = []
        for name in self.STAGES:
            fn = getattr(auditor, name)

            def wrapped(*a, _fn=fn, **k):
                res = _fn(*a, **k)
                self.findings.extend(res)
                return res
            setattr(auditor, name, wrapped)


@app.command()
def scan(
    targets: list[str] = typer.Argument(..., help="Repo paths, GitHub URLs or agent manifests (.yaml)."),
    manifest: bool = typer.Option(False, help="Treat targets as agent manifests."),
    registry: Path | None = typer.Option(None, help="Directory of approved agents to check for duplicates and reuse."),
    fmt: str = typer.Option("md", "--format", help="md, json or sarif."),
    out: Path | None = typer.Option(None, help="Write the report here instead of stdout."),
    setup: str = typer.Option("agentaudit", help="agentaudit (benchmarked policy) or default (Clocked defaults)."),
    precision: bool = typer.Option(False, help="Ask Decide for a second opinion on Guard flags in tool descriptions "
                                               "(fewer false positives, some recall cost)."),
    fail_on: str = typer.Option("high", help="Exit 1 if any finding is at or above this severity, or on quarantine."),
    budget: float = typer.Option(500, help="Maximum credits this scan may spend."),
):
    """Audit one or more agents and print a report."""
    load_dotenv()
    try:
        agents = [_load(t, manifest) for t in targets]
        reg_agents = _registry(registry)
    except CliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from e
    if not os.environ.get("CLOCKED_API_KEY"):
        console.print(f"[red]Error:[/red] {explain(RuntimeError('CLOCKED_API_KEY is not set'))}")
        raise typer.Exit(2)
    reg = [(a.name, capability_facts(a)) for a in reg_agents + agents]
    reports, failed = [], None
    with Clocked(tag="cli-scan", budget=budget) as c:
        auditor = Auditor(c, setup=setup, precision=precision)
        rec = _Recorder(auditor)
        for a in agents:
            console.print(f"[bold]Auditing[/bold] {a.name}: {len(a.tools)} tools, {len(a.artifacts)} artifacts")
            rec.findings = []
            try:
                rep = auditor.run(a, reg)
            except (ClockedError, RuntimeError) as e:
                failed = e
                if rec.findings:
                    partial = Report(a.name, a.origin, findings=rec.findings)
                    partial.verdict = {"verdict": {"choice": "incomplete"}}
                    partial.usage = {"calls": c.usage.calls, "credits": c.usage.credits, "cost_usd": c.usage.cost_usd}
                    reports.append(partial)
                break
            reports.append(rep)
            console.print(f"  verdict [bold]{verdict_of(rep)}[/bold], {len(rep.findings)} findings")
        spent = c.usage.credits
    if reports:
        text = _render(reports, fmt)
        if failed:
            text = ("<!-- PARTIAL REPORT: the scan stopped early -->\n" if fmt == "md" else "") + text
        if out:
            out.write_text(text)
            console.print(f"Wrote {out}")
        else:
            sys.stdout.write(text + "\n")
    console.print(f"[dim]{spent:.0f} credits spent[/dim]")
    if failed:
        console.print(f"[red]Error:[/red] {explain(failed, budget)}")
        raise typer.Exit(3)
    raise typer.Exit(exit_code(reports, fail_on))


# Measured per-call costs on the main account (Oct 31 runs), as (low, high) credits.
COST = {"guard": (3, 4), "inspect": (3, 5), "protect": (3, 4), "extract": (5, 13), "fill": (4, 6),
        "verify": (2, 4), "compare": (8, 16), "rerank": (2, 5), "decide": (1, 1), "supply_chain": (6, 14),
        "adjudicate": (1, 1)}


def estimate_agent(agent: Agent, has_registry: bool, precision: bool = False) -> dict:
    """Upper and lower credit estimates for one audit, from artifact counts. Makes no API calls."""
    kinds = [a.kind for a in agent.artifacts if a.text.strip()]
    n_guard = sum(k in {"tool_description", "instructions", "readme", "config"} for k in kinds)
    n_script = kinds.count("script")
    prot_chars = sum(min(len(a.text), MAX_PROTECT) for a in agent.artifacts
                     if a.kind in {"instructions", "tool_description", "config"} and a.text.strip())
    n_protect = -(-prot_chars // MAX_PROTECT) if prot_chars else 0
    n_supply = sum(k in {"instructions", "readme"} for k in kinds)
    counts = {"guard": n_guard, "inspect": n_script, "protect": n_protect, "supply_chain": n_supply,
              "extract": 1 if any(k in {"readme", "instructions", "config"} for k in kinds) else 0,
              "fill": 1, "verify": 1, "decide": 1,
              "compare": 1 if has_registry else 0, "rerank": 1 if has_registry else 0,
              "adjudicate": kinds.count("tool_description") if precision else 0}
    lo = sum(COST[k][0] * n for k, n in counts.items())
    hi = sum(COST[k][1] * n for k, n in counts.items())
    return {"agent": agent.name, "counts": counts, "low": lo, "high": hi}


@app.command()
def estimate(
    targets: list[str] = typer.Argument(..., help="Repo paths, GitHub URLs or agent manifests (.yaml)."),
    manifest: bool = typer.Option(False, help="Treat targets as agent manifests."),
    registry: Path | None = typer.Option(None, help="Directory of approved agents (adds Compare and Rerank)."),
    precision: bool = typer.Option(False, help="Include the precision-mode second opinions (worst case)."),
):
    """Estimate the credits a scan will cost, without calling Clocked."""
    try:
        agents = [_load(t, manifest) for t in targets]
        has_reg = bool(_registry(registry)) or len(agents) > 1
    except CliError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(2) from e
    tot_lo = tot_hi = 0
    for a in agents:
        e = estimate_agent(a, has_reg, precision)
        tot_lo, tot_hi = tot_lo + e["low"], tot_hi + e["high"]
        c = e["counts"]
        console.print(f"[bold]{a.name}[/bold]: {len(a.artifacts)} artifacts → Guard ×{c['guard']}, Inspect ×{c['inspect']}, "
                      f"Protect ×{c['protect']}, supply-chain ×{c['supply_chain']}"
                      + (", Compare + Rerank" if has_reg else "") + f"  ≈ {e['low']}–{e['high']} credits")
    sys.stdout.write(json.dumps({"low": tot_lo, "high": tot_hi}) + "\n")
    console.print(f"Suggested: [bold]--budget {int(tot_hi * 1.2) + 5}[/bold]  (cached calls are free on re-runs)")


@app.command()
def demo(name: str = typer.Argument(None, help="Example to show; omit to list them.")):
    """Replay recorded audits from examples/reports. No API key or network needed."""
    files = sorted(REPORTS.glob("*.json"))
    if not files:
        console.print("[red]Error:[/red] no recorded examples found in examples/reports")
        raise typer.Exit(2)
    if not name:
        console.print("[bold]Recorded audits[/bold] (run `agentaudit demo NAME`):\n")
        for p in files:
            d = json.loads(p.read_text())
            console.print(f"  [bold]{p.stem:24s}[/bold] {d.get('verdict_label', '?'):16s} {d.get('blurb', '')}")
        return
    p = REPORTS / f"{name}.json"
    if not p.exists():
        console.print(f"[red]Error:[/red] no example named {name!r}. Try: " + ", ".join(f.stem for f in files))
        raise typer.Exit(2)
    d = json.loads(p.read_text())
    Console().print(Markdown(d.get("markdown") or f"# {d['agent']}\n\n(no markdown recorded)"))


@app.command()
def usage():
    """Show credits spent so far, by experiment tag."""
    from collections import Counter

    from .clocked import LEDGER
    tot, acct = Counter(), Counter()
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            r = json.loads(line)
            tot[r["tag"]] += r.get("credits") or 0
            acct[r.get("account", "main")] += r.get("credits") or 0
    for tag, cr in tot.most_common():
        console.print(f"{tag:28s}{cr:8.0f}")
    for a, cr in sorted(acct.items()):
        console.print(f"[bold]{'account ' + a:28s}{cr:8.0f}[/bold] of 20000")


if __name__ == "__main__":
    app()
