---
name: homunculus-productivity-change-detection
description: Check whether a software task changed the repository and has adequate completion evidence. Use whenever you are about to finish, hand off, summarize, or declare an engineering task complete after edits, commits, generated files, or tests.
---

# Change Detection

Run this skill near the end of every engineering task. It is the portable,
explicit counterpart to a lifecycle Stop hook: it detects Git working-tree or
HEAD changes and verifies that the shared task ledger contains a completion
summary, verification status, and blocker status.

```bash
python3 <change-detection-skill>/scripts/change_detection.py
```

Exit status `0` means no relevant mutation was found or completion evidence is
complete. Exit status `2` means the task changed the repository but needs a
ledger record before it can be presented as complete.

If the Task Ledger skill was installed outside the standard sibling skill
location, set `HOMUNCULUS_TASK_LEDGER_SCRIPT` to its `scripts/ledger.py` path.

Do not claim lifecycle enforcement: this is a skill invocation, not an
automatically registered Codex or Claude hook.
