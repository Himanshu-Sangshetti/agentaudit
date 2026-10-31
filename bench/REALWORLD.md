# Real-world study: 9 public MCP server repositories

**Method.** A seeded random sample (seed 20261103) of 9 of the 36 permissively licensed public MCP repos cloned for this project. Collection was static (nothing executed). Each repo was audited in default and precision modes with an empty registry. Every flag was reviewed by hand. Per our disclosure policy, results are reported in aggregate, and per-repo output stays out of the repository. Credits: 1,600.

| | Default mode | Precision mode |
|---|---|---|
| Repos quarantined | 2 / 9 | 0 / 9 |
| Guard flags (all hand-verified false positives: short imperative tool descriptions) | 6 | 0 |
| Protect flags (all localhost or documentation-address `internal_url` / `ip_address` matches, medium severity) | 3 | 3 |
| Inspect flags (one low-severity `uvx --version` setup check) | 1 | 1 |
| Confirmed real issues | 0 | 0 |

**Takeaways.**
1. For reputable servers, the main operational risk of an automated audit is **false quarantines**, not misses. Per-tool false positives compound across agents with many tools, which matches the governance finding in RESULTS.md. Precision mode removed all false quarantines here.
2. Static extraction found no tool definitions in 5/9 repos, because they register tools dynamically. Use the opt-in live mode (`tools/list`) for those.
3. After this study, the Protect `internal_url` definition was narrowed to exclude localhost and placeholder addresses. Benchmarks in RESULTS.md were run before this change (governance results at commit 9d0db6f).
