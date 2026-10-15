# Verification / falsification transcript — PR #425

Scratch root: `/private/tmp/pr425-review-osv/` (worktree `wt` at `ec4282db`, removed at the end).
Ports used: 3425 (next) / 3426 (game server). Read-only `gh` only; nothing posted.

## 0. Metadata + patch

```
gh pr view 425 --json title,body,headRefOid,headRefName,baseRefName,state,isDraft,mergeStateStatus,changedFiles,additions,deletions,url
```
→ state `MERGED`, head `ec4282db3f319d1a4a724167106ce39514aac2d7`, base `main`,
15 changed files, +799/−109.

```
gh pr diff 425 --patch > /private/tmp/pr425-review-osv/pr425.diff   # 2287 lines, 12 commits
gh pr diff 425 --name-only
```

```
git cat-file -t ec4282db…   → commit   (head is present locally)
git worktree list                      (checked for path collisions with parallel agents)
git worktree add /private/tmp/pr425-review-osv/wt ec4282db… --detach
```

## 1. Baseline

```
pnpm install --frozen-lockfile
```
→ `EXIT=0`, "Done in 16.7s using pnpm v11.15.1".

```
npx jest --runInBand
```
→ `Test Suites: 8 passed, 8 total / Tests: 140 passed, 140 total`.
(PR body says 139 at `0e82a9d3`; commit 12 adds the Escape test → 140. Consistent.)

```
npx next lint                          → LINT_EXIT=0, "No ESLint warnings or errors"
npx tsc --noEmit                       → TSC_EXIT=0
npx tsc -P tsconfig.server.json --noEmit → TSCS_EXIT=0
```

```
PLAYWRIGHT_WEB_PORT=3425 PLAYWRIGHT_GAME_SERVER_PORT=3426 \
PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers npx playwright test --reporter=list
```
→ **first attempt: 6 failures**, all in `Full multiplayer flow`, starting at
"Bob joins via lobby" (`page.waitForURL` 15s timeout); Charlie's log shows
`<button disabled data-testid="match-join">`. See §2 — this was killed.

```
gh pr checks 425
gh run view 30069677091 --log --job 89407832337 | rg "passed|Tests:|Running"
```
→ CI "Webapp baseline" **pass**: `Tests: 140 passed, 140 total`, `Running 30 tests`,
`30 passed (56.4s)`. Workflow `build.yml:109` runs `pnpm webapp e2e`.

## 2. FALSIFIED — "this PR breaks the e2e suite"

Hypothesis: the 6 local failures are a regression.

```
lsof -ti :3425 -ti :3426 | xargs -r kill -9      # stale dev servers from the killed first run
rm -rf packages/webapp/test-results
PLAYWRIGHT_WEB_PORT=3425 PLAYWRIGHT_GAME_SERVER_PORT=3426 \
PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers npx playwright test e2e/multiplayer.spec.ts --reporter=list
```
→ **16 passed (41.0s)**, including the three new scenarios:
`Lobby offers 觀戰 …(#421)`, `Alice leaves keeping her seat and returns via 回到桌子`,
`Bob releases his seat — the match terminates for the table`.

An intervening run had aborted with `[WebServer] Error: listen EADDRINUSE :::3426`,
confirming a leaked server was the cause. **Finding killed.** CI 30/30 at head agrees.

## 3. FALSIFIED — "jest.setup.ts dialog shim is dead code"

jsdom 26.1.0 is installed (`node_modules/.pnpm/jsdom@26.1.0_…`), and jsdom ≥24 is
widely said to implement `HTMLDialogElement.showModal`. Probe printed a live
own-property descriptor for `showModal` — but that could be the shim itself. Real test:

```
sed -i '' "/setupFilesAfterEnv/d" jest.config.js && rm jest.setup.ts
npx jest --runInBand --testPathIgnorePatterns "zz-scratch"
```
→ `Test Suites: 2 failed, 6 passed / Tests: 12 failed, 128 passed`,
`TypeError: dialog.showModal is not a function` at `Modal.tsx:50`.

