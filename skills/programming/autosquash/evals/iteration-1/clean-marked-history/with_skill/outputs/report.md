# Autosquash evaluation report

- Result: pass
- Disposable repository: `/tmp/autosquash-eval.rECmE7/repo`
- Resolved base: `origin/main` at `4a2d82aba6e1`
- Remote branch: `origin/feature/autosquash-eval`
- Marked commits folded: 2
- Old feature tip: `bbba196bbf3c3bfe119411c8784b1cd0fcc9e6f6`
- New feature tip: `2ce96d3824d938cd59b94e1da058f036c53c6291`
- Verification: `./verify.sh` passed; committed-tree identity check passed
- Workspace restoration: yes (clean before and after)
- Push: succeeded with an exact force-with-lease; local HEAD equals the remote feature ref
- Final history: two ordinary feature commits remain and no `fixup!` or `squash!` subjects remain
- Unmarked commits: the two feature commits and the base commit remained in scope only as their original commits; none were folded together
- Recovery: `git reflog; git reset --hard bbba196bbf3c3bfe119411c8784b1cd0fcc9e6f6`
