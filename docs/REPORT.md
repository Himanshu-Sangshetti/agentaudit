# Context Is the Control: Auditing AI Agents with Decision Models

*Technical report, AgentAudit v0.1, November 2026. All numbers are regenerated from per-row records by `bench/report.py`; see `bench/RESULTS.md` for every table with 95% confidence intervals.*

## Abstract

Enterprises now deploy AI agents (MCP servers, agent skills and assistant configurations) faster than they can review them. We present **AgentAudit**, a pre-deployment audit that composes nine endpoints of the Clocked decision-model API into one governed verdict, and **AgentAudit-Bench**, to our knowledge the first independent evaluation of Clocked's Guard (prompt injection) and Inspect (script behaviour) endpoints on agent artifacts.

First, we validate our harness by reproducing Clocked's published decision benchmark exactly (507/868). We then measure how much of the accuracy comes from how the model is deployed:

1. **Tool poisoning.** On held-out MCP tool descriptions, agent-specific context and a consensus decision rule raise balanced accuracy from 84.9 to **97.6** and cut false positives from 25.9% to **2.2%** (Holm-adjusted McNemar p = 1.9×10⁻⁷). Tuning only Clocked's threshold gives no gain. On real-world tool descriptions never used for design, false positives fall from 23.2% to 5.4% at 100% recall.
2. **Scripts.** Supplying the approved change scope lets Inspect separate the same command under authorized and unauthorized scopes. Accuracy on these pairs rises from 50% (chance) to 79%. Without scope pairs the gain over a threshold-tuned default is small and not significant.
3. **Malicious skills.** On a real 2026 malware campaign, a new supply-chain check (Extract + Decide) raises balanced accuracy from 72.9 (best single endpoint) to **88.6** (recall 48.3% → 80.5%, false positives 3.2%).
4. **Governance.** On 38 held-out agents, the full audit reaches 78.9% verdict accuracy (89.5% in precision mode), against 60.5% for a single decision call. Leave-one-endpoint-out ablations show each safety endpoint and Compare is necessary for exactly the defect class it covers.

Clocked Guard's outputs were fully deterministic in a re-run (30/30 Guard re-runs identical).

## 1. Introduction

Agent platforms make it cheap to create agents and expensive to govern them. One practitioner's account of "850 agents built and a dozen in use" captures the problem (Rezolve.ai, 2026). The risks are concrete:
- **Tool poisoning:** instructions hidden in tool descriptions the model reads but the user doesn't see (Invariant Labs, 2025; MCPTox, Wang et al., 2025).
- **Malicious skills:** delivered through marketplaces (Liu et al., USENIX Security 2026).
- **Unowned agents:** agents with broad access and no accountable owner.

Decision models such as Clocked, TypeSafe Jev, OpenAI Decisions and Microsoft-Decision-1 return typed judgments with probabilities in milliseconds. That makes them natural building blocks for automated review. Two questions remain open:

1. How well do they work on agent artifacts?
2. What does it take to deploy them well?

**Contributions:**
1. AgentAudit, an open-source audit (CLI, GitHub Action with SARIF, REST hook, web app). Each of Clocked's nine endpoints has a measured job, and authority (autonomy) is set by policy rather than by the model.
2. AgentAudit-Bench: four suites with server- or source-disjoint dev/test splits, external real-world sets, free open-source baselines, a pre-registered protocol and all per-row records.
3. An analysis of *where* the gains come from: a policy × rule ablation, a threshold-only control, leave-one-endpoint-out governance ablations, and a single-call control.
4. A supply-chain check that targets what Guard and Inspect miss in real malicious skills: payloads written as prose prerequisites rather than scripts.

## 2. Related work

**Tool poisoning and MCP security.**
- MCPTox (Wang et al., arXiv:2508.14925) benchmarks 485 poisoned descriptions across 45 servers.
- MCPSecBench (Yang et al., arXiv:2508.13220) catalogs 17 attack types.
- MCP-TDP (Liu et al., arXiv:2605.24069) finds that prompt guardrails barely reduce attack success.
- ShareLock (arXiv:2606.27027) splits payloads across tools.

