# Transcript notes

1. Created disposable working and bare repositories with `git init -b main repo` and `git init --bare origin.git`.
2. Committed the fixture on `main` as `4a2d82a` and pushed it to `origin/main`.
3. Created `feature/autosquash-eval` with ordinary commits `1cb6ccc feat: add alpha value` and `04cdffb feat: add beta value`.
4. Used `git commit --fixup` to create `fff8780` targeting `1cb6ccc` and `bbba196` targeting `04cdffb`, then pushed the feature branch.
5. Ran the skill plan command:

   `python3 <skill>/scripts/autosquash.py plan --base origin/main --remote origin`

   Evidence: the plan reported an in-sync remote and exactly two unambiguous fixups mapped to the intended targets.

6. Ran the skill apply command:

   `python3 <skill>/scripts/autosquash.py apply --base origin/main --remote origin --verify './verify.sh'`

   Evidence: the helper reported `bbba196bbf3c -> 2ce96d3824d9`, two folded commits, one passing verification command, restored workspace, and a force-with-lease push.

7. Post-run checks fetched the remote, reran `./verify.sh`, compared `HEAD` with `origin/feature/autosquash-eval`, searched feature subjects for marked commits, checked clean status, and enumerated bare-origin refs.

   Evidence: all checks exited zero; the bare origin contains `main` at `4a2d82a...` and `feature/autosquash-eval` at `2ce96d3...`; the final log contains only the base and two ordinary feature commits.
