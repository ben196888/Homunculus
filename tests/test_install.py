"""End-to-end tests for scripts/install.sh.

Every run uses a throwaway HOME and a PATH of stubs (npx, claude, and
codex/cursor when a test wants them detected) plus
symlinks to python3/git, so the real ~/.claude, ~/.codex and ~/.cursor are
never touched and nothing hits the network.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT / "scripts" / "install.sh"
sys.path.insert(0, str(ROOT / "scripts"))
import agent_setup  # noqa: E402

NPX_STUB = """#!/bin/sh
echo "npx $*" >> "$STUB_STATE/calls.log"
"""

CLAUDE_STUB = """#!/bin/sh
echo "claude $*" >> "$STUB_STATE/calls.log"
# Like the real CLI, any invocation creates the user config file.
touch "$HOME/.claude.json"
touch "$STUB_STATE/mcp.list" "$STUB_STATE/marketplaces"
case "$1 $2" in
  "mcp get") grep -qx "$3" "$STUB_STATE/mcp.list"; exit $? ;;
  "mcp add") shift 4; echo "$1" >> "$STUB_STATE/mcp.list" ;;
  "plugin marketplace")
    if [ "$3" = list ]; then cat "$STUB_STATE/marketplaces"; else echo "$4" >> "$STUB_STATE/marketplaces"; fi ;;
