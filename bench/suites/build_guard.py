"""Build the Guard suite (tool poisoning in MCP tool descriptions) with a fixed dev/test split.

Positives: MCPTox (arXiv 2508.14925), 150 poisoned descriptions stratified by paradigm and risk, at most
4 per server. Negatives: real tool descriptions from the reference MCP servers (modelcontextprotocol/servers
and servers-archived, MIT), InjecAgent tool specs (MIT), and our hand-written hard negatives.

MCPTox ships without a license, so its text is kept out of the repo: the split stores text in
data/built/ (git-ignored) and a public ID manifest in bench/data/.
"""
import collections
import glob
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bench/suites"))
from hard_negatives import HARD_NEGATIVES  # noqa: E402

from agentaudit.collect import collect_repo  # noqa: E402

SEED = 20261031
rng = random.Random(SEED)
rows = []

# Positives: MCPTox
tox = [v | {"key": k} for s in json.loads((ROOT / "data/raw/mcptox/pure_tool.json").read_text()) for k, v in s.items()]
strata = collections.defaultdict(list)
for r in tox:
    strata[(r["paradigm"], r["security risk"])].append(r)
per_server = collections.Counter()
picked = []
# Round-robin over strata so every paradigm × risk cell is represented.
for lst in strata.values():
    rng.shuffle(lst)
while len(picked) < 150 and any(strata.values()):
    for key in list(strata):
        while strata[key]:
            r = strata[key].pop()
            if per_server[r["server_name"]] < 4:
                per_server[r["server_name"]] += 1
                picked.append(r)
                break
        if len(picked) >= 150:
            break
for r in picked:
    rows.append({"id": f"mcptox:{r['key']}", "text": r["tool_content"].strip(), "label": 1, "source": "mcptox",
                 "group": r["paradigm"], "risk": r["security risk"], "server": r["server_name"]})

# Negatives: real reference MCP servers
real = []
for d in sorted(glob.glob(str(ROOT / "data/raw/mcp/archived/src/*")) + glob.glob(str(ROOT / "data/raw/mcp/official-servers/src/*"))):
    a = collect_repo(d)
    for t in a.tools:
        if len(t.description) > 20:
            real.append({"id": f"mcpref:{Path(d).name}:{t.name}", "text": t.description, "label": 0,
                         "source": "mcp_reference", "group": "real", "server": Path(d).name})
rows += real

# Negatives: InjecAgent tool specs (summary + parameters, as an agent would see them)
inj = []
for tk in json.loads((ROOT / "data/raw/injecagent_tools.json").read_text()):
    for t in tk["tools"]:
        params = "; ".join(f"{p['name']}: {p.get('description', '')}" for p in t.get("parameters", []))
        inj.append({"id": f"injecagent:{tk['toolkit']}:{t['name']}", "text": f"{t['summary']} Parameters: {params}".strip(),
                    "label": 0, "source": "injecagent", "group": "synthetic_tool", "server": tk["toolkit"]})
rng.shuffle(inj)
rows += inj[:90]

# Negatives: hard negatives
rows += [{"id": f"hardneg:{i:02d}", "text": t, "label": 0, "source": "hard_negative", "group": "hard", "server": "-"}
         for i, t in enumerate(HARD_NEGATIVES)]

# Split by server so no server's tools appear in both dev and test.
servers = sorted({(r["source"], r["server"]) for r in rows if r["source"] != "hard_negative"})
rng.shuffle(servers)
dev_servers = set(servers[: int(len(servers) * 0.3)])
hard_ids = [r["id"] for r in rows if r["source"] == "hard_negative"]
rng.shuffle(hard_ids)
dev_hard = set(hard_ids[:12])
for r in rows:
    r["split"] = "dev" if ((r["source"], r["server"]) in dev_servers or r["id"] in dev_hard) else "test"

built = ROOT / "data/built"
built.mkdir(parents=True, exist_ok=True)
for split in ("dev", "test"):
    part = [r for r in rows if r["split"] == split]
    (built / f"guard_{split}.jsonl").write_text("\n".join(json.dumps(r) for r in part))
    c = collections.Counter((r["source"], r["label"]) for r in part)
    print(split, len(part), dict(c))
(ROOT / "bench/data").mkdir(parents=True, exist_ok=True)
(ROOT / "bench/data/guard_manifest.json").write_text(json.dumps(
    {"seed": SEED, "rows": [{k: r[k] for k in ("id", "label", "source", "group", "split")} for r in rows]}, indent=0))
