# PR #432 — `feat(webapp): unify game and developer views`

**State:** MERGED into `main` (head `28496a8c`, 21 files, +861/−197). Nothing below is
blocking; it is all follow-up.

**Baseline (PR head, scratch worktree at `/private/tmp/pr432-review-osv/wt`):**
`tsc --noEmit` clean · `next lint` clean · `jest` 147/147 · `playwright` 37/37 (50.2s)
· `pnpm webapp e2e:production` 4/4 (1.7s). Every claim below is measured against
that green baseline. Ports 3432/3433 only.

---

## Short answer to "what can we delete"

The PR is **less bloated than it looks**. Of the 861 added lines, 341 are tests,
docs and Playwright config, and 172 lines of source were deleted (`DevView`,
`TabPanel`, the duplicated observer banner). The real surface is 519 new source
lines, and **205 of them are one file**: `DevToolsWidget.tsx`.

That file is where the deletion is. I attempted to delete five other things that
looked deletable and all five turned out to be load-bearing — details in
"Rejected claims" so nobody re-raises them.

**Verified deletable: ~100 lines, gate stays green.**

---

## Valid findings

### F1 — `DevToolsWidget.tsx` is 205 lines because 18 inline style objects and two copy-pasted radio fieldsets are inlined into JSX. It compresses to 102.

`packages/webapp/src/components/dev/DevToolsWidget.tsx`

Two things bloat it:

1. **18 `style={{…}}` literals**, including a 24-line `isMobile ? {…} : {…}`
   ternary passed to `Modal`, that are all static CSS. The project already has a
   `.modal` class block in `src/app/globals.css`; this widget is the only place in
   the new code that hand-rolls the same thing in JS.
2. **Two near-identical `<fieldset>` radio blocks** (Perspective, Transport) written
   with two different idioms — a module-level `PERSPECTIVE_OPTIONS` array of objects
   vs. an inline `as const` tuple array — for the same markup.

Knock-on: the `style?: React.CSSProperties` prop added to the shared
`design/Modal.tsx` in this PR has **exactly one consumer**, this widget
(`rg -n "<Modal" -A6 src` → only `DevToolsWidget.tsx:71`). It is a styling escape
hatch cut into a production design-system component for a dev-only surface.

**Fix (prototyped and verified, patch attached as `simplify-DevToolsWidget.patch`):**
move the static styles into a `.dev-tools*` block in `globals.css`, extract one local
generic `RadioGroup<T>` used by both fieldsets, and swap `Modal`'s `style` prop for
`className` (same surface area, keeps styling in CSS).

| Measure | Head | After |
| --- | --- | --- |
| `DevToolsWidget.tsx` | 205 lines | 102 lines |
| Net across all touched files | — | **−80 lines** (+24 CSS) |

Verified on the prototype, not inferred:

```
pnpm exec tsc --noEmit                -> clean
pnpm exec next lint                   -> No ESLint warnings or errors
pnpm exec jest --runInBand            -> 147 passed
PLAYWRIGHT_WEB_PORT=3432 PLAYWRIGHT_GAME_SERVER_PORT=3433 \
  pnpm exec playwright test           -> 37 passed (49.7s)
```

Note this is a refactor of a dev-only surface, so the payoff is maintenance, not
user-facing. If the widget is expected to stay frozen, this is legitimately
skippable — but it is the only place in the diff where real volume is available.

### F2 — `getFirstValue` is defined twice

`packages/webapp/src/app/dev/page.tsx:9-11` duplicates the private
`getFirstValue` in `packages/webapp/src/components/dev/devConfig.ts:94-96`, and the
page already imports `SearchParamValue` from that module. Export the `devConfig`
one and delete the page-local copy. Verified: gate green.

### F3 — `stubPlayerNameMap` is exported but has no external importer

`packages/webapp/src/components/playerNameMap.ts:4`. `rg -n "stubPlayerNameMap"`
across the repo returns only its own declaration and its use on line 21 of the same
file — the only external import anywhere is `getPlayerName`. Drop the `export`.
(The `playerNameMap` → `stubPlayerNameMap` rename in this PR was safe precisely
because the old name had no importers left after `DevView` was deleted.)

### F4 — `handlePerspectiveChange` is an identity wrapper

`packages/webapp/src/components/dev/DevGameHost.tsx` — the handler is
`(next) => setPerspective(next)`. Pass `setPerspective` directly. (`handleTransportChange`
is **not** the same case: it early-returns on a no-op and resets `matchID`. Keep it.)

### F5 — `data-testid={`dev-perspective-${option.value}`}` has no consumer

