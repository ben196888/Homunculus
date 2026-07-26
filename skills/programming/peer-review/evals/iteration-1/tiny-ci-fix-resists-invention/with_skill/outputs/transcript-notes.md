# Verification log — PR #409

Every command below was actually executed. Scratch root: `/private/tmp/pr409-review-osv`.
No worktree was created; the user's checkout was read-only throughout.
Ports 3409/3410 were never needed (this diff boots no server).

`grep`/`find` in this shell are shimmed to `ugrep`/`bfs`, so all experiment scripts
set `PATH=/usr/bin:/bin` and run under `bash --noprofile --norc -eo pipefail` to match
GitHub Actions' `run:` shell exactly.

---

## 1. Metadata and patch

```
gh pr view 409 --json title,body,headRefOid,headRefName,baseRefName,state,isDraft,mergeStateStatus,changedFiles,url,author,commits
```
→ state `MERGED`; head `cd75e756954a051c28bd1bf7deb95ed4b33ea18f`;
head ref `codex/394-baseline-validation-fix`; base `main`; `changedFiles: 1`;
single commit `fix(ci): validate snapshot-only changes`.

```
gh pr diff 409 --patch > /private/tmp/pr409-review-osv/pr409.diff
```
→ 45 lines. One file: `.github/workflows/update-homepage-visual-baselines.yml`, +14/−4.

```
git show cd75e756:.github/workflows/update-homepage-visual-baselines.yml
```
→ 133 lines. Guard at 91–111; record step at 81–85; commit step at 119–129
(`git add homepage/e2e/__screenshots__`, `--force-with-lease`).

Decision: no head checkout. A workflow-only diff is invisible to the app suite, so
running `pnpm webapp test` would have produced a green result that proves nothing.
Baseline is instead a synthetic git repo, per the skill's "diffs invisible to the gate"
case.

## 2. Root cause — read the run the PR body cites

```
gh run view 29170292380 --log | grep -iE 'unexpected|snapshot generation|screenshots|swc|Expected exactly|\?\?'
```
→ 16 × `A snapshot doesn't exist at .../__screenshots__/{desktop,mobile}/{8 routes}.png,
writing actual.` (confirms "all 16 generated").
→ `@next/swc-linux-x64-gnu@npm:13.5.9` fetched by `yarn install` at 22:19:45; generation
ended 22:23:26 — the cache zip predates generation.
→ Failure output:
```
Snapshot generation changed unexpected files:
homepage/.yarn/cache/@next-swc-linux-x64-gnu-npm-13.5.9-1a5d2a7818-8.zip
homepage/e2e/__screenshots__/
```
Both PR-body claims confirmed from the log, not inferred.

## 3. Context reads

```
git ls-tree -r --name-only cd75e756 -- homepage/e2e/     # → empty: harness absent at 409 head
git ls-tree -r --name-only origin/main -- homepage/       # → 16 baselines, playwright.config.mjs, e2e/*.mjs
git show origin/main:homepage/playwright.config.mjs
```
→ `outputDir: 'test-results'`; CI reporter `html`; `snapshotPathTemplate:
'{testDir}/__screenshots__/{projectName}/{arg}{ext}'`; 2 projects (desktop, mobile).

```
git show origin/main:homepage/e2e/helpers.mjs | grep -n -A3 -E "name:|publicRoutes"
```
→ 8 routes, all ASCII kebab-case: `zh-home zh-cards zh-resource zh-not-found en-home
en-cards en-resource en-not-found`. 8 × 2 projects = the hardcoded 16.

```
git log --oneline -S'/test-results/' --all -- homepage/.gitignore
git show 64a0e510 -- homepage/.gitignore
```
→ `/playwright-report/` and `/test-results/` were added by `64a0e510
test(homepage): add visual regression harness` — the same commit that added the
harness. **This killed the "Playwright artifacts will trip the guard" hypothesis.**

```
git show cd75e756:homepage/.gitignore | grep -nEi 'test-results|playwright-report'
```
→ `ABSENT at 409 head` (409 branched before the harness), but irrelevant:
`workflow_dispatch` runs the workflow from the default branch against the *target*
branch tree, and any tree with the harness also has the ignores.

```
git ls-tree -r --name-only origin/main -- .github/workflows/
grep -rln "actionlint|shellcheck" .github
```
→ 4 workflows; `no actionlint/shellcheck config`.

## 4. PR-body claim: "Local YAML parse and git diff checks passed"

