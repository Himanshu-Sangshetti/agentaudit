"""Reproduce Clocked's published jev-benchmark Decide result (507/868, engine v66) with our harness.

Questions, rows and scoring follow jev-benchmark (github.com/ejs-5/jev-benchmark, MIT); the four
task definitions below are copied verbatim from its run_public_bench.py. Only its JSON data files are
read. Jev's per-row answers come from the benchmark's published public_raw.json.

Usage: uv run python bench/suites/jev_repro.py [--limit N]
"""
import argparse
import json
import statistics as st
from pathlib import Path

from scipy.stats import binomtest

from agentaudit.clocked import Clocked

ROOT = Path(__file__).resolve().parents[2]
JEV = ROOT / "data/raw/jev-benchmark"
LEVELS = ["tiny", "small", "medium", "large"]
TASKS = {
    "route": {"kind": "choice", "file": "public_route.json",
              "ask": "Is this engineering work about the user interface or the server?",
              "criteria": {"frontend": "Work on the user interface - screens, components, dialogs, styling, what a person sees and clicks.",
                           "backend": "Work on the server - API endpoints, database, schemas, background jobs, logic a user never sees."}},
    "triage": {"kind": "choice", "file": "public_triage.json",
               "ask": "What kind of change is this developer describing?",
               "criteria": {"fix": "Repairing something that was broken or behaving wrongly.",
                            "feat": "Adding a new capability that did not exist before.",
                            "refactor": "Restructuring existing code without changing what it does.",
                            "test": "Adding or changing automated tests only."}},
    "score": {"kind": "score", "file": "public_score.json",
              "ask": "How large is this code change?",
              "criteria": ["A one-line tweak (under 20 lines changed)", "A small focused change (20-100 lines)",
                           "A medium multi-file change (100-500 lines)", "A large sweeping change (over 500 lines)"]},
    "gate": {"kind": "noul", "file": "public_gate.json",
             "ask": "Could this change break production or the build if it went wrong? "
                    "(true for CI pipelines, docker, database migrations, release/build configuration)"},
}


def question(sp):
    if sp["kind"] == "noul":
        return {"type": "noul", "instructions": sp["ask"]}
    return {"type": sp["kind"], "instructions": sp["ask"], "criteria": sp["criteria"]}


def prediction(a, kind):
    if kind == "choice":
        return a["choice"], a.get("confidence")
    if kind == "score":
        return LEVELS[max(0, min(3, int(round(a["score"]))))], a.get("confidence")
    n = a["noul"]
    return ("yes" if n >= .5 else "no"), abs(n - .5) * 2


def mcnemar(a, b):
    """Exact McNemar on paired correctness: rows only A got right, only B got right, p."""
    x = sum(1 for i, j in zip(a, b) if i and not j)
    y = sum(1 for i, j in zip(a, b) if j and not i)
    return x, y, (binomtest(x, x + y).pvalue if x + y else 1.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    raw = json.loads((JEV / "public_raw.json").read_text())
    out, totals = {}, {"clocked": 0, "jev": 0, "n": 0}
    (ROOT / "bench/results").mkdir(parents=True, exist_ok=True)
    with Clocked(tag="jev-repro", budget=1200) as c:
        for task, sp in TASKS.items():
            rows = json.loads((JEV / sp["file"]).read_text())[: args.limit]
            jev = {r["id"]: r for r in raw[f"{task}|jev"]}
            recs = []
            for r in rows:
                try:
                    call = c.decide(state=r["text"], questions={"q": question(sp)})
                    pred, conf = prediction(call.result["answers"]["q"], sp["kind"])
                    recs.append({"id": r["id"], "label": r["label"], "pred": pred, "conf": conf,
                                 "rtt_ms": call.round_trip_ms, "model_ms": call.model_ms})
                except Exception as e:  # unanswered counts as wrong, as in the benchmark
                    recs.append({"id": r["id"], "label": r["label"], "pred": None, "error": str(e)[:200]})
            ok_c = [x["pred"] == x["label"] for x in recs]
            ok_j = [jev[x["id"]]["pred"] == x["label"] for x in recs]
            only_c, only_j, p = mcnemar(ok_c, ok_j)
            lat = [x["rtt_ms"] for x in recs if "rtt_ms" in x]
            out[task] = {"n": len(recs), "clocked": sum(ok_c), "jev": sum(ok_j), "clocked_only": only_c,
                         "jev_only": only_j, "p": round(p, 4), "median_rtt_ms": st.median(lat) if lat else None}
            totals["clocked"] += sum(ok_c); totals["jev"] += sum(ok_j); totals["n"] += len(recs)
            (ROOT / f"bench/results/jev_repro_{task}.jsonl").write_text("\n".join(json.dumps(x) for x in recs))
            print(task, out[task], flush=True)
        print("TOTAL", totals, "credits spent", c.usage.credits)
    if not args.limit:
        (ROOT / "bench/results/jev_repro_summary.json").write_text(json.dumps({"tasks": out, "totals": totals}, indent=1))


if __name__ == "__main__":
    main()
