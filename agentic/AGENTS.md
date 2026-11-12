# Global Agent Instructions

These are my personal defaults for every project. Keep them applied unless a
more specific project-level `AGENTS.md` (or `CLAUDE.md`) overrides them.

## Git Commit Convention

- Use Conventional Commits:
  `<type>(<optional scope>): <short description>`
- Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`,
  `style`, `perf`
- Keep the subject line under 72 characters
- Use imperative mood ("add", not "added")
- Do not add a commit body unless the change is non-obvious

## Commit Frequency

- Make one commit per small-scope change; granular commits are easier to
  review, revert, and bisect
- Never batch unrelated changes into a single commit

## Fixup / Squash for Minor Corrections

- For typos, syntax errors, or other minor corrections to an earlier commit
  on the same branch, reference the original commit with:
  - `git commit --fixup <sha>`
  - `git commit --squash <sha>`
- Do not amend, fixup, or squash on protected branches (GitLab Flow):
  - `main`
  - `master`
  - `develop`

## Codebase Search

- Default to `rg` for text search and file discovery:
  - `rg <pattern>`
  - `rg --files`
- Use language filters to narrow scope early:
  - `rg -t sh <pattern>`
  - `rg -t ts <pattern>`
- Use `ast-grep` only for structural or AST-level search, such as function
  calls, annotations, API usage, and refactoring patterns
  (e.g. `ast-grep -p 'foo($ARG)'`)
- Use `git grep` and `git log -S` for history, regression debugging, and
  origin tracing
- Avoid `grep -R`, `find`, and `ls` for code exploration
- Do not use `ast-grep` when plain text search is sufficient
- Always narrow scope before scanning
