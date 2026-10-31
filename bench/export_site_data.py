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


data = {"guard_test": guard("test"), "guard_external": guard("external"), "ablation": ablation(),
        "inspect": inspect(), "skills": skills(), "governance": governance(), "jev": jev(),
        "determinism": json.loads((R.RES / "determinism.json").read_text())}
out = ROOT / "docs/site/data.json"
out.write_text(json.dumps(data, indent=1))
print("wrote", out, f"({out.stat().st_size // 1024} KB)")
