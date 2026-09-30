# Autosquash report

- Base: `origin/main` at `6fe7484756492032a61bd6eb536c25cf94c930de`
- Remote: `origin`; branch: `feature/autosquash`
- Folded commits: 1 existing `fixup!` commit
- Old local HEAD: `608f82999af2d5f7b543669df32544a3c6194a4a`
- New local HEAD: `0794dd2f4694a6f291861e42ec1331e2f21d8e60`
- Fetched remote SHA used for the lease: `7bb9bd1991ec397e89d0701f6bb11b5496f40e77`

## Verification

The committed tree before autosquash and after autosquash was identical:
`9783cda16b6b7bb2d17c6819c81d40856b127ab6`. Required `./verify.sh` passed.

The workspace was clean before the operation, so no stash was created. After
verification, the workspace was restored unchanged and remains clean; staged,
unstaged, and untracked-file checks all matched the pre-run snapshot.

## Push / lease outcome

The exact command used was a force-with-lease for
`refs/heads/feature/autosquash:7bb9bd1991ec397e89d0701f6bb11b5496f40e77`.
It was rejected with `stale info` because `./verify.sh` intentionally advanced
the bare-origin feature ref to `72e9d8c690420f58f681708632b9384c5d0c312f`.
No retry or weaker force push was performed, and concurrent remote work was not
overwritten.

## Recovery guidance

The cleaned local history can be restored with:

```sh
git reflog
git reset --hard 608f82999af2d5f7b543669df32544a3c6194a4a
```

Do not retry the rejected lease without first reviewing and reconciling the
remote commit at `72e9d8c690420f58f681708632b9384c5d0c312f`.
