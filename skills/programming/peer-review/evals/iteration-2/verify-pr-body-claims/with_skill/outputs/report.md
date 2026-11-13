# PR #425 — validated review

`fix(webapp): exit-choice dialog, leave-terminates, lobby re-entry and spectate`
Head reviewed: **`ec4282db`** (`fix/420-421-exit-and-reentry` → `main`). State: **MERGED**
(as `6cfedcb4`). 15 files, +799/−109.

Everything below was executed against a disposable worktree at that exact SHA
(`/private/tmp/pr425-review-osv/wt`, since removed), ports 3425/3426. Commands and
raw results are in `transcript-notes.md`.

---

## Baseline

| Gate | Result |
| --- | --- |
| `pnpm install --frozen-lockfile` | exit 0 |
| `npx jest --runInBand` | **140/140 pass** |
| `npx next lint` | clean |
| `npx tsc --noEmit` (app) | clean |
| `npx tsc -P tsconfig.server.json --noEmit` | clean |
| `npx playwright test e2e/multiplayer.spec.ts` (isolated) | **16/16 pass** |
| CI "Webapp baseline" at head (run 30069677091) | jest 140/140, Playwright **30/30** |

Green baseline. The body's "139/139" is the count at `0e82a9d3`; the final commit
adds one Escape test, hence 140. Not a discrepancy.

---

## Short answer

The description is unusually honest. **Nine of its eleven behavioral claims are real,
and I verified each by running it rather than reading it.** Two things it promises do
not hold in edge cases it does not mention. Neither is a merge blocker (and the PR is
already merged), so both are follow-ups.

Do not raise "the local e2e suite is broken" with the author. I hit six failures on my
first pass and killed that finding — it was my own stale dev servers, not the code.

---

## Confirmed findings (2 real + 2 nits)

### 1. `回到桌子` becomes unreachable once **every** seated player steps out — REAL, live-reproduced

The headline promise of #421 is that `回大廳（保留座位）` keeps your seat and the lobby
then offers `回到桌子`. It does — until the last connected player leaves.

`回大廳` unmounts the board, dropping the boardgame.io socket. boardgame.io's
`socket.on('disconnect')` calls `onConnectionChange(..., false)`, which persists
`isConnected: false` into match metadata
(`node_modules/…/boardgame.io/dist/cjs/server.js:3637` and `:3919`). Once *all* seats
are disconnected, `isAbandonedMatch` (`src/app/lobby/actions.ts:64`) returns true →
`getLobbyStatus` → `'Abandoned'` → `toVisibleMatch` returns `null` → the room is
filtered out of `listPublicMatches`. And `mySeatMatchIDs` (`src/app/lobby/page.tsx:91-98`)
is derived from that *already-filtered* list, so it can never resurrect the row.

**Experiment (real Chromium, 3 browser contexts):**

| Step | Result |
| --- | --- |
| 3 players join, host starts | board for all three |
| Alice alone takes `回大廳` | her lobby shows `match-return` (the promise holds) |
| Bob and Carol also take `回大廳`; all three reload + `重新整理` | **`match-row-<id>` count 0 in all three lobbies; zero `match-return` anywhere** |
| Alice navigates to `/game/<id>` by URL | board resumes, **no observer banner** — the seat was never released |

The seat survives and the room survives; only the UI path back to it is gone.

Severity: **follow-up, not blocking.** `isAbandonedMatch` predates this PR, but #421
is what makes it load-bearing — "step out and come back" is now a first-class
advertised flow rather than an accident.

Smallest fix: stop deriving owned rows from the filtered list — pass the locally-held
match IDs into the filter, or list them separately:

```ts
// lobby/page.tsx — keep rooms this browser holds a seat in, even when Abandoned
const raw = await lobbyClient.listMatches(GAME_NAME);
const owned = raw.matches.filter((m) => loadCredentials(m.matchID) !== null);
```

Verify with the three-context scenario above, asserting `match-return` is still
visible after all three players leave.

### 2. `isTerminated` never consults `gameover` — a completed game reads as "terminated, no scores" — REAL

`src/app/game/[matchID]/page.tsx:143-145`:

```ts
const isTerminated =
  Boolean(match) && hasStarted && match!.players.some((player) => !hasPlayerName(player));
```

Nothing excludes a finished match, and the `isTerminated` branch sits *after*
`shouldShowBoard` (which requires `allSeatsFilled`). So: game ends normally → one
player hits `離開座位` (a natural post-game action) → their seat empties →
`allSeatsFilled` false → every remaining player's **result screen is replaced by**
`有玩家離席，遊戲已終止` / `這局不會計算勝負` ("this round doesn't count"). It did count.

**Experiment** — I transcribed the page's four predicates verbatim into a test and ran
the branch matrix:

| scenario | head | naive one-line fix | proposed fix |
| --- | --- | --- | --- |
| in-progress, seats intact | board | board | board |
| in-progress, seat vacated | terminated-overlay | terminated-overlay | terminated-overlay |
| finished, seats intact | board | board | board |
| **finished, seat vacated** | **terminated-overlay** (wrong) | waiting-room (worse) | **board** (correct) |

