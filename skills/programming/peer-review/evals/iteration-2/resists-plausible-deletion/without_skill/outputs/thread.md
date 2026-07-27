Retrospective pass on this one (already merged) — the question I was asked was
"what can we delete, it feels bloated". Answer: less than it looks, and the best
candidate isn't in the dev harness.

**The one I'd actually cut: the hand-rolled Tab trap in `design/Modal.tsx`.**

I probed native `<dialog>.showModal()` in this repo's own Chromium (Playwright
1.61.1) against a page mirroring the drawer's DOM. Native already gives us
everything the trap implements except one thing:

- containment — focus never reached elements outside the dialog across 8 Tabs,
  including a `position: fixed` sibling with `z-index: 1301`;
- radio groups — native already skips unchecked radios, so the 12-line
  de-duplication filter is re-deriving browser behaviour;
- a `position: fixed` control *inside* the dialog — identical Tab order before
  and after setting `position: fixed`;
- stacked dialogs — the second `showModal()` confined the cycle to itself.

The only real gap: native inserts one stop at the document/browser-chrome
boundary before wrapping. So ~40 lines of shared-component focus logic buys us
one fewer dead Tab press.

Two reasons that's worth revisiting rather than shrugging at:

1. The test comment at `e2e/multiplayer.spec.ts:69` ("Fixed-position controls
   are visible and must remain in the modal's focus loop") describes a problem
   the browser doesn't have. That assertion exists because the trap's first
   version used `offsetParent !== null` (6ec8342), which is `null` for
   `position: fixed`, so it dropped its own close button — fixed in 81fa712 with
   `getClientRects()`. The test is guarding a regression the trap introduced.
2. `Modal` has four call sites and three are production (`BoardGame` end-game
   modal, `ExitDialog`, the game room page). A dev-harness keyboard nicety is now
   carried by every production dialog.

Also worth noting either way: the docstring at `Modal.tsx:7-13` still says
`showModal()` supplies "an inert background (a real focus trap)", which the 40
lines below it now contradict.

Suggested: drop `onKeyDownCapture` + `FOCUSABLE_SELECTOR`, keep `style` and
`tabIndex={-1}`, and relax the two exact-target assertions to "focus stays inside
the drawer". Net ~-52 lines. Entirely reasonable to keep the polished wrap
instead — but then the comment and the test rationale should be corrected.

**Things I looked at as deletion candidates and would keep**, in case they come
up again:

- `playwright.production.config.ts` + `production-dev-route.spec.ts` +
  `e2e:production`. This didn't add CI time — it *replaced* `pnpm webapp build`,
  and the script builds first. `serves standalone client assets` is the only
  coverage we have for the hand-staged standalone output (`Dockerfile:58-60`
  copies `.next/standalone`, `.next/static` and `public` separately); break that
  and we ship a JS-less site with a fully green suite. And the 404 assertions are
  the only proof the old `?dev=true` production bypass is really gone, since the
  gate only evaluates in a built app.
- `e2e/devTools.ts` — 43 lines replacing ~12 inline tab-click sites across three
  specs; net negative.
- `GameView.tsx` — absorbs the 30 lines of observer banner deleted from the game
  room page; two real call sites.

One non-deletion note: `GameView.tsx:16` moved the observer-banner condition from
`!credentials` to `playerID == null`. Equivalent for all current callers, but the
meaning shifted from "no credentials" to "no seat". Fine today; just flagging the
semantic drift.
