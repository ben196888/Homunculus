### `.github/workflows/update-homepage-visual-baselines.yml:84` (and the identical filter at `:103`)

risk: `core.quotePath` wraps any path with a space or non-ASCII byte in double
quotes, so `^.. homepage/...` never matches and a real baseline is reported as an
outside-baseline change. Latent — today's eight `publicRoutes[].name` values are all
ASCII kebab-case; a route named `首頁` or `en home` breaks the run. Replace the pipe
with a git pathspec exclusion:
`git status --porcelain=v1 -uall -- ':(exclude,glob)homepage/e2e/__screenshots__/**/*.png' > "$RUNNER_TEMP/pre-generation-status"`.

```
?? "homepage/e2e/__screenshots__/desktop/\351\246\226\351\240\201.png"   # survives grep -Ev
```

### `.github/workflows/update-homepage-visual-baselines.yml:85` (and `:104`)

risk: `|| true` covers the whole pipeline, so a failing `git status` writes a
truncated file and the guard reports success — verified: `fatal: not a git
repository` still yields a passing step under `-eo pipefail`. The pathspec form
above needs no `|| true` (`git status` exits 0 on empty output) and aborts with
rc=128 instead.

### `.github/workflows/update-homepage-visual-baselines.yml:102`

nit: the pre/post comparison is on status codes and paths, not content, so a path
already dirty before generation can be rewritten by generation undetected. Harmless
in practice because `:127` stages only `homepage/e2e/__screenshots__` — noting it so
it is not mistaken for a leak later.
