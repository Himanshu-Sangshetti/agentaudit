"""Precision mode on the Guard suites: a Decide second opinion (p >= 0.3) on rows the frozen rule flags.
Writes bench/results/guard_<split>_precision.jsonl (same rows; `adjudicated` holds Decide's probability)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bench.metrics import rule_consensus  # noqa: E402

from agentaudit.audit import adjudicate_tool_flag  # noqa: E402
from agentaudit.clocked import Clocked  # noqa: E402

for split in sys.argv[1:] or ["test", "external"]:
    texts = {json.loads(l)["id"]: json.loads(l)["text"] for l in (ROOT / f"data/built/guard_{split}.jsonl").read_text().splitlines()}
    recs = [json.loads(l) for l in (ROOT / f"bench/results/guard_{split}_agentaudit.jsonl").read_text().splitlines()]
    with Clocked(tag=f"guard-{split}-precision", budget=400) as c:
        for r in recs:
            if rule_consensus(r):
                r["adjudicated"] = adjudicate_tool_flag(c, texts[r["id"]])
        print(split, "credits", c.usage.credits)
    (ROOT / f"bench/results/guard_{split}_precision.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
