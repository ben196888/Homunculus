# Transcript notes

1. Created `/tmp/autosquash-ordinary.6a8TWy` with `git init -b main`.
2. Configured a repository-local evaluation identity and disabled commit signing.
3. Committed `chore: initial commit` on `main`.
4. Created `feature/ordinary-fix` and committed `add feature`.
5. Added a final ordinary commit with the exact subject `fix typo`.
6. Captured branch refs, `HEAD`, and the `main..HEAD` commit list.
7. Ran `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash main`.
8. Git reported: `Successfully rebased and updated refs/heads/feature/ordinary-fix.`
9. Captured the same evidence after cleanup. Before and after refs match exactly.
10. Searched feature subjects for `^(fixup!|squash!)`; none were found.
11. Confirmed the tip subject equals `fix typo` and the worktree is clean.

No project source or autosquash skill files were read or modified. Only the
disposable repository and this output directory were used.
