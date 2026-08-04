#!/usr/bin/env python3
"""Read-only GitLab MR inspection for the Homunculus MR Steward."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any



def load_ledger() -> Any:
    explicit = os.environ.get("HOMUNCULUS_TASK_LEDGER_SCRIPT")
    here = Path(__file__).resolve()
    candidates = [
        Path(explicit) if explicit else None,
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


ledger = load_ledger()


def run_glab(args: list[str], cwd: Path) -> Any:
    result = subprocess.run(["glab", *args], cwd=cwd, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def iid_from(value: str) -> str:
    match = re.search(r"(?:merge_requests/|!)(\d+)$", value)
    if not match:
        raise ValueError("MR must be an IID, !IID, or GitLab merge-request URL")
    return match.group(1)


def current_iid(cwd: Path, branch: str) -> str | None:
    items = run_glab(["mr", "list", "--state", "opened", "--source-branch", branch, "-F", "json"], cwd)
    if len(items) == 1:
        return str(items[0]["iid"])
    if len(items) > 1:
        raise ValueError(f"multiple open merge requests found for branch {branch}; specify one")
    return None


def unresolved_discussions(cwd: Path, iid: str) -> int | None:
    try:
        discussions = run_glab(["api", f"projects/:id/merge_requests/{iid}/discussions?per_page=100", "--paginate"], cwd)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return None
    return sum(1 for discussion in discussions if any(note.get("resolvable") and not note.get("resolved") for note in discussion.get("notes", [])))


def status_of(mr: dict[str, Any], threads: int | None) -> tuple[str, list[str]]:
    pipeline = mr.get("pipeline") or {}
    pipeline_status = pipeline.get("status") or mr.get("head_pipeline", {}).get("status")
    merge_status = mr.get("detailed_merge_status") or mr.get("merge_status")
    actions: list[str] = []
    if not pipeline_status:
        actions.append("Check GitLab pipeline status; it was unavailable to the steward.")
    elif pipeline_status != "success":
        actions.append(f"Inspect and resolve the {pipeline_status} pipeline before merge.")
    if merge_status in {"cannot_be_merged", "conflict", "checking"}:
        actions.append("Resolve merge conflicts or wait for GitLab mergeability to finish checking.")
    if threads:
        actions.append(f"Adjudicate {threads} unresolved review thread(s) with programming-resolve-review-thread.")
    if not actions:
        actions.append("MR is read-only assessed as ready for the separate merge-readiness workflow.")
        return "ready-for-review", actions
    return "needs-follow-up", actions


def inspect(cwd: Path, mr_ref: str | None) -> dict[str, Any]:
    context = ledger.git_context(cwd)
    if not context:
        raise ValueError("MR Steward must run inside a Git repository")
    iid = iid_from(mr_ref) if mr_ref else current_iid(cwd, context["branch"])
    if not iid:
        return {"status": "no-open-mr", "branch": context["branch"], "actions": ["Create or specify an open GitLab MR before running stewardship."]}
    mr = run_glab(["mr", "view", iid, "-F", "json"], cwd)
    threads = unresolved_discussions(cwd, iid)
    status, actions = status_of(mr, threads)
    pipeline = (mr.get("pipeline") or mr.get("head_pipeline") or {}).get("status")
    url = mr.get("web_url") or mr.get("webUrl")
    state, path = ledger.load(context)
    ledger.refresh_change(state, context)
    ledger.update_mr(state, {"url": url, "iid": iid, "pipeline": pipeline, "unresolved_threads": threads, "status": status})
    ledger.save(state, path)
    return {"status": status, "iid": iid, "url": url, "title": mr.get("title"), "branch": context["branch"], "pipeline": pipeline, "merge_status": mr.get("detailed_merge_status") or mr.get("merge_status"), "unresolved_threads": threads, "actions": actions, "ledger": str(path)}


def render(report: dict[str, Any]) -> str:
    lines = [f"## MR Steward — {report['status']}"]
    if report.get("title"):
        lines.append(f"{report['title']} ({report.get('url') or 'URL unavailable'})")
    else:
        lines.append(f"Branch: {report.get('branch')}")
    if report.get("pipeline"):
        lines.append(f"Pipeline: {report['pipeline']}")
    if report.get("unresolved_threads") is not None:
        lines.append(f"Unresolved threads: {report['unresolved_threads']}")
    lines.append("\nNext actions:")
    lines.extend(f"- {action}" for action in report["actions"])
    lines.append("\nThis steward only inspected state; it did not push, comment, approve, merge, close, or otherwise change GitLab.")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mr", nargs="?")
    parser.add_argument("--cwd", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = inspect(Path(args.cwd).resolve(), args.mr)
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as error:
        raise SystemExit(f"MR Steward could not inspect the merge request: {error}")
    print(json.dumps(report, indent=2) if args.json else render(report))


if __name__ == "__main__":
    main()