`DevToolsWidget.tsx:137`. `rg -n "dev-perspective-"` matches only the emitting line;
the e2e helpers select perspective radios by accessible name and only
`dev-transport-offline` is selected by testid. Dead attribute.

### F6 — `hasLocalSetupOverrides` prop chain is untested and product-optional

`DevGameHost.tsx:89` → `DevToolsWidget.tsx:23,31,196-200`, a three-hop prop whose
only effect is a hint paragraph. Nothing covers it. Deleting it keeps the gate green
(verified) — but it removes visible copy, so this is your call, not dead code.
Flagging it as a decision, not a defect.

**F2–F6 verified together:** `tsc` clean, `next lint` clean, `jest` 147/147,
`playwright` 37/37 (54.9s), −20 lines net.

---

## Rejected claims (all of these look deletable and are not)

These are the ones I would have shipped as findings without running the experiment.
Recording them so the next reviewer does not re-raise them.

| Claim | Experiment | Result |
| --- | --- | --- |
| **The 33-line `onKeyDownCapture` focus trap in `design/Modal.tsx` duplicates native `<dialog>.showModal()` focus containment.** | Deleted the whole handler + `FOCUSABLE_SELECTOR`, ran full e2e. | **Killed.** `multiplayer.spec.ts:56 contains keyboard focus and restores it to the launcher` fails (36/37). |
| Follow-up: *the trap only survives because the test artificially sets `position:fixed` on the close button.* | Deleted the handler **and** the test's `element.style.position = 'fixed'` mutation, reran. | **Killed.** Still fails at `expect(lastControl).toBeFocused()`. Chrome's native modal dialog does **not** wrap Shift+Tab from the first control back to the last — it escapes to browser chrome. The trap buys real behavior, not a rigged test. |
| **The radio-group filter inside the trap duplicates the browser's own "skip unchecked radios" tab behavior.** | Replaced the 13-line filter with `const focusable = candidates;`, kept the rest, reran focus tests. | **Killed.** Same test fails. The filter is not about tab order — it identifies the correct *last tabbable element*, which would otherwise be the unchecked `online` radio. |
| **`GameView`'s `boardKey` prop is speculative remount plumbing.** | Removed `boardKey` from `GameView.tsx` and `DevGameHost.tsx`, ran full e2e. | **Killed.** `game-flow.spec.ts:365 Scenario 10` fails (reproduced twice). Changing `playerID` without remounting leaves a stale boardgame.io client. |
| **The production e2e harness (`playwright.production.config.ts`, `production-dev-route.spec.ts`, `e2e:production`) is heavy machinery to guard one `notFound()` call.** | Ran `PLAYWRIGHT_PRODUCTION_WEB_PORT=3432 pnpm run e2e:production`. | **Killed.** 4 tests in **1.7s**; the ~46s is the `next build`, and `build.yml` *replaced* the standalone `pnpm webapp build` step with this — near-zero incremental CI cost. |
| **The three `DEV_URLS` all hit the same `notFound()` and two are redundant.** | Timed them in the run above. | **Not worth raising.** 0.3s combined, and `/dev?dev=true` is a deliberate regression guard for the `?dev=true` production bypass this PR removed. |
| **The always-rendered launcher (`opacity: 0` + `pointerEvents: none`) should just unmount.** | *Not tested.* | Withdrawn as unproven. The commit sequence (patch 1 → patch 2) shows it was changed from conditional-render deliberately, plausibly for native dialog focus restore, but I did not run it. |

---

## Follow-up notes (not deletions)

- **N1 — `cp` list drift.** `package.json` `e2e:production` copies `.next/static` and
  `public` into the standalone dir, duplicating `Dockerfile:58-60` by hand. If the
  Dockerfile gains a fourth copy, the production e2e silently stops matching the
  deploy. Worth a cross-referencing comment on both sides.
- **N2 — `role="alert"` on `<main>`.** `dev/page.tsx` puts `role="alert"` on the
  `<main>` element, which overrides the `main` landmark. Use an inner
  `<div role="alert">`.
- **N3 — two match-ID generators.** `dev/page.tsx` builds `dev-${randomUUID()}`
  (node) and `DevGameHost.createMatchID()` builds the same format from
  `window.crypto.randomUUID()`. One exported helper would do.

---

## Verdict

Already merged, so: no blockers, no re-open. If you want the bloat gone, F1 is the
only change with meaningful volume (−80 lines, patch attached and gate-verified);
F2–F5 are a 20-line tidy-up that can ride along. Leave the focus trap, the radio
filter, `boardKey`, and the production e2e alone — I tried to delete all four and
the suite caught every one.
