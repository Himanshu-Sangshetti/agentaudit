"""Build the external Guard suite (RQ3b): data never used to design the frozen configuration.

Negatives: 199 tool descriptions from 24 public MCP servers (MIT/Apache/BSD; data/raw/registry_benign).
Paired set: fevziegeyurtsevenler/mcp-tool-poisoning (HF, Apache-2.0), 25 tools, each with its benign and
  poisoned description; both sides are included, so FPR and recall are measured on matched text.
Everything here is evaluated once with the frozen configuration; there is no dev split.
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
rows = []
for l in (ROOT / "data/raw/registry_benign/tools.jsonl").read_text().splitlines():
    r = json.loads(l)
    rows.append({"id": r["id"], "text": r["text"], "label": 0, "source": "registry_real", "group": r.get("license", "")})
for l in (ROOT / "data/raw/ext/mtp.jsonl").read_text().splitlines():
    r = json.loads(l)
    rows.append({"id": f"mtp:{r['id']}:benign", "text": r["benign_description"], "label": 0, "source": "mtp_pair",
                 "group": "benign_original"})
    rows.append({"id": f"mtp:{r['id']}:poisoned", "text": r["poisoned_description"], "label": 1, "source": "mtp_pair",
                 "group": r["technique"]})
(ROOT / "data/built/guard_external.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
print(len(rows), dict(collections.Counter((r["source"], r["label"]) for r in rows)))
