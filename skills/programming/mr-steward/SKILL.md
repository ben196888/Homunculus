---
name: homunculus-programming-mr-steward
description: Inspect the current or specified GitLab merge request, record its read-only state in the shared task ledger, and return prioritized follow-up actions. Use for "steward this MR", "check MR readiness", "watch this merge request", or repeated CI and review follow-up. Never push, comment, approve, merge, close, or modify GitLab.
argument-hint: "[GitLab MR URL or !IID]"
---

# MR Steward

Run the bundled script from the repository that owns the merge request:

```bash
python3 <mr-steward-skill>/scripts/mr_steward.py "$ARGUMENTS"
```

If no argument is supplied, it finds the single open MR for the current branch.
It records MR, pipeline, and unresolved-thread state in the shared ledger, then
returns the highest-priority next action.

## Boundaries

- Read-only GitLab inspection only. Do not push, comment, approve, merge, close,
  or edit a merge request.
- Do not treat this as merge authorization; use the future merge-readiness
  workflow once it exists.
- When review threads need work, use `programming-resolve-review-thread`.
- When CI needs diagnosis, use `dev-mr-assist` or `dev-mr-babysit`.
- Record any implementation completion before ending a changed task:

```bash
python3 <task-ledger-skill>/scripts/ledger.py record-completion \
  --summary "<outcome>" --verification "<passed checks or rationale>" --blockers "none"
```
