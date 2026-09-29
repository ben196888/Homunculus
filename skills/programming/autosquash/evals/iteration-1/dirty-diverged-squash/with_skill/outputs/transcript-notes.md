# Transcript notes

All Git operations set up for this evaluation were run in the disposable tree under `/tmp/autosquash-eval.EW9Gor`; all helper operations used `GIT_TERMINAL_PROMPT=0`.

1. Initialized bare origin with default branch `main`, cloned it to `work`, and configured a local evaluation identity.
2. Created an initial commit containing `README.md`, `app.txt`, and `test.sh`, then pushed `main`.
3. Created `feature/autosquash`, committed `feat: add feature marker` (`74eee979088980a816369b4ed39e235d5b398cfa`), and pushed it.
4. Cloned a second disposable actor, committed `docs: add remote branch note` on the remote feature branch, and pushed it.
5. In the original clone, committed `squash! feat: add feature marker` (`2e2bd4d392bb9f7636540b928852065f3cfea671`), creating divergence.
6. Added a staged README edit, an unstaged `app.txt` edit, and untracked `scratch.txt`; captured the before fingerprint.
7. Ran the skill plan:

   `python3 .../scripts/autosquash.py plan --base origin/main --remote origin`

   It reported base `origin/main`, remote `origin/feature/autosquash (diverged)`, and one squash commit targeting `74eee9790889`.

8. Inspected the fixture README and used its smallest relevant check, `sh test.sh`.
9. Ran the skill apply command non-interactively with:

   `--squash-message '74eee979088980a816369b4ed39e235d5b398cfa=feat: add feature and squashed markers' --verify 'sh test.sh'`

10. Helper result:

    `Autosquash complete: 2e2bd4d392bb -> c239bcaa26f5`

    It also reported one folded commit, diverged reconciliation, one passed verification, restored workspace, exact force-with-lease push, and the reflog recovery command.
11. Independently verified local/remote SHA equality, zero marked commits in the feature range, the final log, `sh test.sh`, and the restored dirty-state fingerprint.
