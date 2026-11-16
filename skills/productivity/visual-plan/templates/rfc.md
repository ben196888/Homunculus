# Template: rfc

Use for cross-cutting or architectural alignment before implementation. This is the template `development-workflow`'s document step invokes. Use **implementation-plan** instead when someone asks directly for an approval-oriented concrete behavior change.

| Section | Default visual |
| --- | --- |
| Problem | Short prose (≤3 lines) |
| Current vs proposed | Architecture diagram (two panels or annotated) |
| Target layout (UI changes) | Whole-screen wireframes at desktop and mobile widths; label widths and highlight the changed region |
| Expected UI (UI changes) | State mockups (default, hover/active, empty, error as applicable) with real labels and copy |
| Data flow | Data-flow or sequence diagram |
| Decision table | Decision table (options, choice, why) |
| Rollout timeline | Timeline (milestones / phases) |
| Risks | Heat map or risk table |
| Verification | Short checklist |
| Out of scope / non-goals | Short list |

RFCs that propose UI changes must include **Target layout** and **Expected UI** in the RFC body in `plan.md`, following [UI changes in approved plans](../SKILL.md#ui-changes-in-approved-plans). Embed ASCII/box-drawing wireframes or inline SVG text so hashing and approval include them. For non-UI RFCs, skip both sections and include one line: `Target layout / Expected UI: not applicable — no UI change`.

Outputs: follow SKILL.md — always emit plan.md and visual-plan.md; also emit
visual-plan.html and a Canvas when the environment supports them (skip either when unavailable).
