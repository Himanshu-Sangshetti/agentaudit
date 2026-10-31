"""Render a Report as Markdown, SARIF 2.1.0 (GitHub code scanning) or JSON."""

from __future__ import annotations

import json

from .audit import SEVERITY_RANK, Report

SARIF_LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "none": "note"}
RULES = {
    "guard": ("AA001", "Injected instructions in agent-readable text"),
    "inspect": ("AA002", "Script behaviour outside the agent's declared scope"),
    "protect": ("AA003", "Secret or personal data embedded in agent configuration"),
    "verify": ("AA004", "Capability claim contradicted by the agent's actual tools"),
    "supply_chain": ("AA005", "Untrusted download or execution prerequisite"),
}


def _answer(v):
    if not isinstance(v, dict):
        return v
    if "choice" in v:
        return v["choice"]
    if "value" in v:
        return v["value"]
    if "score" in v:
        return round(v["score"], 2)
    return v


def verdict_of(rep: Report) -> str:
    return _answer(rep.verdict.get("verdict", {})) or "unknown"


def to_markdown(rep: Report) -> str:
    v = rep.verdict
    lines = [f"# AgentAudit: {rep.agent}", "",
             f"**Verdict:** `{verdict_of(rep)}`"
             + (f" ({v['verdict'].get('confidence', 0):.0%} confidence)" if isinstance(v.get("verdict"), dict) else ""),
             f"**Autonomy:** `{_answer(v.get('autonomy', {}))}`  ·  **Risk of acting:** "
             f"{_answer(v.get('risk_of_acting', {}))} / 4", ""]
    lines += ["## Registry record", "", "| Field | Value |", "|---|---|"]
    for k, val in rep.record.items():
        lines.append(f"| {k} | {_answer(val) if _answer(val) not in (None, '') else '—'} |")
    lines += ["", f"## Findings ({len(rep.findings)})", ""]
    if not rep.findings:
        lines.append("No findings.")
    for f in rep.findings:
        lines.append(f"- **{f.severity.upper()}** · {RULES.get(f.check, (f.check,))[0]} · {f.title} — `{f.path}`")
        for e in f.evidence[:3]:
            lines.append(f"  - > {e['quote'][:200]}")
    if rep.duplicates:
        lines += ["", "## Overlapping agents", ""] + [f"- {d['agent']} ({d['relation']})" for d in rep.duplicates]
    if rep.reuse:
        lines += ["", "## Existing agents for the same job", ""] + [
            f"- {r['agent']}: {r['action']} (score {r['score']:.2f})" for r in rep.reuse if r.get("score") is not None]
    u = rep.usage
    lines += ["", f"<sub>{u.get('calls', 0)} Clocked calls · {u.get('credits', 0):.0f} credits · "
                  f"${u.get('cost_usd', 0):.4f}</sub>"]
    return "\n".join(lines)


def to_sarif(reports: list[Report]) -> dict:
    results, used = [], {}
    for rep in reports:
        for f in rep.findings:
            if f.check not in RULES or f.severity == "none":
                continue
            rid, desc = RULES[f.check]
            used[rid] = desc
            path = f.path.split("::")[0].split("#")[0]
            results.append({
                "ruleId": rid, "level": SARIF_LEVEL.get(f.severity, "warning"),
                "message": {"text": f"{f.title}: " + "; ".join(e["quote"][:120] for e in f.evidence[:2])},
                "locations": [{"physicalLocation": {"artifactLocation": {"uri": path}}}],
                "properties": {"agent": rep.agent, "severity": f.severity, "check": f.check},
            })
    return {"version": "2.1.0", "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
            "runs": [{"tool": {"driver": {"name": "AgentAudit", "informationUri": "https://github.com/",
                                          "rules": [{"id": k, "shortDescription": {"text": v}} for k, v in used.items()]}},
                      "results": results}]}


def to_json(rep: Report) -> str:
    return json.dumps(rep.to_dict(), indent=2)


def exit_code(reports: list[Report], fail_on: str) -> int:
    """Non-zero when any report is quarantined or has a finding at or above fail_on."""
    floor = SEVERITY_RANK.get(fail_on, 3)
    for r in reports:
        if verdict_of(r) == "quarantine" or any(SEVERITY_RANK.get(f.severity, 0) >= floor for f in r.findings):
            return 1
    return 0
