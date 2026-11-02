# Template: rfc

Use for cross-cutting or architectural alignment before implementation. This is the template `development-workflow`'s document step invokes. Use **implementation-plan** instead when someone asks directly for an approval-oriented concrete behavior change.

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
