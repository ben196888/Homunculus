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

Install the P0 workflow skills:

```bash
npx skills add github.com/ben196888/homunculus --skill homunculus-productivity-task-ledger homunculus-productivity-change-detection homunculus-programming-mr-steward -g --copy
```

List available skills without installing:

```bash
npx skills add github.com/ben196888/homunculus --list
```

## Install script (all agents on a machine)

For a shared agent machine (Claude Code, Codex, and Cursor), run the
idempotent installer. It copies every Homunculus skill into each agent's
global skills directory, then tries to install the full pstack Claude Code
plugin (subagent workflows such as `/pstack:poteto-mode`):

```bash
./scripts/install.sh            # from github.com/ben196888/homunculus
./scripts/install.sh .          # from this checkout
./scripts/install.sh /path/to/Homunculus
```

Safe to rerun. If `claude` is not on `PATH`, or Claude Code is not signed in,
the skill copy still succeeds and the plugin step prints a skip note.

## Skills

- `homunculus-productivity-commit-plan` - review a multi-commit plan as the intended git history before implementation.
- `homunculus-productivity-create-printable-html` - self-contained, multilingual HTML documents optimized for printing.
- `homunculus-programming-codebase-search` - fast repository exploration using `rg`.
- `homunculus-programming-autosquash` - safely fold marked fixup and squash commits and update the remote branch.
- `homunculus-programming-wt-add` - create git worktrees for isolated tasks.
- `homunculus-programming-wt-drop` - remove completed worktrees and branches.
- `homunculus-programming-wt-find` - recover worktrees from partial context.
- `homunculus-productivity-development-workflow` - plan, clarify, document, implement, verify.
- `homunculus-productivity-rfc-writer` - write RFCs for cross-cutting or architectural changes.
- `homunculus-productivity-task-ledger` - persist concise local ticket, branch, verification, and MR state across tasks.
- `homunculus-productivity-change-detection` - check changed work has completion evidence before handoff.
- `homunculus-programming-mr-steward` - inspect GitLab MR state and recommend read-only follow-up actions.
- `homunculus-productivity-harness-session-retro` - analyze recent Codex sessions and recommend skills or harness components to create, improve, merge, keep, or retire.


### Third-party aliases

Vendored via `skill-aliases.yml` (see below). Public names keep the
`homunculus-` prefix.

**Ponytail** ([DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail), MIT):
`homunculus-programming-ponytail`, `-ponytail-review`, `-ponytail-audit`,
`-ponytail-debt`, `-ponytail-help`.

**pstack portable skills** ([cursor/plugins](https://github.com/cursor/plugins)
`pstack/`, MIT © Lauren Tan): all `homunculus-principles-*` principles,
`homunculus-writing-unslop`, `homunculus-writing-technical-writing`,
`homunculus-programming-tdd`. Cursor-only subagent workflows (`poteto-mode`,
`how`, `why`, `swarm`, `arena`, …) are not vendored here; install the full
pstack Claude Code plugin via `./scripts/install.sh` for those.

## Layout

Each skill lives under `skills/<subpath>/SKILL.md`. Public skill names use
`homunculus-<subpath-with-slashes-replaced-by-dashes>`. Supporting files live
beside the skill that uses them.

## Third-Party Skill Aliases

Homunculus can vendor third-party skills into `skills/` under local aliases.
Add desired aliases to `skill-aliases.yml`, then materialize them with:

```bash
pnpm skill-alias update productivity/article-editor
pnpm skill-alias update
```

Alias keys are paths relative to `skills/`. For example,
`productivity/article-editor` is copied to
`skills/productivity/article-editor/` and installed as
`homunculus-productivity-article-editor`.

When an upstream repo contains the same skill name more than once, set
`path:` to the skill directory relative to that repo root (for example
`path: skills/ponytail` or `path: pstack/skills/unslop`).

The resolved upstream commit is recorded in `skill-aliases.lock.yml`. Removing
an alias from the manifest does not delete files during update; run
`pnpm skill-alias prune` to remove stale locked aliases explicitly.
