# Autosquash report

- Base: `origin/main` (`48475ea4fbf28ef7e68a8381bafffff573ca891f`)
- Remote: `origin`; branch `feature/autosquash`
- Marked commits folded: 2 (`fixup!` only; ordinary commits remained in scope as targets)
- Observed old SHAs:
  - `db1e55a8046b3f491bd9bf9f746d012734718c75` target `feat: add alpha`, with fixup `590f20518537aa78cd55607554a769e303abec5a`
  - `5bda6e4b47ff471755516657ba53b1765774e942` target `feat: add beta`, with fixup `0c60deb33068ef7c3cf830f1fea6b249fa542cc1`
- Observed new SHAs:
  - alpha: `9395f59877d3246bb679bdc2211c11462fcfac79`
  - beta / final tip: `a9a7882836eee0b69aba427146ce40ec1b6da8d0`
- Tree verification: passed. Old tip `0c60deb33068^{tree}` and new tip `HEAD^{tree}` were both `4f688c463da0c4707f39c56b78d885629217a71c`; `git diff --exit-code 0c60deb33068 HEAD` was clean.
- Project verification: `./verify.sh` passed.
- Workspace restoration: yes. Final porcelain status was clean; no user changes were present to restore.
- Push/lease outcome: succeeded using explicit force-with-lease against the fetched `origin/feature/autosquash` SHA. The bare origin feature ref is now `a9a7882836eee0b69aba427146ce40ec1b6da8d0`.
- Recovery guidance: if rollback is required, inspect `git reflog` and restore the pre-rewrite tip with `git reset --hard 0c60deb33068ef7c3cf830f1fea6b249fa542cc1`. Do not use this reset if new local work has been added.
