#!/usr/bin/env python3
"""Evaluate task completion evidence after a repository mutation."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

def load_ledger() -> Any:
    explicit = os.environ.get("HOMUNCULUS_TASK_LEDGER_SCRIPT")
    here = Path(__file__).resolve()
    candidates = [
        Path(explicit) if explicit else None,
        here.parents[2] / "task-ledger" / "scripts" / "ledger.py",
        here.parents[2] / "homunculus-productivity-task-ledger" / "scripts" / "ledger.py",
        here.parents[3] / "productivity" / "task-ledger" / "scripts" / "ledger.py",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            spec = importlib.util.spec_from_file_location("homunculus_task_ledger", candidate)
            module = importlib.util.module_from_spec(spec)
            assert spec and spec.loader
            spec.loader.exec_module(module)
            return module
    raise RuntimeError("Task Ledger skill is not installed. Install homunculus-productivity-task-ledger or set HOMUNCULUS_TASK_LEDGER_SCRIPT.")


def evaluate(cwd: str) -> tuple[str, str]:
    ledger = load_ledger()
    context = ledger.git_context(cwd)
    if not context:
        return "not-a-repository", "No Git repository found; no completion check was needed."
    state, path = ledger.load(context)
    ledger.refresh_change(state, context)
    ledger.save(state, path)
    if not state["change"]["mutated"]:
        return "no-relevant-mutation", "No relevant repository mutation was detected."
    missing = ledger.completion_missing(state)
    if missing:
        return "incomplete", "Record " + ", ".join(missing) + " before reporting this changed task complete."
    return "complete", "Completion evidence is recorded for the detected repository change."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", default=os.getcwd())
    args = parser.parse_args()
    status, message = evaluate(args.cwd)
    print(f"Change detection: {status}. {message}")
    if status == "incomplete":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
