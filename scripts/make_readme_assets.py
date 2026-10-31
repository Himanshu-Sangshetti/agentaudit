"""Generate the README assets from repository data. No API calls, no credits.

  (hero figure: see bench/figures.py)
  docs/assets/terminal.svg  real CLI output (`agentaudit demo payroll-helper`, a recorded report)
  docs/assets/pipeline.svg  architecture diagram

Run: uv run --group bench python scripts/make_readme_assets.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from rich.console import Console  # noqa: E402
from rich.markdown import Markdown  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/assets"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE = "#2a78d6", "#eb6834"  # AgentAudit / Clocked as shipped
CARD, INK, INK2, GRID = "#ffffff", "#0b0b0b", "#52514e", "#e6e5e0"


# --- hero ----------------------------------------------------------------------

def arm(rows, name):
    return next(r for r in rows if r["arm"] == name)


def hero():
    d = json.loads((ROOT / "docs/site/data.json").read_text())
    gt, ge, sk = d["guard_test"], d["guard_external"], d["skills"]
    gov = {r["arm"]: r["acc"] for r in d["governance"]["rows"]}
    panels = [
        ("Poisoned MCP tools", "false alarms on benign tools (lower is better)",
         f"held-out test, n={arm(gt, 'Clocked Guard (default)')['n']}\nbalanced accuracy "
         f"{arm(gt, 'Clocked Guard (default)')['bacc']} → {arm(gt, 'Clocked + AgentAudit')['bacc']}",
         [("Clocked Guard, as shipped", arm(gt, "Clocked Guard (default)")["fpr"], ORANGE),
          ("Clocked + AgentAudit", arm(gt, "Clocked + AgentAudit")["fpr"], BLUE)], 30),
        ("Real-world MCP tools", "false alarms (lower is better)",
         f"199 tools, 24 public servers, never seen\nin design · attacks caught: "
         f"{arm(ge, 'Clocked + AgentAudit')['recall']:.0f}%",
         [("Clocked Guard, as shipped", arm(ge, "Clocked Guard (default)")["fpr"], ORANGE),
          ("Clocked + AgentAudit", arm(ge, "Clocked + AgentAudit")["fpr"], BLUE)], 30),
        ("Real malware campaign", "malicious skills caught (higher is better)",
         f"Feb 2026 ClawHub skills, test n={arm(sk, 'AgentAudit pipeline')['n']}\nfalse alarms: "
         f"{arm(sk, 'AgentAudit pipeline')['fpr']}%",
         [("Best single Clocked endpoint", arm(sk, "Clocked Inspect (default)")["recall"], ORANGE),
          ("AgentAudit pipeline", arm(sk, "AgentAudit pipeline")["recall"], BLUE)], 100),
        ("Governance verdicts", "correct verdict (higher is better)",
         f"{d['governance']['n']} held-out agents\n4 verdict classes",
         [("One Decide call", gov["One Decide call"], ORANGE),
          ("Full audit", gov["Full audit"], BLUE),
          ("Full audit, precision mode", gov["Full audit, precision mode"], BLUE)], 100),
    ]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none"})
    fig, axes = plt.subplots(1, 4, figsize=(15, 3.6), gridspec_kw={"wspace": 0.55})
    fig.patch.set_facecolor(CARD)
    for ax, (title, metric, note, bars, xmax) in zip(axes, panels):
        ax.set_facecolor(CARD)
        ys = list(range(len(bars)))[::-1]
        for y, (label, val, color) in zip(ys, bars):
            ax.barh(y, val, color=color, height=0.58, edgecolor=CARD, linewidth=2)
            ax.text(val + xmax * 0.025, y, f"{val:.1f}%", va="center", fontsize=11, fontweight="bold", color=INK)
            ax.text(0, y + 0.42, label, va="bottom", fontsize=9, color=INK2)
        ax.set_xlim(0, xmax * 1.22)
        ax.set_ylim(-0.6, len(bars) - 0.1)
        ax.set_yticks([])
        ax.set_xticks([0, xmax / 2, xmax])
        ax.tick_params(axis="x", colors=INK2, labelsize=8, length=0)
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color(GRID)
        ax.set_title(title, loc="left", fontsize=12.5, fontweight="bold", color=INK, pad=24)
        ax.text(0, 1.035, metric, transform=ax.transAxes, fontsize=9, color=INK2)
        ax.text(0, -0.16, note, transform=ax.transAxes, fontsize=8.5, color=INK2, va="top", linespacing=1.5)
    fig.text(0.125, 1.17, "Same Clocked models, deployed with agent context", fontsize=15, fontweight="bold", color=INK)
    fig.text(0.125, 1.09, "■", color=ORANGE, fontsize=13)
    fig.text(0.138, 1.09, "Clocked as shipped (or a single Decide call)", color=INK2, fontsize=10)
    fig.text(0.36, 1.09, "■", color=BLUE, fontsize=13)
    fig.text(0.373, 1.09, "Clocked + AgentAudit", color=INK2, fontsize=10)
    fig.savefig(OUT / "hero.svg", bbox_inches="tight", pad_inches=0.35, facecolor=CARD)
    fig.savefig(OUT / "hero.png", bbox_inches="tight", pad_inches=0.35, facecolor=CARD, dpi=150)
    plt.close(fig)


# --- terminal ------------------------------------------------------------------

def terminal():
    rep = json.loads((ROOT / "examples/reports/payroll-helper.json").read_text())
    md = rep["markdown"]
    md = md.split("## Existing agents for the same job")[0].rstrip()  # keep the capture compact
    import io
    console = Console(record=True, width=104, force_terminal=True, color_system="truecolor", file=io.StringIO())
    console.print("[bold green]$[/bold green] agentaudit demo payroll-helper")
    console.print(Markdown(md))
    svg = console.export_svg(title="agentaudit demo payroll-helper")
    planted = ["payroll_svc_tok", "priya.nair", "Priya Nair", "555 0134", "payroll-backup.example.net"]
    leaked = [p for p in planted if p in svg]
    if leaked:
        raise SystemExit(f"refusing to write terminal.svg: planted values visible: {leaked}")
    (OUT / "terminal.svg").write_text(svg)


# --- pipeline ------------------------------------------------------------------

def box(x, y, w, h, title, sub="", fill="#ffffff", stroke="#c9ced8", title_color=INK, rx=10):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
    s += f'<text x="{x + 14}" y="{y + 24}" font-size="14" font-weight="700" fill="{title_color}">{title}</text>'
    for i, line in enumerate(sub.split("\n") if sub else []):
        s += f'<text x="{x + 14}" y="{y + 44 + 17 * i}" font-size="12" fill="{INK2}">{line}</text>'
    return s


def arrow(x1, y1, x2, y2):
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#8a909c" stroke-width="1.6" '
            f'marker-end="url(#a)"/>')


def pipeline():
    W, H = 1180, 470
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
             'font-family="-apple-system, Segoe UI, Helvetica, Arial, sans-serif">',
             '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
             'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#8a909c"/></marker></defs>',
             f'<rect width="{W}" height="{H}" rx="16" fill="#fbfbfa" stroke="#e3e5ea"/>']
    # inputs
    parts.append(box(24, 120, 200, 230, "Agent", "MCP server repo\nagent skill (SKILL.md)\nmanifest / Studio-style\nagent: role + MCP\nservers, overrides\n\nnothing is executed",
                     fill="#ffffff"))
    parts.append(arrow(226, 235, 262, 235))
    # endpoint groups
    gx, gw = 266, 300
    groups = [(28, "Safety", "Guard · injected instructions\nInspect · scripts vs scope\nProtect · secrets, redaction", "#eef4fc", BLUE),
              (168, "Documents", "Extract + Decide · supply chain\nFill · registry record, claims\nDecide · verdict, 2nd opinion", "#fdf1ec", ORANGE),
              (308, "Fact-check", "Verify · claims vs capabilities\nCompare · duplicate agents\nRerank · what to reuse", "#eaf7f1", "#127a55")]
    for y, title, sub, fill, color in groups:
        parts.append(box(gx, y, gw, 126, title, sub, fill=fill, stroke=color, title_color=color))
        parts.append(arrow(gx + gw + 2, y + 63, 610, 235))
    parts.append(f'<text x="{gx}" y="20" font-size="12" fill="{INK2}">nine Clocked endpoints, one job each</text>')
    # policy layer
    parts.append(box(614, 150, 220, 170, "Policy layer", "owner from registry\nautonomy set by policy,\nnot the model\nreuse needs Compare\n+ Rerank to agree",
                     fill="#ffffff", stroke="#2b2f36"))
    parts.append(arrow(836, 235, 872, 235))
    # outputs
    outs = [(40, "Verdict", "approve · needs owner\nreuse existing · quarantine"),
            (150, "Per-tool enablement", "enable · review · keep disabled\n(tools start disabled)"),
            (260, "Evidence + escalation", "character offsets, SARIF,\nhuman-approval item")]
    for y, t, s in outs:
        parts.append(box(876, y, 280, 96, t, s))
    parts.append(f'<text x="876" y="{H - 40}" font-size="13" font-weight="700" fill="{INK}">Ships as</text>')
    parts.append(f'<text x="876" y="{H - 20}" font-size="12" fill="{INK2}">CLI · GitHub Action · REST hook · web app</text>')
    parts.append(f'<text x="24" y="{H - 20}" font-size="12" fill="{INK2}">AgentAudit pipeline. Every finding cites the '
                 'exact text it came from.</text>')
    parts.append("</svg>")
    (OUT / "pipeline.svg").write_text("".join(parts))


if __name__ == "__main__":
    # The hero figure now comes from bench/figures.py (docs/assets/hero.png): ROC, score distributions, forest plot.
    terminal()
    pipeline()
    print("wrote", sorted(p.name for p in OUT.iterdir()))
