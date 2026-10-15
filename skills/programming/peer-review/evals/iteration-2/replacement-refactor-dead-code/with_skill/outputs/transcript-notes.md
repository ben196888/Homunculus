# Verification log — PR #423, every command actually run

Scratch root: `/private/tmp/pr423-review-cace19/`
Worktree: `/private/tmp/pr423-review-cace19/head` (detached at `3646a5eb`, removed at end)
Ports used: 3423 (Next), 3424 (game server). User's repo working tree never modified.

## 1. Metadata and patch

```
gh pr view 423 --json title,body,headRefOid,headRefName,baseRefName,state,isDraft,mergeStateStatus,changedFiles,additions,deletions,mergedAt
```
→ `state: MERGED`, `mergedAt: 2026-07-22T21:35:39Z`, head `3646a5eb24f8ff8c6663da22a10252c7b81161e6`,
branch `fix/418-overtime-token`, base `main`, 31 files, +560/−453, `isDraft: false`.

```
gh pr diff 423 --patch > /private/tmp/pr423-review-cace19/pr423.diff   # 2352 lines
gh pr diff 423 --name-only                                             # 31 paths
```
Patch is 7 commits. Read in full. Commit 7/7 "fix(webapp): reject overtime on free actions"
is the one that closes the free-slot loophole present in commit 3/7 — material to the review.

```
gh api repos/ocftw/open-star-ter-village/commits/3646a5eb.../check-runs --jq '.check_runs[] | "\(.name) | \(.status) | \(.conclusion)"'
```
→ Webapp baseline completed/success; Homepage baseline completed/success; Homepage preview
smoke success; Required baseline success; Required evidence success (x3); Detect affected
projects success; Evidence validator tests skipped; two Netlify rule checks neutral.

## 2. Worktree

```
git -C /Users/benliu/WebPrjcts/open-star-ter-village worktree add /private/tmp/pr423-review-cace19/head 3646a5eb... --detach
```
→ `HEAD is now at 3646a5eb fix(webapp): reject overtime on free actions`

## 3. Dead-code sweep for the removed mechanism

```
rg -in 'mirror' --glob '!node_modules' --glob '!pnpm-lock.yaml' .
```
→ 14 hits, **zero in code**: 8 in `docs/phase-1-simplified-mode-spec.md` (historical task log),
1 in `packages/webapp/README.md` ("mirror the alpha uptime checks", unrelated),
2 in `homepage/_cards/**` (Mirror Media, unrelated).

```
for p in ignoreOccupied ACTION_CONFIGS MirrorableActionName validateMirror overtime-status actionConfig onMirror 'Mirror\b'; do rg -n "$p" packages/webapp/src packages/webapp/e2e; done
```
→ **empty for all eight.**

```
rg -n 'ActionSlots' packages/webapp/src/game/store/slice/actionSlots.ts
```
→ `export type ActionSlots = Record<ActionMoveName, ActionSlot>;` — removal is type-enforced,
since `ActionMoveName = keyof ActionMoves` and `Mirror` is gone from `ActionMoves`.

```
rg -n 'getTotalRounds' .            # only its own definition (rule.ts:295) + registration (rule.ts:342)
rg -n 'getRound|table.round'        # only table.ts:39,50,51,62
rg -n 'getPlayerOvertimeTokens|getOvertimeMaxActionCost|getNumOvertimeTokens|useOvertimeToken|resetOvertimeTokens'
```
→ overtime selectors/mutators are all wired to real callers (`refill.ts`, `setup.ts`,
`validators.ts`, `ContextAction.tsx:148`). The round trio is not.

## 4. Environment facts read, not guessed

```
sed -n '1,200p' .github/workflows/build.yml
```
→ webapp gate order: `pnpm install --frozen-lockfile` → `lint` → `tsc --noEmit` →
`test --runInBand` → `build` → `playwright install chromium` → `e2e`. Reproduced in that order.

```
cat packages/webapp/playwright.config.ts
```
→ ports come from `PLAYWRIGHT_WEB_PORT` (default 3000) and `PLAYWRIGHT_GAME_SERVER_PORT`
(default 3001) — so 3423/3424 are settable without editing the repo.

```
sed -n '1,60p' packages/webapp/src/server.ts
```
→ `Server({ games: [game], origins: [...] })`, **no `db` option** ⇒ boardgame.io in-memory
storage. Confirms the PR's "a deploy already resets matches" risk note.

```
rg -n -C2 "refill" packages/webapp/src/game/game.ts
```
→ `refill(context)` at `game.ts:62` inside `turn.onEnd`, for every player — overtime token
restore has the same lifecycle as the AP reset.

```
cat packages/webapp/src/game/core/playerView.ts
```
→ only `hand` is stripped from other players; `token.overtime` is visible client-side, so the
UI preflight `validateOvertime` reads a real value.

