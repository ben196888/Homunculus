# Homunculus

Personal collection of agentic skills for Claude Code, Codex, and other agents
that support the `skills` package.

## Install

Install all skills globally for all supported agents:

```bash
npx skills add ben196888/Homunculus --all --copy -g
```

Install selected skills:

```bash
npx skills add ben196888/Homunculus --skill codebase-search wt-add wt-drop wt-find -g --copy
```

List available skills without installing:

```bash
npx skills add ben196888/Homunculus --list
```

## Skills

- `codebase-search` - fast repository exploration using `rg`.
- `development-workflow` - plan, clarify, document, implement, verify.
- `rfc-writer` - write RFCs for cross-cutting or architectural changes.
- `wt:add` - create git worktrees for isolated tasks.
- `wt:drop` - remove completed worktrees and branches.
- `wt:find` - recover worktrees from partial context.
- `codex:programming` - prepare structured Claude-to-Codex delegation prompts.

## Layout

Each skill lives under `skills/<name>/SKILL.md`. Supporting files live beside
the skill that uses them.
