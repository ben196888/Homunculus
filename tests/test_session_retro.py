import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "skills" / "productivity" / "harness-session-retro" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import session_retro


class SessionRetroTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.codex = self.root / "codex"
        self.repo = self.root / "repo"
        (self.codex / "sessions" / "2026" / "02" / "01").mkdir(parents=True)
        (self.repo / "skills" / "programming" / "code-review").mkdir(parents=True)
        (self.repo / "skills" / "productivity" / "unused").mkdir(parents=True)
        self.write_skill(
            "programming/code-review",
            "homunculus-programming-code-review",
            "Review merge requests with evidence.",
        )
        self.write_skill(
            "productivity/unused",
            "homunculus-productivity-unused",
            "Handle an old workflow.",
        )
        subprocess.run(("git", "init"), cwd=self.repo, check=True, capture_output=True)
        subprocess.run(("git", "config", "user.email", "test@example.com"), cwd=self.repo, check=True)
        subprocess.run(("git", "config", "user.name", "Test"), cwd=self.repo, check=True)
        subprocess.run(("git", "add", "skills"), cwd=self.repo, check=True)
        old_environment = {
            **os.environ,
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00",
        }
        subprocess.run(("git", "commit", "-m", "add skills"), cwd=self.repo, check=True, env=old_environment, capture_output=True)

    def write_skill(self, relative: str, name: str, description: str) -> None:
        path = self.repo / "skills" / relative / "SKILL.md"
        path.write_text(
            f"---\nname: {name}\ndescription: {description}\n---\n\n# Test\n",
            encoding="utf-8",
        )

    def write_session(
        self,
        session_id: str,
        title: str,
        updated_at: str,
        prompts: list[str],
        originator: str = "Codex Desktop",
        tool_input: str | None = None,
    ) -> None:
        path = self.codex / "sessions" / "2026" / "02" / "01" / f"rollout-{session_id}.jsonl"
        records = [
            {"type": "session_meta", "payload": {"id": session_id, "originator": originator, "source": "vscode"}}
        ]
        records.extend(
            {"type": "event_msg", "payload": {"type": "user_message", "message": prompt}}
            for prompt in prompts
        )
        if tool_input:
            records.append(
                {
                    "type": "response_item",
                    "payload": {"type": "function_call", "name": "exec_command", "arguments": tool_input},
                }
            )
        path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")
        with (self.codex / "session_index.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"id": session_id, "thread_name": title, "updated_at": updated_at}) + "\n")

    def test_classifies_population_and_skill_signals_without_persisting_prompts(self):
        ids = [f"0000000{number}-0000-0000-0000-00000000000{number}" for number in range(1, 7)]
        self.write_session(
            ids[0],
            "Review MR 10",
            "2026-02-06T00:00:00Z",
            [
                "[$programming:code-review] review https://gitlab.example/a/b/-/merge_requests/10",
                "<skill><name>programming-code-review</name><path>/tmp/skills/programming/code-review/SKILL.md</path>tests experiment feature flag</skill>",
                "You missed the failing test; fix the report.",
            ],
            tool_input='{"cmd":"sed -n 1,200p /tmp/skills/programming/code-review/SKILL.md"}',
        )
        self.write_session(ids[1], "Explore service flow", "2026-02-05T00:00:00Z", ["Explore how data flows across two repositories SECRET_PROMPT"])
        self.write_session(ids[2], "Delegated search", "2026-02-04T00:00:00Z", ["Locate the implementation"])
        self.write_session(ids[3], "Stop check", "2026-02-03T00:00:00Z", ["Review completion"], originator="Claude Code")
        self.write_session(ids[4], "Nightly digest", "2026-02-02T00:00:00Z", ["Automation: summarize changes"])
        self.write_session(ids[5], "Current retro", "2026-02-01T00:00:00Z", ["Analyze these sessions"])
        with sqlite3.connect(self.codex / "state_5.sqlite") as connection:
            connection.execute(
                "CREATE TABLE thread_spawn_edges (parent_thread_id TEXT NOT NULL, child_thread_id TEXT NOT NULL PRIMARY KEY, status TEXT NOT NULL)"
            )
            connection.execute("INSERT INTO thread_spawn_edges VALUES (?, ?, ?)", (ids[0], ids[2], "completed"))

        data = session_retro.analyze(
            codex_dir=self.codex,
            repo=self.repo,
            limit=10,
            exclude_ids={ids[5]},
            min_sessions=1,
            min_retirement_exposure=1,
        )

        self.assertEqual({"stop_gate": 1, "spawned_child": 1, "automation": 1, "primary": 2}, data["population"])
        review = next(item for item in data["workflow_signals"] if item["key"] == "mr_review")
        self.assertEqual(1, review["count"])
        code_review = next(item for item in data["skill_signals"] if item["name"] == "homunculus-programming-code-review")
        self.assertEqual(1, code_review["prompt_mentions"])
        self.assertEqual(1, code_review["harness_injections"])
        self.assertEqual(1, code_review["instruction_loads"])
        self.assertEqual(1, code_review["correction_signals"])
        unused = next(item for item in data["skill_signals"] if item["name"] == "homunculus-productivity-unused")
        self.assertTrue(unused["retirement_review"])
        persisted = json.dumps(data)
        self.assertNotIn("SECRET_PROMPT", persisted)
        self.assertNotIn(str(self.codex), persisted)

    def test_report_marks_retirement_as_review_not_deletion(self):
        session_id = "00000001-0000-0000-0000-000000000001"
        self.write_session(session_id, "Routine task", "2026-02-01T00:00:00Z", ["Do routine work"])
        data = session_retro.analyze(
            codex_dir=self.codex,
            repo=self.repo,
            limit=1,
            min_retirement_exposure=1,
        )
        report = session_retro.render_report(data)
        self.assertIn("Retirement review", report)
        self.assertIn("Verify implicit and low-frequency value", report)
        self.assertNotIn("delete this skill", report.lower())


if __name__ == "__main__":
    unittest.main()
