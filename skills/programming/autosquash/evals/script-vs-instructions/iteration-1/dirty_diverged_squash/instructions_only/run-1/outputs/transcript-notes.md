# Transcript notes

1. Fetched `origin`; remote feature advanced to `1a79c1a`, while local HEAD was `23e4f06`.
2. Inspected `origin/main..HEAD`: `f21da9d feat: add feature`, then `23e4f06 squash! feat: add feature`; no merges.
3. Snapshot showed README unstaged work, staged `staged.txt`, and untracked `scratch.txt` (hash `2fbf7dee647928d720cb5dccf60f93496688b503`).
4. Saved dirty state as stash `2dc1e7b2f8b76276c98fd4783e6dcf32743af2cd`.
5. Rebasing local-only work onto fetched `origin/feature/autosquash` produced `0554efe`; tree before autosquash was `5c47f72c0a892179c177cfb400b99c8d7d6dadce`.
6. Native interactive autosquash against `origin/main` folded the squash commit and produced `67b9aae` plus preserved remote work as final `c432a94`; tree identity was unchanged.
7. `./verify.sh` passed. `git stash apply --index` restored the exact staged, unstaged, and untracked work.
8. Exact lease push succeeded: `1a79c1a...c432a94` forced update. The workflow stash was then dropped.
