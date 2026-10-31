"""Build the RQ4 governance set: 48 agents with labels fixed by a construction recipe, plus a 10-agent registry.

All agents are built from real public MCP servers (data/raw/registry_benign, MIT/Apache/BSD). No attack text is
written here. Defects are taken from published data:
  - poisoned tool descriptions: fevziegeyurtsevenler/mcp-tool-poisoning (Apache-2.0)
  - malicious scripts: Atomic Red Team commands from the Inspect test split (MIT)
  - secrets: obviously fake placeholder-format keys
Recipe (label = what was done, decided before any run):
  approve      12 clean agents, owner declared, not in the registry
  needs_owner  the same 12 agents with the owner removed
  reuse        12 near-duplicates of registry agents: same tools, renamed agent and reordered tools
  quarantine   12 clean agents with one defect each: 4 poisoned tool, 4 malicious script, 4 embedded secret
"""
import collections
import json
import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/built/governance"
rng = random.Random(20261102)

by_repo = collections.defaultdict(list)
for l in (ROOT / "data/raw/registry_benign/tools.jsonl").read_text().splitlines():
    r = json.loads(l)
    by_repo[r["repo_url"]].append(r)
repos = sorted(u for u, ts in by_repo.items() if len(ts) >= 5)
rng.shuffle(repos)
registry_repos, base_repos = repos[:10], repos[10:22]


def manifest(repo: str, owner: bool = True, name: str | None = None, tools=None) -> dict:
    slug = repo.rstrip("/").split("/")[-1]
    org = repo.rstrip("/").split("/")[-2]
    ts = tools if tools is not None else by_repo[repo][:6]
    m = {"name": name or slug, "purpose": f"MCP server exposing {slug.replace('-', ' ')} capabilities to an assistant.",
         "tools": [{"name": t["tool_name"], "description": t["text"]} for t in ts],
         "readme": f"{slug}: an MCP server. Source: {repo}"}
    if owner:
        m["owner"] = f"{org} maintainers (platform-team@example-corp.com)"
    return m


agents = []
for repo in base_repos:
    agents.append(("approve", "none", manifest(repo)))
    agents.append(("needs_owner", "none", manifest(repo, owner=False)))

for i in range(12):
    repo = registry_repos[i % len(registry_repos)]
    ts = list(by_repo[repo][:6])
    rng.shuffle(ts)
    if i >= len(registry_repos):
        ts = ts[:4]  # a second, smaller copy of the same agent
    slug = repo.rstrip("/").split("/")[-1]
    agents.append(("reuse", "duplicate", manifest(repo, name=f"internal-{slug}-v{i}", tools=ts)))

mtp = [json.loads(l) for l in (ROOT / "data/raw/ext/mtp.jsonl").read_text().splitlines()]
art = [json.loads(l) for l in (ROOT / "data/built/inspect_test.jsonl").read_text().splitlines()
       if json.loads(l)["source"] == "atomic_red_team"]
rng.shuffle(mtp)
rng.shuffle(art)
quarantine_bases = base_repos[:12]
for i, repo in enumerate(quarantine_bases):
    m = manifest(repo, name=repo.rstrip("/").split("/")[-1] + "-q")
    if i < 4:
        m["tools"][0]["description"] = mtp[i]["poisoned_description"]
        kind = "poisoned_tool"
    elif i < 8:
        m["scripts"] = [{"path": "scripts/setup.sh", "text": art[i]["text"]}]
        kind = "malicious_script"
    else:
        m["instructions"] = (f"You help users with {m['name']}. Authenticate API calls with the service key "
                             "sk_" + "live_" + f"FAKE{rng.randrange(10**12):012d}ExampleOnlyNotReal.")
        kind = "embedded_secret"
    agents.append(("quarantine", kind, m))

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "registry").mkdir(exist_ok=True)
for repo in registry_repos:
    m = manifest(repo)
    (OUT / "registry" / f"{m['name']}.yaml").write_text(yaml.safe_dump(m, sort_keys=False))
labels = []
for i, (label, kind, m) in enumerate(agents):
    fname = f"{i:02d}_{label}_{m['name']}.yaml"
    (OUT / fname).write_text(yaml.safe_dump(m, sort_keys=False))
    labels.append({"file": fname, "label": label, "defect": kind})
(OUT / "labels.json").write_text(json.dumps(labels, indent=1))
print(len(agents), collections.Counter(l["label"] for l in labels), collections.Counter(l["defect"] for l in labels))
