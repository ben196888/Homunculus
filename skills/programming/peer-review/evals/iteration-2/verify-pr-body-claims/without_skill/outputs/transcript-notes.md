# Verification transcript — PR #425

Scratch root: `/private/tmp/prreview-425-cace19`
Clone: `/private/tmp/prreview-425-cace19/repo` (`git clone --local --no-hardlinks` of the user's repo; the user's working tree, index, branches and `.claude/worktrees` were never touched)
Ports used: 3425 (Next), 3426 (game server) only.
GitHub access: read-only `gh pr view` / `gh pr diff` only. Nothing posted, commented, approved, or pushed.

---

## 1. PR metadata

```
gh pr view 425 --json number,title,state,headRefName,baseRefName,mergeCommit,body
```
→ `{"b":"main","h":"fix/420-421-exit-and-reentry","mc":{"oid":"6cfedcb4408635596720b6c7278daf05aae27134"},"n":425,"s":"MERGED","t":"fix(webapp): exit-choice dialog, leave-terminates, lobby re-entry and spectate"}`

```
gh pr view 425 --json body --jq .body   # 46 lines, saved to body.md
gh pr diff 425 --name-only
```
→ 15 files. Notably **`GameOverDialog.tsx` is NOT among them** — first thing checked, and it turns out the component lives inside `BoardGame.tsx`.

## 2. Scratch clone + diff stat

```
git clone --local --no-hardlinks /Users/benliu/WebPrjcts/open-star-ter-village repo
git diff --stat 162bf212 6cfedcb4
```
→ 15 files, 799 insertions, 109 deletions. `globals.css`: 65 insertions, **0 deletions**.

## 3. MUI claim

```
git diff 162bf212 6cfedcb4 -- packages/webapp/src/app/globals.css
git grep -n -i "\.Mui\|@mui\|Mui-" 6cfedcb4 -- packages/webapp
git grep -n -i "\.Mui\|@mui" 162bf212 -- packages/webapp
```
→ At merge: `@mui/*` still imported by `package.json`, `dev/page.tsx`, `game/[matchID]/page.tsx`, `layout.tsx`, `lobby/page.tsx`, `DevView.tsx`, `TabPanel.tsx`, `ContextAction.tsx`. The only removal is `BoardGame.tsx`'s `Dialog, DialogContent` — so "no MUI **dialog** remains" is true, "no MUI" would not be.
→ No `.Mui*` in any CSS at base either.

```
git log --oneline --all -S'.Mui' -- 'packages/webapp/**/*.css'
```
→ `330fbb61 refactor(webapp): migrate GameOverDialog off MUI` (removes 15 lines from `globals.css`) and `db65df94`. `330fbb61` is on `origin/fix/420-421-exit-and-reentry`, but the net squashed diff has 0 deletions in `globals.css`, so #424 had already landed the removal. **Claim 4 confirmed.**

## 4. GameOverDialog migration

```
git show 6cfedcb4:packages/webapp/src/components/GameOverDialog.tsx
```
→ `fatal: path ... does not exist`. Component is exported from `BoardGame.tsx`.

```
git diff 162bf212 6cfedcb4 -- packages/webapp/src/components/BoardGame.tsx
```
→ `<Dialog><DialogContent sx={{p:0}}>` → `<Modal open={open} onClose={onClose} ariaLabel="遊戲結束" width="min(440px, 100%)">`. Migration is **real**. Inner JSX left at the old indent depth.

## 5. Source read

