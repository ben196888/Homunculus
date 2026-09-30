# Transcript notes

Disposable paths:

- Working repository: `/tmp/autosquash-eval.Tua78q/work`
- Bare origin: `/tmp/autosquash-eval.Tua78q/origin.git`

Key commands executed:

```text
git init --bare origin.git
git init -b main work
git -C work commit --allow-empty -m 'chore: initialize repository'
git -C work remote add origin ../origin.git
git -C work push -u origin main
git -C work switch -c feature/clean-marked-history
git -C work commit -m 'feat: add alpha marker'
git -C work commit -m 'feat: add beta marker'
git -C work commit --fixup 035d828ee9cea15b010f93aa30a734cd4965f475
git -C work commit --fixup 9a9fb01ce13577f784c12a247e39bc07fe0a289a
git -C work push -u origin feature/clean-marked-history
GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash main
git push --force-with-lease origin feature/clean-marked-history
git --git-dir=../origin.git symbolic-ref HEAD refs/heads/main
```

History before cleanup:

```text
* c9d9f67 fixup! feat: add beta marker
* 0065990 fixup! feat: add alpha marker
* 9a9fb01 feat: add beta marker
* 035d828 feat: add alpha marker
* ca36a79 chore: initialize repository
```

Push evidence:

```text
+ c9d9f67...811aa3b feature/clean-marked-history -> feature/clean-marked-history (forced update)
```

Verification evidence:

```text
git rev-list --count main..feature/clean-marked-history                         # 2
git log --format=%s main..feature/clean-marked-history | rg -c '^fixup!'        # 0
git rev-parse feature/clean-marked-history == git rev-parse origin/feature/clean-marked-history
alpha-marker.txt and beta-marker.txt exist; the original filenames do not
bare origin HEAD -> refs/heads/main
verification=passed
```

Bare origin refs:

```text
811aa3bb72e2c9dfe065d1e08516cb6b8682168c refs/heads/feature/clean-marked-history
ca36a7948947f206136f58c132dd15f9bbde9b70 refs/heads/main
```
