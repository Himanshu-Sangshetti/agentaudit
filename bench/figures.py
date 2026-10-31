"""Render the write-up figures from per-row records (no credits). Output: docs/figures/*.png

Palette: the first three slots of the validated reference palette (blue, orange, aqua), which pass the
colorblind checks in every chart form. Aqua is below 3:1 contrast on the surface, so every mark carries a
direct value label.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from bench import report as R  # noqa: E402
from bench.metrics import rule_consensus, rule_verdict  # noqa: E402

OUT = ROOT / "docs/figures"
OUT.mkdir(parents=True, exist_ok=True)
AA, DEF, BASE = "#2a78d6", "#eb6834", "#1baf7a"
SURF, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0"

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID, "axes.spines.top": False,
    "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlelocation": "left",
})


def hbar(ax, labels, values, colors, ci=None, title="", xlabel="", xlim=(0, 100), fmt="{:.1f}"):
    y = np.arange(len(labels))[::-1]
    ax.barh(y, values, color=colors, height=0.56, edgecolor=SURF, linewidth=2)
    if ci is not None:
        lo = [v - c[0] for v, c in zip(values, ci)]
        hi = [c[1] - v for v, c in zip(values, ci)]
        ax.errorbar(values, y, xerr=[lo, hi], fmt="none", ecolor=INK2, elinewidth=1.2, capsize=3)
    for yi, v, c in zip(y, values, ci or [None] * len(values)):
        x = (c[1] if c else v) + (xlim[1] - xlim[0]) * 0.015
        ax.text(x, yi, fmt.format(v), va="center", fontsize=9, color=INK)
    ax.set_yticks(y, labels)
    ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def arms_guard(split):
    d = R.load(R.RES / f"guard_{split}_default.jsonl")
    a = R.load(R.RES / f"guard_{split}_agentaudit.jsonl")
    rows = [("Clocked Guard, default", R.arm_row("", d, rule_verdict), DEF)]
    t = R.clocked_dev_threshold("guard")
    rows.append(("Clocked, tuned threshold", R.arm_row("", d, R.threshold_rule(t)), DEF))
    for model, nice in (("protectai", "ProtectAI DeBERTa, tuned"), ("deepset", "deepset DeBERTa, tuned")):
        p = R.RES / f"baseline_guard_{split}_{model}.jsonl"
        if p.exists():
            rows.append((nice, R.arm_row("", R.load(p), R.threshold_rule(R.dev_threshold("guard", model))), BASE))
    rows.append(("Clocked + AgentAudit", R.arm_row("", a, rule_consensus), AA))
    return rows


def fig_guard(split, fname, title):
    rows = arms_guard(split)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw={"wspace": 0.9})
    labels = [r[0] for r in rows]
    cols = [r[2] for r in rows]
    hbar(axes[0], labels, [100 * r[1]["bacc"] for r in rows], cols,
         ci=[(100 * r[1]["bacc_ci"][0], 100 * r[1]["bacc_ci"][1]) for r in rows],
         title="Balanced accuracy (higher is better)", xlabel="%", xlim=(0, 108))
    hbar(axes[1], labels, [100 * r[1]["fpr"] for r in rows], cols,
         ci=[(100 * r[1]["fpr_ci"][0], 100 * r[1]["fpr_ci"][1]) for r in rows],
         title="False-positive rate (lower is better)", xlabel="% of benign items flagged", xlim=(0, 40))
    fig.suptitle(title, x=0.01, y=1.07, ha="left", fontsize=12, fontweight="bold")
    fig.text(0.01, -0.04, "Bars: point estimate. Whiskers: 95% stratified bootstrap CI. Baseline thresholds tuned on the "
             "dev split, like ours.", fontsize=8, color=INK2)
    fig.savefig(OUT / fname, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_ablation():
    d = R.load(R.RES / "guard_test_default.jsonl")
    a = R.load(R.RES / "guard_test_agentaudit.jsonl")
    cells = {}
    for pol, recs in (("Clocked default policy", d), ("AgentAudit policy", a)):
        for rule_name, rule in (("verdict rule", rule_verdict), ("consensus rule", rule_consensus)):
            cells[(pol, rule_name)] = R.arm_row("", recs, rule)
    fig, axes = plt.subplots(1, 2, figsize=(10, 2.6), gridspec_kw={"wspace": 0.7})
    labels = [f"{p}\n+ {r}" for p in ("Clocked default policy", "AgentAudit policy") for r in ("verdict rule", "consensus rule")]
    vals = [cells[(p, r)] for p in ("Clocked default policy", "AgentAudit policy") for r in ("verdict rule", "consensus rule")]
    cols = [DEF, DEF, AA, AA]
    hbar(axes[0], labels, [100 * v["bacc"] for v in vals], cols, title="Balanced accuracy", xlim=(0, 108))
    hbar(axes[1], labels, [100 * v["fpr"] for v in vals], cols, title="False-positive rate", xlim=(0, 32))
    fig.suptitle("Ablation: where the gain comes from (Guard, tool poisoning, test n=253)", x=0.01, y=1.1, ha="left",
                 fontsize=12, fontweight="bold")
    fig.savefig(OUT / "fig2_ablation.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_skills():
    from agentaudit.audit import EXPECTED_IN_INSTRUCTIONS, is_attack
    G, I, A, S = (R.load(R.RES / f"skills_test_{x}.jsonl") for x in ("guard_default", "inspect_default", "agentaudit", "supplychain"))
    sc = {r["id"]: r for r in S}

    def pipe(r):
        gi = bool(r.get("guard")) and r["guard"].get("category") not in EXPECTED_IN_INSTRUCTIONS and is_attack(r["guard"], "consensus")
        return gi or (bool(r.get("inspect")) and is_attack(r["inspect"], "verdict")) or (sc[r["id"]].get("p_untrusted") or 0) >= 0.5

    arms = [("Clocked Guard, default", R.arm_row("", G, lambda r: bool(r.get("guard")) and is_attack(r["guard"], "verdict")), DEF),
            ("Clocked Inspect, default", R.arm_row("", I, lambda r: bool(r.get("inspect")) and is_attack(r["inspect"], "verdict")), DEF),
            ("Supply-chain check alone\n(Extract + Decide)", R.arm_row("", S, lambda r: (r.get("p_untrusted") or 0) >= 0.5), AA),
            ("AgentAudit pipeline", R.arm_row("", A, pipe), AA)]
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.0), gridspec_kw={"wspace": 0.75})
    labels, cols = [a[0] for a in arms], [a[2] for a in arms]
    hbar(axes[0], labels, [100 * a[1]["recall"] for a in arms], cols,
         ci=[(100 * a[1]["recall_ci"][0], 100 * a[1]["recall_ci"][1]) for a in arms],
         title="Malicious skills caught (recall)", xlabel="%", xlim=(0, 105))
    hbar(axes[1], labels, [100 * a[1]["fpr"] for a in arms], cols,
         ci=[(100 * a[1]["fpr_ci"][0], 100 * a[1]["fpr_ci"][1]) for a in arms],
         title="Benign skills flagged (FPR)", xlabel="%", xlim=(0, 12))
    fig.suptitle("A real 2026 malware campaign: 124 malicious + 223 benign skills (test n=244)", x=0.01, y=1.08,
                 ha="left", fontsize=12, fontweight="bold")
    fig.savefig(OUT / "fig4_skills.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_scope():
    d = [r for r in R.load(R.RES / "inspect_test_default.jsonl") if r["source"] == "scope_pair"]
    a = [r for r in R.load(R.RES / "inspect_test_agentaudit.jsonl") if r["source"] == "scope_pair"]
    arms = [("Clocked Inspect, default\n(script only)", R.arm_row("", d, rule_verdict), DEF),
            ("+ change scope (verdict rule)", R.arm_row("", a, rule_verdict), AA),
            ("+ change scope (consensus rule)", R.arm_row("", a, rule_consensus), AA)]
    fig, ax = plt.subplots(figsize=(6.5, 2.3))
    hbar(ax, [x[0] for x in arms], [100 * x[1]["bacc"] for x in arms], [x[2] for x in arms],
         title="Same script, approved vs unapproved scope (14 pairs, test)", xlabel="accuracy %", xlim=(0, 105))
    ax.axvline(50, color=INK2, linestyle=(0, (3, 3)), linewidth=1)
    ax.text(50.5, -0.75, "chance", fontsize=8, color=INK2)
    fig.savefig(OUT / "fig3_scope.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_governance():
    labels = json.loads((ROOT / "data/built/governance/labels.json").read_text())
    dev = {l["file"] for l in labels[::5]}
    defects = [("poisoned_tool", "poisoned\ntool"), ("malicious_script", "malicious\nscript"),
               ("embedded_secret", "embedded\nsecret"), ("duplicate", "duplicate\nagent"), ("none", "clean\nagent")]
    arms = [("full", "Full audit"), ("precision", "Full audit, precision mode"), ("decide_only", "One Decide call (control)"),
            ("loo_injection", "  without Guard"), ("loo_script", "  without Inspect"), ("loo_pii", "  without Protect"),
            ("loo_compare", "  without Compare"), ("loo_fill", "  without Fill"), ("loo_extract", "  without Extract"),
            ("loo_grounding", "  without Verify"), ("loo_rerank", "  without Rerank")]
    M = np.zeros((len(arms), len(defects)))
    counts = []
    for i, (key, _) in enumerate(arms):
        recs = [r for r in R.load(R.RES / f"governance_{key}.jsonl") if r["file"] not in dev]
        row = []
        for j, (d, _) in enumerate(defects):
            sub = [r for r in recs if r["defect"] == d]
            ok = sum(r["pred"] == r["label"] for r in sub)
            M[i, j] = ok / len(sub)
            row.append(f"{ok}/{len(sub)}")
        counts.append(row)
    fig, ax = plt.subplots(figsize=(7.6, 5.0))
    # sequential: one hue, light to dark (blue ramp)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", ["#f3f7fd", "#9cc1ef", "#2a78d6", "#123f78"])
    ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            ax.text(j, i, counts[i][j], ha="center", va="center", fontsize=9,
                    color="#ffffff" if M[i, j] > 0.55 else INK)
    ax.set_xticks(range(len(defects)), [d[1] for d in defects])
    ax.set_yticks(range(len(arms)), [a[1] for a in arms])
    ax.xaxis.tick_top()
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xticks(np.arange(-.5, len(defects)), minor=True)
    ax.set_yticks(np.arange(-.5, len(arms)), minor=True)
    ax.grid(which="minor", color=SURF, linewidth=2)
    ax.tick_params(which="minor", length=0)
    ax.axhline(2.5, color=INK2, linewidth=1)
    ax.set_title("Governance verdicts on 38 held-out agents: correct verdicts per defect type", pad=34)
    fig.text(0.01, 0.0, "Darker = more agents with the correct verdict. Removing an endpoint blinds the audit to exactly "
             "its defect type.", fontsize=8, color=INK2)
    fig.savefig(OUT / "fig5_governance.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_guard("test", "fig1_guard_test.png", "Tool poisoning in MCP tool descriptions (held-out test, n=253)")
    fig_guard("external", "fig1b_guard_external.png", "Never-seen data: 199 real MCP tools + 25 published attacks (n=249)")
    fig_ablation()
    fig_scope()
    fig_skills()
    fig_governance()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
