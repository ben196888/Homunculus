# PR #425 — claim verification report

**PR:** ocftw/open-star-ter-village#425 — `fix(webapp): exit-choice dialog, leave-terminates, lobby re-entry and spectate`
**State:** MERGED (squash) as `6cfedcb4`; base `162bf212`; branch head was `ec4282db` (evidence cites `0e82a9d3`).
**How verified:** disposable clone at `/private/tmp/prreview-425-cace19/repo` checked out at the merge commit; full `pnpm install`; `next lint`, `tsc` (both configs), `jest --runInBand`, Playwright on ports 3425/3426, plus four throwaway Playwright probes written to attack specific claims. Every command and its real output is in `transcript-notes.md`.

Bottom line: **the description is mostly honest.** Nine of the ten behavioural promises are real and reproducible in a live browser. There is **one genuine functional hole** worth bugging the author about, one **stale-evidence process issue**, and a handful of low-value accuracy nits you can bundle or drop.

---

## Verified TRUE — do not raise these

| Claim | How it was confirmed |
| --- | --- |
| Leave opens a three-choice dialog with no navigation before an explicit choice | `GameHeader.tsx` renders `<ExitDialog>` only when `exitOpen`; the PR's own e2e asserts the URL is unchanged while the dialog is open; passes. |
| 取消 / Escape / backdrop all close safely, focus returns to the invoking control | Probe 2 in real Chromium: Escape unmounts the dialog (count 0), backdrop click at (5,5) unmounts it, `document.activeElement` is back on `header-leave`. The jest tests only fire a synthetic `cancel`, so this needed a real browser — it holds. |
| Terminated overlay is genuinely non-dismissible with an inert background | Probe 4: Escape → still there, backdrop click → still there, `link.focus()` on the nav link does **not** move `document.activeElement` (real `<dialog>` inertness), and it survives a page reload. |
| 離開座位 terminates the match for the whole table and the room drops out of the lobby | The PR's own e2e passes; probe 4 reproduces it independently and the leaver's lobby shows 0 rows for the room. |
| 回到桌子 is credential-based, never name matching | `lobby/page.tsx` builds `mySeatMatchIDs` purely from `loadCredentials(matchID)`. No name comparison anywhere in the lobby. |
| Stale credentials route to the room and demote to observer | Probe 3: planted a bogus `{playerID:'1', credential:'bogus', playerName:'Impostor'}` blob. The lobby row rendered `data-action="return"` with 回到桌子; clicking it landed in observer mode and the bogus entry was cleared from localStorage. |
| No MUI dialog remains | `BoardGame.tsx` was the last `Dialog`/`DialogContent` import; it is gone. (MUI itself is still all over `Alert`/`Snackbar`/`Box`/`Tabs` — the claim is correctly scoped to dialogs.) |
| GameOverDialog migrated to the bespoke shell, behaves unchanged | Real, though it lives in `BoardGame.tsx`, not the `GameOverDialog.tsx` the body names. Its 5 existing tests pass. |
| Compact header shows only the seated player's chip + a ⋯ menu with `aria-haspopup` and 44px targets | `GameHeader.tsx` `chipIDs`; `.icon-btn` / `.menu-item` in `globals.css` are both 44px minimum. |
| Lint / tsc / jest / Playwright green | `next lint` clean, both `tsc --noEmit` clean, jest **140/140**, Playwright **16/16** on the multiplayer spec. |

**One false alarm to ignore:** the first full Playwright run showed 5 failures in `multiplayer.spec.ts` starting at "Alice starts the game". That was a stale listener already bound to :3426 (`EADDRINUSE` at the top of the log), not a code defect. A clean re-run is fully green. Do not report it.

---

## Finding 1 (Medium, real) — 回大廳 loses the room entirely if every seated player steps out

This is the one worth the author's time, because it undercuts the PR's headline promise ("回大廳 keeps the seat; the lobby then offers 回到桌子").

`回大廳` keeps the seat name but drops the socket. `isAbandonedMatch` in `packages/webapp/src/app/lobby/actions.ts:64-67` treats a match as abandoned when **every** player is `!name || isConnected === false`, and `toVisibleMatch` filters `Abandoned` rooms out of the lobby entirely. So once the last connected player uses 回大廳, the room disappears — including from the lobby of the very players whose seats are still reserved in it.

Reproduced (probe 1): three players joined, host started, all three chose 回大廳. Server metadata afterwards:

