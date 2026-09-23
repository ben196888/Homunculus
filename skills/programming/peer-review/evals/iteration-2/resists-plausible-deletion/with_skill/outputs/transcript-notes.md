# Verification log — PR #432

Scratch worktree: `/private/tmp/pr432-review-osv/wt` (detached at `28496a8c`).
User's repo, branches, index and `.claude/worktrees` untouched. Ports 3432/3433 only.
Worktree removed at the end.

## 0. Metadata and patch (read-only `gh`)

```
gh pr view 432 --json title,body,headRefOid,...,commits
```
-> MERGED, base `main`, head `28496a8c`, 21 files, +861/−197, 9 commits.

```
gh pr diff 432 --patch > /private/tmp/pr432-review-osv/pr432.diff   # 1836 lines
gh pr diff 432 --name-only                                          # 21 paths
```

```
git diff --numstat <base>..HEAD -- packages .github
```
-> largest additions: `DevToolsWidget.tsx` 205, `multiplayer.spec.ts` +140,
`DevGameHost.tsx` 94, `devConfig.ts` 79, `devConfig.test.ts` 53, `GameView.tsx` 44,
`Modal.tsx` +41. Deletions: `DevView.tsx` 85, `[matchID]/page.tsx` 30,
`dev/page.tsx` 29, `TabPanel.tsx` 28.

## 1. Setup

```
git worktree add /private/tmp/pr432-review-osv/wt 28496a8c... --detach
pnpm install --frozen-lockfile
```
-> "Done in 9.1s using pnpm v11.15.1". Install resolved cleanly against the head
lockfile, so everything below ran on the actual PR head.

## 2. Baseline

```
pnpm exec tsc --noEmit
```
-> no output (clean).

```
pnpm exec jest --runInBand
```
-> `Test Suites: 9 passed, 9 total / Tests: 147 passed, 147 total`.

```
PLAYWRIGHT_WEB_PORT=3432 PLAYWRIGHT_GAME_SERVER_PORT=3433 \
PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers pnpm exec playwright test --reporter=line
```
-> `37 passed (50.2s)`.

```
PLAYWRIGHT_PRODUCTION_WEB_PORT=3432 PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers \
  pnpm run e2e:production
```
-> `4 passed (1.7s)`; wall clock `47.730 total` (dominated by `next build` + `tsc -P
tsconfig.server.json`). All four: `serves standalone client assets` 354ms,
`/dev` 118ms, `/dev?dev=true` 94ms, `/dev?user=player1&mode=offline` 93ms.

## 3. Static reads used as evidence

```
rg -n "stubPlayerNameMap|playerNameMap|TabPanel|DevView" --glob '!node_modules' .
```
-> `stubPlayerNameMap` appears only in `playerNameMap.ts:4` (decl) and `:21` (use).
Four external files import `getPlayerName` only. No `TabPanel`/`DevView` references
survive the deletion.

```
rg -n "standalone|static|public" Dockerfile
```
-> `Dockerfile:58-60` copy `.next/standalone`, `.next/static`, `public` — the same
list `e2e:production` reproduces by hand. Production e2e is deploy-faithful; the
duplication is a drift risk.

```
rg -n "hasLocalSetupOverrides|data-anchor|dev-perspective-|dev-transport-" packages/webapp
```
-> `dev-perspective-*` testid emitted at `DevToolsWidget.tsx:137`, zero consumers.
`dev-transport-offline` consumed at `multiplayer.spec.ts:60`. `data-anchor` consumed
at `mobile.spec.ts:43`. `hasLocalSetupOverrides` has no test reference.

```
rg -n "<Modal" -A6 packages/webapp/src | rg "style="
```
-> single hit, `DevToolsWidget.tsx:71`. `Modal`'s new `style` prop has one consumer.

```
rg -c "style=\{\{" src/components/dev/DevToolsWidget.tsx   -> 18
rg -n "output|standalone" packages/webapp/next.config.*    -> output: 'standalone'
rg -n '"next"' packages/webapp/package.json                -> "next": "14.2.3"  (sync searchParams OK)
sed -n '1,40p' packages/webapp/src/app/dev/page.tsx
```
-> `notFound()` is the first statement in `DevPage`, before any query parsing, so all
three `DEV_URLS` exercise one code path.

## 4. Falsification experiments

Tree restored with `git checkout -- .` and confirmed clean (`git status --porcelain`
empty) between every experiment.

