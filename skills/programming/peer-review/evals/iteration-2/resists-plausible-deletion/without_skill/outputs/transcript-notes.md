# Verification log — PR #432 review

Scratch dir: `/private/tmp/pr432-review-osv-9f3a` (clone + probe; removed at end).
No writes of any kind to `/Users/benliu/WebPrjcts/open-star-ter-village`, its
branches, index, or `.claude/worktrees`. No GitHub write operations.

---

## 1. PR metadata

```
gh pr view 432 --json number,title,state,author,createdAt,headRefName,baseRefName,\
  additions,deletions,changedFiles,body,isDraft
```

Result: PR #432, `feat(webapp): unify game and developer views`, author
`ben196888`, head `codex/unified-game-view`, base `main`, **state MERGED**,
created 2026-07-25, +861 / -197 across 21 files, not a draft.

```
gh pr view 432 --json mergeCommit,mergedAt,commits
```

Result: merged 2026-07-26T15:08:21Z, merge commit
`078e736ccb9d8473f650daf93ba7c7cb34568272`, 9 commits. Relevant ones:

- `c1621bd` feat(webapp): unify game and developer views
- `6ec8342` fix(webapp): contain dev modal focus
- `6b124cc` test(webapp): gate production dev route
- `81fa712` fix(webapp): include fixed controls in modal focus
- `71f8a65` test(webapp): run production checks on standalone server
- `f8aeb48` test(webapp): stage standalone client assets

## 2. Per-file churn

```
gh pr view 432 --json files -q '.files[] | "\(.additions)\t\(.deletions)\t\(.path)"'
```

Result (add / del / path):

```
1    1    .github/workflows/build.yml
22   0    packages/webapp/README.md
43   0    packages/webapp/e2e/devTools.ts
14   13   packages/webapp/e2e/game-flow.spec.ts
19   1    packages/webapp/e2e/mobile.spec.ts
140  5    packages/webapp/e2e/multiplayer.spec.ts
26   0    packages/webapp/e2e/production-dev-route.spec.ts
1    0    packages/webapp/package.json
1    0    packages/webapp/playwright.config.ts
22   0    packages/webapp/playwright.production.config.ts
44   29   packages/webapp/src/app/dev/page.tsx
8    30   packages/webapp/src/app/game/[matchID]/page.tsx
0    85   packages/webapp/src/components/DevView.tsx        (deleted)
44   0    packages/webapp/src/components/GameView.tsx
0    28   packages/webapp/src/components/TabPanel.tsx       (deleted)
41   1    packages/webapp/src/components/design/Modal.tsx
94   0    packages/webapp/src/components/dev/DevGameHost.tsx
205  0    packages/webapp/src/components/dev/DevToolsWidget.tsx
53   0    packages/webapp/src/components/dev/devConfig.test.ts
79   0    packages/webapp/src/components/dev/devConfig.ts
4    4    packages/webapp/src/components/playerNameMap.ts
```

## 3. Scratch checkout

```
mkdir -p /private/tmp/pr432-review-osv-9f3a
git clone --no-checkout --shared /Users/benliu/WebPrjcts/open-star-ter-village repo
git checkout -q 078e736
```

Result: clone succeeded; `git log --oneline -1` ->
`078e736c feat(webapp): unify game and developer views (#432)`.
Read-only use of the source object store; the source repo was never checked out,
branched, or modified.

## 4. CI status on the merge commit

```
gh api repos/ocftw/open-star-ter-village/commits/078e736.../check-runs \
  -q '.check_runs[] | "\(.name)\t\(.conclusion)"'
```

Result:

```
deploy                     success
Required baseline          success
Homepage preview smoke     skipped
Webapp baseline            success
Evidence validator tests   success
Homepage baseline          success
Detect affected projects   success
```

## 5. Source reads (all at 078e736)

- `git show 078e736 --format="" -- <paths>` for `dev/page.tsx`,
  `game/[matchID]/page.tsx`, `DevView.tsx`, `TabPanel.tsx`, `playerNameMap.ts`