esac
exit 0
"""

REAL_HOME = Path(os.path.expanduser("~")).resolve()


def snapshot(home: Path) -> dict:
    files = {}
    for path in sorted(home.rglob("*")):
        rel = str(path.relative_to(home))
        if path.is_symlink():
            files[rel] = "link:" + os.readlink(path)
        elif path.is_file():
            files[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.home = base / "home"
        self.home.mkdir()
        # Safety: never let a test point the installer at a real HOME.
        self.assertNotEqual(self.home, REAL_HOME)
        self.assertTrue(str(self.home).startswith(str(Path(tempfile.gettempdir()).resolve())))

        self.state = base / "stub-state"
        self.state.mkdir()
        self.bin = base / "bin"
        self.bin.mkdir()
        for name in ("python3", "git"):
            target = shutil.which(name)
            self.assertIsNotNone(target, f"{name} is required")
            (self.bin / name).symlink_to(target)
        self.add_stub("npx", NPX_STUB)
        self.add_stub("claude", CLAUDE_STUB)
        self.env = {
            "HOME": str(self.home),
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "STUB_STATE": str(self.state),
            "HOMUNCULUS_GROK_BOT": "0",
            "LANG": "C.UTF-8",
        }

    def add_tool_stubs(self):
        for name in ("codex", "cursor"):
            self.add_stub(name, "#!/bin/sh\nexit 0\n")

    def add_stub(self, name, body):
        path = self.bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)

    def install(self, *args, env=None, stdin=None, cwd=None, script=None):
        run_env = dict(self.env, **(env or {}))
        self.assertNotEqual(Path(run_env["HOME"]).resolve(), REAL_HOME)
        cmd = ["bash", str(script or INSTALL), *args] if stdin is None else ["bash", "-s", "--", *args]
        result = subprocess.run(
            cmd,
            env=run_env,
            input=stdin,
            cwd=cwd or self.temp.name,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def calls(self):
        log = self.state / "calls.log"
        return log.read_text().splitlines() if log.exists() else []

    def backups(self):
        return [p for p in self.home.rglob("*") if ".homunculus-bak-" in p.name]

    def test_fresh_install_then_rerun_changes_nothing(self):
        self.add_tool_stubs()
        self.install("--source", str(ROOT), "--yes")

        source = (ROOT / "agentic" / "AGENTS.md").read_text().strip()
        codex = (self.home / ".codex" / "AGENTS.md").read_text()
        claude = (self.home / ".claude" / "CLAUDE.md").read_text()
        rule = (self.home / ".cursor" / "rules" / "homunculus-global.mdc").read_text()
        for text in (codex, claude, rule):
            self.assertIn(source, text)
            self.assertIn(agent_setup.BEGIN, text)
        self.assertTrue(rule.startswith("---\n"))
        self.assertIn("alwaysApply: true", rule.split("---")[1])

        self.assertTrue((self.home / ".codex" / "skills" / "homunculus-programming-wt-add" / "SKILL.md").exists())
        npx = [c for c in self.calls() if c.startswith("npx ")]
        self.assertEqual(
            sorted(c.split("--agent ")[1].split()[0] for c in npx), ["claude-code", "codex", "cursor"]
        )
        self.assertIn("claude plugin install pstack@cursor-plugins -y", self.calls())

        toml = (self.home / ".codex" / "config.toml").read_text()
        self.assertIn("[mcp_servers.discord]", toml)
        self.assertIn('env_vars = ["DISCORD_TOKEN"]', toml)
        cursor_mcp = json.loads((self.home / ".cursor" / "mcp.json").read_text())
        self.assertEqual(cursor_mcp["mcpServers"]["discord"]["env"], {"DISCORD_TOKEN": "${env:DISCORD_TOKEN}"})
        self.assertEqual((self.state / "mcp.list").read_text().split(), ["discord"])

        before = snapshot(self.home)
        self.install("--source", str(ROOT), "--yes")
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(self.backups(), [])
        self.assertEqual(sum(c.startswith("claude mcp add") for c in self.calls()), 1)
        self.assertEqual(sum(c.startswith("claude plugin marketplace add") for c in self.calls()), 1)

    def test_dry_run_writes_nothing(self):
        self.add_tool_stubs()
        (self.home / ".codex").mkdir()
        out = self.install("--source", str(ROOT), "--dry-run")
        self.assertIn("[dry-run]", out)
        self.assertIn("would run (unless already registered): claude mcp add", out)
        self.assertEqual(snapshot(self.home), {})
        self.assertEqual([p.name for p in self.home.iterdir()], [".codex"])
        self.assertFalse(any(c.startswith("npx ") for c in self.calls()))
        # Any claude call, even a read-only probe, would create ~/.claude.json.
        self.assertFalse(any(c.startswith("claude ") for c in self.calls()))

    def test_mcp_ignores_dirs_created_by_installer(self):
        # No codex/cursor on PATH: their dirs appear during run one (instructions),
        # but must not make run two configure their MCP.
        args = ("--source", str(ROOT), "--yes", "--no-skills", "--no-plugin")
        codex_cfg = self.home / ".codex" / "config.toml"
        cursor_cfg = self.home / ".cursor" / "mcp.json"
        out = self.install(*args)
        self.assertIn("Codex not detected", out)
        self.assertIn("Cursor not detected", out)
        self.assertFalse(codex_cfg.exists())
        self.assertFalse(cursor_cfg.exists())
        self.assertTrue((self.home / ".codex" / "AGENTS.md").exists())

        before = snapshot(self.home)
        out = self.install(*args)
        self.assertIn("Codex not detected", out)
        self.assertIn("Cursor not detected", out)
        self.assertFalse(codex_cfg.exists())
        self.assertFalse(cursor_cfg.exists())
        self.assertEqual(snapshot(self.home), before)

    def only_instructions(self, *args):
        return self.install("--source", str(ROOT), "--no-skills", "--no-plugin", "--no-mcp", *args)

    def test_differing_file_defaults_to_backup_and_merge(self):
        target = self.home / ".claude" / "CLAUDE.md"
        target.parent.mkdir()
        target.write_text("# Mine\n\nKeep this rule.\n")
        self.only_instructions("--tools", "claude")
        merged = target.read_text()
        self.assertTrue(merged.startswith(agent_setup.BEGIN))
        self.assertIn("Keep this rule.", merged)
        backups = self.backups()
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "# Mine\n\nKeep this rule.\n")

        before = snapshot(self.home)
        self.only_instructions("--tools", "claude")
        self.assertEqual(snapshot(self.home), before)

    def test_source_change_refreshes_block_and_keeps_user_text(self):
        target = self.home / ".codex" / "AGENTS.md"
        target.parent.mkdir()
        target.write_text("Above.\n\n" + agent_setup.BEGIN + "\nold\n" + agent_setup.END + "\n\nBelow.\n")
        self.only_instructions("--tools", "codex")
        text = target.read_text()
        self.assertTrue(text.startswith("Above.\n\n" + agent_setup.BEGIN))
        self.assertTrue(text.endswith("\nBelow.\n"))
        self.assertNotIn("\nold\n", text)
        self.assertEqual(len(self.backups()), 1)

    def test_overwrite_and_skip_flags(self):
        claude = self.home / ".claude" / "CLAUDE.md"
        codex = self.home / ".codex" / "AGENTS.md"
        for path in (claude, codex):
            path.parent.mkdir()
            path.write_text("custom\n")
        self.only_instructions("--tools", "claude", "--overwrite")
        self.only_instructions("--tools", "codex", "--skip")
        self.assertEqual(claude.read_text(), agent_setup.render("claude"))
        self.assertEqual(codex.read_text(), "custom\n")
        self.assertEqual([p.parent.name for p in self.backups()], [".claude"])

    def test_grok_bot_skips_mcp_unless_forced(self):
        marker = Path(self.temp.name) / "agent-data"
        marker.mkdir()
        self.add_tool_stubs()
        env = {"HOMUNCULUS_GROK_BOT": "", "HOMUNCULUS_GROK_BOT_MARKER": str(marker)}
        args = ("--source", str(ROOT), "--no-skills", "--no-plugin", "--no-instructions")
        out = self.install(*args, env=env)
        self.assertIn("Grok Bot machine detected", out)
        self.assertFalse((self.home / ".codex" / "config.toml").exists())
        self.assertFalse((self.home / ".cursor" / "mcp.json").exists())
        self.assertFalse(any(c.startswith("claude mcp") for c in self.calls()))

        self.install(*args, "--mcp", env=env)
        self.assertTrue((self.home / ".cursor" / "mcp.json").exists())

    def test_mcp_only_for_detected_tools_and_keeps_existing_entries(self):
        self.add_stub("cursor", "#!/bin/sh\nexit 0\n")
        (self.home / ".cursor").mkdir()
        (self.home / ".cursor" / "mcp.json").write_text('{"mcpServers": {"other": {"url": "https://x"}}}')
        (self.bin / "claude").unlink()
        self.install("--source", str(ROOT), "--no-skills", "--no-plugin", "--no-instructions")
        data = json.loads((self.home / ".cursor" / "mcp.json").read_text())
        self.assertEqual(sorted(data["mcpServers"]), ["discord", "other"])
        self.assertFalse((self.home / ".codex").exists())

    def test_existing_codex_server_is_left_alone(self):
        self.add_tool_stubs()
        config = self.home / ".codex" / "config.toml"
        config.parent.mkdir()
        config.write_text('model = "x"\n\n[mcp_servers."discord"]\ncommand = "mine"\n')
        self.install("--source", str(ROOT), "--no-skills", "--no-plugin", "--no-instructions", "--tools", "codex")
        self.assertEqual(config.read_text(), 'model = "x"\n\n[mcp_servers."discord"]\ncommand = "mine"\n')

    def test_mcp_definitions_hold_no_secret_values(self):
        servers = json.loads((ROOT / "agentic" / "mcp-servers.json").read_text())["servers"]
        for cfg in servers.values():
            self.assertNotIn("env", cfg, "reference variables via env_vars, never inline values")

    def test_legacy_mac_set_up_file_is_replaced(self):
        target = self.home / "AGENTS.md"
        target.write_text("legacy\n")
        legacy = {hashlib.sha256(b"legacy\n").hexdigest()}
        with patch.object(agent_setup, "LEGACY_SHA256", legacy), patch("builtins.print"):
            agent_setup.install_instructions("codex", target, "skip", dry_run=False)
        self.assertEqual(target.read_text(), agent_setup.render("codex"))

    def prompt_session(self, dest, answers):
        """Run the instructions step on a pseudo-terminal, answering each prompt."""
        import pty
        import select

        pid, fd = pty.fork()
        if pid == 0:
            os.environ["HOME"] = str(self.home)
            os.execvp(sys.executable, [
                sys.executable, str(ROOT / "scripts" / "agent_setup.py"),
                "instructions", "--tool", "claude", "--dest", str(dest),
            ])
        output = b""
        pending = list(answers)
        while True:
            ready, _, _ = select.select([fd], [], [], 10)
            if not ready:
                os.kill(pid, 9)
                self.fail("prompt session timed out: " + output.decode(errors="replace"))
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
            if output.rstrip().endswith(b"[m]") and pending:
                os.write(fd, pending.pop(0).encode() + b"\n")
                output += b"\n"
        os.waitpid(pid, 0)
        os.close(fd)
        return output.decode(errors="replace")

    def test_tty_prompt_offers_diff_and_respects_choice(self):
        target = self.home / ".claude" / "CLAUDE.md"
        target.parent.mkdir()
        target.write_text("mine\n")
        out = self.prompt_session(target, ["d", "s"])
        self.assertIn("[o]verwrite / [s]kip / [d]iff", out)
        self.assertIn("+# Global Agent Instructions", out)
        self.assertEqual(target.read_text(), "mine\n")
        self.assertEqual(self.backups(), [])

        self.prompt_session(target, ["o"])
        self.assertEqual(target.read_text(), agent_setup.render("claude"))
        self.assertEqual(len(self.backups()), 1)

    def make_remote(self):
        remote = Path(self.temp.name) / "remote"
        files = subprocess.run(
            ["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
        for rel in files:
            if (ROOT / rel).is_file():
                (remote / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, remote / rel)
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=remote, check=True)
        subprocess.run(["git", "add", "-A"], cwd=remote, check=True)
        subprocess.run([*git, "commit", "-qm", "init"], cwd=remote, check=True)
        return remote, git

    def test_one_liner_bootstraps_and_rerun_updates_copy(self):
        remote, git = self.make_remote()
        env = {"HOMUNCULUS_REPO_URL": f"file://{remote}"}
        args = ("--yes", "--no-skills", "--no-plugin", "--no-mcp")
        script = INSTALL.read_text()

        self.install(*args, "--dry-run", env=env, stdin=script)
        self.assertEqual(snapshot(self.home), {})

        self.install(*args, env=env, stdin=script)
        checkout = self.home / ".homunculus"
        self.assertTrue((checkout / ".git").is_dir())
        self.assertIn("Global Agent Instructions", (self.home / ".claude" / "CLAUDE.md").read_text())

        before = snapshot(self.home)
        self.install(*args, env=env, stdin=script)
        self.assertEqual(snapshot(self.home), before)

        with open(remote / "agentic" / "AGENTS.md", "a") as handle:
            handle.write("\n## New Section\n\n- New rule\n")
        subprocess.run([*git, "commit", "-qam", "update"], cwd=remote, check=True)
        self.install(*args, env=env, stdin=script)
        self.assertIn("- New rule", (self.home / ".claude" / "CLAUDE.md").read_text())
        self.assertIn("- New rule", (checkout / "agentic" / "AGENTS.md").read_text())


if __name__ == "__main__":
    unittest.main()