## 5. Baseline (green)

```
pnpm install --frozen-lockfile      → Done in 11.6s
pnpm webapp lint                    → ✔ No ESLint warnings or errors
pnpm webapp exec tsc --noEmit       → clean (no output)
pnpm webapp test --runInBand        → Test Suites: 4 passed; Tests: 114 passed, 114 total
PLAYWRIGHT_WEB_PORT=3423 PLAYWRIGHT_GAME_SERVER_PORT=3424 pnpm e2e --reporter=line
                                    → 26 passed (1.2m)
```

## 6. Falsification experiments

Tree restored and `git status --porcelain` confirmed empty after each one.

### E1 — "the round counter is dead code" → **CONFIRMED**
Deleted `Table.round` (interface field, `round: 0`, `state.round += 1` in `playEvent`,
`getRound`, its selector registration) and `RuleSelector.getTotalRounds` + registration.
`git diff --stat` → 2 files, 16 deletions.
- `tsc --noEmit` → clean
- `lint` → ✔ No ESLint warnings or errors
- `test --runInBand` → **114 passed, 114 total**

Nothing depends on it. Restored via `git checkout --`.

### E2 — "is the no-surcharge rule actually pinned?" → **YES, tests are load-bearing**
Mutated `applyActionCost.ts`:
`useActionTokens(..., cost)` → `useActionTokens(..., options?.useOvertime ? cost + 1 : cost)`
- `test --runInBand` → **Tests: 4 failed, 110 passed, 114 total**

Restored from backup.

### E3 — "is the commit-7/7 free-slot fix load-bearing?" → **YES**
Mutated `validators.ts`: `if (opts?.useOvertime) {` → `if (opts?.useOvertime && occupied) {`
(i.e. reverted to the commit-3/7 shape).
- `test --runInBand` → **Tests: 2 failed, 112 passed, 114 total**

Restored from backup.

### E4 — "deleting ACTION_CONFIGS lost compile-time exhaustiveness" → **CONFIRMED**
Deleted the whole `case 'recruit':` block from `handleConfirm` in `ContextAction.tsx`.
- `tsc --noEmit` → **clean**
- `lint` → **✔ No ESLint warnings or errors**
- `test --runInBand` → **114 passed, 114 total**
- `PLAYWRIGHT_WEB_PORT=3423 PLAYWRIGHT_GAME_SERVER_PORT=3424 pnpm e2e --reporter=line`
  → **2 failed, 24 passed** — Scenario 3 (Recruit Talents) and Scenario 10
  (contributeJoinedProjects).

So an entire action's dispatch can be deleted and the typecheck, linter, and whole unit
suite stay green; only Playwright notices. Restored from backup.

### E5 — testing my own proposed fix (both directions)
Added to the `handleConfirm` switch:
```ts
default: { const _exhaustive: never = actionName; return _exhaustive; }
```
- With all five cases present: `tsc` clean, `lint` clean, **114/114 pass** → no regression.
- Then removed `case 'recruit':` on top of the guard:
  `src/components/board/ContextAction.tsx(271,15): error TS2322: Type '"recruit"' is not assignable to type 'never'.`

The guard is silent when correct and fires exactly on the defect E4 demonstrated.
Restored from backup; `git status --porcelain` empty.

## 7. Claims killed (with the command that killed them)

| Claim | Killed by |
| --- | --- |
| `mirror` not fully removed | §3 greps — zero code hits across eight identifiers |
| `useOvertime` on a free slot burns the token | E3 — 2 tests fail when the guard is reverted; merged code rejects with `OVERTIME_TARGET_NOT_USED` |
| `applyActionCost` double-spends for unvalidated callers | Read all 5 callers: each validates and throws before it; "atomicity" test pins the ordering |
| State-shape change breaks in-flight matches | `src/server.ts` — `Server()` with no `db` ⇒ in-memory; deploy resets matches anyway |
| Early turn-end skips the token restore | `game.ts:62` — `refill` runs in `turn.onEnd` for every player, same call site as the AP reset |
| `?? 0` in `getNumOvertimeTokens` is dead defense | True but two characters and correct in intent; not worth author time |
| AP dots hardcode `length: 4` | Pre-existing, only re-indented by this diff |

## 8. Cleanup

```
git -C /Users/benliu/WebPrjcts/open-star-ter-village worktree remove --force /private/tmp/pr423-review-cace19/head
git -C /Users/benliu/WebPrjcts/open-star-ter-village worktree list
git -C /Users/benliu/WebPrjcts/open-star-ter-village status --porcelain
```
Nothing was posted, pushed, or commented anywhere. All `gh` usage was read-only
(`pr view`, `pr diff`, `api ... /check-runs`).
