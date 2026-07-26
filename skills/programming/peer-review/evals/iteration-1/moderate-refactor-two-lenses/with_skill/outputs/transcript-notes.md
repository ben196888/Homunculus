# Verification log — PR #411, ocftw/open-star-ter-village

Scratch root: `/private/tmp/pr411-review-b7`
Worktree: `/private/tmp/pr411-review-b7/head` at `43fe0c32` (detached), removed at end.
Ports used: 3411 only (3412 not needed).
The user's tree at `/Users/benliu/WebPrjcts/open-star-ter-village` was only ever read
(`gh`, `git worktree add`, `git show`); no branch, index, or existing worktree touched.

---

## 1. Metadata and patch

```
gh pr view 411 --json title,body,headRefOid,headRefName,baseRefName,state,isDraft,mergeStateStatus,changedFiles,additions,deletions,url,author,createdAt,updatedAt
```

Result: `state: MERGED`, `isDraft: false`, `mergeStateStatus: UNKNOWN`,
`headRefOid: 43fe0c323ae2b032da17087273718f0516ff7ac7`, `headRefName: fix/b004-shared-app-header`,
`baseRefName: main`, `changedFiles: 6`, `+232 / -104`, author `ben196888`,
created 2026-07-12, updated 2026-07-20.

```
gh pr view 411 --json mergedAt,mergeCommit --jq '{mergedAt,mergeCommit}'
```

Result: `{"mergedAt":"2026-07-20T11:20:40Z","mergeCommit":{"oid":"a61dfcb17b0bada66c111ecd2905b9d50df507c7"}}`

```
gh pr diff 411 --patch > /private/tmp/pr411-review-b7/pr411.diff
wc -l  ->  445
```

## 2. Materializing the head

```
git worktree add /private/tmp/pr411-review-b7/head 43fe0c323ae2b032da17087273718f0516ff7ac7 --detach
```

Result: `HEAD is now at 43fe0c32`. `git status --short` empty.

First attempt to reuse the user's installed `node_modules` by symlink was **wrong** and I
backed it out:

```
git show HEAD:pnpm-lock.yaml   ->  fatal: path 'pnpm-lock.yaml' does not exist in 'HEAD'
git ls-files | rg -i 'lock|\.yaml$'   ->  yarn.lock, .yarn/cache/*.zip, homepage/yarn.lock
rg -n '"packageManager"' package.json  ->  "packageManager": "yarn@3.4.1"
```

So the head predates the pnpm migration; the current tree's pnpm `node_modules` is the
wrong dependency graph. Symlinks removed, `.yarnrc.yml` read (`nodeLinker: node-modules`,
`yarnPath: .yarn/releases/yarn-3.4.1.cjs`), 172M of committed `.yarn/cache` present.

```
YARN_ENABLE_NETWORK=0 yarn install --immutable
```

Result: `Done with warnings in 8s 91ms` — resolved fully offline from the zero-install
cache. Only peer-dependency warnings (YN0002) and one build (`@sentry/cli`).

## 3. Baseline gate

```
yarn workspace @open-star-ter-village/webapp test
```

```
PASS src/game/game.test.ts
PASS src/components/design/AppHeader.test.tsx
PASS src/components/board/BoardProjectSlot.test.tsx
Test Suites: 3 passed, 3 total
Tests:       59 passed, 59 total
```

