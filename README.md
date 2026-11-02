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

## Machine setup (Codex, Claude Code, Cursor)

`scripts/install.sh` is the official, idempotent setup for any machine that
runs coding agents: an agent VM (such as a Grok Bot box) or a daily laptop,
on macOS or Linux. It installs global instructions, skills, the pstack
Claude Code plugin, and MCP servers.

One-liner (no clone needed):

```bash
curl -fsSL https://raw.githubusercontent.com/ben196888/homunculus/main/scripts/install.sh | bash
```

When it is not run from inside a Homunculus checkout, the script fetches a
pinned copy (detached at `--ref`, default `main`) into `~/.homunculus` and
runs from there; rerunning updates that copy. If `~/.homunculus` has local
changes it is left as-is. Needs `git`, `python3`, and (for skills) `npx`.

From a checkout:

```bash
./scripts/install.sh --source .          # skills from this checkout
./scripts/install.sh                     # skills from github.com/ben196888/homunculus
./scripts/install.sh --dry-run --source .
```

Pass flags through the one-liner with `bash -s --`:

```bash
curl -fsSL https://raw.githubusercontent.com/ben196888/homunculus/main/scripts/install.sh | bash -s -- --yes --tools codex,claude
```

### Flags

| Flag | Effect |
| --- | --- |
| `-n`, `--dry-run` | Print what would change; write nothing |
| `-y`, `--yes` | Never prompt; differing instruction files get the default (merge) |
| `--merge` | Differing instruction file: back up, put the Homunculus block on top, keep existing content below (default) |
| `--overwrite` | Differing instruction file: back up, then replace |
| `--skip` | Differing instruction file: leave it alone |
| `--tools codex,claude,cursor` | Limit every step to these tools (default: all three) |
| `--source PATH\|URL` | Where skills come from (positional `SOURCE` still works; `.` = this checkout) |
| `--ref REF` | Git ref for the `~/.homunculus` copy (env `HOMUNCULUS_REF`) |
| `--no-instructions` / `--no-skills` / `--no-plugin` | Skip that step |
| `--no-mcp` | Skip MCP configuration |
| `--mcp` | Configure MCP even on a Grok Bot machine |

Environment: `HOMUNCULUS_HOME` (checkout dir, default `~/.homunculus`),
`HOMUNCULUS_REPO_URL`, `HOMUNCULUS_GROK_BOT` (`1` force / `0` disable Grok
Bot detection), `CODEX_HOME`, `CLAUDE_CONFIG_DIR`.

### Per-tool support

| | Codex | Claude Code | Cursor (incl. Grok Bot on Cursor) |
| --- | --- | --- | --- |
| Global instructions | `~/.codex/AGENTS.md` | `~/.claude/CLAUDE.md` | `~/.cursor/rules/homunculus-global.mdc` (`alwaysApply: true`) |
| Homunculus skills | full set mirrored to `~/.codex/skills` | non-pstack set in `~/.claude/skills` | non-pstack set in `~/.agents/skills` |
| pstack | vendored aliases (in the skill set) | `pstack@cursor-plugins` plugin | Cursor's native pstack plugin |
| MCP (when detected) | `[mcp_servers.*]` appended to `~/.codex/config.toml` | `claude mcp add --scope user` | `~/.cursor/mcp.json` |
| Detected by | `codex` on `PATH` or `~/.codex` exists | `claude` on `PATH` | `cursor`/`cursor-agent` on `PATH`, `~/.cursor`, or `/Applications/Cursor.app` |

Instructions and skills install for every tool in `--tools`; MCP is only
written for tools detected before the run starts.

### Global instructions

[`agentic/AGENTS.md`](agentic/AGENTS.md) is the single source. At install
time it is wrapped in a marked block
(`<!-- BEGIN HOMUNCULUS GLOBAL INSTRUCTIONS ... -->` …
`<!-- END HOMUNCULUS GLOBAL INSTRUCTIONS -->`) and written to each tool's
file; the Cursor rule adds always-apply frontmatter. Preview with
`python3 scripts/agent_setup.py render --tool claude`.

- Missing file: created.
- File already has the block: only the block is refreshed; text around it stays.
- File is an unmodified copy from the old mac-set-up `agentic/` installer:
  backed up and replaced.
- Any other existing file: backed up to `<file>.homunculus-bak-<timestamp>`,
  then merged. On a terminal you are asked to merge, overwrite, skip, or
  view a diff; without a TTY (agent VMs, CI) the `--merge`/`--overwrite`/`--skip`
  flag decides, defaulting to merge.

Nothing is backed up or rewritten when the file is already current, so a
rerun changes nothing.

### MCP servers

Servers are listed in [`agentic/mcp-servers.json`](agentic/mcp-servers.json)
(currently Discord, `npx -y discord-mcp@latest`). Entries name the env vars a
server needs (`env_vars`); secret values are never written to config. Codex
gets `env_vars = [...]`, Cursor gets `"env": {"VAR": "${env:VAR}"}`, and
Claude Code inherits the variable from your shell. Export them yourself,
e.g. `export DISCORD_TOKEN=...` in your shell profile. Existing entries with
the same name are never changed.

