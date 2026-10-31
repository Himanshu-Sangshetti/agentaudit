"""Build the Inspect suite: malicious vs benign scripts, plus scope-conditioned pairs.

Malicious: Atomic Red Team (MIT), the first command-executor test of sampled ATT&CK techniques, with
  input arguments replaced by their defaults.
Benign: scripts that ship with real MCP servers (package.json scripts, Dockerfiles, shell scripts; MIT/Apache
  repos), MIT-licensed admin PowerShell (lazywinadmin/PowerShell), and five well-known installers.
Scope pairs: bench/suites/scope_pairs.py; one row per (script, scope), label decided by the scope.
Split: 30% dev / 70% test, disjoint by technique (ART) or repository (benign); pairs split by pair.
"""
import collections
import json
import random
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
sys.path.insert(0, str(ROOT / "bench/suites"))
from scope_pairs import PAIRS  # noqa: E402

SEED = 20261031
rng = random.Random(SEED)
MAX = 12_000
rows = []

# Malicious: Atomic Red Team
art = []
for y in sorted((RAW / "art/atomics").glob("T*/T*.yaml")):
    doc = yaml.safe_load(y.read_text(errors="replace"))
    for t in doc.get("atomic_tests", []):
        ex = t.get("executor", {})
        cmd = ex.get("command")
        if not cmd or ex.get("name") == "manual":
            continue
        for arg, spec in (t.get("input_arguments") or {}).items():
            cmd = cmd.replace("#{" + arg + "}", str(spec.get("default", "")))
        if len(cmd.strip()) < 15:
            continue
        art.append({"id": f"art:{doc['attack_technique']}:{t.get('auto_generated_guid', t['name'])[:8]}",
                    "text": cmd.strip()[:MAX], "label": 1, "source": "atomic_red_team",
                    "group": ex.get("name"), "technique": doc["attack_technique"],
                    "unit": doc["attack_technique"].split(".")[0], "name": t["name"]})
        break  # one test per technique file
by_exec = collections.defaultdict(list)
for r in art:
    by_exec[r["group"]].append(r)
quota = {"powershell": 60, "command_prompt": 40, "sh": 20, "bash": 20}
for ex, lst in by_exec.items():
    rng.shuffle(lst)
    rows += lst[: quota.get(ex, 0)]

# Benign: scripts shipped with real MCP servers
benign = []
repo_roots = sorted((RAW / "registry_repos").iterdir()) + sorted((RAW / "mcp/official-servers/src").iterdir()) \
    + sorted((RAW / "mcp/archived/src").iterdir())
for repo in repo_roots:
    if not repo.is_dir():
        continue
    cands = [p for p in repo.rglob("*") if p.is_file() and "node_modules" not in p.parts and ".git" not in p.parts
             and (p.suffix in {".sh", ".ps1"} or p.name in {"Dockerfile", "package.json"})]
    rng.shuffle(cands)
    taken = 0
    for p in cands:
        text = p.read_text(errors="replace")
        if p.name == "package.json":
            try:
                scripts = json.loads(text).get("scripts", {})
            except json.JSONDecodeError:
                continue
            text = "\n".join(f"# npm {k}\n{v}" for k, v in scripts.items())
        if len(text.strip()) < 40:
            continue
        benign.append({"id": f"mcpscript:{repo.name}:{p.relative_to(repo)}", "text": text[:MAX], "label": 0,
                       "source": "mcp_repo_script", "group": p.suffix or p.name, "unit": repo.name})
        taken += 1
        if taken >= 3:
            break
rng.shuffle(benign)
rows += benign[:70]

ps = sorted((RAW / "lazywinadmin").rglob("*.ps1"))
rng.shuffle(ps)
for p in ps[:45]:
    rows.append({"id": f"lazywinadmin:{p.relative_to(RAW / 'lazywinadmin')}", "text": p.read_text(errors="replace")[:MAX],
                 "label": 0, "source": "admin_powershell", "group": "powershell", "unit": "lazywinadmin:" + p.parent.name})
for p in sorted((RAW / "benign_scripts").glob("*.sh")):
    rows.append({"id": f"installer:{p.stem}", "text": p.read_text(errors="replace")[:MAX], "label": 0,
                 "source": "installer", "group": "sh", "unit": "installer:" + p.stem})

# Split: whole techniques / repositories go to one side.
units = sorted({r["unit"] for r in rows})
rng.shuffle(units)
dev_units = set(units[: int(len(units) * 0.3)])
for r in rows:
    r["split"] = "dev" if r["unit"] in dev_units else "test"

# Scope pairs: both rows of a pair stay on the same side.
pair_ids = list(range(len(PAIRS)))
rng.shuffle(pair_ids)
dev_pairs = set(pair_ids[:6])
for i, (script, ok_scope, bad_scope) in enumerate(PAIRS):
    split = "dev" if i in dev_pairs else "test"
    rows.append({"id": f"scope:{i:02d}:in", "text": script, "scope": ok_scope, "label": 0, "source": "scope_pair",
                 "group": "in_scope", "unit": f"pair{i}", "split": split})
    rows.append({"id": f"scope:{i:02d}:out", "text": script, "scope": bad_scope, "label": 1, "source": "scope_pair",
                 "group": "out_of_scope", "unit": f"pair{i}", "split": split})

built = ROOT / "data/built"
built.mkdir(parents=True, exist_ok=True)
for split in ("dev", "test"):
    part = [r for r in rows if r["split"] == split]
    (built / f"inspect_{split}.jsonl").write_text("\n".join(json.dumps(r) for r in part))
    print(split, len(part), dict(collections.Counter((r["source"], r["label"]) for r in part)))
(ROOT / "bench/data/inspect_manifest.json").write_text(json.dumps(
    {"seed": SEED, "rows": [{k: r.get(k) for k in ("id", "label", "source", "group", "split")} for r in rows]}, indent=0))