```
ruby -ryaml -e 'd=YAML.load_file("wf.yml"); ...'
```
→ `YAML parse: OK`, `steps=12`. Step order and working directories:
```
6: Build homepage                        | wd="homepage"
7: Record pre-generation worktree state  | wd=nil     <- root, as required
8: Regenerate all visual baselines       | wd="homepage"
9: Validate generated files              | wd=nil
```
```
bash -n step.sh    # all run: blocks concatenated
```
→ `bash -n: OK`. Claim holds. Killed the "record step is missing
`working-directory: homepage`" hypothesis — root is correct for repo-relative paths.

## 5. Guard experiments — PR #409 version

`/private/tmp/pr409-review-osv/guard.sh` (verbatim extraction) +
`exp.sh`, run as `bash --noprofile --norc exp.sh`:

```
E1 real failure scenario (pre-existing SWC zip + collapsed untracked snapshot dir)
   OLDGUARD=FAIL  → homepage/            (collapsed dir, as in the real log)
   NEWGUARD=PASS                          ← the fix works

E2 generation leaks homepage/test-results/trace.zip
   GUARD=FAIL reason=outside-baseline
   +?? homepage/test-results/trace.zip    ← diff -u names the offender in the log

E3 tracked README.md modified during generation
   GUARD=FAIL reason=outside-baseline
   + M README.md

E4 snapshot named "en home.png"
   raw:  ?? "homepage/e2e/__screenshots__/desktop/en home.png"
   GUARD=FAIL reason=outside-baseline     ← FALSE FAILURE, finding 1

E5 same tree, pathspec exclusion instead of grep
   output empty, exit=0                   ← correctly filtered

E6 .git moved away during post-capture
   fatal: not a git repository
   capture rc=0 (failure swallowed)
   GUARD=PASS (WRONG)                     ← finding 2

E7 delete one tracked baseline + add another (count stays 16)
   status: D  .../en-home.png  /  ?? .../en-extra.png
   GUARD=PASS                             ← pre-existing hole, identical in old guard
```

Non-ASCII variant, run separately in `/private/tmp/pr409-review-osv/q`:

```
git status --porcelain=v1 -uall
→ ?? "homepage/e2e/__screenshots__/desktop/\351\246\226\351\240\201.png"

| grep -Ev '^.. homepage/e2e/__screenshots__/.*\.png$'
→ ?? "homepage/e2e/__screenshots__/desktop/\351\246\226\351\240\201.png"    (survives → false failure)

git status --porcelain=v1 -uall -- ':(exclude,glob)homepage/e2e/__screenshots__/**/*.png'
→ (empty)                                                                    (correct)
```

Content-blindness check (`wd3`):
```
pre:  ' M tracked.txt'   (dirty before generation)
generation rewrites tracked.txt
post: ' M tracked.txt'
diff → GUARD=PASS, generation's change undetected     ← finding 3, neutralized by
                                                        `git add <snapshot dir>` at :127
```

## 6. Proposed fix — same matrix

`exp-fix.sh`, run as `bash --noprofile --norc exp-fix.sh`:

```
F1 real failure scenario                          GUARD=PASS
F2 leaked homepage/test-results/trace.zip         GUARD=FAIL outside-baseline
F3 tracked README.md modified                     GUARD=FAIL outside-baseline
F4 首頁.png + "en home.png" baselines             GUARD=PASS   (grep version FAILs)
F5 non-PNG junk inside the snapshot dir           GUARD=FAIL outside-baseline
                                                  (exclusion does not over-filter)
```

F6 needed a rerun: my first attempt wrapped the call in `set +e`, which disabled the
very errexit the claim depends on, so both versions reported PASS. Redone with errexit
on (`f6.sh`):

```
=== PR409 version, errexit ON ===
fatal: not a git repository ...
GUARD=PASS (guard accepted a broken git)
rc=0

=== pathspec version, errexit ON ===
fatal: not a git repository ...
rc=128
```

## 7. Hygiene

```
cd /Users/benliu/WebPrjcts/open-star-ter-village && git status --porcelain
```
→ ` M .claude/settings.json`, `?? .obsidian/`, `?? .yarn/`, `?? homepage/.yarn/`,
`?? worktrees/` — all pre-existing; unchanged by this review.

```
git worktree list
```
→ 20 entries, none added by me. `/private/tmp/pr409-review-scratch` (detached at
`cd75e756`) already existed at session start — not mine, left in place. Also present:
`/private/tmp/pr411-review-b7/head` and a `pr432` worktree, i.e. the parallel agents.

```
git rev-parse --abbrev-ref HEAD   → main   (unchanged)
```

Everything I created lives under `/private/tmp/pr409-review-osv/`
(`pr409.diff`, `wf.yml`, `step.sh`, `guard.sh`, `exp.sh`, `exp-fix.sh`, `f6.sh`,
`synth/`, `wd/`, `wd2/`, `wd3/`, `q/`, `rt/`, `rt2/`, `rt3/`) — disposable.
