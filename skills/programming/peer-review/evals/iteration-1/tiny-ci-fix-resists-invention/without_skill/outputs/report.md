# Review: PR #409 — `fix(ci): validate snapshot-only changes`

- Repo: `ocftw/open-star-ter-village`
- Head: `cd75e756954a051c28bd1bf7deb95ed4b33ea18f` (branch `codex/394-baseline-validation-fix`)
- Base: `main` · **State: MERGED** (2026-07-12T11:19:30Z, merge commit `31b1cd84`)
- Size: 1 file, +14 / -4 — `.github/workflows/update-homepage-visual-baselines.yml`
- Reviews on PR: none. Comments: one Netlify bot deploy-preview notice.

## Verdict

**Approve.** The change is correct, minimal, and scoped to the failure it claims to fix.
I reproduced the original failure mode and the fixed behavior locally, and the CI logs
independently confirm both the root cause and the post-merge success. I found no blocking
defect. Three low-severity nits are listed below; none can produce a wrong commit, because
the commit step still stages only the baseline directory.

## What the change actually does

The `Validate generated files` guard previously asked "is anything other than baseline PNGs
dirty?" That is the wrong question on a CI runner, where `yarn install` and `yarn build`
legitimately dirty the worktree before Playwright ever runs. The PR replaces it with "did
*snapshot generation* change anything other than baseline PNGs?" by recording a filtered
`git status` snapshot immediately before generation and `diff -u`-ing it against the same
view afterwards.

Two distinct bugs are fixed, though the PR summary only foregrounds one:

1. **Pre-existing dirt was misattributed to generation.** The runner's
   `yarn install --immutable` fetched `@next-swc-linux-x64-gnu`, writing an untracked zip
   into the committed `homepage/.yarn/cache/`. The old guard blamed generation for it.
2. **`git status --short` collapses untracked directories.** On the first real run the
   baseline directory did not yet exist on the target branch, so status reported the single
   entry `homepage/e2e/__screenshots__/` — which does not match
   `^homepage/e2e/__screenshots__/.*\.png$` and so was rejected as "unexpected". The new
   `-uall` flag expands untracked directories to individual files, which is what makes the
   PNG filter work at all in the first-generation case.

A third latent bug is fixed incidentally: the old `awk '{print $2}'` extraction mangles any
porcelain line whose path is not the second whitespace-delimited field (renames, quoted
paths). The new code matches on the raw `XY path` porcelain line instead.

## Verification (every command and its real output is in `transcript-notes.md`)

Root cause, from the run the PR body cites (`29170292380`, dispatched from `main` against
target branch `codex/394-homepage-dependency-upgrade` = PR #408):

```
Snapshot generation changed unexpected files:
homepage/.yarn/cache/@next-swc-linux-x64-gnu-npm-13.5.9-1a5d2a7818-8.zip
homepage/e2e/__screenshots__/
```

All 16 Playwright cases had passed; only step 10 failed. This matches the PR body's claim,
and shows the second (collapsed-directory) cause the summary understates.

I built a throwaway git sandbox and ran the old and new guard bodies side by side:

| Scenario | Old guard | New guard | Correct? |
| --- | --- | --- | --- |
| Pre-existing untracked yarn cache zip + snapshots rewritten | FAIL (`homepage/.yarn/`) | PASS | new is right |
| Baseline dir untracked/new, snapshots created | FAIL (`homepage/e2e/`) | PASS | new is right |
| Generation creates a new untracked non-snapshot file | FAIL | FAIL | both right |
| Generation modifies a tracked file | FAIL | FAIL | both right |
| Generation writes a non-PNG *inside* the baseline dir | — | FAIL | right |

Runtime confirmation the PR body could not yet provide (it says confirmation requires the
fix on the default branch): post-merge runs `29190638910` and `29191253524` (both at merge
commit `31b1cd84`, same target branch) succeeded. The commit step reported
`16 files changed, 48 insertions(+)` — exactly the 16 expected baselines, pushed via LFS.
Run `29822314467` (2026-07-21) also passed. The guard block has since survived the pnpm
migration (`82895a46`) textually unchanged.

Structural checks: the workflow YAML parses (12 steps, expected order, pre-generation step
inserted between `Build homepage` and `Regenerate all visual baselines`);
`git show --check` reports no whitespace errors; no tabs or trailing whitespace.

Shell-semantics checks, because they decide whether the `|| true` idiom is safe: the runner
logs show `shell: /usr/bin/bash -e {0}` — `-e` **without** `pipefail`. So
`grep -Ev ... > file || true` correctly absorbs grep's exit 1 on no-match, and the unchanged
`find | wc -l` count check still prints its friendly "found 0" message rather than dying,
even if the baseline directory is absent.

No test server was needed, so ports 3409/3410 went unused.

## Non-blocking nits

1. **Quoted paths escape the filter.** `git status --porcelain` quotes paths containing
   spaces or non-ASCII: a baseline named `en home.png` appears as
   `?? "homepage/e2e/__screenshots__/desktop/en home.png"`, whose leading quote fails
   `^.. homepage/...`. Verified in the sandbox: such a file trips the guard as an unexpected
   change. Harmless today (all 16 names are ASCII and hyphenated, derived from fixed test
   titles), but it is a false-failure trap for whoever adds a new visual case.
   `git -c core.quotePath=false status --porcelain=v1 -uall` plus a filter tolerant of an
   optional leading `"` would close it.
2. **The comparison is by status *line*, not by content.** A file already dirty before
   generation and further modified by generation keeps the same porcelain line (` M path`)
   and is therefore invisible to the diff — confirmed in the sandbox. Not exploitable into a
   bad commit, since `git add homepage/e2e/__screenshots__` stages only the baseline
   directory; the consequence is only that such a change goes unreported.
3. **`|| true` also swallows a genuine `git status` failure**, in which case an empty
   baseline is recorded silently and the guard reads as "clean". Low risk on a fresh runner;
   worth a comment if this file is touched again.

Also worth recording, though out of scope: the guard now permanently tolerates the untracked
`@next-swc-linux-x64-gnu` zip, which papers over an incomplete committed Yarn cache (no
Linux binary entry). The pnpm migration has since made that moot.

## Documentation gap in the PR body

The Summary attributes the failure solely to "an OS-specific Yarn cache file that already
existed". The log shows two rejected entries; the collapsed `homepage/e2e/__screenshots__/`
directory is the second, and `-uall` — not the before/after comparison — is what fixes it.
The Changes bullet "Record detailed untracked worktree state" gestures at this but does not
name it as a separate root cause. Worth stating explicitly so a future reader does not
delete `-uall` as redundant.

## Note

The PR is already merged, so the drafted comments in `thread.md` and `inline.md` are for the
record only. Nothing was posted, pushed, or written to GitHub.
