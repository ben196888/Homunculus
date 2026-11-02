# Template: rfc

Use for cross-cutting or architectural alignment before implementation. This is what `development-workflow`'s document step should invoke for large or cross-cutting design (use **implementation-plan** instead when the ask is an approval-oriented concrete behavior change).

| Section | Default visual |
| --- | --- |
| Problem | Short prose (≤3 lines) |
| Current vs proposed | Architecture diagram (two panels or annotated) |
| Data flow | Data-flow or sequence diagram |
| Decision table | Decision table (options, choice, why) |
| Rollout timeline | Timeline (milestones / phases) |
| Risks | Heat map or risk table |
| Verification | Short checklist |
| Out of scope / non-goals | Short list |

Outputs: follow SKILL.md — always emit plan.md and visual-plan.md; also emit
visual-plan.html and a Canvas when the environment supports them (skip either when unavailable).
