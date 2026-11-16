# Template: task

Use for multi-step engineering work before implementation (commit-sized or small feature plans).
Prefer **implementation-plan** when the artifact is for human approval (decision callout, before/after, unchanged, status) rather than a commit-sized breakdown.

| Section | Default visual |
| --- | --- |
| Goal / context | Short prose (≤3 lines) + optional one-liner status |
| Wireframes (UI changes) | `## Wireframes` near the top: desktop and mobile, current and target, fenced `text` blocks + annotations table |
| Workflow | Workflow chart (before→after or steps) |
| Affected files / areas | Heat map (impact × risk) |
| Commit timeline | Timeline (Conventional Commits subjects; foundations→cleanup) |
| Verification | Short checklist |
| Out of scope | Short list |

For UI changes, `## Wireframes` is required near the top of `plan.md`: Desktop · current, Desktop · target, Mobile · current, Mobile · target as fenced `text` ASCII blocks, then an Annotations table (label → component/file). Images, HTML, or Canvas are supplements, not substitutes. Follow [UI changes in approved plans](../SKILL.md#ui-changes-in-approved-plans), including the hidden-information rule and self-check.

For non-UI tasks, skip the section and include exactly: `Wireframes: not applicable — no UI change`.

Optional if needed: architecture or data-flow diagrams as extra sections the user requests.

Outputs: follow SKILL.md — always emit plan.md and visual-plan.md; also emit
visual-plan.html and a Canvas when the environment supports them (skip either when unavailable).
