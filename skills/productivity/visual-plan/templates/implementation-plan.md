<!-- template-id: implementation-plan -->
# Template: implementation-plan

Use when proposing a concrete behavior or system change that needs human approval
before implementation — decision-first, before/after, what stays the same, and a
status checklist. Prefer this over **task** when the artifact is for approval
rather than a commit-sized engineering breakdown; prefer **rfc** when the ask is
cross-cutting architecture alignment with option trade-offs.

To rename this template later: change the `template-id` comment, this H1, the
filename, and every id listed in SKILL.md's Template ids rename checklist.

| Section | Default visual |
| --- | --- |
| Decision needed | Decision callout (lead + one-paragraph proposal) at the top |
| How it works / flow | Workflow chart (Mermaid flowchart; label new checks or paths) |
| Before vs after | Before/after table (situation × today × after change) |
| Implementation | Numbered steps (each step: title + short detail) |
| Unchanged | Short list or labeled properties (what deliberately stays the same) |
| Status | Checklist (plan → approval → PR → review → deploy / done) |

Optional if needed: ownership / who-approves table; short prose under the callout
for investigation context. Do not add heat maps or commit timelines unless the
user asks (those belong on **task** / **rfc**).

Keep content generic to the change under review; do not bake in product- or
bot-specific names unless the user supplied them.

Outputs: follow SKILL.md — emit plan.md, visual-plan.md, visual-plan.html, and a
Canvas when the environment supports one (skip Canvas when unavailable).
