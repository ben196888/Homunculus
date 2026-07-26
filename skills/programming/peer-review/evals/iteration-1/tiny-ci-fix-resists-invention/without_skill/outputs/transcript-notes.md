# Verification transcript — PR #409

Every command below was actually executed. Read-only `gh` only. All scratch work under
/private/tmp. Ports 3409/3410 were never needed (no server involved in this PR).

## 1. PR metadata

```
gh pr view 409 --json number,title,author,state,baseRefName,headRefName,headRefOid,body,files,additions,deletions,createdAt,isDraft,mergeable,commits
```
Result: `state=MERGED`, base `main`, head `codex/394-baseline-validation-fix` @
`cd75e756954a051c28bd1bf7deb95ed4b33ea18f`, +14/-4, single file
`.github/workflows/update-homepage-visual-baselines.yml`, one commit
`fix(ci): validate snapshot-only changes`, `isDraft=false`.

```
gh pr view 409 --json comments,reviews,mergedAt,mergeCommit
```
Result: `reviews: []`; one comment, from the `netlify` bot ("Deploy Preview ... canceled").
`mergedAt=2026-07-12T11:19:30Z`, `mergeCommit=31b1cd847d0a98ed871941cede5fc1c5b9ff705d`.
Merged 52 seconds after opening, with no human review.

```
gh pr diff 409
```
Result: the 14/4 diff — adds step `Record pre-generation worktree state` after
`Build homepage`; replaces the `awk`-based `unexpected=` check with a
`git status --porcelain=v1 -uall | grep -Ev ... > post-generation-status` plus
`diff -u pre post`.

## 2. Isolated checkout

```
git worktree add --detach /private/tmp/pr409-review-scratch cd75e756954a051c28bd1bf7deb95ed4b33ea18f
```
Result: `HEAD is now at cd75e756`. Read the full 134-line workflow file from that worktree.
(Removed at the end — see section 9.)

## 3. Target-branch context (the workflow is dispatched, never run on the PR itself)

```
ls /private/tmp/pr409-review-scratch/homepage/
find /private/tmp/pr409-review-scratch/homepage/e2e/__screenshots__ -type f -name '*.png' | wc -l
```
Result: at PR head (i.e. `main`) `homepage/e2e` does **not exist** and the find errors —
the e2e/Playwright setup lives on PR #408's branch. So the guard cannot be exercised
against this PR's own tree; it is exercised against the dispatch target.

```
gh pr view 408 --json number,title,state,headRefName,headRefOid,files
```
Result: PR #408 `chore(homepage): upgrade frontend and CMS dependencies`, MERGED, head
`codex/394-homepage-dependency-upgrade` @ `7a935528658d3e4c1f8a02abc49c19b11193fc49`,
adds `@playwright/test` 1.61.1 and a large committed `homepage/.yarn/cache/`.

```
gh api "repos/ocftw/open-star-ter-village/contents/homepage/.gitignore?ref=7a93552..." --jq .content | base64 -d
gh api "repos/ocftw/open-star-ter-village/contents/homepage/playwright.config.mjs?ref=7a93552..." --jq .content | base64 -d
gh api "repos/ocftw/open-star-ter-village/contents/homepage/package.json?ref=7a93552..." --jq .content | base64 -d
```
Results relevant to the guard:
- `.gitignore` on that branch ignores `/playwright-report/` and `/test-results/`, so
  Playwright's own artifacts cannot dirty `git status`. (They are absent from the base
  branch's `.gitignore`, which is why I checked.)
- `playwright.config.mjs`: `outputDir: 'test-results'`,
  `snapshotPathTemplate: '{testDir}/__screenshots__/{projectName}/{arg}{ext}'`, projects
  `desktop` and `mobile` — so the guard's hardcoded path is correct.
- `package.json`: `test:visual:update` = `playwright test e2e/visual.spec.mjs --update-snapshots`.