### E1 — delete the whole `Modal` focus trap  -> CLAIM KILLED

Removed `onKeyDownCapture` (33 lines) from `design/Modal.tsx`.
```
pnpm exec playwright test --reporter=line     # ports 3432/3433
```
-> `1 failed / 36 passed (1.5m)`.
Failure: `multiplayer.spec.ts:56 Developer widget > contains keyboard focus and
restores it to the launcher`, at line 73 `await expect(lastControl).toBeFocused()`.

### E1b — is E1 only failing because the test rigs `position:fixed`?  -> CLAIM KILLED

Kept the trap deleted **and** removed the test's
`await closeButton.evaluate((el) => { el.style.position = 'fixed'; })` block.
```
pnpm exec playwright test multiplayer.spec.ts -g "focus"
```
-> `1 failed / 1 passed (30.4s)`. Same assertion fails at the now-shifted line 68:
```
- waiting for getByTestId('dev-transport-offline').getByRole('radio')
  14 x locator resolved to <input checked type="radio" value="offline" name="dev-transport"/>
     - unexpected value "inactive"
```
Chrome's native `<dialog>` does not wrap Shift+Tab from the dialog's first control
back to its last. The trap is load-bearing on the unmodified DOM.

### E2 — delete only the radio-group filter inside the trap  -> CLAIM KILLED

Replaced the 13-line `focusable = candidates.filter(...)` with
`const focusable = candidates;` (trap otherwise intact).
```
pnpm exec playwright test multiplayer.spec.ts -g "focus"
```
-> `1 failed / 1 passed (21.2s)`, same test, same assertion at line 73. Without the
filter the computed "last tabbable" is the unchecked `online` radio.

### E3 — delete `GameView`'s `boardKey` remount plumbing  -> CLAIM KILLED

Removed `boardKey` from `GameView.tsx` (prop, `Key` import, `key={boardKey}`) and the
`boardKey={...}` line in `DevGameHost.tsx`. `tsc --noEmit` clean.
```
pnpm exec playwright test --reporter=line
```
-> `1 failed / 36 passed (1.0m)`:
`game-flow.spec.ts:365 Scenario 10: contributeJoinedProjects`, at
`expectActions` line 48 waiting for `[data-testid="player-status-Alice"]`.
Reproduced in isolation:
```
pnpm exec playwright test game-flow.spec.ts -g "Scenario 10"   -> 1 failed
```

### E4 — the "safe deletion" bundle (F2–F6)  -> CONFIRMED, gate green

Applied together: export `getFirstValue` from `devConfig.ts` and delete the copy in
`dev/page.tsx`; un-export `stubPlayerNameMap`; drop `handlePerspectiveChange` in
favour of `setPerspective`; drop the `dev-perspective-*` testid; drop the
`hasLocalSetupOverrides` prop chain. `git diff --stat` = 5 files, +4 −20.
```
pnpm exec next lint            -> No ESLint warnings or errors
pnpm exec tsc --noEmit         -> clean
pnpm exec jest --runInBand     -> 147 passed
pnpm exec playwright test      -> 37 passed (54.9s)
```

### E5 — the F1 simplification, run as a real prototype  -> CONFIRMED, gate green

Rewrote `DevToolsWidget.tsx` with one generic `RadioGroup<T>` and CSS classes; added
a 24-line `.dev-tools*` block to `globals.css`; changed `Modal`'s `style` prop to
`className`. `git diff --stat`: 4 files, +89 −169 (net **−80**);
`wc -l DevToolsWidget.tsx` 205 -> **102**.
```
pnpm exec tsc --noEmit         -> clean
pnpm exec next lint            -> No ESLint warnings or errors
pnpm exec jest --runInBand     -> 147 passed
pnpm exec playwright test      -> 37 passed (49.7s)
```
Patch saved as `simplify-DevToolsWidget.patch` (348 lines) next to this file.

## 5. Not tested (stated as such in the report, not shipped as a finding)

- The always-rendered launcher (`opacity: 0` + `pointerEvents: none`) vs. conditional
  unmount. Plausibly required for native dialog focus restore, but I ran no
  experiment, so it is withdrawn rather than raised.

## 6. Cleanup

```
git checkout -- .          # tree clean
git worktree remove /private/tmp/pr432-review-osv/wt --force
git worktree prune
```
Nothing was posted, pushed, or commented anywhere. `gh` used read-only throughout.
