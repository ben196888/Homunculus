# Autosquash evaluation report

Result: **PASS**

A disposable repository was created at `/tmp/autosquash-ordinary.6a8TWy` with
`main` and `feature/ordinary-fix`. The feature branch contained two ordinary
commits, ending with a commit whose exact subject was `fix typo`.

The branch was cleaned with:

```sh
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash main
```

Because neither feature commit had a `fixup!` or `squash!` subject, autosquash
left both commits and their object IDs unchanged. Verification confirmed:

- the feature tip is still `ba5cd9705c06d80acfd7bc453fbc7664ce0a2f65`;
- its exact subject is still `fix typo`;
- the feature range contains no `fixup!` or `squash!` commit;
- the worktree is clean after the operation.
