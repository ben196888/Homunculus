# Clean marked history evaluation

Result: passed.

- Created an isolated working repository and a bare `origin` under `/tmp/autosquash-eval.Tua78q/`.
- Created and pushed `main`, then created `feature/clean-marked-history` with two normal commits and two later `fixup!` commits targeting them.
- Cleaned the feature history with an interactive autosquash rebase onto `main`.
- Updated the remote feature branch with `git push --force-with-lease`.
- Verified that the local and remote feature tips match, the feature contains exactly two commits above `main`, no `fixup!` subjects remain, and the expected renamed files are present.

Final refs:

- `main`: `ca36a7948947f206136f58c132dd15f9bbde9b70`
- `feature/clean-marked-history`: `811aa3bb72e2c9dfe065d1e08516cb6b8682168c`
