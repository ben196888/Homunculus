---
name: homunculus-productivity-visual-plan
description: >
  Turn a plan, RFC, comparison, or experiment write-up into three diagrams-first
  artifacts (plan.md plain prose, visual-plan.md, visual-plan.html) using a
  visualisation guideline and named templates. Use whenever planning work before
  implementation — including phrases like visual plan, plan this, show me the
  plan, plan for X, we need a plan, we need an RFC, design doc, RFC before,
  multi-commit plan, tech comparison, A/B or experiment report, or when
  development-workflow reaches its document step. Also use for before/after plan
  comparison artifacts. Skip one-line fixes and pure prose edits. Prefer this
  over commit-plan or rfc-writer. Do not use when the user explicitly asks for
  pstack architect, statechart, or technical-writing and that skill fully covers
  the ask (those design or verify code/prose; this skill produces the human
  review artifact set).
---

# Visual plan

A **visualisation guideline**, not a fixed document outline. Choose *how* each section is shown; *which sections* come from the user or a template.

## Section source (priority)

1. **User-provided sections always win.** If the user lists headings or a custom outline, use that exact structure.
2. Else use a **named template** the user or caller asked for (`task`, `rfc`, `tech-comparison`, `ab-test-report`).
3. Else pick the **closest template**, and state which one you picked and why in one line at the top (`template: <name> · reason: …`).

Templates live beside this skill: [templates/](templates/). Each file lists sections and the default visual for that section. The four starters are enough for plan / RFC / compare / experiment asks; do not invent new template files unless the user asks.

`development-workflow`'s document step means: run visual-plan with the **rfc** template (unless the user overrode sections or named another template).

## Visualisation guideline

Map content kinds to visuals (pick only what the content needs):

| Content kind | Default visual |
| --- | --- |
| Steps, user flow, before→after process | Workflow chart (Mermaid flowchart) |
| Components, boundaries, add/change/remove | Architecture diagram |
| Requests, payloads, contracts, ordering | Data-flow or sequence diagram |
| Impact × risk, effort, or score intensity | Heat map (SVG if Mermaid cannot) |
| Phases, commits, rollout, milestones | Timeline |
| Options with choice + why | Decision table |
| Multi-criteria option scores | Scored matrix |
| Experiment metrics / lifts | Charts with confidence ranges |

Rules:

- Every section **leads with its visual**; caption ≤ ~3 lines.
- Ground current state in inspected code or data with real paths/figures. Label proposals. Invent nothing.
- **Mermaid by default**; SVG only where Mermaid cannot (e.g. heat-map grid, custom charts).
- **Render-check** every diagram before presenting.
- Prefer stable section ids (`{#slug}`) and per-commit or per-phase tags on diagram nodes so all three outputs share structure.
- End with short **Verification** and **Out of scope** lists when the template (or user) includes them; do not invent sections the template omitted unless the user asked.

## Outputs (every run)

Produce **all three** from the same sections and diagrams (same facts):

1. **`plan.md`** — plain Markdown prose/bullets, **no diagrams**. The conventional wordy form of the plan (useful as the "before" in a comparison and for terminals that will not render Mermaid).
2. **`visual-plan.md`** — diagrams-first Markdown (embedded Mermaid; SVG files beside it when needed). Put `template: <name>` at the top.
3. **`visual-plan.html`** — one **self-contained** interactive HTML page of the same plan:
   - Mermaid via CDN (or inline) + small vanilla JS; **no build step**, no bundler
   - Collapsible sections
   - Heat-map hover → risk/impact reason (when a heat map exists)
   - Commit/phase **step-through** that highlights affected nodes (when a timeline exists)
   - Optional click on architecture nodes → files/commits
   - **Before/after workflow toggle** when a plain `plan.md` (or before-state diagram) exists for comparison
   - Axis titles on heat maps: Risk along the left, Impact under the columns

Save the three files next to each other in the working directory the user named (or a sensible draft folder) and report their paths.

## Example

[references/product-cache/](references/product-cache/) — mock task-template visuals (architecture + data-flow SVGs and a sample plan; no runnable fixture). Scenario choices there are not requirements for other plans.
