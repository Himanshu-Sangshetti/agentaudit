"""Paper figures for the README and docs, rendered from docs/site/data.json (run bench/export_site_data.py first).

Palette: three validated hues by family (orange = Clocked as shipped, blue = AgentAudit, aqua = open-source
baselines); within a family, line style is the second encoding, and curves are labeled directly. A 4th hue fails
the all-pairs normal-vision check, so it is not used. Output: docs/figures/*.png and docs/assets/hero.png
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
D = json.loads((ROOT / "docs/site/data.json").read_text())
OUT = ROOT / "docs/figures"
OUT.mkdir(parents=True, exist_ok=True)
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
SURF, INK, INK2, GRID = "#ffffff", "#0b0b0b", "#52514e", "#e9e8e4"
FAMILY = {"clocked": ORANGE, "agentaudit": BLUE, "baseline": AQUA}

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF, "font.family": "DejaVu Sans",
    "font.size": 9.5, "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": "#cfcdc6", "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold",
    "axes.titlesize": 10.5, "axes.titlelocation": "left", "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.7,
    "legend.frameon": False, "lines.solid_capstyle": "round",
})


def style_for(arm: str):
    a = arm.lower()
    if "agentaudit" in a or "supply" in a:
        return BLUE, ("--" if ("supply" in a or "precision" in a) else "-")
    if "protectai" in a:
        return AQUA, "-"
    if "deepset" in a:
        return AQUA, "--"
    return ORANGE, ("--" if ("inspect" in a or "tuned" in a) else "-")


def roc_panel(ax, curves, ops=None, title="", inset=True):
    ax.plot([0, 1], [0, 1], color="#bdbbb3", linestyle=(0, (2, 3)), linewidth=1)
    for c in curves:
        col, ls = style_for(c["arm"])
        ax.plot([p["fpr"] for p in c["points"]], [p["tpr"] for p in c["points"]], color=col, linestyle=ls, linewidth=2,
                label=f"{c['arm']}  (AUROC {c['auroc']:.3f})")
    if ops:
        for name, pt in ops.items():
            col = ORANGE if "Clocked" in name else BLUE
            ax.scatter([pt["fpr"]], [pt["tpr"]], s=46, color=col, marker="D" if "precision" in name else "o",
                       edgecolor=SURF, linewidth=1.6, zorder=5)
    ax.set_xlim(-0.01, 1.0)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("false-positive rate")
    ax.set_ylabel("true-positive rate (recall)")
    ax.set_title(title)
    ax.legend(loc="lower right", fontsize=7.4, handlelength=2.4)
    if inset:
        ins = ax.inset_axes([0.40, 0.36, 0.52, 0.34])
        for c in curves:
            col, ls = style_for(c["arm"])
            ins.plot([p["fpr"] for p in c["points"]], [p["tpr"] for p in c["points"]], color=col, linestyle=ls, linewidth=1.6)
        if ops:
            for name, pt in ops.items():
                col = ORANGE if "Clocked" in name else BLUE
                ins.scatter([pt["fpr"]], [pt["tpr"]], s=26, color=col, marker="D" if "precision" in name else "o",
                            edgecolor=SURF, linewidth=1, zorder=5)
                short = {"Clocked default verdict": "as shipped", "AgentAudit frozen (consensus)": "AgentAudit",
                         "AgentAudit precision mode": "precision"}.get(name, name)
                ins.annotate(short, (pt["fpr"], pt["tpr"]), xytext={"as shipped": (-14, -13), "AgentAudit": (5, -24), "precision": (5, -13)}.get(short, (5, -13)),
                             textcoords="offset points", fontsize=7, color=INK)
        ins.set_xlim(-0.005, 0.3)
        ins.set_ylim(0.6, 1.01)
        ins.tick_params(labelsize=7)
        ins.set_xlabel("zoom: FPR 0–0.3 · dots = deployed operating points", fontsize=7, color=INK2)
        for s in ins.spines.values():
            s.set_edgecolor("#cfcdc6")


def scores_panel(ax, rows, key, title):
    rng = np.random.default_rng(3)
    for lab, yc, col in ((0, 0.0, "#8a8880"), (1, 1.0, ORANGE if key == "p_default" else BLUE)):
        vals = np.array([r[key] for r in rows if r["label"] == lab])
        ax.scatter(vals, yc + rng.uniform(-0.28, 0.28, len(vals)), s=9, color=col, alpha=0.55, linewidth=0)
        med = np.median(vals)
        ax.plot([med, med], [yc - 0.36, yc + 0.36], color=INK, linewidth=1.6)
    ax.axvline(0.5, color=INK2, linestyle=(0, (3, 3)), linewidth=1)
    ben = np.array([r[key] for r in rows if r["label"] == 0])
    ax.text(0.99, 0.45, f"benign above 0.5: {np.mean(ben >= 0.5) * 100:.0f}%", ha="right", fontsize=8, color=INK,
            transform=ax.get_yaxis_transform())
    nb = sum(1 for r in rows if r["label"] == 0)
    na = sum(1 for r in rows if r["label"] == 1)
    ax.set_yticks([0, 1], [f"benign (n={nb})", f"poisoned (n={na})"])
    ax.set_ylim(-0.6, 1.5)
    ax.set_xlim(-0.02, 1.02)
    ax.set_xlabel("Guard injection probability  (bar = median, dashed = 0.5)")
    ax.set_title(title)
    ax.grid(axis="y", visible=False)


def forest_panel(ax, rows, suites, title):
    y, ticks, labels = 0.0, [], []
    for suite in suites:
        ax.text(50.5, y + 0.1, suite, fontsize=8.6, fontweight="bold", color=INK, ha="left", va="bottom")
        y -= 0.75
        for r in [r for r in rows if r["suite"] == suite]:
            col = FAMILY.get(r["group"], INK2)
            lo, hi = r["bacc_ci"]
            ax.plot([lo, hi], [y, y], color=col, linewidth=2.2)
            ax.scatter([r["bacc"]], [y], s=34, color=col, edgecolor=SURF, linewidth=1.2, zorder=4)
            ax.text(min(hi + 0.8, 101.5), y, f"{r['bacc']:.1f}", va="center", fontsize=7.6, color=INK)
            ticks.append(y)
            labels.append(r["arm"])
            y -= 0.6
        y -= 0.5
    ax.set_yticks(ticks, labels, fontsize=7.8)
    ax.set_ylim(y + 0.3, 0.9)
    ax.set_xlim(50, 104)
    ax.set_xlabel("balanced accuracy, %  (dot and 95% bootstrap CI; 50 = chance)")
    ax.set_title(title)
    ax.grid(axis="y", visible=False)


def fig_hero():
    fig = plt.figure(figsize=(17, 5.8))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.05, 1.0, 1.1], wspace=0.78)
    ax1 = fig.add_subplot(gs[0])
    roc_panel(ax1, D["roc"]["test"]["curves"], D["roc"]["test"]["operating_points"], "a  ROC: poisoned MCP tools (test, n=253)")
    sub = gs[1].subgridspec(2, 1, hspace=0.95)
    b1, b2 = fig.add_subplot(sub[0]), fig.add_subplot(sub[1])
    scores_panel(b1, D["score_dist"]["test"], "p_default", "b  Score distribution: Clocked as shipped")
    scores_panel(b2, D["score_dist"]["test"], "p_agentaudit", "    … with the AgentAudit policy")
    ax3 = fig.add_subplot(gs[2])
    forest_panel(ax3, D["forest"], ["Tool poisoning (test)", "Real-world tools (external)", "Malicious skills (test)"],
                 "c  Every arm on three suites")
    fig.suptitle("Same Clocked models, deployed with agent context: false alarms collapse while recall holds",
                 x=0.07, y=1.03, ha="left", fontsize=13.5, fontweight="bold")
    fig.text(0.07, -0.05, "Orange: Clocked as shipped  ·  Blue: Clocked + AgentAudit  ·  Aqua: open-source detectors "
             "(thresholds tuned on dev).  All numbers computed from released per-row records.", fontsize=8.4, color=INK2)
    for p in (OUT / "fig0_hero.png", ROOT / "docs/assets/hero.png"):
        fig.savefig(p, dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_roc_external_and_skills():
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.9), gridspec_kw={"wspace": 0.28})
    roc_panel(axes[0], D["roc"]["external"]["curves"], D["roc"]["external"]["operating_points"],
              "a  Never-seen data: 199 real tools + 25 published attacks")
    roc_panel(axes[1], D["skills_roc"], None, "b  Real malicious-skill campaign (test, n=244)", inset=False)
    fig.savefig(OUT / "fig1_roc_external_skills.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_calibration_sweep():
    fig, axes = plt.subplots(1, 3, figsize=(14.5, 4.1), gridspec_kw={"wspace": 0.32})
    ax = axes[0]
    ax.plot([0, 1], [0, 1], color="#bdbbb3", linestyle=(0, (2, 3)), linewidth=1)
    for arm, cal in D["calibration"].items():
        col = BLUE if "AgentAudit" in arm else ORANGE
        xs, ys, ns = ([b[k] for b in cal["bins"]] for k in ("mean_p", "frac_pos", "n"))
        ax.plot(xs, ys, color=col, linewidth=2, marker="o", markersize=4, label=f"{arm} (ECE {cal['ece']:.3f})")
        ax.scatter(xs, ys, s=[14 + n * 0.7 for n in ns], color=col, alpha=0.22, linewidth=0)
    ax.set_xlabel("mean predicted probability")
    ax.set_ylabel("fraction actually poisoned")
    ax.set_title("a  Calibration (marker area = rows per bin)")
    ax.legend(fontsize=7.6, loc="upper left")
    for i, key, lab, ttl in ((1, "bacc", "balanced accuracy, %", "b  Threshold sweep: accuracy"),
                             (2, "fpr", "false-positive rate, %", "c  Threshold sweep: false alarms")):
        ax = axes[i]
        for arm, rows in D["threshold_sweep"].items():
            ax.plot([r["t"] for r in rows], [r[key] for r in rows], color=BLUE if "AgentAudit" in arm else ORANGE,
                    linewidth=2, label=arm)
        ax.axvline(0.5, color=INK2, linestyle=(0, (3, 3)), linewidth=1)
        ax.set_xlabel("threshold on the injection probability")
        ax.set_ylabel(lab)
        ax.set_ylim(0, 102 if key == "bacc" else 100)
        ax.set_title(ttl)
        if i == 2:
            ax.legend(fontsize=7.6, loc="upper right")
    fig.text(0.07, -0.06, "Tuning the threshold cannot close the gap: even picked in hindsight on the test set, Clocked as shipped tops "
             "out near 88 balanced accuracy, while with the agent policy it stays at 93.9 or higher for every threshold from 0.2 to 1.\n"
             "The policy moves benign tool descriptions to low scores instead of shifting the cut-off. Thresholds here are swept on "
             "the test split for illustration only; the reported numbers use thresholds frozen on dev.", fontsize=8.2, color=INK2)
    fig.savefig(OUT / "fig2_calibration_sweep.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_by_source_precision():
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.3), gridspec_kw={"wspace": 0.6, "width_ratios": [1.35, 1]})
    ax = axes[0]
    nice = {"mcp_reference": "Reference MCP servers (test)", "injecagent": "InjecAgent tool specs (test)",
            "hard_negative": "Hand-written hard negatives (test)", "registry_real": "24 public MCP servers (external)",
            "mtp_pair": "Published benign originals (external)"}
    rows = D["by_source"]
    srcs = [(r["split"], r["source"]) for r in rows if r["arm"] == "Clocked Guard (default)"]
    for i, (sp, src) in enumerate(srcs):
        yv = len(srcs) - 1 - i
        for r in rows:
            if r["split"] == sp and r["source"] == src:
                aa = "AgentAudit" in r["arm"]
                col, off = (BLUE, -0.15) if aa else (ORANGE, 0.15)
                ax.plot(r["ci"], [yv + off] * 2, color=col, linewidth=2.2)
                ax.scatter([r["fpr"]], [yv + off], s=34, color=col, edgecolor=SURF, linewidth=1.2, zorder=4)
                ax.text(r["ci"][1] + 1, yv + off, f"{r['flagged']}/{r['n']}", va="center", fontsize=7.6, color=INK)
    ax.set_yticks(range(len(srcs))[::-1], [nice.get(s, s) for _, s in srcs], fontsize=8)
    ax.set_xlabel("benign items flagged, %  (Wilson 95% CI)")
    ax.set_xlim(-1, 80)
    ax.set_title("a  False alarms by benign source (orange: as shipped · blue: AgentAudit)")
    ax.grid(axis="y", visible=False)
    ax = axes[1]
    pc = D["precision_curve"]
    ax.plot([r["fpr"] for r in pc], [r["recall"] for r in pc], color=BLUE, linewidth=2, marker="o", markersize=4)
    tags = {0.0: "t=0 (default mode)", 0.05: "t=0.05", 0.3: "t=0.3 (precision mode)", 0.95: "t=0.95"}
    for r in pc:
        if r["t"] in tags:
            ax.annotate(tags[r["t"]], (r["fpr"], r["recall"]), xytext=(7, -2), textcoords="offset points", fontsize=7.8, color=INK)
    ax.set_xlabel("false-positive rate, %")
    ax.set_ylabel("recall, %")
    ax.set_xlim(-0.2, 3.6)
    ax.set_ylim(50, 100)
    ax.set_title("b  Precision mode: second-opinion threshold t")
    fig.savefig(OUT / "fig3_sources_precision.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_forest_all():
    fig, ax = plt.subplots(figsize=(8.8, 9.2))
    forest_panel(ax, D["forest"], ["Tool poisoning (test)", "Real-world tools (external)", "Scripts (test)", "Malicious skills (test)"],
                 "Every arm on every suite: balanced accuracy")
    fig.text(0.0, 0.01, "Orange: Clocked as shipped · Blue: AgentAudit · Aqua: open-source detectors (dev-tuned thresholds)",
             fontsize=8, color=INK2)
    fig.savefig(OUT / "fig4_forest.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_governance():
    g = D["governance"]
    defects = [("poisoned_tool", "poisoned\ntool"), ("malicious_script", "malicious\nscript"), ("embedded_secret", "embedded\nsecret"),
               ("duplicate", "duplicate\nagent"), ("none", "clean\nagent")]
    rows = [r for r in g["rows"] if r["key"] != "full_v1_inferred_owner"]
    M = np.array([[r["cells"][d][0] / r["cells"][d][1] for d, _ in defects] for r in rows])
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.4), gridspec_kw={"width_ratios": [2.4, 1], "wspace": 0.08})
    ax = axes[0]
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list("seq", ["#f2f6fc", "#a9c8f0", "#2a78d6", "#123f78"])
    ax.imshow(M, cmap=cmap, vmin=0, vmax=1, aspect="auto")
    for i, r in enumerate(rows):
        for j, (d, _) in enumerate(defects):
            k, n = r["cells"][d]
            ax.text(j, i, f"{k}/{n}", ha="center", va="center", fontsize=8.5, color="#ffffff" if M[i, j] > 0.55 else INK)
    ax.set_xticks(range(len(defects)), [d[1] for d in defects])
    ax.set_yticks(range(len(rows)), [r["arm"] for r in rows])
    ax.xaxis.tick_top()
    ax.grid(False)
    ax.axhline(2.5, color=INK, linewidth=1)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("a  Correct verdicts per defect type (38 held-out agents)", pad=40)
    ax = axes[1]
    accs = [r["acc"] for r in rows]
    cols = [BLUE if r["key"] in ("full", "precision") else ORANGE if r["key"] == "decide_only" else "#a9c8f0" for r in rows]
    ax.barh(range(len(rows)), accs, color=cols, height=0.6)
    for i, v in enumerate(accs):
        ax.text(v + 1, i, f"{v:.1f}", va="center", fontsize=8)
    ax.set_ylim(len(rows) - 0.5, -0.5)
    ax.set_yticks([])
    ax.set_xlim(0, 108)
    ax.set_xlabel("overall verdict accuracy, %")
    ax.set_title("b  Overall", pad=40)
    ax.grid(axis="y", visible=False)
    fig.text(0.02, -0.04, "Removing one endpoint blinds the audit to exactly its defect type (Guard → poisoned tools, Inspect → scripts, "
             "Protect → secrets, Compare → duplicates).\nOverall accuracy alone hides this: removing Guard also removes its false alarms "
             "on clean agents. Cells hold 3–19 agents; read them as counts, not rates.", fontsize=8, color=INK2)
    fig.savefig(OUT / "fig5_governance.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


def fig_ablation_latency():
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.0), gridspec_kw={"wspace": 0.42})
    ax = axes[0]
    ab = {r["arm"]: r for r in D["ablation"]}
    steps = [("Clocked\nas shipped", ab["Clocked policy + verdict rule"]), ("+ consensus\nrule only", ab["Clocked policy + consensus rule"]),
             ("+ agent policy\nonly", ab["AgentAudit policy + verdict rule"]), ("+ both\n(frozen)", ab["AgentAudit policy + consensus rule"])]
    for i, (lab, r) in enumerate(steps):
        col = ORANGE if i == 0 else BLUE if i == 3 else "#7fa9e3"
        ax.errorbar([i], [r["bacc"]], yerr=[[r["bacc"] - r["bacc_ci"][0]], [r["bacc_ci"][1] - r["bacc"]]], fmt="o", color=col,
                    ecolor=col, elinewidth=2.4, capsize=0, markersize=8)
        ax.text(i + 0.1, r["bacc"] - 0.4, f"{r['bacc']:.1f}\nFPR {r['fpr']:.1f}%", fontsize=8, va="center", color=INK)
    ax.set_xticks(range(4), [s[0] for s in steps], fontsize=8)
    ax.set_xlim(-0.4, 3.9)
    ax.set_ylim(75, 100.5)
    ax.set_ylabel("balanced accuracy, %  (95% CI)")
    ax.set_title("a  Ablation on the Guard test split: context does most of the work")
    ax = axes[1]
    lat = D["latency"]
    for i, l in enumerate(lat):
        ax.plot([l["p10"], l["p90"]], [i, i], color=INK2, linewidth=1.2)
        ax.plot([l["p25"], l["p75"]], [i, i], color=BLUE, linewidth=8, solid_capstyle="butt")
        ax.scatter([l["p50"]], [i], s=42, color=SURF, edgecolor=INK, zorder=4)
        ax.text(l["p90"] + 14, i, f"median {l['p50']} ms  (n={l['n']})", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(lat)), [l["endpoint"] for l in lat], fontsize=8.5)
    ax.set_xlim(200, 1050)
    ax.set_xlabel("round-trip latency, ms  (box p25–p75, whisker p10–p90)")
    ax.set_title("b  Latency per call through the public gateway")
    ax.grid(axis="y", visible=False)
    fig.savefig(OUT / "fig6_ablation_latency.png", dpi=170, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    for old in OUT.glob("*.png"):
        old.unlink()
    fig_hero()
    fig_roc_external_and_skills()
    fig_calibration_sweep()
    fig_by_source_precision()
    fig_forest_all()
    fig_governance()
    fig_ablation_latency()
    print("wrote", sorted(p.name for p in OUT.glob("*.png")))
