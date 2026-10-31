"""Export every number the write-up charts use, computed from per-row records (0 credits).
Output: docs/site/data.json"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench import report as R  # noqa: E402
from bench.metrics import rule_consensus, rule_verdict  # noqa: E402

from agentaudit.audit import EXPECTED_IN_INSTRUCTIONS, is_attack  # noqa: E402


def pack(name, row, group):
    return {"arm": name, "group": group, "n": row["n"],
            "bacc": round(100 * row["bacc"], 1), "bacc_ci": [round(100 * x, 1) for x in row["bacc_ci"]],
            "recall": round(100 * row["recall"], 1), "recall_ci": [round(100 * x, 1) for x in row["recall_ci"]],
            "fpr": round(100 * row["fpr"], 1), "fpr_ci": [round(100 * x, 1) for x in row["fpr_ci"]],
            "auroc": round(row["auroc"], 3), "median_ms": row["median_ms"], "credits": row["credits_per_row"]}


def guard(split):
    d = R.load(R.RES / f"guard_{split}_default.jsonl")
    a = R.load(R.RES / f"guard_{split}_agentaudit.jsonl")
    out = [pack("Clocked Guard (default)", R.arm_row("", d, rule_verdict), "clocked")]
    t = R.clocked_dev_threshold("guard")
    out.append(pack("Clocked, tuned threshold", R.arm_row("", d, R.threshold_rule(t)), "clocked"))
    for m, nice in (("keyword", "Keyword regex"), ("protectai", "ProtectAI DeBERTa"), ("deepset", "deepset DeBERTa")):
        p = R.RES / f"baseline_guard_{split}_{m}.jsonl"
        if p.exists():
            th = R.dev_threshold("guard", m)
            rule = R.threshold_rule(th) if th is not None else rule_verdict
            out.append(pack(nice + (" (tuned)" if th is not None else ""), R.arm_row("", R.load(p), rule), "baseline"))
    out.append(pack("Clocked + AgentAudit", R.arm_row("", a, rule_consensus), "agentaudit"))
    pp = R.RES / f"guard_{split}_precision.jsonl"
    if pp.exists():
        prec = lambda r: None if "error" in r else bool(rule_consensus(r) and r.get("adjudicated", 1) >= 0.3)  # noqa: E731
        out.append(pack("AgentAudit, precision mode", R.arm_row("", R.load(pp), prec), "agentaudit"))
    return out


def ablation():
    d = R.load(R.RES / "guard_test_default.jsonl")
    a = R.load(R.RES / "guard_test_agentaudit.jsonl")
    return [pack(f"{p} + {r}", R.arm_row("", recs, rule), "x")
            for p, recs in (("Clocked policy", d), ("AgentAudit policy", a))
            for r, rule in (("verdict rule", rule_verdict), ("consensus rule", rule_consensus))]


def inspect():
    d = R.load(R.RES / "inspect_test_default.jsonl")
    a = R.load(R.RES / "inspect_test_agentaudit.jsonl")
    t = R.clocked_dev_threshold("inspect")
    sp = lambda rs: [r for r in rs if r["source"] == "scope_pair"]  # noqa: E731
    nsp = lambda rs: [r for r in rs if r["source"] != "scope_pair"]  # noqa: E731
    return {"all": [pack("Clocked Inspect (default)", R.arm_row("", d, rule_verdict), "clocked"),
                    pack("Clocked, tuned threshold", R.arm_row("", d, R.threshold_rule(t)), "clocked"),
                    pack("Clocked + AgentAudit", R.arm_row("", a, rule_verdict), "agentaudit")],
            "scope_pairs": [pack("Script only (Clocked default)", R.arm_row("", sp(d), rule_verdict), "clocked"),
                            pack("+ change scope, verdict rule", R.arm_row("", sp(a), rule_verdict), "agentaudit"),
                            pack("+ change scope, consensus rule", R.arm_row("", sp(a), rule_consensus), "agentaudit")],
            "no_scope_pairs": [pack("Clocked Inspect (default)", R.arm_row("", nsp(d), rule_verdict), "clocked"),
                               pack("Clocked + AgentAudit", R.arm_row("", nsp(a), rule_verdict), "agentaudit")]}


def skills():
    G, I, A, S = (R.load(R.RES / f"skills_test_{x}.jsonl") for x in ("guard_default", "inspect_default", "agentaudit", "supplychain"))
    sc = {r["id"]: r for r in S}

    def pipe(r):
        gi = bool(r.get("guard")) and r["guard"].get("category") not in EXPECTED_IN_INSTRUCTIONS and is_attack(r["guard"], "consensus")
        return gi or (bool(r.get("inspect")) and is_attack(r["inspect"], "verdict")) or (sc[r["id"]].get("p_untrusted") or 0) >= 0.5

    gp = [r | {"p": (r.get("guard") or {}).get("injection")} for r in G]
    ip = [r | {"p": (r.get("inspect") or {}).get("malicious")} for r in I]
    ap = [r | {"p": max((r.get("guard") or {}).get("injection") or 0, (r.get("inspect") or {}).get("malicious") or 0,
                        sc.get(r["id"], {}).get("p_untrusted") or 0)} for r in A]
    sp = [r | {"p": r.get("p_untrusted")} for r in S]
    return [pack("Clocked Guard (default)", R.arm_row("", gp, lambda r: bool(r.get("guard")) and is_attack(r["guard"], "verdict")), "clocked"),
            pack("Clocked Inspect (default)", R.arm_row("", ip, lambda r: bool(r.get("inspect")) and is_attack(r["inspect"], "verdict")), "clocked"),
            pack("Supply-chain check only", R.arm_row("", sp, lambda r: (r.get("p_untrusted") or 0) >= 0.5), "agentaudit"),
            pack("AgentAudit pipeline", R.arm_row("", ap, pipe), "agentaudit")]


def governance():
    labels = json.loads((ROOT / "data/built/governance/labels.json").read_text())
    dev = {l["file"] for l in labels[::5]}
    defects = ["poisoned_tool", "malicious_script", "embedded_secret", "duplicate", "none"]
    arms = [("full", "Full audit"), ("precision", "Full audit, precision mode"), ("decide_only", "One Decide call"),
            ("loo_injection", "without Guard"), ("loo_script", "without Inspect"), ("loo_pii", "without Protect"),
            ("loo_compare", "without Compare"), ("loo_extract", "without Extract"), ("loo_fill", "without Fill"),
            ("loo_grounding", "without Verify"), ("loo_rerank", "without Rerank"),
            ("full_v1_inferred_owner", "v1: owner inferred (disclosed)")]
    rows = []
    for key, name in arms:
        recs = [r for r in R.load(R.RES / f"governance_{key}.jsonl") if r["file"] not in dev]
        cells = {d: [sum(r["pred"] == r["label"] for r in recs if r["defect"] == d), sum(r["defect"] == d for r in recs)]
                 for d in defects}
        rows.append({"arm": name, "key": key, "acc": round(100 * sum(r["pred"] == r["label"] for r in recs) / len(recs), 1),
                     "cells": cells})
    return {"defects": defects, "rows": rows, "n": len([l for l in labels if l["file"] not in dev])}


def jev():
    s = json.loads((R.RES / "jev_repro_summary.json").read_text())
    pub = {"route": 84.4, "triage": 68.9, "score": 35.6, "gate": 69.4}
    return [{"task": t, "n": v["n"], "ours": round(100 * v["clocked"] / v["n"], 1), "published": pub[t],
             "jev": round(100 * v["jev"] / v["n"], 1)} for t, v in s["tasks"].items()]


import numpy as np  # noqa: E402

from bench.metrics import auroc  # noqa: E402


def roc_points(labels, scores, max_pts=120):
    y, sc = np.asarray(labels), np.asarray(scores, float)
    ths = np.unique(np.concatenate([[np.inf], np.sort(sc)[::-1]]))[::-1]
    P, N = (y == 1).sum(), (y == 0).sum()
    pts = [(float(((sc >= t) & (y == 0)).sum() / N), float(((sc >= t) & (y == 1)).sum() / P), float(t if np.isfinite(t) else 1.0)) for t in ths]
    pts = sorted(set(pts))
    if len(pts) > max_pts:
        idx = np.linspace(0, len(pts) - 1, max_pts).astype(int)
        pts = [pts[i] for i in idx]
    return [{"fpr": round(a, 4), "tpr": round(b, 4), "t": round(c, 4)} for a, b, c in pts]


def op_point(recs, rule):
    L = [r["label"] for r in recs]
    P = [rule(r) for r in recs]
    tp = sum(1 for y, p in zip(L, P) if y == 1 and p is True); fn = sum(1 for y, p in zip(L, P) if y == 1 and p is not True)
    tn = sum(1 for y, p in zip(L, P) if y == 0 and p is False); fp = sum(1 for y, p in zip(L, P) if y == 0 and p is not False)
    return {"fpr": round(fp / (fp + tn), 4), "tpr": round(tp / (tp + fn), 4)}


def guard_curves(split):
    d = {r["id"]: r for r in R.load(R.RES / f"guard_{split}_default.jsonl")}
    a = {r["id"]: r for r in R.load(R.RES / f"guard_{split}_agentaudit.jsonl")}
    ids = list(d)
    L = [d[i]["label"] for i in ids]
    arms = {"Clocked Guard (default)": [d[i].get("p") or 0 for i in ids],
            "Clocked + AgentAudit policy": [a[i].get("p") or 0 for i in ids]}
    for m, nice in (("protectai", "ProtectAI DeBERTa"), ("deepset", "deepset DeBERTa")):
        p = R.RES / f"baseline_guard_{split}_{m}.jsonl"
        if p.exists():
            b = {r["id"]: r for r in R.load(p)}
            arms[nice] = [b[i].get("p") or 0 for i in ids]
    curves = [{"arm": k, "auroc": round(auroc(L, v), 3), "points": roc_points(L, v)} for k, v in arms.items()]
    ops = {"Clocked default verdict": op_point(list(d.values()), rule_verdict),
           "AgentAudit frozen (consensus)": op_point(list(a.values()), rule_consensus)}
    pp = R.RES / f"guard_{split}_precision.jsonl"
    if pp.exists():
        ops["AgentAudit precision mode"] = op_point(R.load(pp), lambda r: bool(rule_consensus(r) and r.get("adjudicated", 1) >= 0.3))
    return {"curves": curves, "operating_points": ops}


def score_dist(split):
    d = {r["id"]: r for r in R.load(R.RES / f"guard_{split}_default.jsonl")}
    a = {r["id"]: r for r in R.load(R.RES / f"guard_{split}_agentaudit.jsonl")}
    return [{"label": d[i]["label"], "source": d[i]["source"], "p_default": round(d[i].get("p") or 0, 4),
             "p_agentaudit": round(a[i].get("p") or 0, 4)} for i in d]


def calibration(split):
    out = {}
    for name, f in (("Clocked Guard (default)", "default"), ("Clocked + AgentAudit policy", "agentaudit")):
        recs = R.load(R.RES / f"guard_{split}_{f}.jsonl")
        y = np.array([r["label"] for r in recs], float); p = np.array([r.get("p") or 0 for r in recs], float)
        bins = []
        for lo in np.arange(0, 1, 0.1):
            m = (p >= lo) & ((p < lo + 0.1) if lo < 0.9 else (p <= 1))
            if m.any():
                bins.append({"lo": round(lo, 1), "mean_p": round(float(p[m].mean()), 3), "frac_pos": round(float(y[m].mean()), 3), "n": int(m.sum())})
        out[name] = {"ece": round(R.ece(list(y), list(p)), 3), "bins": bins}
    return out


def sweep(split):
    out = {}
    for name, f in (("Clocked Guard (default)", "default"), ("Clocked + AgentAudit policy", "agentaudit")):
        recs = R.load(R.RES / f"guard_{split}_{f}.jsonl")
        L = [r["label"] for r in recs]
        rows = []
        for t in np.round(np.arange(0.02, 1.0, 0.02), 2):
            P = [(r.get("p") or 0) >= t for r in recs]
            tp = sum(1 for y, q in zip(L, P) if y and q); fn = sum(1 for y, q in zip(L, P) if y and not q)
            tn = sum(1 for y, q in zip(L, P) if not y and not q); fp = sum(1 for y, q in zip(L, P) if not y and q)
            rows.append({"t": float(t), "bacc": round(50 * (tp / (tp + fn) + tn / (tn + fp)), 1), "fpr": round(100 * fp / (fp + tn), 1),
                         "recall": round(100 * tp / (tp + fn), 1)})
        out[name] = rows
    return out


def by_source():
    out = []
    for split in ("test", "external"):
        d = R.load(R.RES / f"guard_{split}_default.jsonl"); a = R.load(R.RES / f"guard_{split}_agentaudit.jsonl")
        for src in sorted({r["source"] for r in d if r["label"] == 0}):
            for name, recs, rule in (("Clocked Guard (default)", d, rule_verdict), ("Clocked + AgentAudit", a, rule_consensus)):
                sub = [r for r in recs if r["source"] == src and r["label"] == 0]  # false alarms: benign rows only
                ok = [rule(r) is True for r in sub]
                k, n = sum(ok), len(ok)
                lo, hi = wilson(k, n)
                out.append({"split": split, "source": src, "arm": name, "flagged": k, "n": n, "fpr": round(100 * k / n, 1),
                            "ci": [round(100 * lo, 1), round(100 * hi, 1)]})
    return out


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    ph = k / n; den = 1 + z * z / n; c = ph + z * z / (2 * n); r = z * ((ph * (1 - ph) + z * z / (4 * n)) / n) ** 0.5
    return (c - r) / den, (c + r) / den


def precision_curve():
    recs = R.load(R.RES / "guard_test_precision.jsonl")
    L = [r["label"] for r in recs]
    rows = []
    for t in [0.0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95]:
        P = [bool(rule_consensus(r) and r.get("adjudicated", 1) >= t) for r in recs]
        tp = sum(1 for y, q in zip(L, P) if y and q); fn = sum(1 for y, q in zip(L, P) if y and not q)
        tn = sum(1 for y, q in zip(L, P) if not y and not q); fp = sum(1 for y, q in zip(L, P) if not y and q)
        rows.append({"t": t, "recall": round(100 * tp / (tp + fn), 1), "fpr": round(100 * fp / (fp + tn), 2),
                     "bacc": round(50 * (tp / (tp + fn) + tn / (tn + fp)), 1)})
    return rows


def skills_roc():
    G, I, S = (R.load(R.RES / f"skills_test_{x}.jsonl") for x in ("guard_default", "inspect_default", "supplychain"))
    A = {r["id"]: r for r in R.load(R.RES / "skills_test_agentaudit.jsonl")}
    sc = {r["id"]: r for r in S}
    ids = [r["id"] for r in G]
    L = [r["label"] for r in G]
    g = {r["id"]: (r.get("guard") or {}).get("injection") or 0 for r in G}
    i = {r["id"]: (r.get("inspect") or {}).get("malicious") or 0 for r in I}
    s_ = {k: v.get("p_untrusted") or 0 for k, v in sc.items()}
    pipe = {k: max((A[k].get("guard") or {}).get("injection") or 0, (A[k].get("inspect") or {}).get("malicious") or 0, s_.get(k, 0)) for k in ids}
    arms = {"Clocked Guard (default)": g, "Clocked Inspect (default)": i, "Supply-chain check": s_, "AgentAudit pipeline": pipe}
    return [{"arm": k, "auroc": round(auroc(L, [v[x] for x in ids]), 3), "points": roc_points(L, [v[x] for x in ids])} for k, v in arms.items()]


def latency():
    out = []
    for name, path in (("Guard (tool descriptions)", "guard_test_agentaudit"), ("Inspect (scripts)", "inspect_test_agentaudit"),
                       ("Decide (jev-benchmark)", None)):
        if path:
            ms = sorted(r["rtt_ms"] for r in R.load(R.RES / f"{path}.jsonl") if r.get("rtt_ms"))
        else:
            ms = sorted(json.loads(l)["rtt_ms"] for t in ("route", "triage", "score", "gate")
                        for l in (R.RES / f"jev_repro_{t}.jsonl").read_text().splitlines() if json.loads(l).get("rtt_ms"))
        q = lambda f: round(ms[int(f * (len(ms) - 1))])  # noqa: E731
        out.append({"endpoint": name, "n": len(ms), "p10": q(.1), "p25": q(.25), "p50": q(.5), "p75": q(.75), "p90": q(.9)})
    return out


def forest():
    rows = []
    for suite, arms in (("Tool poisoning (test)", guard("test")), ("Real-world tools (external)", guard("external")),
                        ("Scripts (test)", inspect()["all"]), ("Malicious skills (test)", skills())):
        for a in arms:
            rows.append({"suite": suite, **{k: a[k] for k in ("arm", "group", "bacc", "bacc_ci", "fpr", "credits", "median_ms")}})
    return rows


data = {"guard_test": guard("test"), "guard_external": guard("external"), "ablation": ablation(),
        "inspect": inspect(), "skills": skills(), "governance": governance(), "jev": jev(),
        "determinism": json.loads((R.RES / "determinism.json").read_text()),
        "roc": {"test": guard_curves("test"), "external": guard_curves("external")},
        "score_dist": {"test": score_dist("test")}, "calibration": calibration("test"),
        "threshold_sweep": sweep("test"), "by_source": by_source(), "precision_curve": precision_curve(),
        "skills_roc": skills_roc(), "latency": latency(), "forest": forest()}
out = ROOT / "docs/site/data.json"
out.write_text(json.dumps(data, indent=1))
print("wrote", out, f"({out.stat().st_size // 1024} KB)")
