# AgentAudit-Bench: evaluation protocol

This file is written and committed **before** the runs it governs. The git history is the pre-registration record: any change after a test run is a new, dated commit, and the report says what changed.

## Research questions

- **RQ1 (detection).** How well do decision-model endpoints (Clocked Guard and Inspect) detect malicious content in agent artifacts (tool descriptions, skills, scripts) compared with open-source detectors and LLM judges, on the same rows?
- **RQ2 (configuration).** How much of the error comes from deployment configuration rather than the model? We compare Clocked default against Clocked with agent-specific policy and decision rules, with ablations isolating each change.
- **RQ3 (generalization).** Do the gains from RQ2 hold:
  - (a) on attack families never seen while designing the configuration (leave-one-paradigm-out)?
  - (b) on an external, real-world dataset never used for design (the ClawHub malicious skills)?
  - (c) under adaptive attacks written to evade the policy?
- **RQ4 (governance).** Does an audit that uses all nine endpoints produce correct governance verdicts (approve / needs owner / reuse / quarantine) on labeled agents, and which endpoints change the verdict? Endpoint ablations answer the second part.
- **RQ5 (cost).** What are latency and cost per audited agent, and per correct detection?

## Rules

1. **Splits are fixed before any tuning.**
   - Splits are disjoint by server or source, so no MCP server has tools in both dev and test.
   - Seed: 20261031.
   - Manifests are in `bench/data/`.
2. **Configuration is designed on dev only.** The test split is run once per frozen configuration. The commit hash of the frozen configuration is recorded in each result file.
3. **Every arm sees identical rows.** A failed request counts as wrong for that arm.
4. **Metrics:**
   - balanced accuracy, recall, FPR, AUROC
   - expected calibration error, where a probability is returned
   - median round-trip and model latency
   - cost
   - 95% bootstrap confidence intervals (2,000 resamples, stratified by label)
   - exact McNemar for paired comparisons
   - Holm correction across the comparisons in each table
5. **All results are reported**, including those where Clocked or AgentAudit loses.
6. **Per-row records are released**, except rows whose source license forbids redistribution (MCPTox has no license). For those we release only IDs and predictions.

## Known threats and how we handle them

- **Leakage, disclosed.** Before the Guard dev run, the audit was demonstrated on two reference servers (filesystem, memory) that later landed in the Guard test split. The policy text was written before that demo and not edited after it. But the idea of the "consensus" decision rule came from looking at those outputs. Robustness check: we also report test metrics with those two servers removed. Result on Oct 31: AgentAudit 97.8 BAcc / 1.7% FPR, against default 88.3 / 19.0%. The conclusion is unchanged.
- **Synthetic, templated attacks.** MCPTox uses three templates. We address this with leave-one-template-out runs, the external real-world skills set, and adaptive attacks (paraphrased, obfuscated, split across fields, and policy-aware payloads written after the configuration was frozen).
- **Small benign set.** We expand real benign tool descriptions beyond the reference servers with a sample from public MCP registries, using hand-checked labels.
- **Single run.** Clocked reports deterministic outputs at a fixed engine version. We record the engine version and re-run a 30-row sample to measure agreement.
- **Policy overfit.** Policy text is kept generic, not tied to MCPTox wording. RQ3 tests this directly.

## Frozen configurations (selected on dev by balanced accuracy)

| Endpoint | Setup | Rule | Dev BAcc | Frozen at |
|---|---|---|---|---|
| Guard | agentaudit (tool-description policy) | consensus | 93.4 (default + verdict: 86.4) | commit 279c578, Oct 31 |
| Inspect | agentaudit (deployment context + change scope) | verdict | 90.4 (consensus 88.6; default + verdict 86.6) | Oct 31, this commit |

Inspect note: consensus has the lower dev FPR (3.8% vs 9.6%). We report both, but the pre-registered selection criterion is balanced accuracy.