Scanners such as Snyk agent-scan (formerly Invariant mcp-scan), Cisco mcp-scanner and MCPShield detect issues. They don't produce ownership records, registry de-duplication or governed verdicts.

**Injection detectors.**
- ProtectAI DeBERTa v2
- Meta Prompt Guard 2
- PIGuard (Li & Liu, arXiv:2410.22770), which targets over-defense
- benchmarks: BIPIA (Yi et al., KDD 2025), InjecAgent (Zhan et al., ACL Findings 2024), AgentDojo (Debenedetti et al., 2024)

**Malicious skills.**
- MaliciousSkillBench (arXiv:2608.19901)
- SkillScreen (Huang et al., arXiv:2610.17727). It reports zero-shot Jev 1.13 at 33.8% recall on unseen families.
- SkillSieve (arXiv:2604.06550)

**Decision models.** Clocked publishes grounding, PII and decision benchmarks, but none for Guard or Inspect. jev-benchmark (ejs-5, 2026) offers mechanically labeled decisions.

## 3. System

AgentAudit normalizes an agent into **artifacts**: tool descriptions, instructions or skill files, scripts (including install hooks and skill code blocks), README and config. Collection is static and never executes the target. An opt-in live mode reads an MCP server's `tools/list`.

| Group | Endpoint | Job | Affects |
|---|---|---|---|
| Safety | Guard | Injection in agent-readable text. Separate policies for tool text and the agent's own prompt | quarantine |
| Safety | Inspect | Scripts judged against declared scope | quarantine |
| Safety | Protect | Secrets and personal data (batched per agent). Spans redact the whole report | quarantine, redaction |
| Documents | Extract | Verbatim facts; download targets for the supply-chain check | record, AA005 |
| Documents | Fill | Registry record; README capability claims | record, Verify input |
| Documents | Decide | Verdict and risk; supply-chain judgment; precision-mode second opinion | verdict |
| Facts | Verify | README claims vs extracted capability facts | AA004 |
| Facts | Compare | Duplicates in the registry | reuse |
| Facts | Rerank | Which existing agent serves the purpose | reuse suggestion |

**Policy layer:**
- The accountable owner comes from registry metadata (manifest or CODEOWNERS), never inferred.
- Autonomy is computed from the verdict, write access and risk.
- A "reuse" suggestion requires both Compare and Rerank.

Two operating points:
- **default:** safety-first.
- **precision:** a Decide second opinion on Guard flags for tool descriptions.

## 4. Benchmark design

The protocol (`bench/PROTOCOL.md`) was committed before each test run. Git history is the record.
- Splits are disjoint by server, technique or repository (seed 20261031).
- Configurations are selected on dev by balanced accuracy, then frozen.
- Each test split is run once per frozen configuration.

**Metrics:**
- balanced accuracy (BAcc), recall, FPR
- 95% stratified bootstrap CIs (2,000 resamples)
- AUROC and ECE
- exact McNemar with Holm correction
- median round trip and credits

These match Clocked's own published method.

| Suite | Positives | Negatives | n (dev / test) |
|---|---|---|---|
| Guard: tool poisoning | MCPTox, stratified | Reference MCP servers, InjecAgent specs, 40 hard negatives | 129 / 253 |
| Guard: external | 25 published poisoned descriptions | 199 real tools from 24 public servers + 25 matched originals | — / 249 |
| Inspect: scripts | Atomic Red Team | MCP-repo scripts, admin PowerShell, installers; 20 scope pairs | 94 / 206 |
| Skills | 124 real malicious SKILL.md (Feb 2026 ClawHub campaign) | 223 benign | 103 / 244 |
| Governance | 12 per verdict, recipe-labeled | — | 10 / 38 |

**Baselines:** ProtectAI and deepset DeBERTa (CPU) and a keyword regex. Each is scored at its standard 0.5 threshold and at a dev-tuned threshold, giving the same tuning advantage our configuration had.

## 5. Results

**Harness validation.** We reproduce Clocked's published jev-benchmark results to the decimal: 84.4 / 68.9 / 35.6 / 69.4, 507/868, against Jev's 508.

**Tool poisoning (test, n = 253):**

