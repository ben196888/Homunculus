import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LEDGER_SCRIPTS = ROOT / "skills" / "productivity" / "task-ledger" / "scripts"
CHANGE_SCRIPTS = ROOT / "skills" / "productivity" / "change-detection" / "scripts"
MR_SCRIPTS = ROOT / "skills" / "programming" / "mr-steward" / "scripts"
sys.path.insert(0, str(LEDGER_SCRIPTS))
sys.path.insert(0, str(CHANGE_SCRIPTS))
sys.path.insert(0, str(MR_SCRIPTS))
import ledger
import change_detection
import mr_steward


class P0SkillsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        for args in (("git", "init"), ("git", "config", "user.email", "test@example.com"), ("git", "config", "user.name", "Test")):
            subprocess.run(args, cwd=self.repo, check=True, capture_output=True)
        (self.repo / "tracked.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(("git", "add", "tracked.txt"), cwd=self.repo, check=True, capture_output=True)
        subprocess.run(("git", "commit", "-m", "base"), cwd=self.repo, check=True, capture_output=True)
        self.ledger_dir = Path(self.temp.name) / "ledger"
        self.environment = patch.dict(os.environ, {"HOMUNCULUS_LEDGER_DIR": str(self.ledger_dir)})
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def context(self):
        return ledger.git_context(self.repo)

    def test_isolates_state_by_branch_and_migrates_v0(self):
        main_context = self.context()
        main_state, main_path = ledger.load(main_context)
        ledger.save(main_state, main_path)
        subprocess.run(("git", "switch", "-c", "feature/other"), cwd=self.repo, check=True, capture_output=True)
        other_context = self.context()
        _, other_path = ledger.load(other_context)
        self.assertNotEqual(main_path, other_path)
        legacy = {"schema_version": 0, "task": {"reference": "ACT-1"}}
        migrated = ledger.migrate(legacy, other_context)
        self.assertEqual(1, migrated["schema_version"])
        self.assertEqual("ACT-1", migrated["task"]["reference"])

    def test_change_detection_passes_unchanged_then_requires_evidence(self):
        status, _ = change_detection.evaluate(str(self.repo))
        self.assertEqual("no-relevant-mutation", status)
        context = self.context()
        state, path = ledger.load(context)
        ledger.save(state, path)
        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        status, message = change_detection.evaluate(str(self.repo))
        self.assertEqual("incomplete", status)
        self.assertIn("Record", message)

    def test_completed_mutation_passes_and_ledger_summary_is_concise(self):
        (self.repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
        context = self.context()
        state, path = ledger.load(context)
        ledger.refresh_change(state, context)
        ledger.update_completion(state, "Changed test fixture", "unit test passed", "none")
        ledger.save(state, path)
        status, _ = change_detection.evaluate(str(self.repo))
        self.assertEqual("complete", status)
        summary = ledger.concise_summary(state)
        self.assertIn("Completion: Changed test fixture", summary)
        self.assertLess(len(summary), 1000)

    def test_mr_steward_uses_only_read_commands_and_records_status(self):
        calls = []

        def fake_glab(args, cwd):
            calls.append(args)
            if args[0:2] == ["mr", "list"]:
                return [{"iid": 12}]
            if args[0:2] == ["mr", "view"]:
                return {"title": "Add ledger", "web_url": "https://gitlab.example/group/project/-/merge_requests/12", "pipeline": {"status": "failed"}, "detailed_merge_status": "mergeable"}
            if args[0] == "api":
                return [{"notes": [{"resolvable": True, "resolved": False}]}]
            self.fail(f"unexpected glab call: {args}")

        with patch.object(mr_steward, "run_glab", side_effect=fake_glab):
            report = mr_steward.inspect(self.repo, None)
        self.assertEqual("needs-follow-up", report["status"])
        self.assertEqual(1, report["unresolved_threads"])
        self.assertTrue(all(command[0] in {"mr", "api"} for command in calls))
        self.assertTrue(all(not any(word in command for word in ("push", "comment", "approve", "merge", "close")) for command in calls))
        state, _ = ledger.load(self.context())
        self.assertEqual("needs-follow-up", state["merge_request"]["status"])


if __name__ == "__main__":
    unittest.main()
