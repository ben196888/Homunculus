# Initial idea

## Starting question

The idea began with a retrospective on 31 July 2026:

> Analyse my last 400 sessions. List down anything I prompt / did again and
> again that worth to extract to be a skill or an agent.

The goal quickly expanded beyond creating more skills. Repeated work should be
assigned to the harness component that best fits it: a bounded skill, a
stateful agent, a hook or gate, an automation, or shared task state.

## First retrospective

The first run used two temporary scripts. The collection step:

1. Read the local Codex session index.
2. Deduplicated sessions and selected the 400 most recent completed records.
3. Located their active or archived JSONL files.
4. Extracted prompts, session metadata, final answers, and tool activity.
5. Used Codex spawn-edge state to identify delegated child sessions.

The analysis step separated stop-gate runs, delegated children, automations,
and primary user-led sessions. It then counted overlapping workflow signals
such as merge-request review and follow-up, planning and implementation,
investigation, testing, skill engineering, experiments, worktrees, Slack
triage, and Jira grooming.

The result became GitLab work item 4. Its initial 400-session snapshot contained
192 Claude stop-gate runs, 73 delegated children, 4 automations, and 131 primary
sessions. Those findings were used to prioritize reusable workflow components.

## From experiment to reusable skill

The useful pattern was to keep evidence collection deterministic, then apply
agent judgment when deciding what to create, improve, merge, keep, or retire.
`scripts/session_retro.py` turns that pattern into a repeatable workflow:

- The Codex directory, repository, session limit, and output paths are
  configurable.
- The active session is excluded automatically.
- Both known Codex state-database locations are read without modification.
- Human skill mentions, harness injections, instruction loads, dependants,
  exposure windows, and follow-up corrections remain distinct signals.
- Injected skill bodies are excluded from human-prompt statistics.
- Raw prompts and transcripts are analyzed locally in memory and are not
  persisted in the report.
- A skill with no observed use is only flagged for retirement review after a
  meaningful exposure window; the report never authorizes automatic deletion.
