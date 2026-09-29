#!/usr/bin/env python3
"""Safely autosquash marked commits and update their remote branch."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROTECTED_BRANCHES = {"main", "master", "develop"}
CONVENTIONAL_SUBJECT = re.compile(
    r"^(feat|fix|docs|refactor|test|chore|style|perf)(\([^)\r\n]+\))?!?: .+"
)
MARKER = re.compile(r"^(fixup|squash)! (.+)$")


class AutosquashError(RuntimeError):
    """A safe, user-actionable autosquash failure."""


def run(
    args: list[str],
    cwd: Path,
    *,
    check: bool = True,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        env=env,
        input=input_text,
    )
    if check and result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise AutosquashError(f"{' '.join(args)} failed: {detail}")
    return result


def git(cwd: Path, *args: str, check: bool = True) -> str:
    return run(["git", *args], cwd, check=check).stdout.strip()


def git_path(cwd: Path, name: str) -> Path:
    value = git(cwd, "rev-parse", "--git-path", name)
    path = Path(value)
    if path.is_absolute():
        return path
    root = Path(git(cwd, "rev-parse", "--show-toplevel"))
    return root / path


def ref_exists(cwd: Path, ref: str) -> bool:
    return run(["git", "rev-parse", "--verify", "--quiet", ref], cwd, check=False).returncode == 0


def resolve(cwd: Path, ref: str) -> str:
    return git(cwd, "rev-parse", "--verify", f"{ref}^{{commit}}")


def current_branch(cwd: Path) -> str:
    branch = git(cwd, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if not branch:
        raise AutosquashError("detached HEAD is not eligible for autosquash")
    if branch in PROTECTED_BRANCHES:
        raise AutosquashError(f"refusing to rewrite protected branch {branch!r}")
    return branch


def choose_remote(cwd: Path, explicit: str | None, branch: str) -> str:
    remotes = [line for line in git(cwd, "remote").splitlines() if line]
    if explicit:
        if explicit not in remotes:
            raise AutosquashError(f"remote {explicit!r} does not exist")
        return explicit
    upstream = git(
        cwd,
        "config",
        "--get",
        f"branch.{branch}.remote",
        check=False,
    )
    if upstream and upstream != ".":
        return upstream
    if "origin" in remotes:
        return "origin"
    if len(remotes) == 1:
        return remotes[0]
    raise AutosquashError("cannot infer a remote; pass --remote")


def forge_base(cwd: Path, remote: str) -> str | None:
    if shutil.which("glab"):
        result = run(["glab", "mr", "view", "--output", "json"], cwd, check=False)
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                name = data.get("target_branch") or data.get("targetBranch")
                if name and ref_exists(cwd, f"refs/remotes/{remote}/{name}"):
                    return f"refs/remotes/{remote}/{name}"
            except json.JSONDecodeError:
                pass
    if shutil.which("gh"):
        result = run(["gh", "pr", "view", "--json", "baseRefName"], cwd, check=False)
        if result.returncode == 0:
            try:
                name = json.loads(result.stdout).get("baseRefName")
                if name and ref_exists(cwd, f"refs/remotes/{remote}/{name}"):
                    return f"refs/remotes/{remote}/{name}"
            except json.JSONDecodeError:
                pass
    return None


def default_base(cwd: Path, remote: str) -> str | None:
    symbolic = git(
        cwd,
        "symbolic-ref",
        "--quiet",
        "--short",
        f"refs/remotes/{remote}/HEAD",
        check=False,
    )
    if symbolic:
        return f"refs/remotes/{symbolic}"
    for name in ("main", "master", "develop"):
        remote_ref = f"refs/remotes/{remote}/{name}"
        if ref_exists(cwd, remote_ref):
            return remote_ref
    return None


def choose_base(cwd: Path, explicit: str | None, remote: str) -> str:
    if explicit:
        resolve(cwd, explicit)
        return explicit
    forge = forge_base(cwd, remote)
    default = default_base(cwd, remote)
    if forge and default and resolve(cwd, forge) != resolve(cwd, default):
        raise AutosquashError(
            f"base signals disagree ({forge} from the PR/MR, {default} from remote HEAD); pass --base"
        )
    chosen = forge or default
    if not chosen:
        raise AutosquashError("cannot infer the base branch; pass --base")
    return chosen


def fetch(cwd: Path, remote: str) -> None:
    run(["git", "fetch", "--prune", remote], cwd)


def upstream_branch(cwd: Path, branch: str, remote: str) -> tuple[str, bool]:
    merge_ref = git(cwd, "config", "--get", f"branch.{branch}.merge", check=False)
    configured_remote = git(cwd, "config", "--get", f"branch.{branch}.remote", check=False)
    if merge_ref.startswith("refs/heads/") and configured_remote == remote:
        return merge_ref.removeprefix("refs/heads/"), True
    return branch, ref_exists(cwd, f"refs/remotes/{remote}/{branch}")


@dataclass
class Commit:
    sha: str
    subject: str


def commits(cwd: Path, base_sha: str, tip: str = "HEAD") -> list[Commit]:
    output = git(cwd, "log", "--reverse", "--format=%H%x00%s", f"{base_sha}..{tip}")
    result: list[Commit] = []
    for line in output.splitlines():
        if not line:
            continue
        sha, subject = line.split("\0", 1)
        result.append(Commit(sha, subject))
    return result


def resolve_marker_target(history: list[Commit], marker_index: int, target: str) -> Commit:
    earlier = history[:marker_index]
    exact = [item for item in earlier if item.subject == target]
    if len(exact) == 1:
        return exact[0]
    prefix = [item for item in earlier if item.subject.startswith(target) or item.sha.startswith(target)]
    if len(prefix) == 1:
        return prefix[0]
    if not prefix:
        raise AutosquashError(f"autosquash target {target!r} is outside the eligible range or missing")
    raise AutosquashError(f"autosquash target {target!r} is ambiguous in the eligible range")


def marker_plan(history: list[Commit]) -> list[dict[str, str]]:
    planned: list[dict[str, str]] = []
    for index, item in enumerate(history):
        match = MARKER.match(item.subject)
        if not match:
            continue
        target = resolve_marker_target(history, index, match.group(2))
        if MARKER.match(target.subject):
            raise AutosquashError(f"marked commit {item.sha[:12]} targets another marked commit")
        planned.append(
            {
                "sha": item.sha,
                "kind": match.group(1),
                "subject": item.subject,
                "target_sha": target.sha,
                "target_subject": target.subject,
            }
        )
    return planned


def has_merge(cwd: Path, base_sha: str, tip: str) -> bool:
    return bool(git(cwd, "rev-list", "--merges", f"{base_sha}..{tip}"))


def is_ancestor(cwd: Path, older: str, newer: str) -> bool:
    return run(["git", "merge-base", "--is-ancestor", older, newer], cwd, check=False).returncode == 0


def untracked_hashes(cwd: Path) -> dict[str, str]:
    output = run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd
    ).stdout
    result: dict[str, str] = {}
    for name in filter(None, output.split("\0")):
        path = cwd / name
        if path.is_file():
            result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        elif path.is_symlink():
            result[name] = hashlib.sha256(os.readlink(path).encode()).hexdigest()
    return result


def workspace_fingerprint(cwd: Path) -> dict[str, Any]:
    return {
        "status": run(["git", "status", "--porcelain=v1", "-z"], cwd).stdout,
        "index_diff": run(["git", "diff", "--cached", "--binary", "--no-ext-diff"], cwd).stdout,
        "worktree_diff": run(["git", "diff", "--binary", "--no-ext-diff"], cwd).stdout,
        "untracked": untracked_hashes(cwd),
    }


def stash_workspace(cwd: Path, fingerprint: dict[str, Any]) -> str | None:
    if not fingerprint["status"]:
        return None
    before = git(cwd, "rev-parse", "--verify", "--quiet", "refs/stash", check=False)
    message = f"homunculus-autosquash-{os.getpid()}"
    run(["git", "stash", "push", "--include-untracked", "-m", message], cwd)
    after = git(cwd, "rev-parse", "--verify", "refs/stash")
    if after == before:
        raise AutosquashError("dirty workspace was not captured in a stash")
    return after


def drop_stash(cwd: Path, stash_oid: str) -> None:
    listing = git(cwd, "stash", "list", "--format=%gd%x00%H")
    for line in listing.splitlines():
        name, oid = line.split("\0", 1)
        if oid == stash_oid:
            run(["git", "stash", "drop", name], cwd)
            return


def restore_workspace(cwd: Path, state: dict[str, Any], *, drop: bool = True) -> None:
    stash_oid = state.get("stash_oid")
    if not stash_oid:
        return
    result = run(["git", "stash", "apply", "--index", stash_oid], cwd, check=False)
    if result.returncode:
        raise AutosquashError(
            "could not restore the saved workspace; no push occurred and the stash was retained "
            f"at {stash_oid[:12]}: {result.stderr.strip() or result.stdout.strip()}"
        )
    if workspace_fingerprint(cwd) != state["workspace"]:
        raise AutosquashError(
            "restored workspace differs from its pre-run fingerprint; no push occurred and "
            f"the stash was retained at {stash_oid[:12]}"
        )
    if drop:
        drop_stash(cwd, stash_oid)


def remove_saved_untracked(cwd: Path, state: dict[str, Any]) -> None:
    for name in state.get("workspace", {}).get("untracked", {}):
        path = cwd / name
        if path.is_file() or path.is_symlink():
            path.unlink()


def validate_message(message: str) -> None:
    subject = message.splitlines()[0] if message.splitlines() else ""
    if len(subject) >= 72:
        raise AutosquashError(f"synthesized subject must be under 72 characters: {subject!r}")
    if not CONVENTIONAL_SUBJECT.fullmatch(subject):
        raise AutosquashError(f"synthesized message is not Conventional Commits format: {subject!r}")


def parse_messages(values: list[str], plan: list[dict[str, str]]) -> dict[str, str]:
    by_target = {item["target_sha"]: item for item in plan if item["kind"] == "squash"}
    parsed: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise AutosquashError("--squash-message must be TARGET_SHA=MESSAGE")
        target, message = value.split("=", 1)
        matches = [sha for sha in by_target if sha.startswith(target)]
        if len(matches) != 1:
            raise AutosquashError(f"squash message target {target!r} is missing or ambiguous")
        validate_message(message)
        parsed[matches[0]] = message
    missing = sorted(set(by_target) - set(parsed))
    if missing:
        short = ", ".join(sha[:12] for sha in missing)
        raise AutosquashError(f"squash targets require synthesized messages: {short}")
    return parsed


def message_editor(cwd: Path, messages: dict[str, str]) -> tuple[tempfile.TemporaryDirectory[str], dict[str, str]]:
    temp = tempfile.TemporaryDirectory(prefix="homunculus-autosquash-")
    root = Path(temp.name)
    subjects: dict[str, str] = {}
    for sha, message in messages.items():
        subject = git(cwd, "show", "-s", "--format=%s", sha)
        if subject in subjects:
            raise AutosquashError(f"duplicate squash target subject cannot be edited safely: {subject!r}")
        subjects[subject] = message
    plan_path = root / "messages.json"
    plan_path.write_text(json.dumps(subjects), encoding="utf-8")
    editor = root / "editor.py"
    editor.write_text(
        """#!/usr/bin/env python3
