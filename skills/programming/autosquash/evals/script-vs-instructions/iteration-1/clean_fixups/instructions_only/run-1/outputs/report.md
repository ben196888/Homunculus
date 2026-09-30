# Autosquash report

- Base: `origin/main` (`e722e36f4e0e459a2d55fbc369c383435904b3b9`)
- Remote: `origin`; branch: `feature/autosquash`
- Folded commits: 2 existing `fixup!` commits
- Old HEAD: `a51903cf5e6a31989b9ac1e6316d70ca93e26d00`
- New HEAD: `2b13b7a91cb3eb3915cdd10731d4bb4f06a72fdd`
- Rewritten commits: `e77877d7e22c648ed827cdbe01284f02ac1adfcb` -> `5eecbc71cc9240b991f809bb6b66ef45e6d6ef11`; `90dde2fb8af4ad31cbd9bf004a2370f5ab15d2ca` -> `2b13b7a91cb3eb3915cdd10731d4bb4f06a72fdd`
- Tree verification: passed; pre-autosquash tree and final tree both `4f688c463da0c4707f39c56b78d885629217a71c`.
- Repository verification: `./verify.sh` passed.
- Workspace restoration: no stash was needed because the worktree was clean. Pre/post status, staged diff, unstaged diff, and untracked-file hashes all matched.
- Push/lease outcome: passed. Used `git push --force-with-lease="refs/heads/feature/autosquash:90dde2fb8af4ad31cbd9bf004a2370f5ab15d2ca" origin HEAD:refs/heads/feature/autosquash`; remote advanced to `2b13b7a91cb3eb3915cdd10731d4bb4f06a72fdd`.

Recovery guidance: use `git reflog` to locate the pre-rewrite state, then restore it with `git reset --hard a51903cf5e6a31989b9ac1e6316d70ca93e26d00`. The old remote tip was `90dde2fb8af4ad31cbd9bf004a2370f5ab15d2ca`; do not force-push a recovery unless the remote lease is checked first.
