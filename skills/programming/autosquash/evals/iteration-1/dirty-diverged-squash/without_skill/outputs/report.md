# Dirty, diverged autosquash evaluation report

## Result

The disposable `feature/reconcile` branch was reconciled, autosquashed, cleaned, verified, and pushed to its bare origin. Local `HEAD` and `origin/feature/reconcile` both resolve to `4ed2c51`. The final worktree is clean and contains no `fixup!` or `squash!` subjects.

## Initial state

- Bare origin: `/tmp/codex-autosquash-eval.lrOsxH/origin.git`
- Working clone: `/tmp/codex-autosquash-eval.lrOsxH/work`
- Branch: `feature/reconcile`
- Divergence: two local commits ahead and one remote commit behind
- Autosquash marker: `a3835f4 squash! feat: add feature value`
- Staged change: `staged-change.txt`
- Unstaged change: `README.md`
- Untracked file: `untracked-scratch.txt`

## Reconciliation

1. Saved tracked and untracked dirty state with `git stash push --include-untracked`.
2. Rebased the local commits onto `origin/feature/reconcile` non-interactively.
3. Ran `GIT_SEQUENCE_EDITOR=:` and `GIT_EDITOR=true` with `git rebase -i --autosquash origin/main`.
4. Restored the stash. `README.md` conflicted because both the remote peer and the saved local work changed it; the resolution retained both lines.
5. Committed the restored staged, unstaged, and untracked content as `4ed2c51 chore: preserve local worktree changes`, then dropped the retained stash.
6. Updated the rewritten remote branch with `git push --force-with-lease origin feature/reconcile`.

## Verification

- `git status --short --branch` shows no path entries and no ahead/behind counts.
- `git diff --quiet` and `git diff --cached --quiet` returned exit code 0.
- `git ls-files --others --exclude-standard` returned no files.
- `HEAD` equals `origin/feature/reconcile`.
- No subject under `origin/main..HEAD` starts with `fixup!` or `squash!`.
- `git fsck --no-dangling` completed successfully.
- `app.txt` contains `feature value: final`.
- `README.md` contains both `Remote peer update.` and `Unstaged local work.`.
- The final history preserves the remote peer note, local feature note, squashed feature result, and recovered dirty changes.
