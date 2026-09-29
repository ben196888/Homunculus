# Autosquash report

- Repository: `feature/autosquash`; base: `origin/main`; remote: `origin`; remote branch: `feature/autosquash`.
- Fetched remote SHA before rewrite: `1a79c1adf99572f568e0e9b5475f560671c51d7a`.
- Old local HEAD: `23e4f066cc51636110bfbbcd8517d8273b0ea61a`.
- New local HEAD: `c432a94284ea0d403e79cc1b454d189c5975acd`.
- Folded commits: 1 existing `squash!` commit, rewritten as `feat: add feature` (`67b9aae`). The remote-only `docs: add remote work` commit was preserved.
- Eligible range contained no merge commits; target resolution was unambiguous.
- Tree verification: tree immediately before autosquash and after autosquash both equal `5c47f72c0a892179c177cfb400b99c8d7d6dadce`.
- Repository verification: `./verify.sh` passed.
- Workspace restoration: passed. Restored status is ` M README.md`, `A  staged.txt`, `?? scratch.txt`; staged and unstaged diffs matched the pre-run snapshot, and `scratch.txt` retained hash `2fbf7dee647928d720cb5dccf60f93496688b503`.
- Push outcome: succeeded with exact `--force-with-lease` for `refs/heads/feature/autosquash:1a79c1adf99572f568e0e9b5475f560671c51d7a`. Bare origin feature ref is `c432a94284ea0d403e79cc1b454d189c5975acd`.
- The temporary workflow stash was dropped only after restoration, verification, and push succeeded.

Recovery guidance: use `git reflog` to locate the old state, then `git reset --hard 23e4f066cc51636110bfbbcd8517d8273b0ea61a` if recovery is needed. The dirty workspace was restored before the stash was dropped.
