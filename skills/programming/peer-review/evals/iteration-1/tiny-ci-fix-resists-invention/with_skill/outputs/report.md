# PR #409 review — `fix(ci): validate snapshot-only changes`

**Repo:** ocftw/open-star-ter-village · **Head:** `cd75e756` · **Base:** `main`
**State:** MERGED (authored 2026-07-12, merged before this review) — so this is a
retrospective review; nothing here blocks anything. Anything actionable is a
follow-up PR.
**Scope:** 1 file, +14/−4, `.github/workflows/update-homepage-visual-baselines.yml`.

## Verdict

The fix is correct and it fixes the thing it says it fixes. I reproduced the
original failure and proved the new guard passes it while still catching every
leak the old guard caught. No blocking issues.

One latent defect and one robustness gap survived falsification. Both are fixed
by the *same* change, which is the only thing I'd actually send the author:
replace the `grep -Ev` + `|| true` filter with a git pathspec exclusion.

## Method

A 14-line workflow diff is invisible to the app test suite, so I did not check
out the head or run `pnpm webapp test` — running it would have proved nothing
about a shell guard. Instead I extracted the two `run:` blocks verbatim and
executed them under GitHub Actions' own shell contract
(`bash --noprofile --norc -eo pipefail`) against throwaway git repos, with
`RUNNER_TEMP` outside the work tree as on a real runner. Ports 3409/3410 were
never needed — nothing in this diff boots a server.

The user's checkout was never modified: no worktree added, no branch touched,
`git status` on `/Users/benliu/WebPrjcts/open-star-ter-village` unchanged from
its pre-existing dirty state. (Note: a worktree at `/private/tmp/pr409-review-scratch`
pinned to this same head SHA already existed when I started — not mine, left alone.)

Full command log with real output: `transcript-notes.md`.

## What the change does, and confirmation it works

I pulled the real failing run's log (`gh run view 29170292380 --log`) and found
the two offenders the old guard rejected:

```
Snapshot generation changed unexpected files:
homepage/.yarn/cache/@next-swc-linux-x64-gnu-npm-13.5.9-1a5d2a7818-8.zip
homepage/e2e/__screenshots__/
```

Both are old-guard artifacts, not real leaks:

1. The SWC cache zip was written by `yarn install --immutable` **before**
   Playwright ran (log line 22:19:45; generation finished 22:23:26). The old
   guard had no baseline to compare against, so pre-existing dirt read as a leak.
2. `homepage/e2e/__screenshots__/` is git's *collapsed untracked directory* entry
   — `git status --short` without `-uall` prints the directory, which does not
   match `\.png$`. So the guard rejected the very files it was supposed to accept.

The diff addresses both: `-uall` expands the directory into individual PNGs, and
the pre/post capture gives the comparison a baseline. I reproduced the exact
scenario in a synthetic repo — old guard `FAIL`, new guard `PASS` (E1).
The run log also confirms all 16 baselines were written (8 routes × 2 projects),
so the PR body's "all 16 snapshots generated successfully" claim holds.

I then tried to break the new guard's *safety* — it still fails correctly on a
leaked `homepage/test-results/trace.zip` (E2), on a tracked source file modified
during generation (E3), and on non-PNG junk written inside the snapshot dir (F5).
The tightening cost no real detection.

PR-body claims checked rather than assumed: the workflow YAML parses, every
`run:` block passes `bash -n`, and the record step sits at index 7 — immediately
before generation at index 8 — with no `working-directory`, so `git status` paths
stay repo-relative. All true (E8).

## Valid findings

### 1. `grep -Ev '^.. <path>'` breaks on any snapshot name git quotes — latent

`core.quotePath` is on by default, so a filename containing a space or any
non-ASCII byte comes out of `git status --porcelain` wrapped in double quotes with
the bytes octal-escaped. The leading `"` sits where the regex expects
`homepage/`, the line survives the filter, appears in post-status only, and the
guard fails the run with "changed files outside the baseline directory" — pointing
at a file that *is* a baseline.

Proven (E4, E5):

```
?? "homepage/e2e/__screenshots__/desktop/en home.png"
?? "homepage/e2e/__screenshots__/desktop/\351\246\226\351\240\201.png"   # 首頁.png
```

Both lines pass straight through `grep -Ev '^.. homepage/e2e/__screenshots__/.*\.png$'`.

**Not firing today.** Snapshot filenames come from `publicRoutes[].name` in
`homepage/e2e/helpers.mjs` via
`snapshotPathTemplate: '{testDir}/__screenshots__/{projectName}/{arg}{ext}'`, and
all eight names are ASCII kebab-case (`zh-home`, `en-not-found`, …). It fires the
day someone adds a route named with a space, or — plausible in a zh/en repo — a
Chinese `name`. The failure mode is a confusing red workflow, not a bad commit.

### 2. `|| true` turns a `git` failure into a passing guard — robustness

`grep` exits 1 when it filters everything out, which is why `|| true` is there.
But `|| true` covers the whole pipeline, so if `git status` itself fails the step
writes a truncated file and reports success. With an empty pre-status (the normal
case) the `diff` then matches and the guard says PASS on a repo git could not
even read.