```
git show 6cfedcb4:packages/webapp/src/components/design/Modal.tsx
git show 6cfedcb4:packages/webapp/src/components/board/ExitDialog.tsx
git show 6cfedcb4:packages/webapp/src/components/lobby/MatchRow.tsx
git show 6cfedcb4:packages/webapp/src/app/lobby/actions.ts   (lines 25-120)
git diff 162bf212 6cfedcb4 -- .../GameHeader.tsx '.../game/[matchID]/page.tsx' '.../lobby/page.tsx'
git diff 162bf212 6cfedcb4 -- jest.config.js jest.setup.ts e2e/mobile.spec.ts e2e/multiplayer.spec.ts
grep -n "  if (\|shouldShowBoard\|isTerminated\|isAbandoned\|isExpired" 'packages/webapp/src/app/game/[matchID]/page.tsx'
```
Key results:
- `isTerminated = Boolean(match) && hasStarted && match.players.some(p => !hasPlayerName(p))` — *some*, not *mixed*.
- Render order is `shouldShowBoard` (256) → `isTerminated` (290) → `isAbandoned && !hasStarted` (301); mutually exclusive since `shouldShowBoard` needs `allSeatsFilled`.
- `usePolling(pollMatch, 3_000, !isExpired)` — previously gated on `(!shouldShowBoard || isFinished) && !isExpired`.
- `mySeatMatchIDs` built purely from `loadCredentials(match.matchID)` — no name matching anywhere.
- `isAbandonedMatch` (`actions.ts:64-67`): `players.every(p => !p.name?.trim() || p.isConnected === false)`; `toVisibleMatch` returns `null` for `Finished` / `Abandoned`.
- `jest.setup.ts` shims `showModal`/`close` in jsdom → the jest suite does **not** exercise real Escape, inertness, or the top layer.

## 6. Install + static gates

```
pnpm install --frozen-lockfile --prefer-offline      → exit 0 (11.3s)
pnpm exec next lint                                  → ✔ No ESLint warnings or errors
pnpm exec tsc --noEmit                               → clean (no output)
pnpm exec tsc -P tsconfig.server.json --noEmit       → clean (no output)
```

## 7. Jest

```
pnpm exec jest --runInBand
```
→ `Test Suites: 8 passed, 8 total / Tests: 140 passed, 140 total` — **body says 139**.

```
pnpm exec jest --runInBand --verbose src/components/board/ExitDialog.test.tsx src/components/lobby/MatchRow.test.tsx
```
→ ExitDialog **7** tests (body says 6); MatchRow **9** tests (body says 9 — correct).
ExitDialog test names include "Escape requests dismissal through the native cancel event" — but with the jsdom shim this fires a synthetic `cancel`, it does not prove Escape works.

## 8. Stale-evidence check

```
git diff --stat 0e82a9d3 6cfedcb4 -- packages/webapp
git log --oneline 0e82a9d3..origin/fix/420-421-exit-and-reentry
git diff 0e82a9d3 6cfedcb4 -- .../Modal.tsx .../ExitDialog.tsx jest.setup.ts
```
→ One commit after the cited evidence commit: `ec4282db fix(webapp): address dialog review findings`. It removed `onCloseRef` + the manual `addEventListener('cancel', ...)` in favour of React's `onCancel` prop, dropped the `close` dispatch from the jsdom shim, and swapped `ariaLabel` for `aria-labelledby`/`aria-describedby`. It also added the 7th ExitDialog test. **Evidence was never re-run against the merged code.**

```
node -p "require('react/package.json').version"   → 18.3.1
```
React 18 registers `cancel` as a non-delegated event, so `onCancel` attaches directly to the element — confirmed working in probe 2 below, so the late change is sound.

## 9. Playwright — first full run (FALSE ALARM)

```
PLAYWRIGHT_WEB_PORT=3425 PLAYWRIGHT_GAME_SERVER_PORT=3426 \
PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers pnpm exec playwright test --reporter=list
```
→ exit 1, **25 passed / 5 failed**. All 5 in `multiplayer.spec.ts` from "Alice starts the game" onward; the Start Game button never enabled.
Top of the log: `[WebServer] Error: listen EADDRINUSE: address already in use :::3426`.
`lsof -nP -iTCP:3425 -iTCP:3426 -sTCP:LISTEN` → two stray node processes (36240, 36497) still bound. Killed them.

## 10. Playwright — clean re-run (GREEN)

