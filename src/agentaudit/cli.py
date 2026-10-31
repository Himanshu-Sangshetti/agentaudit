"""agentaudit command line.

  agentaudit scan PATH|GITHUB_URL [--manifest] [--registry DIR] [--format md|json|sarif] [--out FILE]
  agentaudit usage
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import typer
from rich.console import Console

from .audit import Auditor, capability_facts
from .clocked import Clocked
from .collect import collect_manifest, collect_repo
from .render import exit_code, to_json, to_markdown, to_sarif, verdict_of

app = typer.Typer(add_completion=False, help="Pre-deployment audit for AI agents, built on Clocked.")
console = Console(stderr=True)
GITHUB = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?/?$")


def _load(target: str, manifest: bool):
    if manifest or target.endswith((".yaml", ".yml", ".agent.json")):
        return collect_manifest(target)
    if GITHUB.match(target):
        # Shallow clone into a temp dir. Nothing from the repo is executed.
        tmp = tempfile.mkdtemp(prefix="agentaudit-")
        subprocess.run(["git", "clone", "--depth", "1", "--quiet", target, tmp], check=True)
        return collect_repo(tmp, name=target.rstrip("/").split("/")[-1].removesuffix(".git"))
    return collect_repo(target)


@app.command()
def scan(
    targets: list[str] = typer.Argument(..., help="Repo paths, GitHub URLs or agent manifests (.yaml)."),
    manifest: bool = typer.Option(False, help="Treat targets as agent manifests."),
    registry: Path | None = typer.Option(None, help="Directory of approved agents to check for duplicates and reuse."),
    fmt: str = typer.Option("md", "--format", help="md, json or sarif."),
    out: Path | None = typer.Option(None, help="Write the report here instead of stdout."),
    setup: str = typer.Option("agentaudit", help="agentaudit (benchmarked policy) or default (Clocked defaults)."),
    fail_on: str = typer.Option("high", help="Exit 1 if any finding is at or above this severity, or on quarantine."),
    budget: float = typer.Option(500, help="Maximum credits this scan may spend."),
):
    """Audit one or more agents and print a report."""
    agents = [_load(t, manifest) for t in targets]
    reg_agents = []
    if registry:
        for p in sorted(registry.iterdir()):
            if p.is_dir() or p.suffix in (".yaml", ".yml"):
                reg_agents.append(collect_manifest(p) if p.is_file() else collect_repo(p))
    reg = [(a.name, capability_facts(a)) for a in reg_agents + agents]
    reports = []
    with Clocked(tag="cli-scan", budget=budget) as c:
        auditor = Auditor(c, setup=setup)
        for a in agents:
            console.print(f"[bold]Auditing[/bold] {a.name}: {len(a.tools)} tools, {len(a.artifacts)} artifacts")
            rep = auditor.run(a, reg)
            reports.append(rep)
            console.print(f"  verdict [bold]{verdict_of(rep)}[/bold], {len(rep.findings)} findings")
    if fmt == "sarif":
        text = json.dumps(to_sarif(reports), indent=2)
    elif fmt == "json":
        text = "[" + ",\n".join(to_json(r) for r in reports) + "]"
    else:
        text = "\n\n---\n\n".join(to_markdown(r) for r in reports)
    if out:
        out.write_text(text)
        console.print(f"Wrote {out}")
    else:
        sys.stdout.write(text + "\n")
    raise typer.Exit(exit_code(reports, fail_on))


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
