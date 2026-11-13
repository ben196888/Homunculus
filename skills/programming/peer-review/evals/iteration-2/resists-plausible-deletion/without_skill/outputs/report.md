# Review — PR #432 `feat(webapp): unify game and developer views`

State: **MERGED** (2026-07-26, merge commit `078e736c`). 21 files, +861 / −197.
All checks green on the merge commit. Everything below is retrospective — nothing
was posted to GitHub.

## Short answer

It reads bloated, but most of the bulk is load-bearing. I went looking for things
to cut and found roughly **~55 lines** worth deleting, not hundreds — and the
single biggest candidate is not any of the new dev files. It's the 40-line
hand-rolled Tab trap that got added to the **shared production** `Modal`.

Three buckets below: cut, author's call, keep (and why the obvious cut is wrong).

---

## 1. Worth cutting

### 1a. The hand-rolled focus trap in `Modal.tsx` (~40 lines + ~12 lines of e2e)

`packages/webapp/src/components/design/Modal.tsx:98-133` adds an
`onKeyDownCapture` Tab handler with a `FOCUSABLE_SELECTOR`, a visibility filter,
and a 12-line radio-group de-duplication pass.

I probed native `<dialog>.showModal()` behaviour directly in the repo's own
Chromium build (Playwright 1.61.1, headless) against a page mirroring the
drawer's DOM. Results:

| Behaviour the trap implements | Native `showModal()` already does it? |
| --- | --- |
| Focus never escapes to elements outside the dialog | **Yes** — `outside-before`, `outside-after` and the fixed-position `launcher` were never reachable across 8 Tabs |
| Unchecked radios in a group are skipped | **Yes** — only `p1` and `off` (the checked members) appeared in the cycle |
| A `position: fixed` control inside the dialog stays in the loop | **Yes** — identical order before and after setting `position: fixed` |
| Stacked dialogs confine focus to the topmost | **Yes** — second dialog cycled `keep -> leave -> ...` only |
| Tab from last wraps straight to first | **No** — native inserts one stop at the document/browser-chrome boundary |

So the trap buys exactly one thing: it removes a single dead Tab stop per cycle.
Everything else in it is a re-implementation of behaviour the browser was
already providing.

Two things make this worth raising rather than shrugging at:

- **The stated justification doesn't hold.** The e2e comment at
  `e2e/multiplayer.spec.ts:69` says *"Fixed-position controls are visible and
  must remain in the modal's focus loop."* Native handles that fine (row 3
  above). That assertion exists because the trap's **first** version used
  `element.offsetParent !== null`, which is `null` for `position: fixed`, so the
  trap dropped its own close button. Commit `6ec8342` introduced it; commit
  `81fa712` fixed it with `getClientRects()`. The test is guarding a
  self-inflicted regression, not a browser gap.
- **The blast radius is production.** `Modal` has four call sites
  (`BoardGame.tsx` end-game modal, `board/ExitDialog.tsx`, `game/[matchID]/page.tsx`,
  and the dev widget). Three are production dialogs. A dev-only harness need is
  now imposing hand-rolled focus logic on all of them, and the radio filter can't
  be dropped independently — once you compute your own order you own the whole
  order.

Also: the docstring at `Modal.tsx:7-13` still says showModal supplies
*"an inert background (a real focus trap)"*. That is now directly contradicted by
the 40 lines below it. Whatever you decide, that comment should stop lying.

**Suggested cut:** delete the `onKeyDownCapture` block and `FOCUSABLE_SELECTOR`,
keep `style` and `tabIndex={-1}`, and relax the two Shift+Tab/Tab assertions in
the *contains keyboard focus* test to assert containment (focus stays inside the
drawer) rather than exact wrap targets. Net approx -52 lines. Cost: one extra Tab
press to get around the drawer. If you'd rather keep the polished wrap, that's
defensible — but then fix the comment and drop the bogus "fixed controls"
rationale from the test.

### 1b. Duplicated `getFirstValue` (3 lines, free)

