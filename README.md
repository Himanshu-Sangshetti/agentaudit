# AgentAudit

**A pre-deployment audit for AI agents (MCP servers, agent skills, assistant configs), built on [Clocked](https://clocked.rezolve.ai) decision models.**

Companies now build agents faster than they can govern them. AgentAudit reads everything an agent reads or runs: tool descriptions, system prompts, skill files, scripts and its README. In one call it returns:

- **Safety findings** with character-offset evidence: injected instructions, out-of-scope scripts, embedded secrets, and untrusted download prerequisites.
- **A registry record**: purpose, owner, write access, network reach, data sensitivity and blast radius.
- **Claim checks**: README promises ("read-only", "never sends data out") checked against the agent's actual tools.
- **Sprawl control**: near-duplicates of agents already in your registry, and a pointer to the one to reuse.
- **A governed verdict**: `approve` / `needs_owner` / `reuse_existing` / `quarantine`, with an autonomy tier that **policy sets, not the model**.

It ships as a CLI, a GitHub Action (SARIF in code scanning), a REST hook for agent-building platforms, and a web app.

> Not affiliated with or endorsed by Rezolve.ai. Built for the Clocked Build Challenge.

## Quickstart

```bash
uv tool install git+https://github.com/<you>/agentaudit   # or: pip install -e .
export CLOCKED_API_KEY=...                                 # server-side only

agentaudit scan ./my-mcp-server                            # local repo
agentaudit scan https://github.com/org/some-mcp-server     # shallow clone, nothing executed
agentaudit scan agent.yaml --registry ./approved-agents    # manifest + duplicate/reuse check
agentaudit scan . --format sarif --out agentaudit.sarif    # for GitHub code scanning
agentaudit usage                                           # credits spent, by experiment
```

Exit code 1 means a quarantine verdict or a finding at or above `--fail-on` (default `high`). That makes it a drop-in CI gate. A scan of a typical agent costs about 20–60 credits (well under a cent) and takes a few seconds.

**Web app:** `uv run uvicorn agentaudit.server:app --port 8000`. Judge mode shows recorded audits without spending credits. **GitHub Action:** see `action/` and `.github/workflows/agentaudit-example.yml`.

## How it works: every Clocked endpoint has one job

| Group | Endpoint | Job in the audit | Changes the output by |
|---|---|---|---|
| Safety | **Guard** `/injection` | Injected instructions in tool descriptions, skill files, READMEs. Agent-specific policy, with a separate policy for the agent's own system prompt | AA001 findings → quarantine |
| Safety | **Inspect** `/script` | Scripts, install hooks and skill code blocks, judged against the agent's declared scope | AA002 findings → quarantine |
| Safety | **Protect** `/pii` | Secrets and personal data in prompts and configs. Its spans also redact every other part of the report | AA003 findings, redaction |
| Documents | **Extract** `/extract` | Verbatim owner, systems reached, credentials, and the download targets a skill asks for (with offsets) | Supply-chain check, record |
| Documents | **Fill** `/fill` | The registry record (choice, score and yes/no fields) and the README's capability claims, verbatim | Record, Verify input |
| Documents | **Decide** `/decide` | Governance verdict and risk of acting. Untrusted-download judgment for skills | Verdict |
| Facts | **Verify** `/grounding` | Each README claim checked against machine-extracted capability facts | AA004 findings |
| Facts | **Compare** `/compare` | Duplicate and overlapping agents across the registry | `reuse_existing` (with Rerank) |
| Facts | **Rerank** `/rerank` | "Is there already an agent for this?" over the registry | `reuse_existing` (with Compare) |

Design rules we kept to:
1. **Decision rules are measured, not guessed.** Each endpoint's flag rule was chosen on a dev split and frozen before testing (`bench/PROTOCOL.md`).
2. **Two signals for consequential calls.** "Reuse X" needs both Compare (duplicate) and Rerank (serves the purpose).
3. **Authority comes from policy.** Autonomy is computed from the verdict and the agent's write access, never asked of the model. In the words of Rezolve.ai's CEO: "AI provides intelligence. Policy defines authority."
4. **Never echo a secret.** Protect's findings redact every other field.

## Evidence: AgentAudit-Bench

The first independent benchmark of Clocked's Guard and Inspect endpoints, run with Clocked's own methodology:
- the same rows for every arm
- balanced accuracy and AUROC
- exact McNemar with Holm correction
- 95% stratified bootstrap CIs

Full tables, ablations and per-source breakdowns are in **[bench/RESULTS.md](bench/RESULTS.md)**. The pre-registered protocol and disclosed threats are in **[bench/PROTOCOL.md](bench/PROTOCOL.md)**.

| Suite (held-out) | Clocked default | Clocked + AgentAudit | Notes |
|---|---|---|---|
| Harness check: jev-benchmark (868) | 507/868 | — | Matches Clocked's published 507/868 exactly |
| Tool poisoning, test (253) | 84.9 BAcc · 25.9% FPR | **97.6 · 2.2% FPR** | p = 9×10⁻⁸. The policy does most of the work, the rule the rest |
| Tool poisoning, external (249) | 88.4 · 23.2% FPR | **97.3 · 5.4% FPR** | Real-world benign MCP tools + published attacks, never used for design |
| Scripts, test (206) | 84.4 | **89.9** | Change scope turns 50% (chance) into 79% on scope pairs |
| Malicious skills, real campaign | see RESULTS.md | see RESULTS.md | New Extract + Decide supply-chain check |

Open-source baselines (ProtectAI and deepset DeBERTa, keyword regex) are in every table. They're scored both at their standard threshold and at a threshold tuned on dev, to match the tuning our configuration got.

**Reproduce:** every Clocked response is cached, so `uv run python bench/report.py` regenerates every number without spending credits. Raw runs: `bench/suites/run_*.py`. Credit ledger: `bench/credit_ledger.jsonl`.

## Integrating with an agent platform

Agent builders such as Agentic Studio can call AgentAudit at the moment an agent is created or changed:

```python
from agentaudit.clocked import Clocked
from agentaudit.collect import collect_manifest
from agentaudit.audit import Auditor

with Clocked(tag="studio-gate", budget=100) as c:
    report = Auditor(c).run(collect_manifest("agent.yaml"), registry=[(name, facts), ...])
if report.verdict["verdict"]["choice"] != "approve":
    block_publish(report)
```

The manifest format is platform-neutral YAML: `name`, `owner`, `purpose`, `instructions`, `tools[]`, `scripts[]`, `readme` (see `examples/`).

## Repository map

```
src/agentaudit/   clocked.py (client: cache, retries, per-experiment budgets) · collect.py · audit.py · render.py · cli.py · server.py
bench/            PROTOCOL.md · RESULTS.md · report.py · metrics.py · suites/ · baselines/ · results/ (per-row records)
web/ action/      web app · GitHub Action
examples/         synthetic demo agents and a demo registry
tests/            offline tests (no network)
```

## Data and licenses

Code: MIT. Benchmark rows we wrote (hard negatives, scope pairs) are CC-BY-4.0. Third-party data:
- jev-benchmark (MIT)
- MCPTox (no license: IDs and predictions only, no text redistributed)
- InjecAgent (MIT)
- reference MCP servers (MIT)
- Atomic Red Team (MIT)
- lazywinadmin/PowerShell (MIT)
- agent-skill-malware (MIT)
- mcp-tool-poisoning (Apache-2.0)
- public MCP registry repos (MIT/Apache/BSD; see `data/raw/registry_benign/README.md`)

Findings from scanning public projects are reported only in aggregate.
