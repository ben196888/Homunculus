---
name: homunculus-productivity-task-ledger
description: Maintain concise, local task state across engineering work. Use at the start of a task, when resuming work, when recording verification or blockers, or whenever a task needs durable ticket, branch, plan, test, or MR context. Store only metadata; never store transcripts, credentials, or command output.
---

# Task Ledger

Use this skill to keep work resumable without committing task state into the
repository. Its bundled `scripts/ledger.py` stores versioned JSON under
`$HOMUNCULUS_LEDGER_DIR`, defaulting to `~/.homunculus/task-ledger`, partitioned
by repository and branch.

## Start or resume

From the target repository, run the bundled script with the path to this skill:

```bash
python3 <task-ledger-skill>/scripts/ledger.py init \
  --reference "<ticket or MR>" --plan-summary "<concise plan>"
python3 <task-ledger-skill>/scripts/ledger.py show
```

Initialize before mutating work so committed changes are detected as well as
working-tree changes.

## Record completion evidence

Before calling a changed task complete, record all three fields:

```bash
python3 <task-ledger-skill>/scripts/ledger.py record-completion \
  --summary "<what changed>" \
  --verification "<checks run or why none were run>" \
  --blockers "none"
```

Use `record-mr` after a read-only MR inspection to persist its URL, pipeline,
unresolved-thread count, and current status.

## Boundaries

- Keep summaries concise and factual.
- Do not store secrets, raw command output, or transcripts.
- The ledger is local state, not a substitute for the source ticket, MR, or CI.
