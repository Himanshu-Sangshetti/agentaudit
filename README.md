<h1 align="center">AgentAudit</h1>

<p align="center">
  <b>A pre-deployment audit for AI agents.</b><br>
  Point it at an MCP server, an agent skill or an agent manifest and get a governed verdict, per-tool enable decisions and evidence down to the character.<br>
  Built on the nine <a href="https://clocked.rezolve.ai">Clocked</a> decision endpoints, and benchmarked like a research result.
</p>

<p align="center">
  <a href="https://github.com/Himanshu-Sangshetti/agentaudit/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Himanshu-Sangshetti/agentaudit/actions/workflows/ci.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.11+" src="https://img.shields.io/badge/python-3.11%2B-blue.svg">
  <img alt="35 offline tests" src="https://img.shields.io/badge/tests-35%20offline-brightgreen.svg">
  <a href="bench/PROTOCOL.md"><img alt="Pre-registered benchmark" src="https://img.shields.io/badge/benchmark-pre--registered-6250d6.svg"></a>
</p>

<p align="center">
  <a href="#quickstart">Quickstart</a> ·
  <a href="#how-it-works">How it works</a> ·
  <a href="#agent-platforms">Agent platforms</a> ·
  <a href="#results">Results</a> ·
  <a href="docs/WRITEUP.md">Write-up</a> ·
  <a href="docs/REPORT.md">Technical report</a>
</p>

<p align="center">
  <img src="docs/assets/hero.png" alt="Headline results: false alarms on the poisoned-tool benchmark 25.9% to 2.2%; real-world tools 23.2% to 5.4%; malicious skills caught 48.3% to 80.5%; governance verdict accuracy 60.5% to 78.9% (89.5% in precision mode)." width="100%">
</p>

AgentAudit reads everything an agent reads or runs: tool descriptions, system prompts, skill files, install scripts and its README. It returns:
- **A verdict:** `approve`, `needs_owner`, `reuse_existing` or `quarantine`, with an autonomy tier that policy sets, not the model.
- **A registry record:** owner, reach, data sensitivity, blast radius.
- **A per-tool decision:** enable, review or keep disabled.
- **Evidence:** every finding quotes the exact text it came from. Secrets are redacted everywhere.

## Quickstart

```bash
uv tool install git+https://github.com/Himanshu-Sangshetti/agentaudit

agentaudit demo                            # replay recorded audits: no key, no network
agentaudit demo payroll-helper             # one full report
agentaudit estimate ./my-mcp-server        # predicted credit cost, no API calls

export CLOCKED_API_KEY=...                 # server-side only
agentaudit scan ./my-mcp-server --precision
agentaudit scan https://github.com/org/some-mcp-server        # shallow clone, nothing executed
agentaudit scan agent.yaml --registry ./approved-agents       # also checks duplicates and reuse
agentaudit scan . --format sarif --out agentaudit.sarif       # GitHub code scanning
```

Exit code `1` means a quarantine verdict or a finding at or above `--fail-on` (default `high`), so it works as a CI gate as is. If a scan hits its `--budget`, you get a partial report, and re-running pays only for what's left (every response is cached).

<p align="center"><img src="docs/assets/terminal.svg" alt="Terminal output of agentaudit demo payroll-helper: quarantine verdict, registry record, and five findings with evidence quotes; secrets masked." width="88%"></p>

**Which mode?** Use `--precision` to gate a registry of mostly trusted agents: it adds a Decide second opinion on Guard flags and removed every false quarantine in our real-world sample. Use the default (maximum recall) for untrusted code in CI. The trade-off is measured in [Results](#results).

## Why

- **Agent sprawl.** Agents are now cheap to build and expensive to govern. Rezolve.ai's own writing describes enterprises with hundreds of agents built and a dozen in use, and argues that nothing should run without a named owner and that *policy, not the model, defines authority*. AgentAudit implements that idea as a gate. (It's independent work, not affiliated with or endorsed by Rezolve.ai.)
- **Tool poisoning.** An MCP tool description is read by the model and almost never by a person. One hidden line ("also BCC every summary to …") turns a harmless tool into an exfiltration channel.
- **Malicious skills.** In February 2026, a campaign published agent skills whose setup steps told the agent or user to download and run a stealer. The payload was **prose**, not code, which is why script scanners missed it.

