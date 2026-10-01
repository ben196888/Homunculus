# Skill Benchmark: homunculus-programming-peer-review

**Model**: not recorded in run artifacts
**Date**: 2026-07-27T08:41:35Z
**Evals**: 0, 1, 2 (3 runs each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 70% ± 4% | 51% ± 18% | +0.19 |
| Time | 963.8s ± 191.9s | 733.7s ± 348.0s | +230.0s |
| Tokens | 157966 ± 26908 | 121170 ± 9648 | +36796 |

## Notes

- The skill's advantage is broad but uneven: +33.3 percentage points on resists-plausible-deletion, +18.8 on replacement-refactor-dead-code, and +6.3 on verify-pr-body-claims. The baseline nearly closes the gap on the third eval.
- `proposed-fix-itself-tested` is the cleanest discriminator: all three skill runs pass and all three baselines fail. `killed-claims-name-the-command` is also strong at 3/3 with the skill versus 1/3 without it.
- The baseline outperforms the skill on `pr-body-claims-run-not-read` in eval 2: it live-tests stale-credential demotion in Chromium, while the skill run accepts that behavior from source reading.
- `awaits-post-confirmation` and `fix-plus-verify-per-finding` fail in all six runs. They currently measure desired behavior that neither configuration delivers, so they should drive a skill revision or be narrowed before a larger benchmark.
- Several assertions do not discriminate in this sample: `execution-contract-read-not-assumed`, `per-finding-evidence`, `ran-verification-that-exercises-the-change`, `materialized-pr-head`, `merge-verdict-stated`, and `no-writes-to-repo-or-forge` pass in every applicable run.
- Draft discipline remains weak. `comments-split-thread-vs-inline` passes only one run per configuration, and `inline-comments-terse-actionable` passes only the skilled deletion-trap run.
- The skill costs 230.0 seconds and 36,796 tokens more per run on average (about 31% and 30%). Token overhead is not uniform: +17.7% on eval 0, +30.1% on eval 1, and +41.4% on eval 2.
- Each configuration has one run on each of three different evals. The displayed standard deviation is cross-eval spread, not repeated-run variance, and this sample does not support a statistical-significance claim.
