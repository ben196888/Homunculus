# Inline (line-anchored) comments — PR #432

All against merge commit `078e736ccb9d8473f650daf93ba7c7cb34568272`.

---

### 1. `packages/webapp/src/components/design/Modal.tsx` — lines 3-5 and 101-133

**Anchor:** the `FOCUSABLE_SELECTOR` const and the `onKeyDownCapture` handler.

> Native `showModal()` already contains focus here. I probed it in this repo's
> own Chromium (Playwright 1.61.1) with a page mirroring the drawer DOM: across
> 8 Tabs, focus never reached a sibling `<button>` before the dialog, one after
> it, or a `position: fixed; z-index: 1301` launcher. Native also already skips
> unchecked radios in a group, so lines 108-120 re-derive browser behaviour.
>
> The only thing native doesn't do is skip the one document-boundary stop before
> wrapping. That's the entire benefit of these ~40 lines, and they land on a
> component with three production call sites (`BoardGame` end-game modal,
> `ExitDialog`, `game/[matchID]/page.tsx`), not just the dev drawer.
>
> Suggest deleting the handler and the selector (keeping `style` and
> `tabIndex={-1}`) and relaxing the corresponding e2e assertions to check
> containment rather than exact wrap targets. If you'd rather keep the wrap, fine
> — but see the docstring comment below.

---

### 2. `packages/webapp/src/components/design/Modal.tsx` — lines 7-13

**Anchor:** the component docstring.

> This still says `showModal()` supplies "an inert background (a real focus
> trap)". That's accurate about the platform, but it now sits directly above 40
> lines of manual focus trapping, which reads as a contradiction to the next
> person here. If the manual trap stays, this needs a sentence explaining what it
> adds over native (the wrap-past-browser-chrome stop) so nobody deletes one or
> the other by accident.

---

### 3. `packages/webapp/e2e/multiplayer.spec.ts` — lines 68-75

**Anchor:** the comment `// Fixed-position controls are visible and must remain in the modal's focus loop.`
and the `closeButton.evaluate(... position = 'fixed')` block.

> This describes a browser gap that doesn't exist — I measured identical native
> Tab order with and without `position: fixed` on a control inside the dialog.
> The real history is that the first version of the trap filtered on
> `offsetParent !== null` (6ec8342), which is `null` for fixed positioning, so the
> trap dropped its own close button; 81fa712 fixed it with `getClientRects()`.
>
> So this is a regression test for the trap, not for modal behaviour. Worth
> re-wording the comment to say that, otherwise it reads as evidence the trap is
> necessary.

---

### 4. `packages/webapp/src/app/dev/page.tsx` — lines 8-10

**Anchor:** `function getFirstValue(value: SearchParamValue): string | undefined { ... }`

> Byte-identical to the private `getFirstValue` in
> `src/components/dev/devConfig.ts:23-25`. Export that one and delete this copy.

---

### 5. `packages/webapp/src/components/GameView.tsx` — line 16

**Anchor:** `const isObserver = boardProps.playerID == null;`

> Non-blocking, just noting the semantic drift: the game room previously gated
> this banner on `!credentials` (`game/[matchID]/page.tsx`, removed block). These
> agree for every current caller since `playerID` is passed as
> `credentials?.playerID`, but the condition now means "no seat" rather than "no
> credentials". If a `MatchCredentials` ever carries an undefined `playerID`, the
> banner appears where it previously didn't.

---

### 6. `packages/webapp/src/app/dev/page.tsx` — lines 31-47

**Anchor:** the invalid-config `<main role="alert">` branch.

> Optional, author's call: this branch plus the `DevConfigResult` union and error
> accumulation in `devConfig.ts` is ~40 lines to reject typos in a dev-only URL,
> and could collapse to "unknown value -> use the default".
>
> I'd keep it — silently substituting player1 for `?user=player4` would send
> someone chasing a phantom bug — but flagging it since it's the second-largest
> optional block in the diff.
