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

**Rename checklist for an id:** `templates/<id>.md` filename + H1/`template-id` comment; this table; README skill blurb; `<!-- template: <id> -->` in references; cross-mentions in other templates or SKILL prose.

`development-workflow`'s document step uses **`rfc`** only (unless the user overrode sections or named another template). Use **`implementation-plan`** when the user or caller asks for an approval-oriented plan directly.

Pick **`implementation-plan`** (not **`task`**) when the deliverable is a decision callout, before/after behavior table, unchanged list, and status checklist for human approval before coding. Keep **`task`** for commit-sized engineering breakdowns (heat map + commit timeline). Keep **`rfc`** for cross-cutting architecture with option trade-offs.

## UI changes in approved plans

Every UI plan that is approved and hashed (task plans, RFCs, and the Dexter plan flow, where it is typically the start of `scope`) must contain a `## Wireframes` section **near the top of `plan.md`**, before the long Scope prose. Files, tests, and risks come after it. This replaces the earlier batch-2 convention of separate **Target layout** and **Expected UI** sections.

For each UI change, all four blocks are required:

1. Desktop · current
2. Desktop · target
3. Mobile · current
4. Mobile · target

Rules:

- Each block is a monospace ASCII box drawing in a fenced ```text block. It renders everywhere and is part of the hashed text.
- Label with exact UI copy (Chinese when the product is Chinese). Mark anything not found in the source design as **proposed**.
- After the four blocks, add a short **Annotations** table mapping each labelled element to the component/file that changes.
- Expected-UI *states* (hover, empty, error, flow steps) may follow as extra fenced frames after the four required blocks.
- An SVG/PNG referenced by content hash for a Canvas/Page is optional. It is a supplement, never a substitute. `visual-plan.html` and Canvas are supplements too.
- Keep each plan under ~12KB.

Ground the wireframes in the source design: the prototype capture (for OSV, `/workspace/osv-prototype-capture`) and cached Figma (`/workspace/bin/figma-cache`). Never make new Figma MCP reads.

Non-UI plans skip the section and include exactly: `Wireframes: not applicable — no UI change`. The older line `Target layout / Expected UI: not applicable — no UI change` is still accepted as valid.

Template snippet:

````markdown
## Wireframes

**Desktop · current**
```text
┌ 1024px ─────────────────────┐
│ <exact current copy>        │
└─────────────────────────────┘
```
**Desktop · target**
```text
┌ 1024px ─────────────────────┐
│ <exact target copy> (proposed) │
└─────────────────────────────┘
```
**Mobile · current**
```text
┌ 375px ──────┐
│ ...         │
└─────────────┘
```
**Mobile · target**
```text
┌ 375px ──────┐
│ ...         │
└─────────────┘
```

| Label | Component / file | Change |
| --- | --- | --- |
| `<exact copy>` | `src/.../Component.tsx` | what changes |
````

### Game rules / hidden information

Wireframes, flow frames, and described animations or transitions must never reveal hidden information before the player's confirming action. Example: in OSV 換人力 (refill, issue #496), new job cards must not appear in any transition or animation before 確認人力. A plan showing new cards sliding up before confirm was a hidden-information leak. Until confirm, show backs, ghosts, or still-current faces; ×, swap, and 取消 must not deal or flip new faces. The same applies to deck draws, unseen hands, and any other hidden game information. A leak is a **blocking defect**.

### Wireframe self-check

Run before hashing and submitting for approval:

- [ ] `## Wireframes` is near the top of plan.md (or the non-UI exemption line is present)
- [ ] Before and after, desktop and mobile, in fenced ```text blocks
- [ ] Exact UI copy; proposed items marked
- [ ] Annotations map labels to files/components
- [ ] Hidden information: no frame or animation note reveals hidden info before the confirming action
- [ ] ASCII is in the hashed text; images/HTML/Canvas are supplements
- [ ] Plan stays under ~12KB

Worked example: [references/ui-hand-off/plan.md](references/ui-hand-off/plan.md).

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
- **Mermaid by default**; SVG only where Mermaid cannot (e.g. heat-map grid, custom charts). UI wireframes use the text formats required above.
- **Render-check** every diagram before presenting.
- Prefer stable section ids (`{#slug}`) and per-commit or per-phase tags on diagram nodes so all outputs share structure.
- End with the closing lists the template (or user) includes — e.g. **Verification** / **Out of scope**, or **Unchanged** / **Status** on `implementation-plan`; do not invent sections the template omitted unless the user asked.

## Outputs

Produce these from the **same sections and diagrams** (same facts). Outputs 1–2 are **required** on every run. Outputs 3–4 are **optional**: produce each one when the environment supports it, and **skip it** when it does not (for example no way to write or open an HTML file, no Canvas tool, or the user opted out). Never block the plan on a skipped output; say which outputs were skipped and why in one line.

1. **`plan.md`** — plain Markdown prose/bullets, with an inline `## Wireframes` section for UI changes as required above; no other diagrams. The conventional wordy form of the plan (useful as the "before" in a comparison and for terminals that will not render Mermaid).
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
- [references/ui-hand-off/](references/ui-hand-off/) — mock UI plan with the required `## Wireframes` before/after desktop and mobile blocks, annotations, and a hidden-information confirm flow.

Scenario choices in examples are not requirements for other plans.
