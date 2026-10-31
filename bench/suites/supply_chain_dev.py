"""Design the supply-chain check on the skills DEV split only (Extract + Decide).

Extract pulls, verbatim and with offsets, what the skill asks the agent or user to download, install or run.
Decide then judges, from those targets plus the skill's stated purpose, whether it requires running code from
an untrusted source. Prints dev metrics for the check alone and combined with the other arms.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "bench/suites"))
from bench.metrics import bacc, confusion  # noqa: E402
from run_skills import split_rows  # noqa: E402

from agentaudit.audit import supply_chain_check, is_attack  # noqa: E402
from agentaudit.clocked import Clocked  # noqa: E402

rows = split_rows()["dev"]
I = {r["id"]: r for r in map(json.loads, open(ROOT / "bench/results/skills_dev_inspect_default.jsonl"))}
A = {r["id"]: r for r in map(json.loads, open(ROOT / "bench/results/skills_dev_agentaudit.jsonl"))}
out = []
with Clocked(tag="skills-dev-supplychain", budget=1000) as c:
    for r in rows:
        res = supply_chain_check(c, r["text"][:60000])
        out.append({"id": r["id"], "label": r["label"], **res})
(ROOT / "bench/results/skills_dev_supplychain.jsonl").write_text("\n".join(json.dumps(x) for x in out))
print("credits", c.usage.credits if hasattr(c, "usage") else "?")


def report(name, preds):
    L = [o["label"] for o in out]
    tp, fn, tn, fp = confusion(L, preds)
    print(f"{name:44s} BAcc {100 * bacc(L, preds):5.1f}  recall {tp}/{tp + fn}  FPR {fp}/{fp + tn}")


for t in (0.5, 0.7, 0.9):
    sc = [o["p_untrusted"] >= t for o in out]
    report(f"supply-chain alone (p>={t})", sc)
    ins_code = [bool(A[o["id"]].get("inspect")) and is_attack(A[o["id"]]["inspect"], "verdict") for o in out]
    report(f"supply-chain (p>={t}) OR Inspect-code", [a or b for a, b in zip(sc, ins_code)])
