"""RQ4: are the audit's verdicts right, and does each endpoint carry weight?

Arms:
  full         the frozen audit, all endpoints
  loo:<ep>     leave one endpoint out (its output removed); other calls are cache hits, so only Decide re-runs
  decide_only  one Decide call over the agent's raw artifacts with the same verdict question (no other endpoints)
Writes bench/results/governance_<arm>.jsonl and prints accuracy, macro-F1, the confusion matrix and the flip table.

Usage: uv run python bench/suites/run_governance.py [--limit N] [--arms full loo decide_only]
"""
import argparse
import collections
import glob
import json
from pathlib import Path

from agentaudit.audit import Auditor, capability_facts
from agentaudit.clocked import Clocked
from agentaudit.collect import collect_manifest
from agentaudit.render import verdict_of

ROOT = Path(__file__).resolve().parents[2]
G = ROOT / "data/built/governance"
LABELS = ["approve", "needs_owner", "reuse_existing", "quarantine"]
TO_VERDICT = {"approve": "approve", "needs_owner": "needs_owner", "reuse": "reuse_existing", "quarantine": "quarantine"}
LOO = ["injection", "script", "pii", "extract", "fill", "grounding", "compare", "rerank"]
VERDICT_Q = {"verdict": {"type": "choice", "criteria": {
    "approve": "No high or critical safety findings, an owner is named, and it is not a duplicate.",
    "needs_owner": "Safe enough, but no accountable owner is named.",
    "reuse_existing": "It duplicates an existing approved agent; use that one instead.",
    "quarantine": "Any high or critical injection, risky script or embedded secret finding."}}}


def macro_f1(y, p):
    f = []
    for c in LABELS:
        tp = sum(1 for a, b in zip(y, p) if a == c and b == c)
        fp = sum(1 for a, b in zip(y, p) if a != c and b == c)
        fn = sum(1 for a, b in zip(y, p) if a == c and b != c)
        f.append(2 * tp / (2 * tp + fp + fn) if tp + fp + fn else 0.0)
    return sum(f) / len(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--every", type=int, default=1, help="pilot: take every k-th agent")
    ap.add_argument("--arms", nargs="+", default=["full", "loo", "decide_only"])
    ap.add_argument("--budget", type=float, default=2500)
    a = ap.parse_args()
    labels = json.loads((G / "labels.json").read_text())[:: a.every][: a.limit]
    reg_agents = [collect_manifest(p) for p in sorted(glob.glob(str(G / "registry/*.yaml")))]
    registry = [(x.name, capability_facts(x)) for x in reg_agents]
    arms = (["full"] if "full" in a.arms else []) + ([f"loo:{e}" for e in LOO] if "loo" in a.arms else []) \
        + (["decide_only"] if "decide_only" in a.arms else [])
    results = collections.defaultdict(list)
    with Clocked(tag="governance", budget=a.budget) as c:
        for lab in labels:
            agent = collect_manifest(G / lab["file"])
            truth = TO_VERDICT[lab["label"]]
            for arm in arms:
                if arm == "decide_only":
                    raw = "\n\n".join(f"[{x.kind} {x.path}]\n{x.text}" for x in agent.artifacts)[:19000]
                    reg = "\n".join(f"- {n}" for n, _ in registry)
                    state = f"Agent '{agent.name}'. Declared: {agent.declared}\nRegistry of approved agents:\n{reg}\n\n{raw}"
                    ans = c.decide(state=state, questions=VERDICT_Q).result["answers"]["verdict"]["choice"]
                    pred = ans
                else:
                    skip = {arm.split(":")[1]} if arm.startswith("loo:") else set()
                    rep = Auditor(c, skip=skip).run(agent, registry)
                    pred = verdict_of(rep)
                results[arm].append({"file": lab["file"], "label": truth, "defect": lab["defect"], "pred": pred})
        credits = c.usage.credits
    for arm, recs in results.items():
        (ROOT / f"bench/results/governance_{arm.replace(':', '_')}.jsonl").write_text("\n".join(json.dumps(r) for r in recs))
    print(f"credits spent: {credits}")
    for arm, recs in results.items():
        y, p = [r["label"] for r in recs], [r["pred"] for r in recs]
        acc = sum(1 for i, j in zip(y, p) if i == j) / len(y)
        by_defect = collections.defaultdict(lambda: [0, 0])
        for r in recs:
            by_defect[r["defect"]][1] += 1
            by_defect[r["defect"]][0] += r["pred"] == r["label"]
        print(f"{arm:18s} acc {100 * acc:5.1f}  macroF1 {100 * macro_f1(y, p):5.1f}  "
              + "  ".join(f"{k}:{v[0]}/{v[1]}" for k, v in sorted(by_defect.items())))
    if "full" in results:
        cm = collections.Counter((r["label"], r["pred"]) for r in results["full"])
        print("confusion (rows=truth, cols=pred):", LABELS)
        for t in LABELS:
            print(f"  {t:15s}", [cm[(t, q)] for q in LABELS])


if __name__ == "__main__":
    main()
