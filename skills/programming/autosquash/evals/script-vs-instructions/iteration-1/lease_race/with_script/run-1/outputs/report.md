# Autosquash report

- Base: `origin/main` (`6fe7484756492032a61bd6eb536c25cf94c930de`)
- Remote: `origin`
- Folded commits: 1 (`fixup!` `7fcf7bd9be82e939becbd42e9b9c2641739973b5` into `48346c27d1018286b1895a4503075259c88daf7a`)
- Observed old `HEAD`: `7fcf7bd9be82e939becbd42e9b9c2641739973b5`
- Observed new `HEAD`: `89a9b9af8e70114ae58b2698334ac83db8f2d978` (`feat: add feature`)

## Verification

- Required repository check: `./verify.sh` — passed far enough to complete the check; it intentionally published a concurrent remote update.
- Committed-tree verification: passed. Old and new tree: `9783cda16b6b7bb2d17c6819c81d40856b127ab6`.
- Ordinary unmarked commit `8867275` remained out of scope.

## Workspace restoration

Restoration passed. Final worktree and index are clean (`git status --porcelain=v1 -uall` produced no output); local `HEAD` remains the rewritten commit.

## Push / lease outcome

The explicit fetched-SHA lease rejected the push because the verification command created concurrent remote work. The local remote-tracking ref remained `48346c27d1018286b1895a4503075259c88daf7a`; the bare origin feature ref is now `b84e9b0d29202506ea3e421e5b98ba730e88649e`. No remote history was overwritten.

Recovery: fetch again and run a fresh plan before retrying. Inspect the concurrent commit and reconcile it if needed; then rerun the helper with `--base origin/main --remote origin`. The rejected rewrite is recoverable from the reflog, for example `git reflog show feature/autosquash` and the pre-rewrite entry `7fcf7bd9be82…`; do not force-push without a fresh explicit lease.