import json, os, pathlib, sys
path = pathlib.Path(sys.argv[1])
lines = path.read_text().splitlines()
subject = next((line for line in lines if line.strip() and not line.startswith('#')), None)
messages = json.loads(pathlib.Path(os.environ['HOMUNCULUS_MESSAGE_PLAN']).read_text())
if subject not in messages:
    raise SystemExit(f'No synthesized message for squash target: {subject!r}')
path.write_text(messages[subject].rstrip() + '\\n')
""",
        encoding="utf-8",
    )
    editor.chmod(0o755)
    env = os.environ.copy()
    # Git invokes both variables as shell commands. Supplying them explicitly keeps
    # the workflow headless even when the user's core.editor launches a GUI.
    env["GIT_SEQUENCE_EDITOR"] = "true"
    env["GIT_EDITOR"] = shlex.quote(str(editor))
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["HOMUNCULUS_MESSAGE_PLAN"] = str(plan_path)
    return temp, env


def state_path(cwd: Path) -> Path:
    return git_path(cwd, "homunculus-autosquash.json")


def save_state(cwd: Path, state: dict[str, Any]) -> None:
    path = state_path(cwd)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def load_state(cwd: Path) -> dict[str, Any]:
    path = state_path(cwd)
    if not path.is_file():
        raise AutosquashError("no interrupted Homunculus autosquash operation was found")
    return json.loads(path.read_text(encoding="utf-8"))


def clear_state(cwd: Path) -> None:
    state_path(cwd).unlink(missing_ok=True)


def inspect_plan(cwd: Path, base: str | None, remote: str | None, *, do_fetch: bool) -> dict[str, Any]:
    root = Path(git(cwd, "rev-parse", "--show-toplevel"))
    branch = current_branch(root)
    selected_remote = choose_remote(root, remote, branch)
    if do_fetch:
        fetch(root, selected_remote)
    selected_base = choose_base(root, base, selected_remote)
    base_sha = resolve(root, selected_base)
    remote_branch, upstream = upstream_branch(root, branch, selected_remote)
    remote_ref = f"refs/remotes/{selected_remote}/{remote_branch}"
    remote_sha = resolve(root, remote_ref) if ref_exists(root, remote_ref) else None
    tips = ["HEAD"] + ([remote_ref] if remote_sha and remote_sha != resolve(root, "HEAD") else [])
    if any(has_merge(root, base_sha, tip) for tip in tips):
        raise AutosquashError("rewrite range contains merge commits; merge-preserving autosquash is outside v1")
    histories = [commits(root, base_sha, tip) for tip in tips]
    markers: list[dict[str, str]] = []
    seen: set[str] = set()
    for history in histories:
        for item in marker_plan(history):
            if item["sha"] not in seen:
                markers.append(item)
                seen.add(item["sha"])
    divergence = "unpublished"
    if remote_sha:
        head = resolve(root, "HEAD")
        if remote_sha == head:
            divergence = "in-sync"
        elif is_ancestor(root, remote_sha, head):
            divergence = "local-ahead"
        elif is_ancestor(root, head, remote_sha):
            divergence = "remote-ahead"
        else:
            divergence = "diverged"
    return {
        "root": str(root),
        "branch": branch,
        "base": selected_base,
        "base_sha": base_sha,
        "remote": selected_remote,
        "remote_branch": remote_branch,
        "remote_sha": remote_sha,
        "has_upstream": upstream,
        "divergence": divergence,
        "markers": markers,
    }


def render_plan(plan: dict[str, Any]) -> str:
    lines = [
        f"Branch: {plan['branch']}",
        f"Base: {plan['base']} ({plan['base_sha'][:12]})",
        f"Remote: {plan['remote']}/{plan['remote_branch']} ({plan['divergence']})",
        f"Marked commits: {len(plan['markers'])}",
    ]
    for marker in plan["markers"]:
        lines.append(
            f"- {marker['sha'][:12]} {marker['kind']} -> "
            f"{marker['target_sha'][:12]} {marker['target_subject']}"
        )
    if not plan["markers"]:
        lines.append("No fixup! or squash! commits found; apply would not rewrite or push.")
    return "\n".join(lines)


def run_verification(cwd: Path, commands: list[str]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for command in commands:
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            executable="/bin/sh",
            text=True,
            capture_output=True,
        )
        reports.append({"command": command, "returncode": result.returncode})
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip()
            raise AutosquashError(f"verification failed ({command}): {detail}")
    return reports


def rebase_in_progress(cwd: Path) -> bool:
    return git_path(cwd, "rebase-merge").exists() or git_path(cwd, "rebase-apply").exists()


def start_autosquash(cwd: Path, state: dict[str, Any]) -> bool:
    history = commits(cwd, state["base_sha"])
    plan = marker_plan(history)
    if not plan:
        raise AutosquashError("marked commits disappeared after remote reconciliation")
    messages = parse_messages(state["message_args"], plan)
    state["tree_before"] = git(cwd, "rev-parse", "HEAD^{tree}")
    state["phase"] = "autosquash"
    state["markers"] = plan
    save_state(cwd, state)
    temp, env = message_editor(cwd, messages)
    try:
        result = run(
            ["git", "rebase", "-i", "--autosquash", state["base_sha"]],
            cwd,
            check=False,
            env=env,
        )
    finally:
        temp.cleanup()
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return False
    return True


def continue_rebase(cwd: Path, state: dict[str, Any]) -> bool:
    if state["phase"] == "autosquash":
        messages = parse_messages(state["message_args"], state.get("markers", []))
        temp, env = message_editor(cwd, messages)
        try:
            result = run(["git", "rebase", "--continue"], cwd, check=False, env=env)
        finally:
            temp.cleanup()
    else:
        env = os.environ.copy()
        env["GIT_EDITOR"] = "true"
        env["GIT_SEQUENCE_EDITOR"] = "true"
        env["GIT_TERMINAL_PROMPT"] = "0"
        result = run(["git", "rebase", "--continue"], cwd, check=False, env=env)
    if result.returncode:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        return False
    return True


def finalize(cwd: Path, state: dict[str, Any]) -> dict[str, Any]:
    if git(cwd, "rev-parse", "HEAD^{tree}") != state["tree_before"]:
        raise AutosquashError("autosquash changed the committed tree; no push occurred")
    checks = run_verification(cwd, state["verify"])
    restore_workspace(cwd, state, drop=False)
    branch = state["branch"]
    remote = state["remote"]
    remote_branch = state["remote_branch"]
    expected = state.get("remote_sha")
    try:
        push_env = os.environ.copy()
        push_env["GIT_TERMINAL_PROMPT"] = "0"
        if expected:
            lease = f"refs/heads/{remote_branch}:{expected}"
            run(
                [
                    "git",
                    "push",
                    f"--force-with-lease={lease}",
                    remote,
                    f"HEAD:refs/heads/{remote_branch}",
                ],
                cwd,
                env=push_env,
            )
            push = f"force-with-lease {remote}/{remote_branch}"
        else:
            run(
                ["git", "push", "--set-upstream", remote, f"HEAD:refs/heads/{branch}"],
                cwd,
                env=push_env,
            )
            push = f"set upstream {remote}/{branch}"
    except AutosquashError:
        clear_state(cwd)
        retained = state.get("stash_oid")
        suffix = f"; saved workspace also remains in stash {retained[:12]}" if retained else ""
        raise AutosquashError(
            "push was rejected; the rewritten local branch and restored workspace were kept"
            f"{suffix}. Fetch and run a fresh plan before retrying"
        )
    if state.get("stash_oid"):
        drop_stash(cwd, state["stash_oid"])
    report = {
        "status": "complete",
        "branch": branch,
        "base": state["base"],
        "remote": f"{remote}/{remote_branch}",
        "old_sha": state["old_sha"],
        "new_sha": resolve(cwd, "HEAD"),
        "markers": state["markers"],
        "reconciliation": state["divergence"],
        "verification": checks,
        "workspace_restored": True,
        "push": push,
        "recovery": f"git reflog; git reset --hard {state['old_sha']}",
    }
    clear_state(cwd)
    return report


def apply(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path(args.cwd).resolve()
    if state_path(cwd).exists():
        raise AutosquashError("an autosquash transaction already exists; use continue or abort")
    plan = inspect_plan(cwd, args.base, args.remote, do_fetch=True)
    if not plan["markers"]:
        return {**plan, "status": "no-op", "push": "not attempted"}
    root = Path(plan["root"])
    workspace = workspace_fingerprint(root)
    state = {
        **plan,
        "old_sha": resolve(root, "HEAD"),
        "workspace": workspace,
        "stash_oid": None,
        "verify": args.verify,
        "message_args": args.squash_message,
        "phase": "starting",
    }
    state["stash_oid"] = stash_workspace(root, workspace)
    save_state(root, state)
    remote_ref = f"refs/remotes/{plan['remote']}/{plan['remote_branch']}"
    if plan["remote_sha"] and not is_ancestor(root, plan["remote_sha"], "HEAD"):
        state["phase"] = "integrate"
        save_state(root, state)
        result = run(["git", "rebase", remote_ref], root, check=False)
        if result.returncode:
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            raise AutosquashError(
                "remote reconciliation has conflicts; resolve only clear conflicts, stage them, "
                "then run autosquash.py continue (or autosquash.py abort)"
            )
    if not start_autosquash(root, state):
        raise AutosquashError(
            "autosquash has conflicts; resolve only clear conflicts, stage them, then run "
            "autosquash.py continue (or autosquash.py abort)"
        )
    return finalize(root, load_state(root))


def resume(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path(git(Path(args.cwd).resolve(), "rev-parse", "--show-toplevel"))
    state = load_state(cwd)
    if not rebase_in_progress(cwd):
        raise AutosquashError("transaction exists but Git has no rebase to continue; use abort")
    phase = state["phase"]
    if not continue_rebase(cwd, state):
        raise AutosquashError("rebase still has conflicts; resolve them before continuing")
    if phase == "integrate":
        if not start_autosquash(cwd, state):
            raise AutosquashError("autosquash has conflicts; resolve them before continuing")
    return finalize(cwd, load_state(cwd))


def abort(args: argparse.Namespace) -> dict[str, Any]:
    cwd = Path(git(Path(args.cwd).resolve(), "rev-parse", "--show-toplevel"))
    state = load_state(cwd)
    if rebase_in_progress(cwd):
        run(["git", "rebase", "--abort"], cwd)
    remove_saved_untracked(cwd, state)
    if resolve(cwd, "HEAD") != state["old_sha"]:
        run(["git", "reset", "--hard", state["old_sha"]], cwd)
    restore_workspace(cwd, state)
    clear_state(cwd)
    return {"status": "aborted", "restored_sha": state["old_sha"], "workspace_restored": True}


def emit(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2))
        return
    if value.get("status") == "complete":
        print(f"Autosquash complete: {value['old_sha'][:12]} -> {value['new_sha'][:12]}")
        print(f"Base: {value['base']}")
        print(f"Remote: {value['remote']} ({value['push']})")
        print(f"Marked commits folded: {len(value['markers'])}")
        print(f"Remote reconciliation: {value['reconciliation']}")
        print(f"Verification commands passed: {len(value['verification'])}")
        print("Workspace restored: yes")
        print(f"Recovery: {value['recovery']}")
    elif value.get("status") == "no-op":
        print(render_plan(value))
    else:
        print(json.dumps(value, indent=2))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("plan", "apply"):
        command = sub.add_parser(name)
        command.add_argument("--cwd", default=".")
        command.add_argument("--base")
        command.add_argument("--remote")
        command.add_argument("--json", action="store_true")
        if name == "apply":
            command.add_argument("--verify", action="append", default=[])
            command.add_argument("--squash-message", action="append", default=[])
    for name in ("continue", "abort"):
        command = sub.add_parser(name)
        command.add_argument("--cwd", default=".")
        command.add_argument("--json", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "plan":
            value = inspect_plan(Path(args.cwd).resolve(), args.base, args.remote, do_fetch=True)
            print(json.dumps(value, indent=2) if args.json else render_plan(value))
            return 0
        if args.command == "apply":
            value = apply(args)
        elif args.command == "continue":
            value = resume(args)
        else:
            value = abort(args)
        emit(value, args.json)
        return 0
    except (AutosquashError, OSError, json.JSONDecodeError) as error:
        print(f"autosquash: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
