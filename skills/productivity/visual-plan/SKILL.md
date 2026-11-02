---
name: homunculus-productivity-visual-plan
description: >
  Turn a plan, RFC, comparison, experiment write-up, or approval-oriented
  implementation plan into diagrams-first artifacts (plan.md and visual-plan.md,
  plus visual-plan.html and a Canvas when the environment supports them) using a
  visualisation guideline and named templates. Use whenever planning work before
  implementation — including phrases like visual plan, plan this, show me the
  plan, plan for X, we need a plan, we need an RFC, design doc, RFC before,
  multi-commit plan, implementation plan, before/after plan, tech comparison,
  A/B or experiment report, or when development-workflow reaches its document
  step. Also use for before/after plan comparison artifacts. Skip one-line fixes
  and pure prose edits. Do not use when the user explicitly asks for pstack
  architect, statechart, or technical-writing and that skill fully covers the
  ask (those design or verify code/prose; this skill produces the human review
  artifact set).
---

# Visual plan

A **visualisation guideline**, not a fixed document outline. Choose *how* each section is shown; *which sections* come from the user or a template.

## Section source (priority)

1. **User-provided sections always win.** If the user lists headings or a custom outline, use that exact structure.
2. Else use a **named template** the user or caller asked for (see [Template ids](#template-ids)).
3. Else pick the **closest template**, and state which one you picked and why in one line at the top (`template: <id> · reason: …`).

Templates live beside this skill: [templates/](templates/). Each file lists sections and the default visual for that section. The starters cover commit-sized plans, approval-oriented implementation plans, RFCs, tech comparisons, and experiment reports; do not invent new template files unless the user asks.

### Template ids

Stable ids (rename = replace the id string in every row location below):

| Id | File | Prefer when |
| --- | --- | --- |
| `task` | [templates/task.md](templates/task.md) | Commit-sized engineering breakdown (heat map + commit timeline) |
| `implementation-plan` | [templates/implementation-plan.md](templates/implementation-plan.md) | Approval-oriented concrete behavior change (decision callout, before/after, unchanged, status) |
| `rfc` | [templates/rfc.md](templates/rfc.md) | Cross-cutting architecture with option trade-offs |
| `tech-comparison` | [templates/tech-comparison.md](templates/tech-comparison.md) | Choosing among technologies or approaches |
| `ab-test-report` | [templates/ab-test-report.md](templates/ab-test-report.md) | Experiment write-up / go-no-go from measured results |

**Rename checklist for an id:** `templates/<id>.md` filename + H1/`template-id` comment; this table; `development-workflow` template guidance; README skill blurb; `<!-- template: <id> -->` in references; cross-mentions in other templates or SKILL prose.

`development-workflow`'s document step: run visual-plan with **`rfc`** for large or cross-cutting design, or **`implementation-plan`** for a concrete behavior/system change that needs approval before coding (unless the user overrode sections or named another template).

Pick **`implementation-plan`** (not **`task`**) when the deliverable is a decision callout, before/after behavior table, unchanged list, and status checklist for human approval before coding. Keep **`task`** for commit-sized engineering breakdowns (heat map + commit timeline). Keep **`rfc`** for cross-cutting architecture with option trade-offs.

## Visualisation guideline

Map content kinds to visuals (pick only what the content needs):

| Content kind | Default visual |
| --- | --- |
| Proposed decision for approval | Decision callout (lead + short proposal) |
| Steps, user flow, before→after process | Workflow chart (Mermaid flowchart) |
| Behavior today vs after a change | Before/after table |
| Components, boundaries, add/change/remove | Architecture diagram |
| Requests, payloads, contracts, ordering | Data-flow or sequence diagram |
| Impact × risk, effort, or score intensity | Heat map (SVG if Mermaid cannot) |
| Phases, commits, rollout, milestones | Timeline |
| Options with choice + why | Decision table |
| Multi-criteria option scores | Scored matrix |
| Experiment metrics / lifts | Charts with confidence ranges |
| What deliberately stays the same | Unchanged list / labeled properties |
| Plan progress (approve → ship) | Status checklist |

Rules:

- Every section **leads with its visual**; caption ≤ ~3 lines.
- Ground current state in inspected code or data with real paths/figures. Label proposals. Invent nothing.
- **Mermaid by default**; SVG only where Mermaid cannot (e.g. heat-map grid, custom charts).
- **Render-check** every diagram before presenting.
- Prefer stable section ids (`{#slug}`) and per-commit or per-phase tags on diagram nodes so all outputs share structure.
- End with the closing lists the template (or user) includes — e.g. **Verification** / **Out of scope**, or **Unchanged** / **Status** on `implementation-plan`; do not invent sections the template omitted unless the user asked.

## Outputs

Produce these from the **same sections and diagrams** (same facts). Outputs 1–2 are **required** on every run. Outputs 3–4 are **optional**: produce each one when the environment supports it, and **skip it** when it does not (for example no way to write or open an HTML file, no Canvas tool, or the user opted out). Never block the plan on a skipped output; say which outputs were skipped and why in one line.

1. **`plan.md`** — plain Markdown prose/bullets, **no diagrams**. The conventional wordy form of the plan (useful as the "before" in a comparison and for terminals that will not render Mermaid).
2. **`visual-plan.md`** — diagrams-first Markdown (embedded Mermaid; SVG files beside it when needed). Put `template: <id>` at the top.
3. **`visual-plan.html`** (optional; skip when unavailable) — one **self-contained** interactive HTML page of the same plan:
   - Mermaid via CDN (or inline) + small vanilla JS; **no build step**, no bundler
   - Collapsible sections
   - Heat-map hover → risk/impact reason (when a heat map exists)
   - Commit/phase **step-through** that highlights affected nodes (when a timeline exists)
   - Optional click on architecture nodes → files/commits
   - **Before/after workflow toggle** when a plain `plan.md` (or before-state diagram) exists for comparison
   - Axis titles on heat maps: Risk along the left, Impact under the columns
4. **Canvas** (optional; skip when unavailable) — when the agent environment supports Canvas, publish the same sections as an interactive Canvas page the reviewer can open in the product UI (for example Cursor/Grok Bot `WriteCanvas`). Map sections to the host's callout, diagram, table, steps, properties/unchanged, and checklist building blocks when those exist. **Skip this output** when Canvas is unavailable.

Save the file outputs next to each other in the working directory the user named (or a sensible draft folder), report their paths, report the Canvas link when one was created, and list any skipped outputs.

## Examples

- [references/product-cache/](references/product-cache/) — mock **`task`** visuals (architecture + data-flow SVGs and a sample plan; no runnable fixture).
- [references/job-lease/](references/job-lease/) — mock **`implementation-plan`** (decision callout shape, flow SVG, before/after, implementation, unchanged, status).

Scenario choices in examples are not requirements for other plans.
