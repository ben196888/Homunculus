# Skill Benchmark: homunculus-programming-autosquash

**Model**: gpt-5
**Date**: 2026-09-22T08:24:05Z
**Evals**: 0, 1, 2 (1 run each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 100% ± 0% | 58% ± 38% | +0.42 |
| Time | 0.0s ± 0.0s | 0.0s ± 0.0s | +0.0s |
| Tokens | 0 ± 0 | 0 ± 0 | +0 |

## Notes

- Five of 11 expectations differentiated the configurations. The skill added tree-identity proof, an exact fetched-SHA lease, recovery guidance, exact dirty-state restoration, and verification before push.
- Both configurations achieved the basic history result, so the benchmark isolates safety behavior rather than raw autosquash capability.
- The no-marker case passed both configurations and serves as a regression guard.
- Timing, token, and tool-call telemetry was unavailable; the zero values above do not represent measured costs.
