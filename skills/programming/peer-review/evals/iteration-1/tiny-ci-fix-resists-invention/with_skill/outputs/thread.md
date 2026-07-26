Guard fix confirmed: replayed run 29170292380's two rejects (pre-existing
`@next-swc-linux-x64-gnu` cache zip, collapsed `homepage/e2e/__screenshots__/`
untracked dir) in a scratch repo — old guard fails, new guard passes, and it still
fails on a leaked `test-results/trace.zip`, a modified tracked file, and non-PNG
junk inside the snapshot dir.

Follow-ups, none blocking:

- No test covers this guard, and it has now been wrong once in production. Extract
  it to `homepage/scripts/validate-baseline-changes.sh` and cover the pre-existing-dirt,
  leaked-file, and quoted-filename cases so the next regression is caught before a
  dispatch run.
- No `actionlint` in CI for four workflow files. It bundles `shellcheck`, which flags
  the masked-exit-status pattern in the inline comment below.
- `16` is hardcoded while the real count is `publicRoutes.length × projects.length`.
  Adding a ninth route fails with "Expected exactly 16" instead of anything
  actionable. Out of scope here, worth deriving later.