(PR body's evidence table says 58/58 — actual is 59.)

```
yarn workspace @open-star-ter-village/webapp lint
  ->  ✔ No ESLint warnings or errors

cd packages/webapp && ../../node_modules/.bin/tsc --noEmit -p tsconfig.json
  ->  tsc_exit=0
```

Baseline green. No `typecheck` script exists in `packages/webapp/package.json`; I invoked
`tsc` directly against the checked-in `tsconfig.json`.

## 4. Static reconnaissance

```
rg -n 'Logo|LobbyNav|GameHeader|AppHeader' -l  (packages/webapp/src)
  ->  BoardGame.tsx, design/index.ts, lobby/LobbyNav.tsx, board/GameHeader.tsx,
      design/AppHeader.tsx, app/page.tsx, design/Logo.tsx, design/AppHeader.test.tsx,
      app/game/[matchID]/page.tsx, app/lobby/page.tsx

rg -n '<Logo|Logo size|iconOnly' -g '*.tsx'
  ->  only Logo.tsx (defs) and AppHeader.tsx:36 (the single call site)

rg -n "size=[\"']lg[\"']|Logo\b" packages/webapp/src packages/webapp/e2e
  ->  no `size="lg"` anywhere
git log --oneline -S'size="lg"' -- packages/webapp/src
  ->  (empty — never used in the repo's history)

rg -n 'confirm|beforeunload|Leave|離開|leaveMatch' -g '*.tsx' -g '*.ts' | rg -v 'test|e2e'
  ->  at head, GameHeader's Leave is a plain <Link href="/lobby">; no navigation guard

rg -n -- '--paper:|--paper-3:' src/app/globals.css
  ->  --paper: oklch(0.985 0.012 75);  --paper-3: oklch(0.93 0.022 75);
      (matches the PR body's quoted computed values)

sed -n '170,275p' 'app/game/[matchID]/page.tsx'
  ->  LobbyNav branches and the <Boardgame> branch are mutually exclusive early returns
```

## 5. Deletion experiment — `Logo` `lg` / `STAR_RADIUS` / `big` / barrel export

Edited `Logo.tsx` (drop `lg` from the union, drop `STAR_BOX.lg`, delete `STAR_RADIUS`
in favour of `size === 'sm' ? 10 : 12`, delete `const big`, inline its three ternaries)
and removed `export { default as Logo }` from `design/index.ts`.

```
git diff --stat  ->  Logo.tsx 19 +++---, index.ts 1 -   (5 insertions, 15 deletions)
yarn workspace @open-star-ter-village/webapp test  ->  Tests: 59 passed, 59 total
tsc --noEmit -p tsconfig.json  ->  tsc_exit=0
yarn workspace @open-star-ter-village/webapp lint  ->  ✔ No ESLint warnings or errors
```

**Finding confirmed.** Restored:

```
git checkout -- .../Logo.tsx .../index.ts   ->  git status --short empty (CLEAN)
```

## 6. Falsification experiment A — do the "identical shell" tests guard B-004?

Wrapped `GameHeader`'s `<AppHeader …/>` in a deliberately divergent shell:

```jsx
<div style={{ minHeight: 96, background: 'red', borderBottom: '9px dotted lime', padding: '30px 4px' }}>
```

```
git diff --stat  ->  GameHeader.tsx | 2 ++
yarn workspace @open-star-ter-village/webapp test
  ->  Tests: 59 passed, 59 total
```

**The suite does not notice a 96px red game-header bar with a lime divider.** Restored.

## 7. Falsification experiment B — what *is* pinned?

In `AppHeader.tsx`: `minHeight: compact ? 52 : 999` and `borderBottom: '9px dotted lime'`.

```
● shared application header shell › compact mobile variant keeps only the star tile so chips get the width
Tests: 1 failed, 58 passed, 59 total
```

Only the compact test fires. Both "value-identical" tests pass with a 999px desktop bar.
**Finding confirmed: desktop shell values are unpinned.** Restored (`git status` clean).

## 8. Deletion experiment — duplicated assertion in the sticky test

Replaced the 10-line `it('game header keeps sticky positioning without changing resting
visuals')` with a 4-line version asserting only `position === 'sticky'`.

```
Tests: 59 passed, 59 total
```

**Confirmed deletable** (−6 lines). Restored.

## 9. Type experiment — is `right?` optional for a reason?

`right?: React.ReactNode` → `right: React.ReactNode`.

```
tsc --noEmit -p tsconfig.json  ->  tsc_exit=0
```

**Confirmed:** no caller omits it. Restored.

## 10. Real-browser measurements (Next dev on :3411, Playwright Chromium)

```
PORT=3411 ../../node_modules/.bin/next dev -p 3411   ->  ✓ Ready in 2.3s
curl -s -o /dev/null -w '%{http_code}' http://localhost:3411/lobby   ->  200
```

Playwright resolves only from `packages/webapp`, so the probe scripts were copied there
as `measure*-tmp.cjs` and deleted afterwards; browsers came from
`PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers` (chromium-1228 already present).

### 10a. Lobby header at head, 1280×800

```
{"tag":"HEADER","height":72,"background":"oklch(0.985 0.012 75)",
 "borderBottom":"1px solid oklch(0.93 0.022 75)","padding":"0px 36px","docOverflow":false}
```

Note `1px` computed, not the `1.5px` the PR body quotes.

### 10b. Same page with the pre-PR `LobbyNav` swapped in

```
git show cea7b902:packages/webapp/src/components/lobby/LobbyNav.tsx > .../LobbyNav.tsx
```

```
{"tag":"NAV","height":69,"background":"rgba(0, 0, 0, 0)",
 "borderBottom":"1px solid oklch(0.93 0.022 75)","padding":"18px 36px","docOverflow":false}
```

**Lobby header grew 69 → 72px and gained an explicit background**, which the PR body does
not mention. Background change is a visual no-op:

```
rg -n 'body\s*\{' -A8 globals.css  ->  body.app-root { … background: var(--paper); }  (line 92)
```

Restored `LobbyNav.tsx`.

### 10c. Game header via the `/dev` offline harness, both viewports

```
desktop-1280 {"count":1,"headers":[{"h":72,"bg":"oklch(0.985 0.012 75)","pos":"sticky",
  "wordmark":true,"chips":3,"stripScrollW":417,"stripClientW":417,
  "leaveHref":"/lobby","logoHref":"/"}],"pageOverflow":0} errors: []

mobile-375  {"count":1,"headers":[{"h":52,"bg":"oklch(0.985 0.012 75)","pos":"sticky",
  "wordmark":false,"chips":3,"stripScrollW":417,"stripClientW":171,
  "leaveHref":"/lobby","logoHref":"/"}],"pageOverflow":0} errors: []
```

This **confirms the PR's headline claims** (72px both surfaces, same background, sticky
game header, 52px icon-only compact, chip strip scrolls inside itself, zero page overflow)
and **kills** my duplicate-header hypothesis (`count: 1`) and my overflow hypothesis
(`pageOverflow: 0`).