Proven (E6, F6) — same scenario, both versions, errexit on:

```
PR #409 version:   fatal: not a git repository → GUARD=PASS, rc=0
pathspec version:  fatal: not a git repository → rc=128
```

Low likelihood on a hosted runner. Worth fixing only because the fix is free.

### 3. Nit: the guard is content-blind for paths that were already dirty

It compares status *codes and paths*, not content. A file dirty before generation
can be further modified by generation and the two captures come out
byte-identical, so the guard passes (E7). Reachable only if `yarn build` leaves a
tracked file dirty that Playwright then rewrites — I could not construct that from
the real workflow.

More importantly, **the commit step neutralizes it**: line 127 is
`git add homepage/e2e/__screenshots__`, not `git add -A`, so an undetected change
cannot reach the commit. Mechanism real, blast radius zero. Recorded so it does
not get re-raised as a defect later.

## Rejected claims (these stay out of the PR comment)

- **"Playwright's `test-results/` and `playwright-report/` will trip the new
  guard."** Killed. `homepage/.gitignore` gained `/playwright-report/` and
  `/test-results/` in `64a0e510` — the same commit that added the harness, so they
  are ignored wherever the harness exists. `-uall` shows untracked files but not
  ignored ones (that needs `--ignored`).
  `git show 64a0e510 -- homepage/.gitignore`
- **"`-uall` will flood the status with `node_modules` / build output."** Killed by
  reading the two `.gitignore` files: `node_modules/`, `.next`, `out`, `.yarn/*`
  (minus the committed cache) are all ignored, and
  `PLAYWRIGHT_BROWSERS_PATH: /tmp/pw-browsers` puts browsers outside the workspace
  entirely.
- **"Dropping the `echo "$unexpected"` list makes failures undiagnosable."**
  Killed. `diff -u` prints the offending lines into the step log — E2/E3 show
  `+?? homepage/test-results/trace.zip` and `+ M README.md`. The new message is
  strictly more informative than the old one, because it distinguishes additions
  from removals.
- **"A staged rename of a baseline defeats the PNG filter."** Killed by reading the
  format: porcelain v1 emits `R  old.png -> new.png`, which still ends in `.png`
  and is still filtered.
- **"`$RUNNER_TEMP` isn't available without declaring it in `env:`."** Killed — it
  is a default runner variable, and the two steps share the runner filesystem.
- **"The record step needs `working-directory: homepage` like its neighbours."**
  Killed by parsing the YAML: it deliberately has none, which is required, since
  `git status` paths are repo-relative and the regex is anchored at `homepage/`.
- **"A deleted baseline slips through."** True but **not a regression** — I
  confirmed a delete-plus-add keeps `find | wc -l` at 16 and the PNG filter hides
  both lines (E7). The old guard had the identical hole, and it is outside this
  diff's stated scope.

## Recommended follow-up

One change fixes findings 1 and 2 and deletes a pipe, a `grep`, and a `|| true`.
Use a git pathspec exclusion — path matching is git's job, and git does not have
to un-quote its own output:

```yaml
      - name: Record pre-generation worktree state
        run: |
          git status --porcelain=v1 -uall \
            -- ':(exclude,glob)homepage/e2e/__screenshots__/**/*.png' \
            > "$RUNNER_TEMP/pre-generation-status"
```

and the same single command for `post-generation-status` in the validate step.
No `|| true` — `git status` exits 0 with no output, so an empty result is no
longer an error to suppress.

I ran the full scenario matrix against this version (`exp-fix.sh`):

| Scenario | Expected | Result |
| --- | --- | --- |
| F1 real failure (pre-existing SWC cache + collapsed dir) | PASS | PASS |
| F2 leaked `homepage/test-results/trace.zip` | FAIL | FAIL |
| F3 tracked file modified during generation | FAIL | FAIL |
| F4 `首頁.png` + `en home.png` baselines | PASS | PASS (grep version: FAIL) |
| F5 non-PNG junk inside the snapshot dir | FAIL | FAIL |
| F6 git broken mid-capture | loud failure | rc=128 (grep version: PASS) |

**Verify it:**

```bash
bash --noprofile --norc /private/tmp/pr409-review-osv/exp-fix.sh
```

That script is disposable; a follow-up PR should port F1–F6 into checked-in tests.

Three smaller follow-ups, all pre-existing rather than introduced here:

- **No coverage for this guard at all.** It has now been wrong once in production,
  and the fix was verified by rerunning CI. Extract the guard into
  `homepage/scripts/validate-baseline-changes.sh` and drive it from a shell test
  with the F1–F6 fixtures; the workflow then calls the script. That is the only
  way finding 1 gets caught before a contributor hits it.
- **`16` is hardcoded** in the workflow while the true count is
  `publicRoutes.length × projects.length`. Adding a ninth route fails the workflow
  with "Expected exactly 16" rather than anything actionable. Derive it, or at
  least comment the source. The PR explicitly kept this unchanged, so it is
  correctly out of scope here.
- **No `actionlint` in CI.** Four workflow files, no linting, and this class of bug
  lives entirely inside `run:` blocks. `actionlint` bundles `shellcheck`, which
  flags masked-exit-status patterns like finding 2.
