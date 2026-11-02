#!/usr/bin/env python3
"""Install global agent instructions and MCP config for scripts/install.sh.

agentic/AGENTS.md is the single source. Each tool gets it wrapped in a
managed block, so reruns replace only that block and keep anything the user
wrote around it:

  codex  -> ~/.codex/AGENTS.md
  claude -> ~/.claude/CLAUDE.md
  cursor -> ~/.cursor/rules/homunculus-global.mdc (always-apply rule)

MCP servers come from agentic/mcp-servers.json. Entries name the env vars a
server needs; values are never written, only references.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "agentic" / "AGENTS.md"
MCP_SERVERS = ROOT / "agentic" / "mcp-servers.json"

BEGIN = "<!-- BEGIN HOMUNCULUS GLOBAL INSTRUCTIONS: generated from Homunculus agentic/AGENTS.md; edit there, changes here are replaced on reinstall -->"
END = "<!-- END HOMUNCULUS GLOBAL INSTRUCTIONS -->"
BLOCK_RE = re.compile(
    r"<!-- BEGIN HOMUNCULUS GLOBAL INSTRUCTIONS\b.*?-->.*?<!-- END HOMUNCULUS GLOBAL INSTRUCTIONS -->\n?",
    re.DOTALL,
)
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
CURSOR_FRONTMATTER = (
    "---\n"
    "description: Homunculus global agent instructions (generated from agentic/AGENTS.md)\n"
    "alwaysApply: true\n"
    "---\n"
)

# sha256 of the pre-Homunculus global files installed by ben196888/mac-set-up
# (agentic/AGENTS.md and agentic/CLAUDE.md). A target that still holds one of
# these is replaced outright instead of merged, since the content migrated here.
LEGACY_SHA256 = {
    "2f666c14415c09abdb5f078e508484656a86535ff72cc5dc4c7e53c1fa940980",
    "d04206c550945e90613da915a98b83931de7f0cb33cf6c2c2e7cee1e637910b4",
}


def log(message: str) -> None:
    print(message, flush=True)


def block() -> str:
    body = SOURCE.read_text(encoding="utf-8").strip("\n")
    return f"{BEGIN}\n{body}\n{END}\n"


def render(tool: str, keep: str = "") -> str:
    """Full file content for tool, with optional user content kept after the block."""
    keep = keep.strip("\n")
    if tool == "cursor":
        keep = FRONTMATTER_RE.sub("", keep, count=1).strip("\n")
        head = CURSOR_FRONTMATTER
    else:
        head = ""
    text = head + block()
    if keep:
        text += "\n" + keep + "\n"
    return text


def is_legacy(text: str) -> bool:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return digest in LEGACY_SHA256


def backup(path: Path, dry_run: bool) -> Path:
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    target = path.with_name(f"{path.name}.homunculus-bak-{stamp}")
    n = 1
    while target.exists():
        target = path.with_name(f"{path.name}.homunculus-bak-{stamp}-{n}")
        n += 1
    if dry_run:
        log(f"  [dry-run] would back up {path} -> {target}")
    else:
        shutil.copy2(path, target, follow_symlinks=True)
        log(f"  Backed up {path} -> {target}")
    return target


def write(path: Path, text: str, dry_run: bool) -> None:
    if dry_run:
        log(f"  [dry-run] would write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Temp file + rename: atomic, and replaces a symlink instead of editing its target.
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(text)
    if path.exists():
        shutil.copymode(path, tmp)
    else:
        os.chmod(tmp, 0o644)
    os.replace(tmp, path)
    log(f"  Wrote {path}")


def ask(path: Path, current: str, desired_merge: str) -> str:
    """Prompt on /dev/tty. Returns merge|overwrite|skip."""
    # Separate handles: text mode "r+" fails on a tty (not seekable).
    with open("/dev/tty", encoding="utf-8") as tty_in, open("/dev/tty", "w", encoding="utf-8") as tty:
        while True:
            tty.write(
                f"  {path} exists with different content.\n"
                "  [m]erge (Homunculus block on top, your content kept below) / "
                "[o]verwrite / [s]kip / [d]iff ? [m] "
            )
            tty.flush()
            answer = tty_in.readline().strip().lower()
            if answer in ("", "m", "merge"):
                return "merge"
            if answer in ("o", "overwrite"):
                return "overwrite"
            if answer in ("s", "skip"):
                return "skip"
            if answer in ("d", "diff"):
                import difflib

                tty.writelines(
                    difflib.unified_diff(
                        current.splitlines(True),
                        desired_merge.splitlines(True),
                        str(path),
                        f"{path} (merged)",
                    )
                )


def interactive() -> bool:
    if not sys.stdout.isatty():
        return False
    try:
        with open("/dev/tty"):
            return True
    except OSError:
        return False


def install_instructions(tool: str, dest: Path, mode: str, dry_run: bool) -> None:
    if not dest.exists():
        log(f"  Creating {dest}")
        write(dest, render(tool), dry_run)
        return

    current = dest.read_text(encoding="utf-8")
    if BLOCK_RE.search(current):
        # Already managed: refresh the block in place, keep the user's surrounding text.
        desired = BLOCK_RE.sub(lambda _: block(), current, count=1)
        if tool == "cursor":
            desired = CURSOR_FRONTMATTER + FRONTMATTER_RE.sub("", desired, count=1)
        if desired == current:
            log(f"  {dest} is up to date")
            return
        backup(dest, dry_run)
        write(dest, desired, dry_run)
        return

    if is_legacy(current):
        log(f"  {dest} holds the legacy mac-set-up copy; replacing it")
        backup(dest, dry_run)
        write(dest, render(tool), dry_run)
        return

    merged = render(tool, keep=current)
    action = mode
    if action == "ask":
        action = ask(dest, current, merged) if not dry_run and interactive() else "merge"
    if action == "skip":
        log(f"  Skipped {dest} (exists with different content; rerun with --merge or --overwrite)")
        return
    backup(dest, dry_run)
    if action == "overwrite":
        log(f"  Overwriting {dest}")
        write(dest, render(tool), dry_run)
    else:
        log(f"  Merging into {dest} (existing content kept below the Homunculus block)")
        write(dest, merged, dry_run)


def load_servers() -> dict:
    return json.loads(MCP_SERVERS.read_text(encoding="utf-8"))["servers"]


def warn_missing_env(servers: dict) -> None:
    for name, cfg in servers.items():
        for var in cfg.get("env_vars", []):
            if not os.environ.get(var):
                log(f"  Note: {name} MCP needs ${var} exported in your shell; it is not set now.")


def mcp_codex(config: Path, dry_run: bool) -> None:
    servers = load_servers()
    current = config.read_text(encoding="utf-8") if config.exists() else ""
    additions = []
    for name, cfg in servers.items():
        header = re.compile(
            rf"^\s*\[\s*mcp_servers\s*\.\s*(?:{re.escape(name)}|\"{re.escape(name)}\")\s*\]",
            re.MULTILINE,
        )
        if header.search(current):
            log(f"  Codex MCP '{name}' already configured in {config}")
            continue
        lines = [
            f"# Added by Homunculus (agentic/mcp-servers.json)",
            f"[mcp_servers.{name}]",
            f"command = {json.dumps(cfg['command'])}",
            f"args = {json.dumps(cfg.get('args', []))}",
        ]
        if cfg.get("env_vars"):
            # Codex forwards these variables from the parent environment.
            lines.append(f"env_vars = {json.dumps(cfg['env_vars'])}")
        additions.append("\n".join(lines) + "\n")
        log(f"  Adding Codex MCP '{name}'")
    if not additions:
        return
    if current:
        backup(config, dry_run)
    text = current
    if text and not text.endswith("\n"):
        text += "\n"
    text += ("\n" if text else "") + "\n".join(additions)
    write(config, text, dry_run)
    warn_missing_env(servers)


def mcp_cursor(config: Path, dry_run: bool) -> None:
    servers = load_servers()
    data: dict = {}
    if config.exists():
        try:
            data = json.loads(config.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as error:
            log(f"  Skipping Cursor MCP: {config} is not valid JSON ({error}); fix it and rerun")
            return
    entries = data.setdefault("mcpServers", {})
    changed = False
    for name, cfg in servers.items():
        if name in entries:
            log(f"  Cursor MCP '{name}' already configured in {config}")
            continue
        entry = {"command": cfg["command"], "args": cfg.get("args", [])}
        if cfg.get("env_vars"):
            entry["env"] = {var: "${env:" + var + "}" for var in cfg["env_vars"]}
        entries[name] = entry
        changed = True
        log(f"  Adding Cursor MCP '{name}'")
    if not changed:
        return
    if config.exists():
        backup(config, dry_run)
    write(config, json.dumps(data, indent=2) + "\n", dry_run)
    warn_missing_env(servers)


def mcp_claude(dry_run: bool) -> None:
    servers = load_servers()
    changed = False
    for name, cfg in servers.items():
        # Claude Code passes its own environment to stdio servers, so the
        # server reads env_vars from the shell; nothing secret is stored.
        command = ["claude", "mcp", "add", "--scope", "user", name, "--", cfg["command"], *cfg.get("args", [])]
        if dry_run:
            # Never invoke claude here: even `claude mcp get` creates ~/.claude.json.
            log("  [dry-run] would run (unless already registered): " + " ".join(command))
            continue
        exists = subprocess.run(
            ["claude", "mcp", "get", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode == 0
        if exists:
            log(f"  Claude Code MCP '{name}' already registered")
            continue
        result = subprocess.run(command)
        if result.returncode == 0:
            log(f"  Registered Claude Code MCP '{name}' (user scope)")
            changed = True
        else:
            log(f"  Note: 'claude mcp add {name}' failed; run it manually after signing in")
    if changed:
        warn_missing_env(servers)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    inst = sub.add_parser("instructions", help="install global instructions for one tool")
    inst.add_argument("--tool", choices=("codex", "claude", "cursor"), required=True)
    inst.add_argument("--dest", type=Path, required=True)
    inst.add_argument("--mode", choices=("ask", "merge", "overwrite", "skip"), default="ask")
    inst.add_argument("--dry-run", action="store_true")

    rend = sub.add_parser("render", help="print the generated file for one tool")
    rend.add_argument("--tool", choices=("codex", "claude", "cursor"), required=True)

    for name in ("mcp-codex", "mcp-cursor"):
        mcp = sub.add_parser(name)
        mcp.add_argument("--config", type=Path, required=True)
        mcp.add_argument("--dry-run", action="store_true")
    sub.add_parser("mcp-claude").add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "instructions":
        install_instructions(args.tool, args.dest, args.mode, args.dry_run)
    elif args.command == "render":
        sys.stdout.write(render(args.tool))
    elif args.command == "mcp-codex":
        mcp_codex(args.config, args.dry_run)
    elif args.command == "mcp-cursor":
        mcp_cursor(args.config, args.dry_run)
    elif args.command == "mcp-claude":
        mcp_claude(args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