**Grok Bot machines** supply their own connectors, so the MCP step is skipped
automatically when `/home/box/agent-data` exists (override the path with
`HOMUNCULUS_GROK_BOT_MARKER`, or set `HOMUNCULUS_GROK_BOT=1`/`0`). Use
`--mcp` to configure anyway, or `--no-mcp` to skip MCP on any machine.

### Skills and plugins

Each harness gets exactly **one** copy of every skill. Third-party skills reach each harness either as a native **plugin** or as a
Homunculus **alias** (vendored copy from `skill-aliases.yml`):

| Third-party source | Skills | Claude Code | Cursor | Codex |
| --- | --- | --- | --- | --- |
| pstack ([cursor/plugins](https://github.com/cursor/plugins) `pstack/`) | `principles/*`, `writing/unslop`, `writing/technical-writing`, `programming/tdd` | plugin (`pstack@cursor-plugins`, full set incl. subagent workflows) | plugin (Cursor's native pstack) | alias (no plugin; subagent workflows not available) |
| Ponytail ([DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail)) | `programming/ponytail*` | alias | alias | alias |
| Matt Pocock ([mattpocock/skills](https://github.com/mattpocock/skills)) | `productivity/grilling`, `productivity/edit-article` (pinned) | alias | alias | alias |
| Homunculus's own skills | everything else | Homunculus | Homunculus | Homunculus |

Rule of thumb: when a harness has an official plugin that ships the full
upstream set, use the plugin and skip the alias there; otherwise install the
alias. The installer derives the plugin-covered list from `skill-aliases.yml`
(aliases with `source: cursor/plugins`).

Install locations: Claude Code reads `~/.claude/skills`; Cursor reads the
universal `~/.agents/skills`; Codex gets the full tree mirrored into
`~/.codex/skills`, because the `skills` CLI treats Cursor and Codex as
universal agents sharing `~/.agents/skills`, which must stay pstack-free for
Cursor.

Safe to rerun: it reinstalls the same set each time. If `claude` is not on
`PATH`, or Claude Code is not signed in, the skill copy still succeeds and the
plugin step prints a skip note.

### Calling it from mac-set-up

mac-set-up should hand its agent setup to Homunculus instead of shipping its
own `agentic/AGENTS.md`, `CLAUDE.md`, entry, skills, and MCP scripts. In
`agentic/install.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/ben196888/homunculus/main/scripts/install.sh | bash -s -- --yes
```

Add `--ref <tag-or-sha>` to pin a version. Existing `~/.codex/AGENTS.md` and
`~/.claude/CLAUDE.md` files that mac-set-up installed are recognised and
replaced (with a backup); hand-edited ones are merged. Third-party skill
repos that Homunculus does not vendor (such as Caveman) stay in
mac-set-up.

### Testing the installer

```bash
python3 -m unittest tests/test_install.py   # or: pnpm test:install
shellcheck scripts/install.sh
```

The tests run every install under a throwaway `HOME` with stubbed `npx` and
`claude`, so they never touch your real `~/.claude`, `~/.codex`, or
`~/.cursor`. Never run the installer itself against a real HOME to test it;
use `--dry-run` or `HOME=$(mktemp -d)`.

## Skills

- `homunculus-productivity-visual-plan` - diagrams-first plans (plan.md and visual-plan.md, plus visual-plan.html and a Canvas when the environment supports them) via a visualisation guideline and templates (task, implementation-plan, rfc, tech-comparison, ab-test-report).
- `homunculus-productivity-create-printable-html` - self-contained, multilingual HTML documents optimized for printing.
- `homunculus-programming-codebase-search` - fast repository exploration using `rg`.
- `homunculus-programming-autosquash` - safely fold marked fixup and squash commits and update the remote branch.
- `homunculus-programming-wt-add` - create git worktrees for isolated tasks.
- `homunculus-programming-wt-drop` - remove completed worktrees and branches.
- `homunculus-programming-wt-find` - recover worktrees from partial context.
- `homunculus-productivity-development-workflow` - plan, clarify, document, implement, verify.
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
`homunculus-programming-tdd`. Vendored for Codex (and as the alias source of
truth); Claude Code and Cursor load these via the pstack plugin instead of
the Homunculus copies. Cursor-only subagent workflows (`poteto-mode`, `how`,
`why`, `swarm`, `arena`, …) are not vendored; `./scripts/install.sh` installs
the full pstack Claude Code plugin for those.

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

## Contributing

Homunculus ships no repo-local `AGENTS.md` or `CLAUDE.md`; the files under
`agentic/` are the *global* instructions installed on agent machines. Rules
for working on this repo:

- Commits use Conventional Commits, `<type>(<scope>): <subject>`, with types
  `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`, `perf`
  (scopes in use include `productivity`, `programming`, `setup`).
- Skill ids are `homunculus-<subpath-with-dashes>` and must match their
  directory under `skills/` (checked by `pnpm validate`).
- `visual-plan` template ids are the file names in
  `skills/productivity/visual-plan/templates/` (`task`,
  `implementation-plan`, `rfc`, `tech-comparison`, `ab-test-report`); add
  a file there to add a template id.
- Change global agent instructions only in `agentic/AGENTS.md`; never hand-edit
  generated copies.
- Run `pnpm validate`, `pnpm test`, and the `tests/` suites before opening a PR.
