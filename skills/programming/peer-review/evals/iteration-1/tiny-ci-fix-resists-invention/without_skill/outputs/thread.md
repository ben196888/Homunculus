<!-- Drafted only. PR #409 is already merged; not posted. -->

Approving. I reproduced both the failure and the fix rather than reading the diff alone.

**Root cause confirmed.** Run 29170292380 (dispatched from `main` with
`inputs.branch=codex/394-homepage-dependency-upgrade`) failed only at step 10, with:

```
Snapshot generation changed unexpected files:
homepage/.yarn/cache/@next-swc-linux-x64-gnu-npm-13.5.9-1a5d2a7818-8.zip
homepage/e2e/__screenshots__/
```

So there were **two** causes, not one. The zip is the pre-existing install artifact the
summary describes. The second entry is `git status --short` collapsing an untracked
directory — the baseline directory did not exist on the target branch yet, so status
emitted `homepage/e2e/__screenshots__/`, which the PNG regex cannot match. `-uall` is
what fixes that half, and it is doing independent work from the before/after comparison.
Please say so in the summary so nobody later removes `-uall` as redundant.

**Behavior verified in a scratch repo**, running the old and new guard bodies against the
same worktree states:

| Scenario | Old | New |
| --- | --- | --- |
| Pre-existing untracked cache zip + snapshots rewritten | FAIL | PASS |
| Baseline dir untracked/new, snapshots created | FAIL | PASS |
| Generation creates a new untracked non-snapshot file | FAIL | FAIL |
| Generation modifies a tracked file | FAIL | FAIL |
| Generation writes a non-PNG inside the baseline dir | — | FAIL |

That is exactly the intended narrowing: pre-existing dirt tolerated, generation-caused
dirt still rejected.

**Runtime confirmation now exists.** The Risks section says confirmation needs the fix on
the default branch — it has since landed there: runs 29190638910 and 29191253524 (merge
commit `31b1cd84`, same target branch) both passed, and the commit step reported
`16 files changed, 48 insertions(+)`, i.e. exactly the 16 baselines via LFS. Run
29822314467 passed too, and the guard survived the pnpm migration unchanged.

**Two nits, neither blocking** (details inline): the porcelain filter is defeated by
quoted paths, and the diff compares status *lines*, so a file already dirty before
generation and mutated by it goes unreported. The second one cannot cause a wrong commit
because `git add` is still scoped to the baseline directory — which is the property that
makes the whole guard safe to loosen in the first place. Worth keeping that scoping
explicit if this workflow is refactored.

Verified separately: the YAML parses to the expected 12 steps in the expected order,
`git show --check` is clean, and the runner shell is `bash -e` without `pipefail`, so the
`|| true` on the grep pipelines is correct and the untouched `find | wc -l` count check
still reports "found 0" rather than aborting when the directory is missing.