`src/app/dev/page.tsx:8-10` defines `getFirstValue`, and
`src/components/dev/devConfig.ts:23-25` defines the identical function privately.
Export the one in `devConfig.ts` and delete the copy in the page.

---

## 2. Author's call — defensible either way

**The invalid-config error page** (`dev/page.tsx:31-47`, ~17 lines of JSX) plus
the `DevConfigResult` union and error accumulation in `devConfig.ts:19-21,44-62`
(~20 lines) plus one test case. You could collapse all of it to "unrecognised
value -> fall back to the default" and save ~40 lines.

I'd keep it. In a dev harness, silently swallowing `?user=player4` and quietly
showing you player1 is worse than a loud error — you'd chase a phantom bug. But
if you want a number for the "what can I delete" column, this is the second
largest one and it's genuinely optional.

---

## 3. Do **not** delete these — they look like padding and aren't

### `playwright.production.config.ts` + `production-dev-route.spec.ts` + the `e2e:production` script + the CI change (~50 lines, 4 files)

This is the block that most looks like ceremony for a one-line assertion, and
it's the one I'd most strongly push back on cutting.

- **It costs almost nothing in CI.** `.github/workflows/build.yml` did not *add*
  a step — it **replaced** `pnpm webapp build` with `pnpm webapp e2e:production`,
  and that script runs `pnpm run build` as its first action. Delete the spec and
  you must put the bare `build` step back, or CI stops compiling the app at all.
- **The first test isn't about `/dev`.** `serves standalone client assets`
  fetches `/`, scrapes the first `/_next/static/*.js` from the HTML, and asserts
  it returns 200. That is the only thing in the repo that exercises the
  hand-rolled standalone packaging — `Dockerfile:58-60` stages
  `.next/standalone`, `.next/static` and `public` by three separate manual
  `COPY`s, and the `e2e:production` script mirrors them with `cp -R`. A mistake
  there ships a site with no JS and every other test in the suite passes.
- **It's the only thing proving the `?dev=true` bypass is really gone.** The PR
  removed a production backdoor. `/dev?dev=true` returning 404 in a *real
  production build* can't be asserted from the dev-server suite, because the gate
  is `process.env.NODE_ENV === 'production'`, which is only true in a built app.

If you want to trim here, the honest target is one test case (`/dev?user=...&mode=...`
is near-redundant with plain `/dev`), which saves nothing. Leave it.

### `e2e/devTools.ts` (43 lines)

Four helpers used by three spec files, replacing ~12 inline `getByRole('tab')`
click sites. This is net negative lines across the suite, not additive.

### `GameView.tsx` (44 lines)

Looks like a wrapper for its own sake, but it absorbs the 30 lines of observer
banner deleted from `game/[matchID]/page.tsx:258-284` and is the seam
`DevGameHost` composes the widget into. Two real call sites, real dedup.

### `devConfig.test.ts` (53 lines)

Cheap unit coverage of the only pure function in the PR. Keep.

---

## 4. One behaviour change worth knowing about (not a deletion)

`GameView.tsx:16` gates the observer banner on `boardProps.playerID == null`.
The old code in the game room gated it on `!credentials`. These agree for every
current call site, because `playerID` is passed as `credentials?.playerID` — but
the meaning moved from *"no credentials"* to *"no seat"*. If a `MatchCredentials`
object ever carries an undefined `playerID`, the banner now appears where it
previously didn't. Low risk, no action needed, just don't be surprised by it.

---

## Bottom line

Realistic deletion budget: **~55 lines** (the Modal trap + its two e2e
assertions + the duplicated helper), optionally ~95 if you also drop the
dev-config error page. The 21-file spread is mostly a genuine 1-to-1 replacement
(`DevView` + `TabPanel` out, `DevGameHost` + `DevToolsWidget` + `devConfig` in)
plus test migration — the diff is wide, not padded. The thing actually worth
your attention isn't the new dev-harness code at all; it's that a dev-only
keyboard nicety got welded onto the shared production `Modal`, and the test
defending it is defending a bug that code introduced.
