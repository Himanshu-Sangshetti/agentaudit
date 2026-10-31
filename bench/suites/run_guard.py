"""Run Clocked Guard on the tool-poisoning suite under two setups, and score several decision rules.

Setups (each one is an API call per row):
  default     source="content", Clocked's default instructions and categories (their primary setup)
  agentaudit  source="content", plus AgentAudit's tool-description policy
Decision rules (applied after the call, so they cost nothing extra):
  verdict     flag when Clocked's verdict is not benign
  consensus   flag only when the verdict, the top category and the severity all agree it's an attack

Usage: uv run python bench/suites/run_guard.py --split dev --setup default [--limit N]
"""
import argparse
import json
from pathlib import Path

from agentaudit.audit import GUARD_POLICY
from agentaudit.clocked import Clocked

ROOT = Path(__file__).resolve().parents[2]
SETUPS = {
    "default": {},
    "agentaudit": {"instructions": GUARD_POLICY},
}


def run(split: str, setup: str, limit: int | None, budget: float) -> Path:
    rows = [json.loads(l) for l in (ROOT / f"data/built/guard_{split}.jsonl").read_text().splitlines()][:limit]
    out = ROOT / f"bench/results/guard_{split}_{setup}.jsonl"
    recs = []
    with Clocked(tag=f"guard-{split}-{setup}", budget=budget) as c:
        for r in rows:
            try:
                call = c.injection(text=r["text"], source="content", evidence=True, **SETUPS[setup])
                res = call.result
                recs.append({"id": r["id"], "label": r["label"], "source": r["source"], "group": r["group"],
                             "verdict": res.get("verdict"), "p": res.get("injection"),
                             "category": res.get("category"), "p_benign_cat": res.get("categories", {}).get("benign"),
                             "severity": res.get("severity"), "severity_expected": res.get("severity_expected"),
                             "evidence": res.get("evidence", []), "rtt_ms": call.round_trip_ms,
                             "model_ms": call.model_ms, "credits": call.credits})
            except Exception as e:  # a failed request counts as wrong
                recs.append({"id": r["id"], "label": r["label"], "source": r["source"], "group": r["group"],
                             "error": str(e)[:200]})
        print(f"{split}/{setup}: {len(recs)} rows, {c.usage.credits} credits ({c.usage.cached} cached)")
    out.write_text("\n".join(json.dumps(x) for x in recs))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["dev", "test"], required=True)
    ap.add_argument("--setup", choices=list(SETUPS), required=True)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--budget", type=float, default=1500)
    a = ap.parse_args()
    run(a.split, a.setup, a.limit, a.budget)
