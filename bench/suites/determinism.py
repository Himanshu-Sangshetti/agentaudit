"""Re-send a fixed sample of 30 Guard test rows with the cache off and compare with the recorded answers."""
import json
import random
from pathlib import Path

from agentaudit.audit import GUARD_POLICY
from agentaudit.clocked import Clocked

ROOT = Path(__file__).resolve().parents[2]
rows = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "data/built/guard_test.jsonl").read_text().splitlines()}
rec = {r["id"]: r for r in map(json.loads, (ROOT / "bench/results/guard_test_agentaudit.jsonl").read_text().splitlines())}
ids = sorted(rows)
random.Random(7).shuffle(ids)
same_verdict = same_cat = 0
dp = []
with Clocked(tag="determinism", budget=150, cache=False) as c:
    for i in ids[:30]:
        r = c.injection(text=rows[i]["text"], source="content", evidence=True, instructions=GUARD_POLICY).result
        same_verdict += r.get("verdict") == rec[i]["verdict"]
        same_cat += r.get("category") == rec[i]["category"]
        dp.append(abs((r.get("injection") or 0) - (rec[i]["p"] or 0)))
    out = {"n": 30, "same_verdict": same_verdict, "same_category": same_cat, "max_abs_dp": max(dp),
           "mean_abs_dp": sum(dp) / len(dp), "credits": c.usage.credits}
print(out)
(ROOT / "bench/results/determinism.json").write_text(json.dumps(out, indent=1))
