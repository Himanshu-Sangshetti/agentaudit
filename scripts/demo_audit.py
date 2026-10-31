import json, sys
from agentaudit.clocked import Clocked
from agentaudit.collect import collect_manifest, collect_repo
from agentaudit.audit import Auditor, capability_facts

targets = [collect_manifest("examples/payroll-helper.yaml"),
           collect_repo("data/raw/mcp/official-servers/src/filesystem"),
           collect_repo("data/raw/mcp/official-servers/src/memory")]
registry = [(a.name, capability_facts(a)) for a in targets]
with Clocked() as c:
    aud = Auditor(c)
    for a in targets:
        rep = aud.run(a, registry)
        print("=" * 70, "\n", a.name, "worst:", rep.worst)
        for f in rep.findings:
            print(f"  [{f.severity}] {f.check}: {f.title} @ {f.path} :: {[e['quote'][:90] for e in f.evidence][:2]}")
        print("  record:", {k: (v.get('value') if isinstance(v, dict) else v) for k, v in rep.record.items()})
        print("  verdict:", {k: (v.get('choice'), v.get('confidence')) if 'choice' in v else round(v.get('score',0),2) for k, v in rep.verdict.items()})
        print("  dup:", rep.duplicates, "reuse:", rep.reuse[:2])
        json.dump(rep.to_dict(), open(f"examples/report-{a.name}.json", "w"), indent=1)
    print("usage", c.usage.credits, c.usage.calls)
