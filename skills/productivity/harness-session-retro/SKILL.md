---
name: homunculus-productivity-harness-session-retro
description: Retrospect recent local Codex session history and produce evidence-backed recommendations to create, improve, merge, keep, or retire skills and other agent-harness components. Use whenever the user asks to analyze past sessions, repeated prompts, skill usage, unused skills, harness effectiveness, or opportunities for new skills, agents, hooks, gates, or automations.
---

# Harness Session Retro

Turn recent Codex session history into a maintenance report for the current
skill repository. Keep collection deterministic and local; use model judgment
only after the evidence has been counted.

The workflow reconstructs the retrospective originally prompted with:

> Analyse my last 400 sessions. List down anything I prompt / did again and
> again that worth to extract to be a skill or an agent.

Read `references/initial-idea.md` when the origin of the workflow or the first
400-session retrospective provides useful context.

## Collect evidence

Identify the repository whose `skills/` directory should be assessed. If the
user does not name one, use the current repository. Create a temporary working
directory and run:

```bash
python3 <this-skill>/scripts/session_retro.py \
  --repo <skill-repository> \
  --limit 400 \
  --report <temporary-directory>/evidence.md \
  --json <temporary-directory>/evidence.json
```

The script reads the Codex home directory from `$CODEX_HOME` or `~/.codex`.
Use `--codex-dir` when history lives elsewhere. It automatically excludes the
active task using `$CODEX_SESSION_ID` and `$CODEX_THREAD_ID`.

Treat incomplete coverage as a limitation, not as zero activity. Never copy
raw prompts, transcripts, credentials, or tool output into the final report.
The collector deliberately persists aggregate counts and session titles only.
Modern Codex-injected `<skill>` messages are measured as harness injections and
are excluded from human-prompt analysis.

## Interpret the evidence

Use the following extraction rule:

| Repeated behaviour | Harness primitive |
| --- | --- |
| Bounded procedure with a clear input and output | Skill |
| Multi-step ownership requiring durable state or follow-up | Agent |
| Pass/fail checkpoint tied to an event | Hook or gate |
| Scheduled or event-driven repeat | Automation |
| Shared facts or output shape without a procedure | Reference or template |

Before recommending an action, inspect the relevant current `SKILL.md` files
and their cross-references. For ambiguous high-impact candidates, inspect a few
representative sessions named in the evidence. Do not reread all transcripts.

Distinguish these decisions:

- **Create** when repeated work has no current owner.
- **Improve** when a current skill is used but produces follow-up correction signals,
  leaves repeated manual steps, or lacks representative evaluation fixtures.
- **Merge** when multiple skills split one user intent without a useful
  boundary. Preserve a thin router only when it materially improves discovery.
- **Retire** only after proving the skill had a fair observation window, no
  prompt mention or instruction load, no current dependants, and no important
  low-frequency safety role.
- **Keep** when the skill has a clear boundary and the evidence does not justify
  change.

Absence is not proof of disuse: implicit triggering is only partly visible,
new skills may not have had enough exposure, and rare incident or safety skills
can still be valuable. Phrase script-generated retirement rows as candidates
for review until these checks are complete.

## Write the report

Write to the user-requested path. If none is provided, use
`SESSION_RETRO.md` in the assessed repository. Use this structure:

```markdown
# Harness session retrospective
## Executive summary
## Scope and confidence
## Create
## Improve
## Merge or retire
## Keep
## Prioritized next actions
## Evaluation plan
```

For every create, improve, merge, or retire recommendation include:

- the observed session count and representative task titles;
- the repeated user need or failure mode;
- the current skill overlap and dependency check;
- the proposed primitive and smallest responsible change;
- a measurable validation plan covering correctness, noise, token cost, and
  runtime where applicable.

Rank recommendations by frequency, iteration cost, risk reduction, and how
many other workflows they unlock. State when counts overlap.

## Boundaries

- This is a read-only retrospective unless the user separately authorizes
  skill edits, deletion, issue creation, or other external writes.
- Do not auto-delete skills from an aggregate report.
- Do not claim that prompt mentions equal all usage; harness injections,
  instruction loads, and implicit triggers are separate signals.
- Do not publish session evidence outside the local workspace without explicit
  authorization.
