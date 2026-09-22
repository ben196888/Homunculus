---
name: homunculus-productivity-commit-plan
description: Plan a multi-commit engineering change as an ordered, reviewable sequence of Conventional Commits. Use automatically in Plan mode when a change needs more than one commit, or when the user asks for a commit plan, to plan the commits, to break work into commits, or to see the git history before implementation. Skip routine single-commit changes.
---

# Commit Plan

Before implementing a multi-commit change, inspect the relevant code, existing utilities, checks, and git base. Write the plan in the plan file as an ordered list of commits. Each step is one intended commit, titled with its final Conventional Commits subject. Present the proposed history for user review before writing implementation code. An explicit request for a commit plan takes precedence over the usual single-commit skip.

## Plan file

Use this Markdown structure (the headings and list are not YAML):

```markdown
# <Short title>

## Context
<Why the change is needed; current state with paths; target state; user decisions about scope or strictness; the regression guard that demonstrates unchanged behavior.>
Branch: <branch>, based on <base>.

## Steps (one commit each, Conventional Commits)

1. **<type>(<scope>): <imperative subject under 72 characters>**
   - Files or directories touched; give representative paths for repeated patterns.
   - Key decisions and reasons, behavior or edge cases to preserve, and existing utilities to reuse (with paths).

2. **...**

Out of scope: <explicit list>

## Verification
- Checks that must pass after every commit, including applicable lint, typecheck, and build commands.
- End-to-end checks after the last commit: tests, regression or visual baselines, and relevant manual checks.
- Follow-up workflow: review and a draft PR with verification evidence, when appropriate to the task.
```

Use the actual branch and base when known. If either is undecided, say so rather than inventing it. Make each step concrete enough to review, without listing every file when a directory pattern is clearer. The number of steps follows the work; do not copy the attached TypeScript migration's ten steps into unrelated plans.

## Sequence and boundaries

1. Put foundational configuration, tooling, and dependency changes first.
2. Add shared types, contracts, and constants before their users.
3. Change leaf modules before callers: library code, then components, pages, and integrations as applicable.
4. Put configuration and tests that depend on changed source after that source. This differs from foundational setup in step 1.
5. Leave cleanup, such as removing temporary compatibility flags or dead code, until the conversion is complete; update docs and references last.
6. Keep one concern per commit. Separate renames from behavior changes.
7. Require a green tree after every commit. If a proposed step cannot pass the project's applicable lint, typecheck, and build checks by itself, merge it with a neighbor or split it differently. Specify any temporary compatibility setting needed to keep intermediate commits green.

Use `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, or `perf` according to intent. Use a scope for a monorepo package or area. Write an imperative subject under 72 characters. File-extension migrations are usually `refactor`, tooling and dependency setup `chore`, and test-only changes `test`.

## After the plan is approved

- Run the stated per-commit checks before each commit. In a shell command that joins checks, use `&&` so a failure prevents the commit; do not use `;` for that chain.
- For a minor correction discovered later, use `git commit --fixup <sha>` against the earlier commit on an unprotected branch. Never amend, fix up, or squash commits on `main`, `master`, or `develop`.
- If execution must diverge from the reviewed sequence, update the plan file and tell the user why.
- Use the step list as the progress tracker: mark each completed step with its commit SHA.