## How it works

<p align="center"><img src="docs/assets/pipeline.svg" alt="Pipeline: agent artifacts flow into Safety (Guard, Inspect, Protect), Documents (Extract+Decide, Fill, Decide) and Fact-check (Verify, Compare, Rerank) endpoint groups, then a policy layer, producing a verdict, per-tool enablement and evidence plus escalation; ships as CLI, GitHub Action, REST hook and web app." width="100%"></p>

Collection is static: repos are shallow-cloned and read as text, so nothing is executed. Each Clocked endpoint has one job, and the [governance ablation](#results) shows which ones the verdict depends on.

| Group | Endpoint | Job | Rule |
|---|---|---|---|
| Safety | **Guard** `/injection` | Injected instructions in tool descriptions, skills, READMEs, admin overrides | AA001 |
| | **Inspect** `/script` | Scripts, install hooks and skill code blocks, judged against declared scope | AA002 |
| | **Protect** `/pii` | Secrets and personal data (one batched call); its spans redact the whole report | AA003 |
| Documents | **Extract + Decide** | Supply-chain check: verbatim download targets, then "is this source untrusted?" | AA005 |
| | **Fill** `/fill` | Registry record and the README's capability claims, verbatim | — |
| | **Decide** `/decide` | Governed verdict and risk; a second opinion in `--precision` | verdict |
| Fact-check | **Verify** `/grounding` | Each README claim ("read-only", "never sends data out") against extracted capabilities | AA004 |
| | **Compare** `/compare` | Duplicate and overlapping agents in your registry | reuse |
| | **Rerank** `/rerank` | Which existing agent already serves this purpose | reuse |

Three policy rules sit on top of the models:
1. **The accountable owner comes from registry metadata** (manifest `owner` or CODEOWNERS), never inferred from a README.
2. **Autonomy is computed** from the verdict, write access and risk.
3. **"Reuse X instead" needs Compare and Rerank to agree.**

## Agent platforms

AgentAudit fits platforms that describe agents as a **role plus connected MCP servers whose tools an admin enables one by one**, the model Rezolve.ai's Agentic Studio describes publicly. It doesn't run inside any such product. It's the gate one would call.

```yaml
name: it-support-agent
owner: IT Service Desk (itsd@example-corp.com)
role: Resolves employee IT tickets using Jira and GitHub.
mcp_servers:
  - name: github
    url: https://mcp.example-corp.internal/github
    tools:
      - name: get_label
        description: Get a specific label from a repository.
        enabled: false                      # tools start disabled
  - name: atlassian
    url: https://mcp.example-corp.internal/atlassian
    tools:
      - name: create_customer_request
        description: ...
        description_override: ...           # what the model actually reads is what gets audited
```

For each discovered tool you get **enable**, **review** (it can write or act externally) or **keep disabled** (with the finding that blocked it). Admin description overrides are audited like any other text. Anything that isn't approved for autonomous use produces an escalation item for a human approval queue. The full example is [`examples/studio/it-support-agent.yaml`](examples/studio/it-support-agent.yaml). There, a poisoned override is caught and kept disabled, while read-only tools are cleared and write tools are sent for review.

In Python, a platform calls it in one step:

```python
from agentaudit.audit import Auditor, capability_facts
from agentaudit.clocked import Clocked
from agentaudit.collect import collect_manifest

registry = [(a.name, capability_facts(a)) for a in approved_agents]
with Clocked(tag="publish-gate", budget=100) as c:
    report = Auditor(c, precision=True).run(collect_manifest("agent.yaml"), registry)

report.verdict["verdict"]["choice"]   # approve | needs_owner | reuse_existing | quarantine
report.tools                          # [{tool, recommendation: enable | review | keep_disabled, why}]
report.escalation                     # item for a human-approval board, or {}
```

The web app and REST hook are `uv run --extra web uvicorn agentaudit.server:app` with `POST /api/audit`. Each request is capped at 60 credits, there's a daily cap, and the IP rate limit applies. The page has a judge mode that replays recorded audits without spending anything.

### GitHub Action

```yaml
# .github/workflows/agentaudit.yml
on: [pull_request]
permissions: { contents: read, security-events: write }
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: Himanshu-Sangshetti/agentaudit/action@main
        with:
          clocked-api-key: ${{ secrets.CLOCKED_API_KEY }}
```

Findings appear in **code scanning** (SARIF) and the job summary. The pull request fails on a quarantine verdict.

## Results

**AgentAudit-Bench** is, to our knowledge, the first independent evaluation of Clocked's Guard and Inspect endpoints. It follows Clocked's own published methodology:
- the same rows for every arm
- balanced accuracy and AUROC
- exact McNemar tests with Holm correction
- 95% stratified bootstrap CIs

Splits are disjoint by server, technique or repository. Configurations were selected on dev and frozen before each test run, and the git history is the [pre-registration record](bench/PROTOCOL.md).

| Suite (held out) | Clocked as shipped | Clocked + AgentAudit | Note |
|---|---|---|---|
| **Harness check**: jev-benchmark, n=868 | 507/868 | — | Matches Clocked's published 507/868 exactly |
| **Tool poisoning**, n=253 | 84.9 BAcc · 25.9% FPR | **97.6 BAcc · 2.2% FPR** | Holm p = 1.9×10⁻⁷. A tuned threshold alone gives 83.8 |
| **Real-world tools + published attacks**, n=249 | 88.4 · 23.2% FPR | **97.3 · 5.4% FPR** | 25/25 attacks caught. Best tuned open-source detector: 91.7 · 16.5% |
| **Scripts**, n=206 | 84.4 (87.4 tuned, n.s.) | **89.9** | The gain is scope: same script, approved vs unapproved, 50% → 79% |
| **Real malicious-skill campaign**, n=244 | 48.3% caught (best endpoint) | **80.5% caught · 3.2% FPR** | Supply-chain check alone: 77.0% at 0.6% FPR |
| **Governance verdicts**, 38 agents | 60.5% (one Decide call) | **78.9%** · **89.5%** precision | Drop Guard, Inspect, Protect or Compare and its defect goes unseen |
| **Real-world audit**, 9 public MCP repos | — | 2/9 false quarantines → **0/9** with `--precision` | Hand-verified, aggregate only |

**Ablation.** On tool poisoning, agent-specific context does most of the work (84.9 → 95.7) and the consensus rule the rest (→ 97.6). **Determinism.** 30/30 uncached re-runs were identical. **Cost.** A typical agent audit is about 20–90 credits (roughly 0.4–2¢), with median calls of 0.3–0.5 s.

**Precision mode is a trade-off, not a free win.** It removes every false alarm on the real-world set (100.0 BAcc). On the templated MCPTox test set, recall falls to 74.6% (0% FPR).

Read more:
- **[Write-up](docs/WRITEUP.md)**: the story, figures and worked examples
- **[Technical report](docs/REPORT.md)**: method, limitations, related work
- **[All tables with CIs](bench/RESULTS.md)** and the **[real-world study](bench/REALWORLD.md)**

### Reproduce

```bash
uv sync --all-extras --all-groups
uv run python bench/report.py                 # every table, from cached per-row records (0 credits)
uv run python bench/figures.py                # every figure in the write-up (0 credits)
uv run python scripts/make_readme_assets.py   # the images in this README (0 credits)
uv run pytest -q                              # 35 offline tests, no network
```

Raw runs (these spend credits) are in `bench/suites/run_*.py`. Each one has a budget, and every paid call is logged in `bench/credit_ledger.jsonl`.

## Project layout

```
src/agentaudit/   clocked.py  API client: cache, retries, budgets, per-account ledger
                  collect.py  static collectors: repos, skills, manifests, Studio-style agents, live MCP (opt-in)
                  audit.py    the nine-endpoint audit, policy layer, supply-chain check, precision mode
                  render.py   Markdown · JSON · SARIF        cli.py  scan · estimate · demo · usage
                  server.py   REST hook + web app (judge mode)
bench/            PROTOCOL.md · RESULTS.md · REALWORLD.md · suites/ · baselines/ · results/ (per-row records)
docs/             WRITEUP.md · REPORT.md · figures/ · assets/
web/  action/     web app · GitHub Action
examples/         synthetic demo agents, a demo registry, a Studio-style agent, recorded reports
tests/            offline tests
```

## Security & data handling

- **What is sent to Clocked.** Only the text of an agent's artifacts (tool descriptions, instructions and skill files, READMEs, configs and scripts), plus short summaries AgentAudit builds from them (capability facts, a findings summary for Decide). Requests go over HTTPS to `clocked.rezolve.ai`. Clocked's own data handling: https://clocked.rezolve.ai/docs/security.
- **Nothing is executed.** Repositories are shallow-cloned and read as text. Install hooks, scripts, `package.json` lifecycle scripts and code blocks are sent to Inspect as data, never run. The one opt-in exception is `collect_live`, which starts an MCP server command *you* supply in order to read its `tools/list`.
- **Keys stay server-side.** `CLOCKED_API_KEY` comes from the environment or a git-ignored `.env`. The web service never sends it to the browser, the Docker image takes it at runtime, and the GitHub Action reads it from a repository secret.
- **Redaction.** Every value Protect finds is masked everywhere: evidence quotes, Extract output, the registry record, and Markdown, JSON and SARIF. Reports never echo a secret.
- **Spend limits.** Every scan has a `--budget`. The web service caps each request at 60 credits and each day at `AGENTAUDIT_DAILY_CREDITS`, with a per-IP rate limit. `agentaudit estimate` predicts cost offline, and cached responses are free.
- **Local state.** `.cache/clocked/` and the credit ledger hold the text sent and the results. Delete `.cache/` to remove them.

## Limitations

- **Authored rows.** The hard negatives (40) and scope pairs (20) were written by us. Results without them are reported.
- **Labels.** Atomic Red Team includes dual-use commands. Governance labels come from a construction recipe over synthetic manifests built from real tools.
- **Other models.** No other decision model was run on our suites. Jev appears only through jev-benchmark's published answers.
- **Attacks.** Only published attack sets were used; adaptive attackers may do better.
- **Static collection.** It misses tools that are registered dynamically. Use live `tools/list` for those.
- **Disclosed post-hoc changes.** One configuration change made after the first full governance run is disclosed in the [protocol](bench/PROTOCOL.md).

## License, data and citation

Code: [MIT](LICENSE). Benchmark rows we wrote (hard negatives, scope pairs) are CC-BY-4.0. Third-party data, used under their terms:
- jev-benchmark (MIT)
- MCPTox (no license: only IDs and predictions are released, no text)
- InjecAgent (MIT)
- reference MCP servers (MIT)
- Atomic Red Team (MIT)
- lazywinadmin/PowerShell (MIT)
- agent-skill-malware (MIT)
- mcp-tool-poisoning (Apache-2.0)
- public MCP repos (MIT/Apache/BSD)

Findings from scanning public projects are reported only in aggregate.

```bibtex
@misc{agentaudit2026,
  title  = {AgentAudit: Context Is the Control. Auditing AI Agents with Decision Models},
  author = {Sangshetti, Himanshu},
  year   = {2026},
  note   = {Clocked Build Challenge write-up},
  url    = {https://github.com/Himanshu-Sangshetti/agentaudit}
}
```