Restored (`cp /tmp/jc.bak jest.config.js; cp /tmp/js.bak jest.setup.ts`) → 140/140.
**Shim is load-bearing. Finding killed.**

Side note recorded in the report: because jsdom is shimmed, the component tests do
*not* exercise real top-layer/inert semantics — those were verified in Chromium instead (§6).

## 4. FALSIFIED — "the 3s full-lifetime poll is redundant; the socket already pushes metadata"

`onConnectionChange` **does** push (`server.js:3637-3641`,
`transportAPI.sendAll({type:'matchData'})`), which made the code comment look wrong.
But the relevant event is the REST leave:

```
rg -n "'/games/:name/:id/leave'" node_modules/.pnpm/boardgame.io@*/…/server.js   → 2302
sed -n '2300,2335p' …/server.js
```
→ `/leave` deletes `name`/`credentials` from metadata, then `db.setMetadata` (or
`db.wipe` when no named players remain). **No socket push.** The comment
"the socket does not push metadata changes mid-game" is accurate for the case that
matters, and the poll is required. **Finding killed.**

Also recorded from this read: if the *last* named player leaves, the match is wiped →
remaining pollers get 404 → the existing expired-room path, not the overlay.

## 5. FALSIFIED — "`mySeatMatchIDs` state is redundant"

```
sed -n '1,50p' src/lib/matchCredentials.ts
```
→ `loadCredentials` calls `localStorage.getItem` with no `typeof window` guard, so
computing `hasSeat` during render would throw during SSR. **Finding killed.**

## 6. CONFIRMED — dialog dismissal / focus claims (real Chromium)

Scratch spec `e2e/zz-scratch-dialog.spec.ts` (deleted afterwards), run on 3425/3426:

```
✓ backdrop click closes the exit dialog            (mouse.click(5,5) → count 0, URL still /dev)
✓ Escape closes the exit dialog
✓ desktop: focus returns to the 離開 button after cancel   (activeElement === "header-leave")
✘ background is inert while the dialog is open     ← my probe was wrong, see below
✓ mobile: focus after cancel when opened from the ⋯ menu
    console: MOBILE ACTIVE AFTER CANCEL: BODY
✓ mobile: Escape does not close the ⋯ menu
```

The inert probe failed only because it treated `BODY` (focus leaving the document at
the cycle boundary) as an escape. Rewritten to log the sequence:

```
TAB SEQ ["BUTTON:exit-leave-seat:IN","BUTTON:exit-cancel:IN","BODY::OUT",
         "BUTTON:exit-keep-seat:IN","BUTTON:exit-leave-seat:IN","BUTTON:exit-cancel:IN",
         "BODY::OUT","BUTTON:exit-keep-seat:IN","BUTTON:exit-leave-seat:IN","BUTTON:exit-cancel:IN"]
✓ 1 passed   (no background interactive element ever receives focus)
```

→ backdrop-close, Escape-close, desktop focus-restore and the inert focus trap **all hold**.
→ mobile focus-restore **does not** (finding 3); Escape does not close the `⋯` menu (finding 4).

Corroborating jsdom probe `src/components/design/zz-scratch-modal.test.tsx`:

```
✓ A: invoker that stays mounted gets focus back on close
✓ B: invoker unmounted when the modal opens (the ⋯-menu path) loses focus to body
      console: activeElement after close: BODY undefined
✓ C: non-dismissible modal (no onClose) ignores the cancel event  (defaultPrevented === true)
```

## 7. CONFIRMED — `回到桌子` vanishes when all players step out

Mechanism read first:

```
sed -n '3910,3930p' …/boardgame.io/dist/cjs/server.js
      socket.on('disconnect', … master.onConnectionChange(matchID, playerID, credentials, false))
sed -n '3637p'  …/server.js
      metadata.players[playerID].isConnected = connected;      (persisted via setMetadata)
sed -n '64,66p' src/app/lobby/actions.ts
      isAbandonedMatch = players.every(p => !p.name?.trim() || p.isConnected === false)
```

