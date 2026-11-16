# Template: rfc

Use for cross-cutting or architectural alignment before implementation. This is the template `development-workflow`'s document step invokes. Use **implementation-plan** instead when someone asks directly for an approval-oriented concrete behavior change.

| Section | Default visual |
| --- | --- |
| Problem | Short prose (≤3 lines) |
| Current vs proposed | Architecture diagram (two panels or annotated) |
| Wireframes (UI changes) | `## Wireframes` near the top: desktop and mobile, current and target, fenced `text` blocks + annotations table |
| Data flow | Data-flow or sequence diagram |
| Decision table | Decision table (options, choice, why) |
| Rollout timeline | Timeline (milestones / phases) |
| Risks | Heat map or risk table |
| Verification | Short checklist |
| Out of scope / non-goals | Short list |

RFCs that propose UI changes must include `## Wireframes` near the top of the RFC body in `plan.md` (desktop and mobile, current and target, fenced `text` blocks, plus an Annotations table), following [UI changes in approved plans](../SKILL.md#ui-changes-in-approved-plans), including the hidden-information rule and self-check. For non-UI RFCs, skip the section and include exactly: `Wireframes: not applicable — no UI change`.

Outputs: follow SKILL.md — always emit plan.md and visual-plan.md; also emit
visual-plan.html and a Canvas when the environment supports them (skip either when unavailable).
