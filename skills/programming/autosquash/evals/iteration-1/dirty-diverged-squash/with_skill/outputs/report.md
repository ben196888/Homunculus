# Autosquash evaluation report

Result: PASS

- Disposable repository: `/tmp/autosquash-eval.EW9Gor/work`
- Bare origin: `/tmp/autosquash-eval.EW9Gor/origin.git`
- Branch: `feature/autosquash`
- Resolved base: `origin/main` at `e5bc6bb32a7d`
- Resolved remote: `origin/feature/autosquash`
- Initial branch relationship after fetch: diverged
- Marked commits folded: 1 `squash!` commit
- Old local SHA: `2e2bd4d392bb9f7636540b928852065f3cfea671`
- New local SHA: `c239bcaa26f5dcc4ce81de4879adf12554e5e46f`
- Synthesized target message: `feat: add feature and squashed markers`
- Verification: `sh test.sh` passed while dirty work was isolated
- Committed-tree identity check: passed (reported by the helper)
- Workspace restoration: passed; staged, unstaged, and untracked fingerprints match the before evidence
- Push: passed with exact force-with-lease to `origin/feature/autosquash`
- Remote verification: remote SHA equals local HEAD at `c239bcaa26f5dcc4ce81de4879adf12554e5e46f`
- Remaining marked commits in `origin/main..HEAD`: 0
- Ordinary unmarked remote commit retained: `docs: add remote branch note`
- Reflog recovery: `git reflog; git reset --hard 2e2bd4d392bb9f7636540b928852065f3cfea671`

The pre-plan short branch status used the stale tracking ref and displayed only `ahead 1`; the skill plan fetched origin and correctly reported the branch as diverged before applying any rewrite.
