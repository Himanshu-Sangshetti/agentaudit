"""Skills suite (RQ3b, external real-world): the Feb 2026 ClawHub malicious-skill campaign
(yoonholee/agent-skill-malware, MIT; 124 malicious, 223 benign SKILL.md files).

Arms (raw results saved per call, so decision variants are re-scored without new calls):
  guard_default    Clocked Guard, defaults, on the whole skill file
  inspect_default  Clocked Inspect, defaults, on the whole skill file
  agentaudit       AgentAudit's artifact pipeline: Guard with the instructions policy on the skill text, and
                   Inspect with the deployment context on the commands in its code blocks; flagged if either flags.
Split: 30% dev / 70% test, stratified by label, seed 20261101. Variants are chosen on dev; test is run once.

Usage: uv run python bench/suites/run_skills.py --split dev --arm guard_default
"""
import argparse
import json
import random
from pathlib import Path

from agentaudit.audit import INSTRUCTIONS_POLICY
from agentaudit.clocked import Clocked
from agentaudit.collect import _fenced_shell

ROOT = Path(__file__).resolve().parents[2]
sys_path_ctx = ROOT / "bench/suites"
import sys  # noqa: E402
sys.path.insert(0, str(sys_path_ctx))
from run_inspect import CONTEXT  # noqa: E402

MAX = 60_000


def split_rows():
    rows = [json.loads(l) for l in (ROOT / "data/built/skills_external.jsonl").read_text().splitlines()]
    rng = random.Random(20261101)
    out = {"dev": [], "test": []}
    for label in (0, 1):
        part = [r for r in rows if r["label"] == label]
        rng.shuffle(part)
        cut = int(len(part) * 0.3)
        out["dev"] += part[:cut]
        out["test"] += part[cut:]
    return out


def keep(res: dict) -> dict:
    return {k: res.get(k) for k in ("verdict", "category", "severity", "injection", "malicious", "suspicious")} | {
        "p_benign_cat": (res.get("categories") or {}).get("benign", (res.get("categories") or {}).get("benign administration")),
        "evidence": res.get("evidence", [])[:3]}


def run(split: str, arm: str, budget: float) -> None:
    rows = split_rows()[split]
    recs = []
    with Clocked(tag=f"skills-{split}-{arm}", budget=budget) as c:
        for r in rows:
            base = {"id": r["id"], "label": r["label"], "source": r["source"], "group": r["group"]}
            text = r["text"][:MAX]
            try:
                if arm == "guard_default":
                    call = c.injection(text=text, source="content", evidence=True)
                    recs.append(base | {"guard": keep(call.result), "rtt_ms": call.round_trip_ms, "credits": call.credits})
                elif arm == "inspect_default":
                    call = c.script(script=text, evidence=True)
                    recs.append(base | {"inspect": keep(call.result), "rtt_ms": call.round_trip_ms, "credits": call.credits})
                else:
                    g = c.injection(text=text, source="content", instructions=INSTRUCTIONS_POLICY, evidence=True)
                    rec = base | {"guard": keep(g.result), "rtt_ms": g.round_trip_ms, "credits": g.credits or 0}
                    code = _fenced_shell(text, untagged=True)
                    if code.strip():
                        i = c.script(script=code[:MAX], instructions=CONTEXT, evidence=True)
                        rec["inspect"] = keep(i.result)
                        rec["rtt_ms"] += i.round_trip_ms
                        rec["credits"] += i.credits or 0
                    recs.append(rec)
            except Exception as e:  # a failed request counts as wrong
                recs.append(base | {"error": str(e)[:200]})
        print(f"skills {split}/{arm}: {len(recs)} rows, {c.usage.credits} credits ({c.usage.cached} cached)")
    (ROOT / f"bench/results/skills_{split}_{arm}.jsonl").write_text("\n".join(json.dumps(x) for x in recs))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--arm", choices=["guard_default", "inspect_default", "agentaudit"], required=True)
    ap.add_argument("--budget", type=float, default=2000)
    a = ap.parse_args()
    run(a.split, a.arm, a.budget)