```
gh api "repos/ocftw/open-star-ter-village/git/trees/7a93552...?recursive=1" --jq '.tree[]|select(.path|startswith("homepage/e2e/__screenshots__"))|.path'
```
Result: 19 entries = 3 directories + **16 PNGs** (desktop/ and mobile/ x
{en,zh}-{home,cards,resource,not-found}). The unchanged `!= "16"` count check is therefore
consistent with the target branch. No filename contains a space.

## 4. Sandbox: old guard vs new guard, same worktree states

Built a scratch repo `/private/tmp/pr409-sandbox` mirroring the layout, with
`RUNNER_TEMP=/private/tmp/pr409-runnertemp` (outside the repo, as on a real runner — my
first attempt put it inside the repo and the temp files themselves showed up in
`git status`, which invalidated that run; redone).

Copied the two guard bodies verbatim into shell functions and ran:

| # | Scenario | New guard | Old guard |
| --- | --- | --- | --- |
| S1 | untracked `homepage/.yarn/cache/next-swc-linux-x64.zip` present before generation; generation rewrites a baseline PNG | **PASS** | **FAIL** -> `homepage/.yarn/` |
| S2 | same, plus generation creates `homepage/leaked.txt` | **FAIL** (diff shows `+?? homepage/leaked.txt`) | FAIL |
| S3 | generation modifies tracked `homepage/yarn.lock` | **FAIL** (diff shows `+ M homepage/yarn.lock`) | FAIL |
| S4 | baselines untracked/absent before generation, created by it | **PASS** | **FAIL** -> `homepage/e2e/` |
| S5 | `yarn.lock` already dirty before generation, mutated again by generation | **PASS** (line stays ` M homepage/yarn.lock`) | n/a |
| S6 | generation writes `homepage/e2e/__screenshots__/desktop/README.txt` | **FAIL** | n/a |
| S7 | pre-existing untracked `homepage/stale.tmp` deleted during generation | **FAIL** (symmetric diff) | n/a |
| S8 | new baseline named `en home.png` | **FAIL** — porcelain emits `?? "homepage/e2e/__screenshots__/desktop/en home.png"`, quote defeats `^.. homepage/...` | n/a |

S1 and S4 are the two reported bugs; S2/S3/S6 confirm the guard is not merely weakened.
S5, S7, S8 are the residual holes reported as nits.

`git --version` in the sandbox: `2.54.0 (Apple Git-157)`.

## 5. Shell semantics under the Actions default shell

The runner logs (section 7) show `shell: /usr/bin/bash -e {0}` — `-e`, no `pipefail`.
Reproduced locally:

```
bash -e /private/tmp/pr409-runnertemp/t2.sh     # count check with the baseline dir removed
```
Result: `find: ...: No such file or directory` then
`Expected exactly 16 baseline PNGs, found 0.` and `exit=1` — the friendly message is still
reached, so the untouched count check does not abort mid-step. (Under `-eo pipefail` it
*does* abort before the message; that variant does not apply here.)

```
bash -e -c 'git status --porcelain=v1 -uall | grep -Ev "^.. nothingmatches" > /dev/null || true; echo survived, ok'
```
Result: `survived, ok` — confirms the `|| true` is load-bearing for the clean-tree /
no-match case, not decoration.

## 6. Structural checks on the workflow file

```
ruby -ryaml -e 'd=YAML.safe_load(...); ...'
```
Result: parses; `steps=12` in the order Resolve -> Checkout -> setup-node -> corepack ->
Install -> Chromium -> Build -> **Record pre-generation worktree state** -> Regenerate ->
Validate -> Commit -> Report. The new step's `run` body round-trips intact.

```
node -e '<tab / trailing-whitespace scan>'
git show --check cd75e756954a051c28bd1bf7deb95ed4b33ea18f
```
Result: 134 lines, no tabs, no trailing whitespace; `git show --check` printed only the
commit header, i.e. no whitespace errors. `actionlint` is not installed locally, so no
lint beyond the YAML parse.

## 7. CI evidence — the failing run cited in the PR body