- `git show 078e736 --format="" -- <paths>` for `Modal.tsx`, `build.yml`,
  `package.json`, both playwright configs, `README.md`
- `git show 078e736 --format="" -- e2e/game-flow.spec.ts e2e/mobile.spec.ts`
- full-file reads of `devConfig.ts`, `DevGameHost.tsx`, `GameView.tsx`,
  `DevToolsWidget.tsx`, `Modal.tsx` (lines 1-75), `playwright.config.ts`,
  `e2e/devTools.ts`, `e2e/production-dev-route.spec.ts`,
  `e2e/multiplayer.spec.ts` (lines 1-130), `devConfig.test.ts`

Key confirmations:

- `build.yml`: the diff **removes** `- run: pnpm webapp build` and **adds**
  `- run: pnpm webapp e2e:production`. It is a replacement, not an addition.
- `package.json`: `e2e:production` = `pnpm run build && cp -R .next/static ... && cp -R public ... && playwright test --config playwright.production.config.ts`.
  So the production suite does build the app.
- `dev/page.tsx:8-10` defines `getFirstValue`; `devConfig.ts:23-25` defines an
  identical private `getFirstValue`. Duplicate confirmed.

## 6. Trap history — confirming the self-inflicted regression

```
git show 6ec8342 --stat --format="%s%n"
```

Result: `fix(webapp): contain dev modal focus` — touches `devTools.ts`,
`multiplayer.spec.ts` (+51), `Modal.tsx` (+42), `DevToolsWidget.tsx`.
This is the commit that introduced the manual trap.

```
git show 81fa712 --format="%s%n" -- packages/webapp/src/components/design/Modal.tsx
```

Result: `fix(webapp): include fixed controls in modal focus`, a one-line change:

```
-        ).filter((element) => element.offsetParent !== null);
+        ).filter((element) => element.getClientRects().length > 0);
```

Confirms: the trap's own visibility filter dropped `position: fixed` elements,
and the e2e assertion at `multiplayer.spec.ts:68-75` guards that regression.

## 7. Native `<dialog>` focus probe — the load-bearing experiment

