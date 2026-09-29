# Autosquash: helper script vs instructions only

Model: `gpt-5.6-luna` at medium reasoning. One run per configuration across four deterministic Git scenarios.

| Metric | With script | Instructions only | Script delta |
| --- | ---: | ---: | ---: |
| Accuracy | 100% (22/22) | 100% (22/22) | tie |
| Mean total tokens | 222,735 | 279,041 | -20.2% |
| Mean uncached input | 23,095 | 29,546 | -21.8% |
| Mean output tokens | 4,056 | 5,334 | -24.0% |
| Mean reasoning tokens | 779 | 1,030 | -24.4% |
| Mean duration | 99.2s | 122.9s | -19.2% |
| Total tokens, all four runs | 890,941 | 1,116,163 | -20.2% |

## Per-scenario total tokens

| Scenario | With script | Instructions only | Script delta |
| --- | ---: | ---: | ---: |
| clean_fixups | 312,309 | 265,998 | 17.4% |
| dirty_diverged_squash | 244,196 | 330,521 | -26.1% |
| no_markers | 132,681 | 176,752 | -24.9% |
| lease_race | 201,755 | 342,892 | -41.2% |


## Interpretation

- Accuracy tied: both variants passed every repository-state assertion.
- The helper was substantially more efficient on the complex and safety-sensitive cases.
- Instructions-only won raw total tokens on the clean-fixup case, but the helper used fewer uncached input tokens there; one run cannot distinguish stable behavior from model variance.
- Keep the helper for the current skill. It buys deterministic safety without an observed accuracy penalty and lowers average token/time cost.
