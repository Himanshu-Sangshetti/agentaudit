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
uv tool install git+https://github.com/Himanshu-Sangshetti/agentaudit
export CLOCKED_API_KEY=...                                 # server-side only

agentaudit demo                                            # try it in 10 seconds: recorded audits, no key needed
agentaudit estimate ./my-mcp-server                        # credit estimate, no API calls
agentaudit scan ./my-mcp-server                            # local repo
agentaudit scan https://github.com/org/some-mcp-server     # shallow clone, nothing executed
agentaudit scan agent.yaml --registry ./approved-agents    # manifest + duplicate/reuse check
agentaudit scan . --format sarif --out agentaudit.sarif    # for GitHub code scanning
agentaudit scan ./agent --precision                        # fewer false flags (Decide second opinion)
agentaudit usage                                           # credits spent, by experiment
```

Exit code 1 means a quarantine verdict or a finding at or above `--fail-on` (default `high`). That makes it a drop-in CI gate. A typical agent audit costs about 20–90 credits (roughly 0.4–2 US cents); run `agentaudit estimate` first to see the cost.

**Web app:** `uv run uvicorn agentaudit.server:app --port 8000`. Judge mode shows recorded audits without spending credits. **GitHub Action:** see `action/` and `.github/workflows/agentaudit-example.yml`.

## How it works: every Clocked endpoint has one job

| Group | Endpoint | Job in the audit | Changes the output by |
|---|---|---|---|
| Safety | **Guard** `/injection` | Injected instructions in tool descriptions, skill files, READMEs. Agent-specific policy, with a separate policy for the agent's own system prompt | AA001 findings → quarantine |
| Safety | **Inspect** `/script` | Scripts, install hooks and skill code blocks, judged against the agent's declared scope | AA002 findings → quarantine |
| Safety | **Protect** `/pii` | Secrets and personal data in prompts and configs. Its spans also redact every other part of the report | AA003 findings, redaction |
| Documents | **Extract** `/extract` | Verbatim owner, systems reached, credentials, and the download targets a skill asks for (with offsets) | Supply-chain check, record |
| Documents | **Fill** `/fill` | The registry record (choice, score and yes/no fields) and the README's capability claims, verbatim | Record, Verify input |
| Documents | **Decide** `/decide` | Governance verdict and risk of acting. Untrusted-download judgment (AA005, with Extract). Second opinion in `--precision` mode | Verdict, AA005 |
| Facts | **Verify** `/grounding` | Each README claim checked against machine-extracted capability facts | AA004 findings |
| Facts | **Compare** `/compare` | Duplicate and overlapping agents across the registry | `reuse_existing` (with Rerank) |
| Facts | **Rerank** `/rerank` | "Is there already an agent for this?" over the registry | `reuse_existing` (with Compare) |

Design rules we kept to:
1. **Decision rules are measured, not guessed.** Each endpoint's flag rule was chosen on a dev split and frozen before testing (`bench/PROTOCOL.md`).
2. **Two signals for consequential calls.** "Reuse X" needs both Compare (duplicate) and Rerank (serves the purpose).
3. **Authority comes from policy.** Autonomy is computed from the verdict and the agent's write access, never asked of the model. In the words of Rezolve.ai's CEO: "AI provides intelligence. Policy defines authority."
4. **Never echo a secret.** Protect's findings redact every other field.

## Evidence: AgentAudit-Bench

To our knowledge, the first independent benchmark of Clocked's Guard and Inspect endpoints, run with Clocked's own methodology:
- the same rows for every arm
- balanced accuracy and AUROC
- exact McNemar with Holm correction
- 95% stratified bootstrap CIs

Full tables, ablations and per-source breakdowns are in **[bench/RESULTS.md](bench/RESULTS.md)**. The pre-registered protocol and disclosed threats are in **[bench/PROTOCOL.md](bench/PROTOCOL.md)**.

| Suite (held-out) | Clocked default | Clocked + AgentAudit | Notes |
|---|---|---|---|
| Harness check: jev-benchmark (868) | 507/868 | — | Matches Clocked's published 507/868 exactly |
| Tool poisoning, test (253) | 84.9 BAcc · 25.9% FPR | **97.6 · 2.2% FPR** | Holm p = 1.9×10⁻⁷. The policy does most of the work, the rule the rest |
| Tool poisoning, external (249) | 88.4 · 23.2% FPR | **97.3 · 5.4% FPR** | Real-world benign MCP tools + published attacks, never used for design |
| Scripts, test (206) | 84.4 (87.4 with a tuned threshold, n.s.) | **89.9** | The gain is scope: 50% (chance) → 79% on scope pairs |
| Malicious skills, real campaign (244) | 72.9 (best single endpoint) | **88.6** · 3.2% FPR | New Extract + Decide supply-chain check: recall 48% → 81% |
| Governance verdicts, held-out agents (38) | 60.5 (one Decide call) | **78.9** · **89.5** in `--precision` | Each safety endpoint and Compare is necessary for its own defect type (cells of 3–9 agents). Owner rule v2 is post hoc and disclosed (v1: 65.8) |
| Real-world: 9 public MCP repos | — | 0 false quarantines in `--precision` (2 in default) | Hand-verified, aggregate only (`bench/REALWORLD.md`) |

**Which mode?** Use `--precision` to gate a registry of mostly reputable agents. The default is the maximum-recall setting for CI on untrusted code. Full write-up: [docs/REPORT.md](docs/REPORT.md).

Open-source baselines (ProtectAI and deepset DeBERTa, keyword regex) are in the Guard tables. They're scored both at their standard threshold and at a threshold tuned on dev, to match the tuning our configuration got.

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

## Security & data handling

- **What is sent to Clocked.** Only the text of an agent's artifacts: tool descriptions, instructions and skill files, READMEs, configs and scripts, plus short summaries AgentAudit builds from them (capability facts, a findings summary for Decide). Each request goes over HTTPS to `clocked.rezolve.ai`. Clocked's own data handling is documented at https://clocked.rezolve.ai/docs/security.
- **Nothing is executed.** Repositories are shallow-cloned and read as text. Install hooks, scripts, `package.json` lifecycle scripts and code blocks are sent to Inspect as data, never run. The one exception is opt-in: `collect_live` starts an MCP server command *you* supply, to read its `tools/list`.
- **Keys stay server-side.** `CLOCKED_API_KEY` is read from the environment or a local `.env` (git-ignored). The web service never sends it to the browser, and the Docker image takes it at runtime (`-e CLOCKED_API_KEY=...`). The GitHub Action reads it from a repository secret.
- **Redaction.** Every value Protect finds (secrets, tokens, personal data) is masked everywhere in the report: evidence quotes, Extract output, the registry record, and the Markdown/JSON/SARIF output. The web API also scrubs the artifact text it returns for highlighting. Reports never echo a secret back.
- **Spend limits.** Every scan has a credit budget (`--budget`; the web service caps each request at 60 credits and each day at `AGENTAUDIT_DAILY_CREDITS`, plus a per-IP rate limit). `agentaudit estimate` predicts cost without calling the API, and responses are cached on disk (`.cache/`) so re-running a scan costs nothing.
- **Local state.** The response cache (`.cache/clocked/`) and the credit ledger contain the text that was sent and the results. Delete `.cache/` to remove them.
