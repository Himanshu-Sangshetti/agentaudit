"""Build bench/RESULTS.md from saved per-row records. Spends no credits.

For each suite and split: every arm (Clocked setups × decision rules, plus local baselines when present) with
balanced accuracy, recall and FPR (95% stratified bootstrap CIs, 2,000 resamples), AUROC, expected
calibration error, median latency and credits per row. Paired comparisons against the reference arm use
exact McNemar with Holm correction. The 2×2 ablation crosses policy (default / agentaudit) with the rule.
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench.metrics import auroc, bacc, confusion, mcnemar, rule_consensus, rule_verdict  # noqa: E402

RES = ROOT / "bench/results"
RNG = np.random.default_rng(20261031)
B = 2000


def load(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def ci(labels, preds, fn) -> tuple[float, float]:
    y = np.asarray(labels)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    vals = []
    for _ in range(B):
        idx = np.concatenate([RNG.choice(pos, len(pos)), RNG.choice(neg, len(neg))])
        vals.append(fn([labels[i] for i in idx], [preds[i] for i in idx]))
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def recall(labels, preds):
    tp, fn, _, _ = confusion(labels, preds)
    return tp / (tp + fn) if tp + fn else float("nan")


def fpr(labels, preds):
    _, _, tn, fp = confusion(labels, preds)
    return fp / (fp + tn) if fp + tn else float("nan")


def ece(labels, probs, bins=10) -> float:
    y, p = np.asarray(labels, float), np.asarray(probs, float)
    edges = np.linspace(0, 1, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.any():
            total += m.mean() * abs(y[m].mean() - p[m].mean())
    return float(total)


def holm(pvals: list[float]) -> list[float]:
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def arm_row(name, recs, rule):
    labels = [r["label"] for r in recs]
    preds = [rule(r) for r in recs]
    probs = [r.get("p") if r.get("p") is not None else 0.0 for r in recs]
    lat = [r["rtt_ms"] for r in recs if r.get("rtt_ms")]
    cr = [r["credits"] for r in recs if r.get("credits") is not None]
    b, (blo, bhi) = bacc(labels, preds), ci(labels, preds, bacc)
    return {"arm": name, "n": len(recs), "bacc": b, "bacc_ci": (blo, bhi),
            "recall": recall(labels, preds), "recall_ci": ci(labels, preds, recall),
            "fpr": fpr(labels, preds), "fpr_ci": ci(labels, preds, fpr),
            "auroc": auroc(labels, probs), "ece": ece(labels, probs),
            "median_ms": st.median(lat) if lat else None, "credits_per_row": st.mean(cr) if cr else None,
            "correct": [(p is True) == (y == 1) and p is not None for y, p in zip(labels, preds)]}


def fmt_pct(x, lo=None, hi=None):
    if x != x:  # nan
        return "—"
    s = f"{100 * x:.1f}"
    return s + (f" [{100 * lo:.1f}, {100 * hi:.1f}]" if lo is not None else "")


def table(rows, ref_name):
    ref = next(r for r in rows if r["arm"] == ref_name)
    others = [r for r in rows if r is not ref]
    pv = [mcnemar(ref["correct"], r["correct"])[2] for r in others]
    adj = dict(zip([r["arm"] for r in others], holm(pv)))
    out = ["| Arm | BAcc [95% CI] | Recall [95% CI] | FPR [95% CI] | AUROC | ECE | Median ms | Credits/row | vs reference (Holm p) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        if r is ref:
            vs = "reference"
        else:
            a_only, b_only, _ = mcnemar(ref["correct"], r["correct"])
            vs = f"{b_only}–{a_only} rows, p={adj[r['arm']]:.2g}"
        out.append(f"| {r['arm']} | {fmt_pct(r['bacc'], *r['bacc_ci'])} | {fmt_pct(r['recall'], *r['recall_ci'])} | "
                   f"{fmt_pct(r['fpr'], *r['fpr_ci'])} | {r['auroc']:.3f} | {r['ece']:.3f} | "
                   f"{r['median_ms']:.0f} | " if r["median_ms"] else
                   f"| {r['arm']} | {fmt_pct(r['bacc'], *r['bacc_ci'])} | {fmt_pct(r['recall'], *r['recall_ci'])} | "
                   f"{fmt_pct(r['fpr'], *r['fpr_ci'])} | {r['auroc']:.3f} | {r['ece']:.3f} | — | ")
        out[-1] += (f"{r['credits_per_row']:.1f} | " if r["credits_per_row"] else "0 (local) | ") + vs + " |"
    return "\n".join(out)


def by_source(recs, rule):
    srcs = sorted({r["source"] for r in recs})
    cells = []
    for s in srcs:
        sub = [r for r in recs if r["source"] == s]
        ok = sum(1 for r in sub if (rule(r) is True) == (r["label"] == 1) and rule(r) is not None)
        cells.append(f"{s} {ok}/{len(sub)}")
    return " · ".join(cells)


def suite(name: str, split: str, frozen_rule, extra_note: str = "") -> str:
    d = load(RES / f"{name}_{split}_default.jsonl")
    a = load(RES / f"{name}_{split}_agentaudit.jsonl")
    arms = [arm_row("Clocked default (verdict)", d, rule_verdict)]
    frozen_label = "consensus" if frozen_rule is rule_consensus else "verdict"
    arms.append(arm_row(f"Clocked + AgentAudit ({frozen_label}) ★ frozen", a, frozen_rule))
    for p in sorted(RES.glob(f"baseline_{name}_{split}_*.jsonl")):
        arms.append(arm_row(f"Baseline: {p.stem.split('_')[-1]}", load(p), rule_verdict))
    lines = [f"### {name.capitalize()}: {split} split (n={len(d)})", "", extra_note, "",
             table(arms, "Clocked default (verdict)"), ""]
    # 2×2 ablation: policy × rule
    lines += ["**Ablation (policy × decision rule), balanced accuracy [95% CI]:**", "",
              "| | verdict rule | consensus rule |", "|---|---|---|"]
    for label, recs in (("default policy", d), ("AgentAudit policy", a)):
        cells = []
        for rule in (rule_verdict, rule_consensus):
            L = [r["label"] for r in recs]
            P = [rule(r) for r in recs]
            lo, hi = ci(L, P, bacc)
            cells.append(f"{100 * bacc(L, P):.1f} [{100 * lo:.1f}, {100 * hi:.1f}] · FPR {fmt_pct(fpr(L, P))}")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += ["", f"Per source (frozen arm): {by_source(a, frozen_rule)}", ""]
    return "\n".join(lines)


def jev_section() -> str:
    s = json.loads((RES / "jev_repro_summary.json").read_text())
    rows = ["| Task | n | Clocked (ours) | Clocked (published) | Jev 1.13 (published per-row) | McNemar p | Median ms |",
            "|---|---|---|---|---|---|---|"]
    published = {"route": 84.4, "triage": 68.9, "score": 35.6, "gate": 69.4}
    for t, v in s["tasks"].items():
        rows.append(f"| {t} | {v['n']} | {100 * v['clocked'] / v['n']:.1f} | {published[t]} | "
                    f"{100 * v['jev'] / v['n']:.1f} | {v['p']:.2f} | {v['median_rtt_ms']:.0f} |")
    tot = s["totals"]
    rows.append(f"| **all** | {tot['n']} | **{tot['clocked']}/{tot['n']}** | 507/868 | {tot['jev']}/{tot['n']} | | |")
    return "\n".join(rows)


def main():
    parts = ["# AgentAudit-Bench results", "",
             "Generated by `bench/report.py` from per-row records in `bench/results/`. No credits are spent to regenerate.",
             "Protocol: `bench/PROTOCOL.md`. ★ = configuration frozen on dev before the test run.", "",
             "## Harness validation: jev-benchmark reproduction", "",
             "Our harness against Clocked's published Decide result (engine v66), on the benchmark's own rows and questions.", "",
             jev_section(), "",
             "## RQ1–RQ2: detection and configuration", ""]
    for split in ("test", "dev"):
        parts.append(suite("guard", split, rule_consensus,
                           "Tool poisoning in MCP tool descriptions. Positives: MCPTox. Negatives: reference MCP "
                           "servers, InjecAgent tool specs, hand-written hard negatives. Split disjoint by server."))
        parts.append(suite("inspect", split, rule_verdict,
                           "Scripts. Positives: Atomic Red Team. Negatives: scripts shipped with real MCP servers, "
                           "MIT admin PowerShell, installers. Plus 20 scope pairs (same script, approved vs unapproved scope)."))
    (ROOT / "bench/RESULTS.md").write_text("\n".join(parts))
    print("wrote bench/RESULTS.md")


if __name__ == "__main__":
    main()