### 10d. Clicking the compact brand tile

```
compact logo link box: {"w":26,"h":26,"x":52,"y":170.375,"href":"/"}
urlBefore= http://localhost:3411/dev   urlAfter= http://localhost:3411/
board still mounted? false
```

**Finding confirmed:** a 26×26 target (under the 44×44 guideline) mid-board navigates
away and unmounts the game.

## 11. Does the finding still apply to today's `main`?

```
git rev-parse origin/main  ->  795d3d4c27afce732d669c120a36178af4368314

git diff --stat 43fe0c32 a61dfcb1 -- packages/webapp/src
  ->  (empty — the merge introduced no changes; what landed == what I reviewed)

git diff --stat 43fe0c32 origin/main -- .../design .../LobbyNav.tsx .../GameHeader.tsx
  ->  GameHeader.tsx | 88 ++++++, Modal.tsx | 98 +++++ (new), index.ts | 1 +
      i.e. AppHeader.tsx, AppHeader.test.tsx, Logo.tsx, LobbyNav.tsx unchanged on main

git show origin/main:.../GameHeader.tsx | rg -n 'AppHeader|onClick|href|離開'
  ->  Leave is now <button onClick={openExit}> feeding ExitDialog; docblock says
      "Leaving always goes through the explicit exit-choice dialog (#420)."

git grep -n 'beforeunload\|useBeforeUnload\|router.events\|onNavigate' origin/main -- packages/webapp/src
  ->  (no hits — no route guard exists)

git grep -n "size=[\"']lg[\"']\|<Logo" origin/main -- packages/webapp/src
  ->  only AppHeader.tsx:36; `lg`, STAR_RADIUS and `big` still dead on main
```

So V1 is **live on main and now worse**: the guarded exit is guarded, the brand link is
not, contradicting `GameHeader`'s own "always" comment. V3/V4 dead code also still present.

## 12. Teardown

```
rm -f packages/webapp/measure-tmp.cjs measure2-tmp.cjs measure3-tmp.cjs
pkill -f 'next dev -p 3411'
lsof -ti :3411   ->  PORT_FREE
git status --short  ->  TREE_CLEAN
git worktree remove /private/tmp/pr411-review-b7/head --force
git worktree list   ->  pr411 worktree absent
```

Nothing was pushed, posted, commented, or approved. All `gh` calls were `pr view` /
`pr diff`.