| Arm | BAcc | FPR | AUROC |
|---|---|---|---|
| Clocked default | 84.9 [80.5, 88.9] | 25.9 | 0.946 |
| Clocked default, dev-tuned threshold | 83.8 | 28.1 | 0.946 |
| Clocked + AgentAudit (frozen) | **97.6 [95.6, 99.3]** | **2.2** | **0.999** |
| ProtectAI DeBERTa (0.5) | 58.6 | 6.5 | 0.898 |

Ablation (BAcc): the policy alone gives 95.7, the rule alone 88.1, both 97.6. Removing the author-written hard negatives gives 97.3 vs 82.5. Recall holds across all three MCPTox templates.

**External generalization (n = 249).**
- Default FPR on real tools: 23.2%.
- AgentAudit: 5.4%.
- Best dev-tuned baseline (ProtectAI): 16.5%.
- Recall: 100% for both Clocked arms.

**Scripts (test, n = 206).**
- AgentAudit: 89.9, against 84.4 for the default and 87.4 for a threshold-tuned default (p = 0.15).
- Scope pairs: 50% → 78.6% (96.4% with the consensus rule).
- Most of the value is scope, not a better generic prompt.

**Malicious skills (test, n = 244):**

| Arm | BAcc | Recall | FPR |
|---|---|---|---|
| Guard default, whole file | 55.2 | 10.3 | 0.0 |
| Inspect default, whole file | 72.9 | 48.3 | 2.5 |
| AgentAudit pipeline (frozen) | **88.6** | **80.5** | 3.2 |
| Supply-chain check alone | 88.2 | 77.0 | 0.6 |

**Governance (test, n = 38).**
- Full audit: 78.9%.
- Precision mode: 89.5%.
- Single Decide control: 60.5%.

Leave-one-out:
- without Guard: poisoned tools 4/4 → 0/4
- without Inspect: scripts 3/3 → 1/3
- without Protect: secrets 3/3 → 1/3
- without Compare: duplicates 7/9 → 0/9

Extract, Fill, Verify and Rerank don't change verdicts here. They supply the record and the reuse suggestions.

**Systems finding.** Per-artifact false positives compound. At ~5% per tool description, a 6-tool agent has ~26% odds of a false flag. This is why agent-level verdicts need either a low per-item FPR (Guard went from 25.9% to 2.2%) or a second opinion (precision mode).

**Real-world study** (9 public MCP repos, hand-verified; `bench/REALWORLD.md`).
- No confirmed issues.
- Default mode would have wrongly quarantined 2/9 servers, all due to short-imperative Guard flags. Precision mode: 0/9.
- For registry gating of reputable servers we therefore recommend precision mode. Default mode stays the maximum-recall setting for CI on untrusted code.

**Determinism and cost.**
- A 30-row uncached re-run was identical (Δp = 0).
- Median round trip: 0.3–0.5 s per call.
- A typical audit costs about 20–90 credits (about 0.4–2 US cents at overage rates).

## 6. Limitations

- **Construct validity.**
  - Atomic Red Team includes dual-use discovery commands.
  - Scope pairs and hard negatives were written by the authors. Results without them are reported.
  - Governance labels come from a construction recipe on synthetic manifests built from real tools.
- **Two configuration changes after seeing full governance results are disclosed:**
  - owner rule v2
  - a rejected filter whose test numbers were printed
- **No other decision model was run on our suites.** Jev appears only via published per-row answers on jev-benchmark and SkillScreen's figure on a different split.
- **Adaptive attacks** were limited to published sets. We didn't write new attack payloads.
- **Single engine version** (clocked-1.0 at the time of writing).

## 7. Ethics and data

- Only public, synthetic or permissively licensed data was used. MCPTox text isn't redistributed (no license).
- Scans of public projects are reported in aggregate only.
- Fake keys are clearly non-functional.
- Nothing from scanned repositories is executed.

## 8. Reproducibility

```bash
uv sync --all-extras --all-groups
uv run python bench/report.py          # every table, from cached records, 0 credits
uv run pytest -q                       # offline tests
```

Raw runs: `bench/suites/run_*.py`. Credit ledger: `bench/credit_ledger.jsonl`.