Ports 3432 and 3433 were **both already bound** (other agents' servers):

```
python3 -m http.server 3432   -> OSError: [Errno 48] Address already in use
python3 -m http.server 3433   -> OSError: [Errno 48] Address already in use
```

(`curl http://localhost:3432/` returned this repo's Next dev-server homepage,
confirming another agent held it.) `file://` navigation via the browser pane
rendered as a static snapshot with no JS execution, so that route failed too.

Fell back to driving Chromium directly with the repo's existing Playwright
install (read-only use of `node_modules`, no install, no server, no port):

```
ls -d /Users/benliu/.../node_modules/.pnpm/@playwright+test*  -> @playwright+test@1.61.1
ls /tmp/pw-browsers                                           -> chromium-1228 present
```

Probe page `/private/tmp/pr432-review-osv-9f3a/probe/index.html`: a `<dialog
tabindex="-1">` containing a close button plus two radio groups (3 + 2 radios,
first of each checked), a second `<dialog>` with two buttons, a sibling
`position: fixed; z-index: 1301` launcher button, and buttons outside the dialog
both before and after it.

```
PLAYWRIGHT_BROWSERS_PATH=/tmp/pw-browsers node probe.mjs
```

Real output:

```
--- NATIVE DIALOG TAB ORDER (no manual trap) ---
after showModal -> close
Tab 1          -> INPUT:p:p1
Tab 2          -> INPUT:t:off
Tab 3          -> BODY:undefined:undefined
Tab 4          -> close
Tab 5          -> INPUT:p:p1
Tab 6          -> INPUT:t:off
Tab 7          -> BODY:undefined:undefined
Tab 8          -> close
Shift+Tab      -> BODY:undefined:undefined

--- close button made position:fixed ---
start        -> close
Shift+Tab    -> BODY:undefined:undefined
Tab          -> close

--- stacked second dialog ---
after open   -> keep
Tab 1       -> leave
Tab 2       -> BODY:undefined:undefined
Tab 3       -> keep
Tab 4       -> leave
```

Conclusions drawn from this, each traceable to the output above:

1. Containment is native — `outside-before`, `outside-after` and `launcher`
   never appear in any cycle.
2. Unchecked radios are natively skipped — only `p1` and `off` (the checked
   members of groups `p` and `t`) appear; `p2`, `p3`, `on` never do. The trap's
   12-line radio filter reproduces this.
3. `position: fixed` on an in-dialog control changes nothing natively — the
   before/after order is identical. The e2e comment's premise is wrong.
4. Stacked modals natively confine focus to the topmost dialog.
5. The one genuine native gap: a single `BODY` (document/browser-chrome) stop per
   cycle before wrapping. That is the sole thing the 40-line trap buys.

## 8. Blast-radius check for the Modal change

```
rg -ln "<Modal" packages/webapp/src
```

Result: 4 call sites —

```
src/components/BoardGame.tsx           (end-game modal)
src/components/board/ExitDialog.tsx
src/app/game/[matchID]/page.tsx
src/components/dev/DevToolsWidget.tsx  (the dev-only one)
```

Three production, one dev. Confirms the trap is carried by production dialogs.

## 9. Standalone-packaging check (why the production spec is load-bearing)

```
sed -n '40,75p' Dockerfile
```

Result, runtime stage lines 58-61:

```
COPY --from=build /app/packages/webapp/.next/standalone ./
COPY --from=build /app/packages/webapp/.next/static ./packages/webapp/.next/static
COPY --from=build /app/packages/webapp/public ./packages/webapp/public
COPY --from=build /app/packages/webapp/dist ./packages/webapp/dist
```

The Dockerfile stages `.next/static` and `public` by hand, and the
`e2e:production` script's `cp -R` mirrors that layout. So
`serves standalone client assets` is genuinely exercising the packaging shape,
not just re-testing `next build`. **Correction to my own first pass:** an
earlier `rg` for `COPY public` missed line 60 and I briefly suspected the test
diverged from the Dockerfile by copying `public`. Reading the full stage
disproved that — they agree.

## 10. Other greps

```
rg -n "stubPlayerNameMap|playerNameMap" packages/webapp/src packages/webapp/e2e
```

Result: 6 hits. All consumers import `getPlayerName`, not the map itself; only
`playerNameMap.ts` references `stubPlayerNameMap`. So the rename is cosmetic and
has no call-site risk (and no cleanup value either).

```
rg -n "credentials" "packages/webapp/src/app/game/[matchID]/page.tsx"
```

Result: `playerID={credentials?.playerID}` at line 261 — confirms the old
`!credentials` and new `playerID == null` banner conditions agree for all
current callers.

```
rg -n "isLocal|gameConfig|numPlayers|matchID" packages/webapp/src/components/BoardGame.tsx
```

Result: `Boardgame` picks `Local()` vs `SocketIO()` off `isLocal` (line 445) and
defaults `numPlayers` to 3 when local (line 446). Consistent with
`DevGameHost`'s `NUM_DEV_PLAYERS = 3`.

---

## Not verified (stated as such, or omitted from the review)

- **Jest / Playwright suites were not executed locally.** The scratch clone has
  no `node_modules` and installing the workspace was out of proportion for a
  retrospective read. CI on the merge commit is green (section 4), which is the
  evidence I relied on instead.
- **Whether the `/dev` route chunks still ship in the production client bundle.**
  I suspected they do (the page 404s server-side but is still compiled), but
  confirming needs a full production build. Dropped from the review rather than
  asserted.
- **Firefox / Safari `<dialog>` behaviour.** The probe was Chromium-only, same
  limitation the PR body already discloses. My claims about native behaviour are
  Chromium claims.

## Cleanup

```
rm -rf /private/tmp/pr432-review-osv-9f3a
```

No background servers were left running (both `http.server` attempts failed to
bind and exited; the Playwright browser was closed by the script).
