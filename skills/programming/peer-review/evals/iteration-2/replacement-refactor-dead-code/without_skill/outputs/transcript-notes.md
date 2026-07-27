# Verification log — PR #423 review

Every command actually executed, with its real result. Read-only against GitHub throughout;
no post/comment/review/approve/push. All build and test work done in a disposable clone at
`/private/tmp/pr423-rev`. The user's repo at `/Users/benliu/WebPrjcts/open-star-ter-village`
was only ever read (`gh` + `git clone --local`); its worktree, branches, and index were not
touched, and no worktree was created under `.claude/worktrees`. No servers were booted, so
ports 3423/3424 went unused.

---

## 1. PR metadata

    gh pr view 423 --json number,title,state,mergeable,mergeStateStatus,baseRefName,\
      headRefName,author,body,additions,deletions,changedFiles,commits

Result: **state MERGED**, base `main`, head `fix/418-overtime-token`, author `ben196888`,
+560 / −453, 31 files, 6 commits (`c63ee2f0`, `76631a66`, `645f7326`, `1793a3fa`, `5b26985a`,
`df8fbef5`) — head commit later `3646a5eb`.

    gh pr view 423 --json mergeCommit,mergedAt,reviews,comments \
      -q '{mergeCommit,mergedAt,reviewCount:(.reviews|length),commentCount:(.comments|length)}'

Result: `mergeCommit 3486d0c29c5ee92be1cd083e08d004f881042fcc`, `mergedAt
2026-07-22T21:35:39Z`, **reviewCount 0**, commentCount 4.

    gh pr diff 423 --patch > /private/tmp/pr423-review-scratch.patch
    gh pr diff 423 --name-only

Result: 2352-line patch; 31 files listed (game core moves/validators/store slices, board
components, e2e spec, docs, pnpm-workspace.yaml, lockfile).

    gh pr view 423 --json comments -q '.comments[] | ...'

Result: 1 Netlify preview comment + 3 author self-updates (ACTION_CONFIGS cleanup in
`5b26985a`; move-level overtime coverage; free-slot rejection tightened in `3646a5eb`).

## 2. CI status

    gh api "repos/ocftw/open-star-ter-village/commits/3646a5eb.../check-runs" \
      -q '.check_runs[] | "\(.name)\t\(.conclusion)"'

