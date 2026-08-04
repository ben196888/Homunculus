#!/usr/bin/env python3
"""Versioned, local-only task state for Homunculus engineering skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def command(args: list[str], cwd: Path) -> str | None:
    try:
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip()


def git_context(cwd: str | Path) -> dict[str, Any] | None:
    path = Path(cwd).resolve()
    root = command(["git", "rev-parse", "--show-toplevel"], path)
    if not root:
        return None
    root_path = Path(root).resolve()
    branch = command(["git", "branch", "--show-current"], root_path) or "detached"
    head = command(["git", "rev-parse", "HEAD"], root_path) or "unborn"
    remote = command(["git", "config", "--get", "remote.origin.url"], root_path) or ""
    status = command(["git", "status", "--porcelain"], root_path) or ""
    files = sorted({line[3:] for line in status.splitlines() if len(line) > 3})
    return {"root": str(root_path), "branch": branch, "head": head, "remote": sanitize_remote(remote), "files": files}


def sanitize_remote(value: str) -> str:
    if "@" not in value or "://" not in value:
        return value
    scheme, rest = value.split("://", 1)
    return f"{scheme}://{rest.split('@', 1)[1]}"


def ledger_root() -> Path:
    return Path(os.environ.get("HOMUNCULUS_LEDGER_DIR", "~/.homunculus/task-ledger")).expanduser()


def key_for(context: dict[str, Any]) -> str:
    material = "\0".join((context["root"], context["remote"], context["branch"]))
    return hashlib.sha256(material.encode()).hexdigest()


def state_path(context: dict[str, Any]) -> Path:
    return ledger_root() / f"v{SCHEMA_VERSION}" / "tasks" / f"{key_for(context)}.json"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_name = handle.name
    os.replace(temp_name, path)


def new_state(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": now(),
        "updated_at": now(),
        "repository": {"root": context["root"], "remote": context["remote"], "branch": context["branch"], "base": None},
        "sessions": [],
        "task": {"reference": None, "plan_summary": None},
        "change": {"baseline_head": context["head"], "last_head": context["head"], "files": context["files"], "fingerprint": None, "generation": 0, "mutated": False},
        "completion": {"summary": None, "verification": None, "blockers": None},
        "merge_request": {"url": None, "iid": None, "pipeline": None, "unresolved_threads": None, "status": None},
    }


def load(context: dict[str, Any], create: bool = True) -> tuple[dict[str, Any], Path]:
    path = state_path(context)
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state = new_state(context)
    elif create:
        state = new_state(context)
    else:
        raise FileNotFoundError(path)
    if state.get("schema_version") != SCHEMA_VERSION:
        state = migrate(state, context)
    return state, path


def migrate(state: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if state.get("schema_version") in (None, 0):
        migrated = new_state(context)
        migrated["task"].update(state.get("task", {}))
        return migrated
    raise ValueError(f"unsupported ledger schema: {state.get('schema_version')}")


def save(state: dict[str, Any], path: Path) -> None:
    state["updated_at"] = now()
    write_json(path, state)


def record_session(state: dict[str, Any], session_id: str | None) -> None:
    if session_id and session_id not in state["sessions"]:
        state["sessions"].append(session_id)
        state["sessions"] = state["sessions"][-20:]


def refresh_change(state: dict[str, Any], context: dict[str, Any]) -> bool:
    change = state["change"]
    fingerprint = hashlib.sha256((context["head"] + "\0" + "\0".join(context["files"])).encode()).hexdigest()
    changed = bool(context["files"]) or context["head"] != change["baseline_head"]
    if changed and fingerprint != change["fingerprint"]:
        change.update({"last_head": context["head"], "files": context["files"], "fingerprint": fingerprint, "generation": change["generation"] + 1, "mutated": True})
        state["completion"] = {"summary": None, "verification": None, "blockers": None}
        return True
    change["last_head"] = context["head"]
    change["files"] = context["files"]
    return changed


def completion_missing(state: dict[str, Any]) -> list[str]:
    completion = state["completion"]
    fields = (("summary", "a concise change outcome"), ("verification", "verification status or a reason it was not run"), ("blockers", "blocker status (use 'none' when clear)"))
    return [label for key, label in fields if not completion.get(key)]


def concise_summary(state: dict[str, Any]) -> str:
    task = state["task"]
    change = state["change"]
    mr = state["merge_request"]
    parts = [f"Homunculus ledger: branch {state['repository']['branch']}."]
    if task.get("reference"):
        parts.append(f"Task: {task['reference']}.")
    if change.get("mutated"):
        files = ", ".join(change["files"][:8]) or "committed changes"
        parts.append(f"Changed: {files}.")
    if mr.get("url"):
        parts.append(f"MR: {mr['url']} ({mr.get('status') or 'status unknown'}).")
    if state["completion"].get("summary"):
        parts.append(f"Completion: {state['completion']['summary']}")
    return " ".join(parts)


def update_completion(state: dict[str, Any], summary: str | None, verification: str | None, blockers: str | None) -> None:
    for key, value in (("summary", summary), ("verification", verification), ("blockers", blockers)):
        if value is not None:
            state["completion"][key] = value


def update_mr(state: dict[str, Any], values: dict[str, Any]) -> None:
    state["merge_request"].update({key: value for key, value in values.items() if value is not None})


def context_or_exit(cwd: str | None) -> dict[str, Any]:
    context = git_context(cwd or os.getcwd())
    if not context:
        raise SystemExit("No Git repository found; ledger was not updated.")
    return context


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("init", "show", "record-completion", "record-mr", "evaluate"))
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--session-id")
    parser.add_argument("--reference")
    parser.add_argument("--plan-summary")
    parser.add_argument("--summary")
    parser.add_argument("--verification")
    parser.add_argument("--blockers")
    parser.add_argument("--url")
    parser.add_argument("--iid")
    parser.add_argument("--pipeline")
    parser.add_argument("--threads", type=int)
    parser.add_argument("--status")
    args = parser.parse_args()
    context = context_or_exit(args.cwd)
    state, path = load(context)
    record_session(state, args.session_id)
    refresh_change(state, context)
    if args.reference is not None:
        state["task"]["reference"] = args.reference
    if args.plan_summary is not None:
        state["task"]["plan_summary"] = args.plan_summary
    if args.command == "record-completion":
        update_completion(state, args.summary, args.verification, args.blockers)
    if args.command == "record-mr":
        update_mr(state, {"url": args.url, "iid": args.iid, "pipeline": args.pipeline, "unresolved_threads": args.threads, "status": args.status})
    save(state, path)
    if args.command == "evaluate":
        print(json.dumps({"mutated": state["change"]["mutated"], "missing": completion_missing(state), "path": str(path)}))
    else:
        print(json.dumps({"path": str(path), "summary": concise_summary(state)}))


if __name__ == "__main__":
    main()