Note the middle column: adding `&& match.gameover === undefined` to `isTerminated`
*alone* **regresses into the waiting-room view**, because `shouldShowBoard` still
demands `allSeatsFilled`. Both lines have to move:

```ts
const isFinished = match ? match.gameover !== undefined : false;
const isTerminated =
  Boolean(match) && hasStarted && !isFinished && match!.players.some((p) => !hasPlayerName(p));
const shouldShowBoard =
  Boolean(match) && hasStarted && (allSeatsFilled || isFinished) && !isExpired;
```

Honest scoping: proven from the page's own predicates, **not reproduced end-to-end** —
reaching `gameover` in an online match is expensive to drive. It fires the first time
anyone leaves their seat *after* a game finishes, not during. Follow-up, not blocking,
and it deserves a test since nothing covers it.

### 3. nit — focus is *not* restored on the mobile `⋯` path

The body says the shared Modal does "explicit focus restoration to the invoking control
on close". True on desktop, false on mobile. `openExit` (`GameHeader.tsx:31-34`) does
`setMenuOpen(false); setExitOpen(true)` in one handler, so `menu-leave` is unmounted
before Modal's cleanup runs and the `document.contains(invoker)` guard
(`Modal.tsx:57`) skips the restore.

Confirmed twice — jsdom probe and real Chromium (`MOBILE ACTIVE AFTER CANCEL: BODY`, vs
`header-leave` on desktop). Fix: keep the menu mounted until the dialog closes, or pass
the `header-menu` button as an explicit restore target.

### 4. nit — the `⋯` menu is mouse-only

`role="menu"` plus `aria-haspopup` sets an expectation the implementation does not meet:
no Escape handler, no arrow-key roving focus, and the only dismiss surface is an
`aria-hidden` click-catching div (`GameHeader.tsx:86-90`). Verified live — pressing
Escape with the menu open leaves it open. One `onKeyDown` on the wrapper covers the
Escape half.

---

## Claims I tried to kill and could not — do NOT raise these

| Claim | How I attacked it | Outcome |
| --- | --- | --- |
| "Escape / backdrop / cancel close safely" | No test anywhere covers backdrop click. Drove it in Chromium: click at (5,5), then `Escape` | **Both close, URL unchanged.** Claim holds |
| "inert-background focus trap" | Tabbed 10x with the dialog open, logging `activeElement` | Cycles only `exit-keep-seat → exit-leave-seat → exit-cancel`; **never lands on a background control.** Claim holds |
| "explicit focus restoration to the invoking control" | Desktop path | Restores to `header-leave`. Holds (mobile exception is finding 3) |
| "no MUI dialog and no `.Mui*` CSS remain" | `rg '\.Mui' src/` → NONE; `rg "from '@mui"` | Holds as written. MUI `Alert/Snackbar/Box/Tabs` remain, but the claim was dialog-scoped and accurate |
| "回到桌子 routes without re-join; the room page validates and demotes to observer when stale" | Read `loadSavedCredentials` (`page.tsx:96-121`) | Real — re-fetches the match and clears credentials when the slot name mismatches |
| "Termination latency is bounded by the 3s poll, not the socket" | Suspected the poll was wasteful, since `onConnectionChange` does `sendAll({type:'matchData'})`. Read the REST `/leave` route | **Killed.** `/leave` (`server.js:2302`) only mutates metadata — no socket push. Comment is right; the poll is necessary |
| `jest.setup.ts` dialog shim is dead code (jsdom 26 ships `showModal`) | Deleted `jest.setup.ts` + the `setupFilesAfterEnv` line, reran | **Killed.** 12 failures, `TypeError: dialog.showModal is not a function`. Load-bearing. Restored → 140/140 |
| `mySeatMatchIDs` state is redundant — call `loadCredentials()` during render | Read `src/lib/matchCredentials.ts:32` | **Killed.** `loadCredentials` touches `localStorage` unguarded; calling it during render breaks SSR. State is justified |
| The local e2e suite is broken by this PR (I saw 6 failures) | Killed my own stale servers on 3425/3426, reran the file in isolation | **Killed.** 16/16. CI at head is 30/30. Environment artifact — do not mention to the author |
| "dev-harness matches (all seats unnamed) are unaffected" | `isTerminated` is `some(!named)`, not "mixed named/unnamed" as the body words it | Wording is loose but harmless — `/dev` is a local harness that never renders this page. Not worth the author's time |

---

## Verdict

Merge was correct; nothing here justified holding it. Two follow-up issues worth filing
(findings 1 and 2 — file 2 first, since it shows users a factually wrong message about
their own completed game), plus two small a11y nits that can ride along with whatever
touches `GameHeader` next.

Drafted comments are in `thread.md` and `inline.md`. Nothing has been posted.
