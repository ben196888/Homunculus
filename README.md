# Homunculus

Personal collection of agentic skills for Claude Code, Codex, and other agents
that support the `skills` package.

## Install

Install all skills for the detected agent:

```bash
npx skills add github.com/ben196888/homunculus
```

Install all skills globally for all supported agents:

```bash
npx skills add github.com/ben196888/homunculus --all --copy -g
```

Install for a specific agent:

```bash
npx skills add github.com/ben196888/homunculus --skill '*' --agent claude-code --copy -g -y
npx skills add github.com/ben196888/homunculus --skill '*' --agent codex --copy -g -y
```

Install selected skills:

```bash
npx skills add github.com/ben196888/homunculus --skill homunculus-programming-codebase-search homunculus-programming-wt-add homunculus-programming-wt-drop homunculus-programming-wt-find -g --copy
```

List available skills without installing:

```bash
npx skills add github.com/ben196888/homunculus --list
```

## Skills

- `homunculus-programming-codebase-search` - fast repository exploration using `rg`.
- `homunculus-programming-wt-add` - create git worktrees for isolated tasks.
- `homunculus-programming-wt-drop` - remove completed worktrees and branches.
- `homunculus-programming-wt-find` - recover worktrees from partial context.
- `homunculus-productivity-development-workflow` - plan, clarify, document, implement, verify.
- `homunculus-productivity-rfc-writer` - write RFCs for cross-cutting or architectural changes.

## Layout

Each skill lives under `skills/<category>/<skill>/SKILL.md`. Public skill names
use `homunculus-<category>-<skill>`. Supporting files live beside the skill
that uses them.
