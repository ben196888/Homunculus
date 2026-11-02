# Template: task

Use for multi-step engineering work before implementation (commit-sized or small feature plans).
Prefer **implementation-plan** when the artifact is for human approval (decision callout, before/after, unchanged, status) rather than a commit-sized breakdown.

| Section | Default visual |
| --- | --- |
| Goal / context | Short prose (≤3 lines) + optional one-liner status |
| Workflow | Workflow chart (before→after or steps) |
| Affected files / areas | Heat map (impact × risk) |
| Commit timeline | Timeline (Conventional Commits subjects; foundations→cleanup) |
| Verification | Short checklist |
| Out of scope | Short list |

Optional if needed: architecture or data-flow diagrams as extra sections the user requests.

Outputs: follow SKILL.md — always emit plan.md and visual-plan.md; also emit
visual-plan.html and a Canvas when the environment supports them (skip either when unavailable).
