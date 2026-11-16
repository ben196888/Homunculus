# Template: task

Use for multi-step engineering work before implementation (commit-sized or small feature plans).
Prefer **implementation-plan** when the artifact is for human approval (decision callout, before/after, unchanged, status) rather than a commit-sized breakdown.

| Section | Default visual |
| --- | --- |
| Goal / context | Short prose (≤3 lines) + optional one-liner status |
| Target layout (UI changes) | Whole-screen wireframes at desktop and mobile widths; label widths and highlight the changed region |
| Expected UI (UI changes) | State mockups (default, hover/active, empty, error as applicable) with real labels and copy |
| Workflow | Workflow chart (before→after or steps) |
| Affected files / areas | Heat map (impact × risk) |
| Commit timeline | Timeline (Conventional Commits subjects; foundations→cleanup) |
| Verification | Short checklist |
| Out of scope | Short list |

For UI changes, both **Target layout** and **Expected UI** are required inside `plan.md` as ASCII/box-drawing wireframes or inline SVG text before hashing and approval. Separate images, HTML, or Canvas are supplements, not substitutes. Follow [UI changes in approved plans](../SKILL.md#ui-changes-in-approved-plans) for source-design grounding and **proposed** labels.

For non-UI tasks, skip both sections and include one line: `Target layout / Expected UI: not applicable — no UI change`.

Optional if needed: architecture or data-flow diagrams as extra sections the user requests.

Outputs: follow SKILL.md — always emit plan.md and visual-plan.md; also emit
visual-plan.html and a Canvas when the environment supports them (skip either when unavailable).
