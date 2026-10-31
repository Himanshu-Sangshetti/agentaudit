"""Real-world study: audit a seeded sample of 9 public MCP server repos (static collection, nothing executed).
Findings are hand-verified before counting and reported only in aggregate (no project is named in public output)."""
import json
import random
from pathlib import Path

from agentaudit.audit import Auditor
from agentaudit.clocked import Clocked
from agentaudit.collect import collect_repo
from agentaudit.render import verdict_of

ROOT = Path(__file__).resolve().parents[2]
repos = sorted(p for p in (ROOT / "data/raw/registry_repos").iterdir() if p.is_dir())
random.Random(20261103).shuffle(repos)
out = []
with Clocked(tag="realworld", budget=1600) as c:
    for repo in repos[:9]:
        agent = collect_repo(repo)
        row = {"repo": repo.name, "tools": len(agent.tools), "artifacts": len(agent.artifacts)}
        for mode in ("default", "precision"):
            rep = Auditor(c, precision=mode == "precision").run(agent, [])
            row[mode] = {"verdict": verdict_of(rep), "findings": [
                {"check": f.check, "severity": f.severity, "title": f.title, "path": f.path,
                 "quote": (f.evidence[0]["quote"][:160] if f.evidence else "")} for f in rep.findings]}
        out.append(row)
        print(repo.name, row["tools"], row["artifacts"], row["default"]["verdict"], len(row["default"]["findings"]),
              row["precision"]["verdict"], len(row["precision"]["findings"]), flush=True)
    print("credits", c.usage.credits)
(ROOT / "data/built/realworld_private.json").write_text(json.dumps(out, indent=1))  # names stay out of git
