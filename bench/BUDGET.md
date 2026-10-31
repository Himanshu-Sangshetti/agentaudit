# Clocked credit budget

Account: 20,000 credits (4,000 trial + 16,000 from the hackathon code). The hard ceiling in `.env` is 17,000, leaving 3,000 for the demo during judging.
Every paid call is logged in `bench/credit_ledger.jsonl` with its experiment tag. Repeated calls hit the disk cache and cost nothing.

Measured cost per call on short inputs (Oct 31 probes): decide 1, fill 1, rerank 2, script 3, pii 3, grounding 3, injection 4, compare 4, extract 5.
Longer inputs cost more, since billing is 25 ms of model time per credit.

| Experiment | Budget (credits) | Status |
|---|---|---|
| day1-probes | 500 | done (478) |
| jev-repro (868 decide) | 1,200 | planned |
| guard-bench (dev + test, 2 configs) | 3,000 | planned |
| inspect-bench (dev + test, 2 configs) | 2,000 | planned |
| verify-bench | 1,000 | planned |
| compare / rerank / decide small sets | 1,500 | planned |
| real-world scan | 3,000 | planned |
| iteration slack | 3,800 | held |
| demo reserve (judging week) | 3,000 | held |

Rules: a pilot of 10–20 rows before any full run, dev/test split fixed before tuning, and no experiment runs without a tag and a budget.