```json
{"players":[{"id":0,"name":"P0","data":{"started":true},"isConnected":false},
            {"id":1,"name":"P1","isConnected":false},
            {"id":2,"name":"P2","isConnected":false}]}
```

Lobby row count for that room: **0**. 回到桌子 button count: **0**. Only a bookmarked `/game/<id>` URL recovers it.

Realistic triggers: the group takes a break together; or Alice uses 回大廳 while Bob and Charlie simply close their tabs. The PR's own e2e never catches this because Bob and Charlie stay connected throughout.

`isAbandonedMatch` predates this PR (it came with #424), so this is not a regression — but #425 is the PR that promises re-entry, so it owns the gap. Suggested direction: do not treat a match with named seats and `data.started === true` as abandoned purely on connection state, or surface a "your reserved rooms" section that bypasses the visibility filter.

## Finding 2 (Low–Medium, real) — the evidence table is stale relative to what merged

The whole Evidence block is pinned to `0e82a9d3`, but `ec4282db` landed after it and **materially rewrote the dialog**: `Modal.tsx` dropped the manual `cancel` listener + `onCloseRef` in favour of React's `onCancel` prop, `jest.setup.ts` stopped dispatching a `close` event, and `ExitDialog` swapped `ariaLabel` for `aria-labelledby` / `aria-describedby`. That commit also added a 7th ExitDialog test.

So the stated numbers do not describe the merged tree: **140 jest tests, not 139; 7 ExitDialog tests, not 6.** Per `CONTRIBUTING.md` the body should have been re-run and updated after `ec4282db`.

The risky part of that late change was checked: React 18 attaches `cancel` as a non-delegated event, so `onCancel` genuinely fires — Escape works (probe 2). No bug, just unverified-at-merge evidence.

## Finding 3 (Low, real) — the terminated-match guard is not the guard the body describes

Body: "a **mixed** named/unnamed seat list … dev-harness matches (all seats unnamed) are unaffected."
Code (`src/app/game/[matchID]/page.tsx:146-147`): `hasStarted && match.players.some(p => !hasPlayerName(p))` — that is *some* unnamed, not *mixed*. An all-unnamed started match would trip it.

Behaviour is still correct, but for a reason the body does not state: the dev harness is a local match on `/dev` that never renders this page at all. The safeguard the description advertises does not exist in the code. Worth a one-line correction so nobody later "fixes" it based on the changelog.

## Finding 4 (Low, real) — the `.Mui*` CSS removal is not in this PR

Stated twice ("no `.Mui*` CSS remain in the app", "No `.Mui*` CSS remains"). The branch does contain `330fbb61`, which deletes 15 lines from `globals.css` — but the **net** diff against the merge base has **zero deletions** in `globals.css` (65 insertions, 0 deletions). #424 had already removed it. True of the app, not attributable to this PR.

## Finding 5 (Low, real) — the room page now polls forever

`usePolling(pollMatch, 3_000, !isExpired)` replaced a condition that stopped once the board was up. Measured: **3 metadata requests per 10s while the board is showing**, per client, for the whole game — and it keeps going indefinitely behind the terminated overlay and after game over. The Risks section mentions the 3s poll only as a latency bound; the cost change is not called out. Reasonable ask: stop polling once `isTerminated` is latched, since nothing can change it back.

## Nits (bundle or drop)

- **⋯ menu keyboard support.** `role="menu"` / `role="menuitem"` with no Escape-to-close and no arrow-key navigation; the dismiss layer is an `aria-hidden` div with `onClick` only. The `aria-haspopup` and 44px claims are true, but the menu is not keyboard-operable.
- **Dead credentials linger.** After termination, remaining players keep their localStorage credential for the dead room forever (probe 4: `STILL PRESENT`). No symptom today because the room is filtered out of the lobby.
- **`GameOverDialog` indentation.** The MUI-wrapper removal in `BoardGame.tsx` left the inner JSX at the old nesting depth. Lint passes; it just reads like a botched dedent.
- **`回到桌子` copy on a not-yet-started room.** `getMatchRowAction` returns `return` for `Waiting` / `Full` when you hold a seat, so a room that has not started says "Return to table". Deliberate (the test asserts it), just slightly off.

---

## What I would actually send

Finding 1 as a thread comment, Findings 2–5 as line-anchored comments, nits folded in or skipped. Drafts are in `thread.md` and `inline.md`.

Since the PR is already merged, all of this is follow-up-issue material rather than blocking review feedback — Finding 1 is the only one worth opening an issue for on its own.