Unit probe `src/app/lobby/zz-scratch-review.test.ts` (all passed):

```
✓ A: in-progress, one player disconnected      → 'In Progress', row visible
✓ B: EVERY seated player disconnected          → 'Abandoned', toVisibleMatch === null
✓ C: 2-player, both disconnected               → toVisibleMatch === null
✓ D: seat released mid-game                    → 'Abandoned', filtered out
✓ E: waiting room, all disconnected            → 'Abandoned'
```

Live reproduction `e2e/zz-scratch-keepseat.spec.ts`, 3 Chromium contexts on 3425/3426:

```
✓ 1 three players start a match                                              (6.8s)
✓ 2 after the FIRST player keeps her seat, her lobby still offers 回到桌子   (128ms)
✓ 3 after ALL players keep their seats, the room is gone from every lobby    (1.3s)
      asserts: match-row-<id> count 0 in all 3 lobbies after reload + 重新整理
               match-return count 0 in all 3 lobbies
               /game/<id> still renders the board with NO observer-mode-banner
  3 passed (9.2s)
```

→ Seat survives server-side; the lobby entry point does not. **Finding stands.**

## 8. CONFIRMED — `isTerminated` ignores `gameover`

Predicates transcribed verbatim from `src/app/game/[matchID]/page.tsx` (head) into
`src/app/lobby/zz-scratch-terminated.test.ts` and `zz-scratch-fix.test.ts`:

```
✓ mid-game seat release -> terminated overlay (intended)
✓ FINISHED game, then seat release -> ALSO terminated overlay (isTerminated never reads gameover)
✓ finished game, seats intact -> board
```

Branch matrix (`zz-scratch-fix.test.ts`, all 7 passed):

```
in-progress, seats intact    head=board              naive=board              proposed=board
in-progress, seat vacated    head=terminated-overlay naive=terminated-overlay proposed=terminated-overlay
finished, seats intact       head=board              naive=board              proposed=board
finished, seat vacated       head=terminated-overlay naive=waiting-room       proposed=board
✓ proposed fix keeps every scenario right
✓ the naive fix regresses the finished+vacated case into the waiting room
✓ head shows the wrong "match terminated, no scores" overlay after a finished game
```

`naive` = `isTerminated && gameover === undefined` only.
`proposed` = that, plus `shouldShowBoard = hasStarted && (allSeatsFilled || isFinished) && !isExpired`.

Scoping: this is a predicate-level proof, not an end-to-end run — driving an online
match to `gameover` was not worth the cost. Recorded as such in the report.

## 9. Body-claim spot checks (read/grep)

```
rg -n "\.Mui" src/                    → NONE            ("no .Mui* CSS remains" ✓)
rg -n "from '@mui" src/               → Alert/Snackbar/Box/Tabs/Container only, no Dialog ✓
rg -n "data-on" src/ e2e/             → NONE            (".icon-btn[data-on] moved to #426" ✓)
rg -n "modal-backdrop" src/           → NONE            (portal shell fully replaced ✓)
rg -n "icon-btn|menu-item" src/       → GameHeader + globals.css only ✓
sed -n '96,121p' src/app/game/[matchID]/page.tsx
    loadSavedCredentials re-fetches the match and clears credentials when
    slot.name !== creds.playerName  ("validates … demotes to observer when stale" ✓)
rg -n "usePolling" src/app/lobby/page.tsx    → 10s lobby poll (row refresh path exists) ✓
```

## 10. Cleanup

```
rm -f  packages/webapp/src/app/lobby/zz-scratch-*.test.ts \
       packages/webapp/src/components/design/zz-scratch-modal.test.tsx \
       packages/webapp/e2e/zz-scratch-*.spec.ts
rm -rf packages/webapp/test-results packages/webapp/playwright-report
git status --porcelain            → empty
git worktree remove /private/tmp/pr425-review-osv/wt --force
git worktree prune
```

The user's repo working tree, index and branches were never touched; no worktree
under `.claude/worktrees` was read from or written to. Nothing was posted to GitHub.
