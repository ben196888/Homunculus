# Autosquash report

- Base: `origin/main` (`e722e36f4e0e`)
- Remote: `origin`; feature ref: `origin/feature/autosquash`
- Divergence: remote reconciliation was required.
- Marked commits folded: 1 (`c6bbc48beefd` squash! targeting `a3593131fbde`)
- Observed old feature HEAD: `c6bbc48beefd81ac80ab370aeb311ba9a953baec`
- Observed new local HEAD: `29a8395c005082b9fc8e235d9e1f81427b7735a3`

The synthesized squash message was `feat: add feature`. The rewritten squashed
commit is `0c80802b3d0e7ee74f431069795a62cfd25c51e3`; the reconciled remote
commit `docs: add remote work` remains visible as `29a8395`.

Tree verification passed: the pre-rewrite marked-series tree
`aae026fab1718dbfea99c7b7b25acd85bf329351` equals the rewritten squashed
commit tree. The final HEAD tree additionally contains the reconciled remote
commit, as expected.

`./verify.sh` passed. Workspace restoration passed: the unstaged README change,
staged `staged.txt`, and untracked `scratch.txt` were restored. The helper
reported the saved dirty state fingerprint as restored successfully.

Push passed with an explicit `--force-with-lease` against the fetched remote
SHA. The bare-origin feature ref is
`29a8395c005082b9fc8e235d9e1f81427b7735a3`, matching local HEAD.

Recovery guidance: inspect `git reflog`, then restore the pre-operation tip with
`git reset --hard c6bbc48beefd81ac80ab370aeb311ba9a953baec` if needed. Because
the workspace was dirty, preserve or reapply its restored changes before any
such reset.

Unmarked commits were left in scope only as ordinary history: the reconciled
`docs: add remote work` commit was retained; no ordinary commit was folded.