```
pnpm exec playwright test e2e/multiplayer.spec.ts --reporter=list
```
→ exit 0, **16 passed (54.0s)**, including all three new scenarios:
- `Lobby offers 觀戰 for an in-progress room without a seat (#421)` ✓
- `Alice leaves keeping her seat and returns via 回到桌子 (#420 + #421)` ✓
- `Bob releases his seat — the match terminates for the table (#420)` ✓
Also `mobile.spec.ts` `compact header ⋯ menu opens the exit-choice dialog (#420)` ✓ in the first run.
**Conclusion: the 5 failures were environmental, not a code defect.**

## 11. Manual dev servers on 3425/3426

```
pnpm run dev:next --port 3425      → curl / → 200
PORT=3426 pnpm run dev:server      → curl /health → {"status":"ok",...,"gameName":"OpenStarTerVillage"}
```

## 12. Probe 1 — "everyone keeps their seat" (`e2e/zz-probe.spec.ts`, scratch only)

3 contexts create/join/start, then all three click 離開 → 回大廳, wait 8s, reload the lobby, read raw server metadata.

```
PROBE raw matches: {"matches":[{"gameName":"OpenStarTerVillage","unlisted":false,
 "players":[{"id":0,"name":"P0","data":{"started":true},"isConnected":false},
            {"id":1,"name":"P1","isConnected":false},
            {"id":2,"name":"P2","isConnected":false}],
 "createdAt":1785123345527,"updatedAt":1785123345527,"matchID":"-9y_iukqWgs"}]}
PROBE row count for own room after all keep-seat: 0
PROBE 回到桌子 button count: 0
```
→ **Finding 1 confirmed.** Seats still named, match still started, but every socket disconnected ⇒ `isAbandonedMatch` ⇒ filtered out of the lobby ⇒ no 回到桌子.

## 13. Probe 2 — Escape / backdrop / focus in a real browser (`e2e/zz-probe2.spec.ts`)

```
PROBE escape closes: OK                        (exit-dialog count → 0, so React unmounted it; native close alone would leave the node)
PROBE focus after close: header-leave          (focus restoration works)
PROBE dialog count after backdrop click: 0     (backdrop dismissal works)
```
→ Dialog-semantics claims **true**.

## 14. Probe 3 — stale credentials demote to observer (`e2e/zz-probe3.spec.ts`)

Planted `open-star-ter-village.match-credentials.<id>` = `{matchID, playerID:'1', credential:'bogus', playerName:'Impostor'}` in a fresh context.

```
PROBE data-action: return
PROBE return btn count: 1
PROBE demoted to observer: OK
PROBE leftover credentials: null
```
→ "routes without re-join, room page validates and demotes to observer" **true**, and the stale blob is cleaned up.

## 15. Probe 4 — overlay semantics + polling (`e2e/zz-probe4.spec.ts`)

```
PROBE match-metadata polls in 10s while the board is up: 3
PROBE overlay visible after Escape: 1
PROBE overlay visible after backdrop click: 1
PROBE background: background inert
PROBE overlay survives reload: OK
PROBE leaver lobby row count: 0
PROBE R2 leftover credentials for dead room: STILL PRESENT
```
→ Non-dismissible + inert background + lobby hiding all **true**. Polling cadence confirmed at ~3/10s per client. Dead credentials linger (nit).

## 16. Cleanup

```
git worktree remove --force /private/tmp/prreview-425-cace19/head0e82   # the only worktree created, in the scratch clone
pkill "next dev" / "src/server.ts"
lsof -nP -iTCP:3425 -iTCP:3426 -sTCP:LISTEN   → empty
cd /Users/benliu/WebPrjcts/open-star-ter-village && git status --porcelain
```
→ The user's repo shows only pre-existing dirt (`M .claude/settings.json`, untracked `.obsidian/`, `.yarn/`, `homepage/.yarn/`, `worktrees/`) — nothing from this review. `git worktree list` unchanged; no worktree under `.claude/worktrees` was created, modified, or removed.
Probe spec files existed only in the scratch clone and were stashed/removed there.
