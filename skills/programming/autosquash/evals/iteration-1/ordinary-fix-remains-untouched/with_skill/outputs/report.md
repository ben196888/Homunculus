# Autosquash report

- Result: no-op; the branch was not rewritten or pushed.
- Branch: `feature/ordinary-fix`
- Resolved base: `origin/main` at `bceda20bc9115753e463be7731eb0c424b74bc41`
- Resolved remote branch: `origin/feature/ordinary-fix`, in sync at `885cd845fbe6f9b4ce635bc25eb616f440496469`
- Marked commits found: 0
- Folded commit count: 0
- Old SHA: `885cd845fbe6f9b4ce635bc25eb616f440496469`
- New SHA: `885cd845fbe6f9b4ce635bc25eb616f440496469`
- Committed tree before/after: `dd8d73efae22f4fe7e09758278a6b1bbaf2cc18c`
- Workspace restoration: not needed; the worktree was clean and no stash was created.
- Push result: not attempted, as required for a plan with no marked commits.
- Project verification: no project check was available in the disposable fixture. The successful planner result plus exact local, tracking, bare-remote, commit, and tree identity checks verify the no-op.
- Recovery: no rewrite occurred. If recovery were nevertheless needed, the original tip is recoverable with `git reset --hard 885cd845fbe6f9b4ce635bc25eb616f440496469` (the same SHA also remains in the reflog).

The latest ordinary commit, `fix typo`, remained visibly out of scope because its subject does not begin with `fixup! ` or `squash! `.

## Planner output

```text
Branch: feature/ordinary-fix
Base: origin/main (bceda20bc911)
Remote: origin/feature/ordinary-fix (in-sync)
Marked commits: 0
No fixup! or squash! commits found; apply would not rewrite or push.
```

Planner exit status: 0.