Result: Required evidence success · Required baseline success · Evidence validator tests
skipped · Homepage baseline success · Homepage preview smoke success · **Webapp baseline
success** · Redirect rules success · Detect affected projects success · Header rules neutral ·
Pages changed neutral.

    rg -n 'playwright|e2e|jest|tsc|lint|build' .github/workflows/*.yml

Result: the `Webapp baseline` job runs `pnpm webapp lint`, `pnpm webapp exec tsc --noEmit`,
`pnpm webapp build`, and `pnpm webapp e2e` (Playwright/chromium) — so the green check does
cover E2E.

## 3. Isolated checkout

    rm -rf /private/tmp/pr423-rev
    git clone --no-checkout --local /Users/benliu/WebPrjcts/open-star-ter-village /private/tmp/pr423-rev
    git -C /private/tmp/pr423-rev checkout -q 3486d0c2...
    git -C /private/tmp/pr423-rev log --oneline -1

Result: `3486d0c2 fix(webapp): per-player overtime token replaces nested mirror move (#423)`.

## 4. Is the old mechanism gone?

    rg -i -n 'mirror' --glob '!pnpm-lock.yaml' --glob '!node_modules' -S .

Result at merge commit: **zero hits in `packages/webapp/src` or `packages/webapp/e2e`.** Hits
only in `packages/webapp/README.md` (unrelated "mirror the alpha uptime checks"),
`homepage/_cards/**` (unrelated, Mirror Media), and `docs/phase-1-simplified-mode-spec.md`
lines 193–244 and 265 — historical prose. Line 265 was newly stale:
`| 9 | mirror (Doin' Overtime): repeats removeAndRefillJobs, costs 2 AP total |`.

    rg -n 'ACTION_CONFIGS|actionConfig' --glob '!node_modules' .

Result: only the same historical doc lines. **No code references.**

    rg -n "from '.*actionConfig'|actionConfig" packages/webapp/src

Result: no output — no orphan imports.

    git diff --diff-filter=D --name-only 3486d0c2^1 3486d0c2

Result: exactly two deletions —
`packages/webapp/src/components/board/actionConfig.ts`,
`packages/webapp/src/game/core/stage/action/move/mirror.ts`.

    git fetch -q origin main; git log --oneline -1 origin/main
    git grep -il 'mirror' origin/main -- 'packages/webapp/src' 'packages/webapp/e2e'
    git grep -il 'mirror' origin/main -- docs
    git grep -n 'mirror (Doin' origin/main -- docs
    git grep -n 'overtime-status' origin/main

Result: main is `795d3d4c`. **All four greps return no hits** — the stale doc prose was removed
by #431, and the `data-testid="overtime-status"` legend has no surviving reference.

Confirmed by reading, at the merge commit:
- `core/stage/action/action.ts` — `moves:` lists 5 regular + `endActionTurn` +
  `discardExcessJobCards`; no `mirror`.
- `core/stage/action/move/type.d.ts` — `ActionMoves` has exactly 5 keys.
- `store/slice/actionSlots.ts` — 5 slots in both `initialState` and `reset`.
- `store/slice/rule.ts` — no mirror config; `overtimeTokens: 1`, `overtimeMaxActionCost: 1`.
- `lib/reducers/actionStepSlice.ts` — `UserActionMoves` has no `Mirror`.
- `JobMarket.tsx` diff — `mirrorOccupied`, the `overtime-status` sticker, **and** the
  now-unused `ActionSlotSelector` import all removed together.

## 5. Replacement correctness (by reading)

Files read in full: `move/applyActionCost.ts`, `move/type.d.ts`, `action.ts`,
`validate/validators.ts`, all five regular moves, `handler/refill.ts`, `store/slice/table.ts`,
`store/slice/players.ts`, `core/playerView.ts`, `components/board/ContextAction.tsx`
(lines 75–270 + overtime grep), `game.ts` (turn config).

Established:
- Every regular move is validate-then-throw-then-mutate, with `applyActionCost` as the sole
  AP/slot choke point.
- `refill` is invoked from `game.ts:62` inside `turn.onEnd`, and resets both the overtime
  token and **all action slots** — so slots are per-turn, not per-round.
- `playerView` strips only `hand` for other players; `token.overtime` is public (intended).
- `getNumOvertimeTokens` has a `?? 0` legacy fallback; `useOvertimeToken` has no floor and
  `table.round` has no fallback.

Rulebook cross-check:

    rg -n -i -B6 -A20 '加班|overtime' docs/rulebook.md

Result: §f "Doin' Overtime — Cost: 1 action point. Repeat one one-action-point action you have
already completed this turn." Plus Q5 (a 1-AP createProject becomes overtime-eligible). The
implementation compares `getActionTokenCost` against `overtimeMaxActionCost` dynamically, so
Q5 holds.

    rg -n -A45 'Scenario 9' packages/webapp/e2e/game-flow.spec.ts

Result: Scenario 9 is the token flow, not the mirror wizard — asserts `overtime-token`
`data-available`, `overtime-confirm` click, `data-overtime="true"`, 2 AP total for two refills,
2 VP, token no longer available. Matches the PR's claim.

## 6. Build and test, executed locally

    pnpm install --frozen-lockfile --prefer-offline

Result: `Done in 16.2s using pnpm v11.15.1`, 1513 resolved.

    cd packages/webapp && npx tsc --noEmit

Result: **clean, exit 0**, no output.

    pnpm webapp test

Result: **4 suites, 114/114 tests passed** in 0.917s — matches the PR's claimed 114/114.

    pnpm webapp lint

Result: `✔ No ESLint warnings or errors`.

E2E not run locally (CI's `Webapp baseline` job already ran `pnpm webapp e2e` green on the head
commit); no server booted, ports 3423/3424 unused.

## 7. Adversarial probe tests (written by me, then deleted)

Wrote `packages/webapp/src/game/probe423.test.ts` in the scratch clone only, ran it, removed it.

    npx jest src/game/probe423.test.ts

Result: **6/6 passed.**

| # | Probe | Result |
|---|---|---|
| P1 | overtime at 0 AP on an occupied slot | rejected `INSUFFICIENT_ACTION_TOKENS`; move throws; token still 1 ✅ |
| P2 | slot state after a successful redemption | stays occupied ✅ (a 3rd attempt still needs a token) |
| P3 | legacy snapshot with `token.overtime` deleted | selector returns 0, move throws, field never written — no `NaN` ✅ |
| P4 | `{ useOvertime: false }` on an occupied slot | `ACTION_OCCUPIED` — no bypass ✅ |
| P5 | hostile client sends `{ useOvertime: 'yes' }` | treated as overtime by both layers; charges exactly 1 AP, spends 1 token — no exploit ✅ |
| P6 | player `1` redeems against a slot occupied by player `0` | **validator returns valid** — confirms the gap in finding A; unreachable only because slots reset per turn |

    rm -f packages/webapp/src/game/probe423.test.ts

## 8. Dead-code and persistence checks on current main

    git grep -n 'getRound\|getTotalRounds' origin/main -- packages/webapp/src
    git grep -n '\.round' origin/main -- packages/webapp/src | rg -v 'Rounded|rounded|round\('
    git grep -n -i 'round' origin/main -- packages/webapp/src/components/board/GameHeader.tsx

Result: `getRound` / `getTotalRounds` match **only their own definitions and export entries**;
`.round` matches only `state.round += 1` and the getter body; `GameHeader.tsx` has no round
badge (only `background` colour matches). **Confirmed dead on main, 5 days post-merge.**

    git show origin/main:packages/webapp/src/server.ts | sed -n '1,60p'
    git grep -ln 'flatfile\|Postgres\|StorageAPI\|db:' origin/main -- packages/webapp/src

Result: `Server({ games, origins })` with **no `db:` option**, and no persistence adapter
anywhere. The PR's "in-memory, so a deploy already resets matches" risk framing is accurate.

## 9. Misc diffs reviewed

    git diff 3486d0c2^1 3486d0c2 -- pnpm-workspace.yaml packages/webapp/.gitignore \
      .../validate/messages.ts .../validate/types.ts
    git diff 3486d0c2^1 3486d0c2 -- docs/phase-1-simplified-mode-spec.md
    git diff 3486d0c2^1 3486d0c2 -- JobMarket.tsx globals.css HandPanel.tsx BoardProjectSlot.tsx

Result: new `ActionExecutionOptions` type; `OVERTIME_UNAVAILABLE` copy retargeted to the
per-player token; `@sentry/react` → `@types/react@^18` peer pin; Playwright gitignore entries;
`ot-pulse` keyframes added to `globals.css`; comment-only edits in `HandPanel`/`BoardProjectSlot`
("mirror" → "normal or overtime"); the doc got a superseded note on Task 12 only.

## 10. Cleanup

Scratch artifacts left at `/private/tmp/pr423-rev` (disposable clone) and
`/private/tmp/pr423-review-scratch.patch`. No git worktree was created, so none needed removal.
The user's repo is untouched.