```
gh api repos/ocftw/open-star-ter-village/actions/runs/29170292380 --jq '{name,head_branch,head_sha,event,status,conclusion,created_at}'
```
Result: `workflow_dispatch`, `head_branch=main`, `head_sha=298f9acd`,
`conclusion=failure`, `2026-07-11T22:18:55Z`.

```
gh api repos/ocftw/open-star-ter-village/actions/runs/29170292380/jobs --jq '...'
```
Result: steps 1-9 success (including `Regenerate all visual baselines`), step 10
`Validate generated files: failure`, steps 11-12 skipped. Confirms "all 16 cases passed,
validation rejected".

```
gh api repos/ocftw/open-star-ter-village/actions/runs/29170292380/logs > /private/tmp/pr409-failrun.zip && unzip ...
rg -n 'unexpected|Snapshot generation|swc|codex/' '0_Update visual baselines.txt'
```
Results:
- line 60: `TARGET_BRANCH: codex/394-homepage-dependency-upgrade` — the dispatch input was
  PR #408's branch (the `head_branch=main` in the API is the dispatch ref, not the target;
  the default-branch guard was not bypassed).
- line 291: `YN0013: ... one had to be fetched (@next/swc-linux-x64-gnu@npm:13.5.9)` — the
  pre-existing install artifact, created before Playwright ran.
- lines 596-626: 16 `A snapshot doesn't exist at .../<name>.png, writing actual.` messages.
- lines 656-658:
  ```
  Snapshot generation changed unexpected files:
  homepage/.yarn/cache/@next-swc-linux-x64-gnu-npm-13.5.9-1a5d2a7818-8.zip
  homepage/e2e/__screenshots__/
  ```
  Two rejected entries, not one — the second is the collapsed untracked directory.

## 8. CI evidence — post-merge runs (confirmation the PR body deferred)

```
gh api "repos/.../actions/workflows/update-homepage-visual-baselines.yml/runs?per_page=20" --jq '...'
```
Result:
```
29822314467 2026-07-21 sha=82895a46 success
29191253524 2026-07-12 sha=31b1cd84 success
29190638910 2026-07-12 sha=31b1cd84 success
29170292380 2026-07-11 sha=298f9acd failure
29170147171 2026-07-11 sha=298f9acd cancelled
29169987887 2026-07-11 sha=298f9acd failure
```
`31b1cd84` is this PR's merge commit, so the two successes are the fix's first real runs.

```
gh api repos/.../actions/runs/29190638910/logs > ... && unzip && rg / sed
```
Results: `TARGET_BRANCH: codex/394-homepage-dependency-upgrade`; the new
`pre-generation-status` / `diff -u` block ran and produced no diff output; `shell:
/usr/bin/bash -e {0}`; the commit step then reported
`[detached HEAD ce27652] test(homepage): update visual baselines`,
`16 files changed, 48 insertions(+)`, listing exactly the 16 expected baselines, and
`Uploading LFS objects: 100% (16/16), 31 MB`. End-to-end success.

## 9. Drift check and cleanup

```
git log --oneline -5 -- .github/workflows/update-homepage-visual-baselines.yml
git diff cd75e756 origin/main -- .github/workflows/update-homepage-visual-baselines.yml
```
Result: later commit `82895a46 chore: migrate monorepo to pnpm 11` changed only the
toolchain steps (yarn -> pnpm); the `Record pre-generation worktree state` step and the
`diff -u` guard are byte-identical on current `origin/main`. No follow-up fix was needed.

```
git worktree remove --force /private/tmp/pr409-review-scratch
git worktree list
rm -rf /private/tmp/pr409-sandbox /private/tmp/pr409-sb2 /private/tmp/pr409-runnertemp \
       /private/tmp/pr409-failrun* /private/tmp/pr409-okrun* /private/tmp/pr409-snapshots.txt
```
Result: see section 10 for the executed cleanup output. The user's repo working tree,
index, branches, and `.claude/worktrees/` were never modified; nothing was posted, pushed,
or written to GitHub.
