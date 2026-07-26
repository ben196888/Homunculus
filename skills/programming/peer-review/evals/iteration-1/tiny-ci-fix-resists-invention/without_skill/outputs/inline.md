<!-- Drafted only. PR #409 is already merged; not posted. -->

## 1. `.github/workflows/update-homepage-visual-baselines.yml` line 84 (added)

Anchor: `            | grep -Ev '^.. homepage/e2e/__screenshots__/.*\.png$' \`
(also applies to the identical line 103 in the `Validate generated files` step)

Nit, non-blocking. `git status --porcelain` quotes any path containing a space or
non-ASCII byte, so the line becomes
`?? "homepage/e2e/__screenshots__/desktop/en home.png"` and the leading `"` makes it miss
this filter — the file then reads as an unexpected non-snapshot change and fails the
guard. I confirmed that in a scratch repo. All 16 current baselines are ASCII and
hyphenated, so this is latent, but it is a false-failure trap for whoever adds a visual
case with a looser test title. Suggest:

```sh
git -c core.quotePath=false status --porcelain=v1 -uall \
  | grep -Ev '^.. "?homepage/e2e/__screenshots__/.*\.png"?$' \
```

## 2. `.github/workflows/update-homepage-visual-baselines.yml` line 85 (added)

Anchor: `            > "$RUNNER_TEMP/pre-generation-status" || true`

Nit, non-blocking. `|| true` is required here (grep exits 1 when the tree is clean, and
the runner shell is `bash -e`), but it also absorbs a genuine `git status` failure. In
that case the baseline file is silently empty and the later comparison reads as "nothing
pre-existing", which is the least safe interpretation. If you touch this again, guarding
only the grep — e.g. `{ git status ... || exit 1; } | grep -Ev ... > file || true` — keeps
the tolerance without hiding a real error.

## 3. `.github/workflows/update-homepage-visual-baselines.yml` lines 106-111 (added)

Anchor:
```
          if ! diff -u \
            "$RUNNER_TEMP/pre-generation-status" \
            "$RUNNER_TEMP/post-generation-status"; then
```

Observation, no change requested. This compares porcelain *lines*, not content, so a file
that was already dirty before generation and is modified again by generation keeps the
same ` M path` line and passes unnoticed (verified in a scratch repo). That is acceptable
here only because `git add homepage/e2e/__screenshots__` at line 127 keeps the commit
scoped to baselines, so an undetected change can never be committed. Please keep that
`git add` path-scoped — it is now load-bearing for this guard's safety, more so than
before this PR.

Also note the comparison is symmetric: a pre-existing untracked file that *disappears*
during generation also fails the guard. Probably the behavior you want, but it is a
consequence of `diff` rather than a stated rule.
