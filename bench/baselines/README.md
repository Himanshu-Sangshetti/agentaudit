# Local baselines

These are free baselines that run on a laptop CPU, with no Clocked calls and no paid APIs. They score exactly the same rows as the Clocked arms (`data/built/guard_{dev,test}.jsonl`, built by `bench/suites/build_guard.py`). The scoring is the same too (`bench/metrics.py`, with the `rule_verdict` decision rule).

## Guard suite (tool poisoning)

| Arm | Model | Revision (commit) | License | Size |
|---|---|---|---|---|
| `protectai` | [protectai/deberta-v3-base-prompt-injection-v2](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2) | `90c9989b1a342275dd0d1a95aad283c04e075671` | Apache-2.0 | 184M |
| `deepset` | [deepset/deberta-v3-base-injection](https://huggingface.co/deepset/deberta-v3-base-injection) | `80dda00d0b0d9a03917a7685e2ddbcd28e04dbb1` | MIT | 184M |
| `keyword` | Regex over injection phrases (`KEYWORDS` in `run_guard_baselines.py`) | n/a | n/a | n/a |

Settings:
- Each model's own `id2label` determines the "injection" class.
- A row counts as an attack when the probability is at least 0.5, each model's standard threshold.
- **Long texts:** windows of 512 tokens, stride 128. The row's probability is the **max over windows**, so payloads past the first 512 tokens are not truncated away.
- `rtt_ms` is local wall-clock inference time per row (tokenize plus forward pass), batch size 1.

Models we didn't run:
- `meta-llama/Prompt-Guard-2-86M` / `-22M`: gated, needing an HF login and Llama license acceptance.
- `leolee99/PIGuard`: needs `trust_remote_code` (custom Python from the model repo). We don't execute downloaded code, so it's excluded.

## Hardware and software

Apple M5 Pro, 24 GB RAM, macOS 26.4.1, CPU only. Python 3.14, torch 2.15.0, transformers 5.22.1.

## Reproduce

```bash
uv sync --group bench
bench/baselines/fetch_models.sh                           # pinned revisions -> data/raw/models/ (plain HTTPS)
uv run python bench/suites/build_guard.py                 # needs data/raw (see build_guard.py)
uv run --group bench python bench/baselines/run_guard_baselines.py
```

Outputs: `bench/results/baseline_guard_{dev,test}_{keyword,protectai,deepset}.jsonl`, one record per row with
`id, label, source, group, p, verdict, category (null), severity (null), rtt_ms`.
