import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "programming" / "autosquash" / "scripts" / "autosquash.py"
SPEC = importlib.util.spec_from_file_location("homunculus_autosquash", SCRIPT)
autosquash = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = autosquash
SPEC.loader.exec_module(autosquash)


class AutosquashIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        self.git(self.root, "init", "--bare", str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.repo))
        self.git(self.repo, "config", "user.email", "test@example.com")
        self.git(self.repo, "config", "user.name", "Test User")
        self.write("README.md", "base\n")
        self.commit("chore: initialize repository")
        self.git(self.repo, "branch", "-M", "main")
        self.git(self.repo, "push", "-u", "origin", "main")
        self.git(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")
        self.git(self.repo, "remote", "set-head", "origin", "-a")
        self.git(self.repo, "switch", "-c", "feature/test")

    def git(self, cwd, *args, check=True):
        return subprocess.run(
            ["git", *args], cwd=cwd, text=True, capture_output=True, check=check
        )

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def commit(self, message):
        self.git(self.repo, "add", "-A")
        self.git(self.repo, "commit", "-m", message)
        return self.git(self.repo, "rev-parse", "HEAD").stdout.strip()

    def helper(self, *args, check=True):
        return subprocess.run(
            ["python3", str(SCRIPT), *args, "--cwd", str(self.repo)],
            text=True,
            capture_output=True,
            check=check,
        )

    def make_fixup(self):
        self.write("feature.txt", "initial\n")
        target = self.commit("feat: add feature")
        self.git(self.repo, "push", "-u", "origin", "feature/test")
        self.write("feature.txt", "initial\ncorrected\n")
        self.git(self.repo, "add", "feature.txt")
        self.git(self.repo, "commit", f"--fixup={target}")
        return target

    def clone_remote(self, name="collaborator"):
        clone = self.root / name
        self.git(self.root, "clone", str(self.remote), str(clone))
        self.git(clone, "config", "user.email", "collaborator@example.com")
        self.git(clone, "config", "user.name", "Collaborator")
        self.git(clone, "switch", "feature/test")
        return clone

    def test_fixup_is_folded_tree_preserved_and_remote_updated(self):
        self.make_fixup()
        tree_before = self.git(self.repo, "rev-parse", "HEAD^{tree}").stdout.strip()
        result = self.helper(
            "apply",
            "--base",
            "origin/main",
            "--verify",
            "test -f feature.txt",
            "--json",
        )
        report = json.loads(result.stdout)
        subjects = self.git(
            self.repo, "log", "--format=%s", "origin/main..HEAD"
        ).stdout.splitlines()
        self.assertEqual(["feat: add feature"], subjects)
        self.assertEqual(tree_before, self.git(self.repo, "rev-parse", "HEAD^{tree}").stdout.strip())
        self.assertEqual("complete", report["status"])
        self.assertIn("force-with-lease", report["push"])
        self.assertEqual(
            self.git(self.repo, "rev-parse", "HEAD").stdout.strip(),
            self.git(self.repo, "rev-parse", "origin/feature/test").stdout.strip(),
        )

    def test_squash_uses_supplied_conventional_message(self):
        self.write("feature.txt", "initial\n")
        target = self.commit("feat: add feature")
        self.git(self.repo, "push", "-u", "origin", "feature/test")
        self.write("feature.txt", "initial\nexpanded\n")
        self.git(self.repo, "add", "feature.txt")
        # Build the fixture directly. `git commit --squash` opens the user's editor,
        # which would make this otherwise unattended integration test interactive.
        self.git(self.repo, "commit", "-m", "squash! feat: add feature")
        self.helper(
            "apply",
            "--base",
            "origin/main",
            "--squash-message",
            f"{target}=feat: add complete feature",
        )
        subject = self.git(self.repo, "show", "-s", "--format=%s").stdout.strip()
        self.assertEqual("feat: add complete feature", subject)

    def test_dirty_staged_unstaged_and_untracked_state_is_restored(self):
        self.make_fixup()
        self.write("staged.txt", "staged\n")
        self.git(self.repo, "add", "staged.txt")
        self.write("README.md", "base\ndirty\n")
        self.write("untracked.txt", "untracked\n")
        before = autosquash.workspace_fingerprint(self.repo)
        self.helper("apply", "--base", "origin/main")
        self.assertEqual(before, autosquash.workspace_fingerprint(self.repo))
        self.assertFalse(self.git(self.repo, "stash", "list").stdout.strip())

    def test_no_markers_is_no_op_and_does_not_push(self):
        self.write("feature.txt", "ordinary\n")
        sha = self.commit("fix: correct typo")
        result = self.helper("apply", "--base", "origin/main", "--json")
        report = json.loads(result.stdout)
        self.assertEqual("no-op", report["status"])
        self.assertEqual(sha, self.git(self.repo, "rev-parse", "HEAD").stdout.strip())
        self.assertFalse(
            self.git(self.repo, "rev-parse", "--verify", "origin/feature/test", check=False).returncode == 0
        )

    def test_first_push_sets_upstream(self):
        self.write("feature.txt", "initial\n")
        target = self.commit("feat: add feature")
        self.write("feature.txt", "initial\nfixed\n")
        self.git(self.repo, "add", "feature.txt")
        self.git(self.repo, "commit", f"--fixup={target}")
        report = json.loads(
            self.helper("apply", "--base", "origin/main", "--json").stdout
        )
        self.assertIn("set upstream", report["push"])
        upstream = self.git(
            self.repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"
        ).stdout.strip()
        self.assertEqual("origin/feature/test", upstream)

    def test_diverged_remote_is_integrated_before_autosquash(self):
        self.make_fixup()
        collaborator = self.clone_remote()
        (collaborator / "remote.txt").write_text("remote\n", encoding="utf-8")
        self.git(collaborator, "add", "remote.txt")
        self.git(collaborator, "commit", "-m", "feat: add remote work")
        self.git(collaborator, "push", "origin", "feature/test")

        report = json.loads(
            self.helper("apply", "--base", "origin/main", "--json").stdout
        )
        subjects = self.git(
            self.repo, "log", "--format=%s", "origin/main..HEAD"
        ).stdout.splitlines()
        self.assertEqual(["feat: add remote work", "feat: add feature"], subjects)
        self.assertTrue((self.repo / "remote.txt").is_file())
        self.assertEqual("diverged", report["reconciliation"])

    def test_concurrent_remote_update_is_rejected_by_exact_lease(self):
        self.make_fixup()
        collaborator = self.clone_remote()
        (collaborator / "race.txt").write_text("race\n", encoding="utf-8")
        self.git(collaborator, "add", "race.txt")
        self.git(collaborator, "commit", "-m", "feat: add concurrent work")
        concurrent_sha = self.git(collaborator, "rev-parse", "HEAD").stdout.strip()
        command = f"git -C {collaborator} push origin HEAD:refs/heads/feature/test"

        result = self.helper(
            "apply", "--base", "origin/main", "--verify", command, check=False
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("push was rejected", result.stderr)
        remote_sha = self.git(
            self.remote, "rev-parse", "refs/heads/feature/test"
        ).stdout.strip()
        self.assertEqual(concurrent_sha, remote_sha)
        self.assertFalse(autosquash.state_path(self.repo).exists())

    def test_reconciliation_conflict_stops_and_abort_restores(self):
        self.write("feature.txt", "original\n")
        target = self.commit("feat: add feature")
        self.git(self.repo, "push", "-u", "origin", "feature/test")
        self.write("feature.txt", "local fix\n")
        self.git(self.repo, "add", "feature.txt")
        self.git(self.repo, "commit", f"--fixup={target}")
        old_sha = self.git(self.repo, "rev-parse", "HEAD").stdout.strip()
        collaborator = self.clone_remote()
        (collaborator / "feature.txt").write_text("remote fix\n", encoding="utf-8")
        self.git(collaborator, "add", "feature.txt")
        self.git(collaborator, "commit", "-m", "fix: change feature remotely")
        self.git(collaborator, "push", "origin", "feature/test")

        result = self.helper("apply", "--base", "origin/main", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("remote reconciliation has conflicts", result.stderr)
        self.assertTrue(autosquash.rebase_in_progress(self.repo))
        self.helper("abort")
        self.assertEqual(old_sha, self.git(self.repo, "rev-parse", "HEAD").stdout.strip())

    def test_failed_stash_restore_retains_stash_and_does_not_push(self):
        self.make_fixup()
        self.write("README.md", "local dirty README\n")
        collaborator = self.clone_remote()
        (collaborator / "README.md").write_text("remote README\n", encoding="utf-8")
        self.git(collaborator, "add", "README.md")
        self.git(collaborator, "commit", "-m", "docs: update README remotely")
        self.git(collaborator, "push", "origin", "feature/test")
        remote_sha = self.git(
            self.remote, "rev-parse", "refs/heads/feature/test"
        ).stdout.strip()

        result = self.helper("apply", "--base", "origin/main", check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn("could not restore the saved workspace", result.stderr)
        self.assertTrue(self.git(self.repo, "stash", "list").stdout.strip())
        self.assertEqual(
            remote_sha,
            self.git(self.remote, "rev-parse", "refs/heads/feature/test").stdout.strip(),
        )
        self.helper("abort")
        self.assertEqual("local dirty README\n", (self.repo / "README.md").read_text())
        self.assertFalse(autosquash.state_path(self.repo).exists())

    def test_protected_detached_merge_and_invalid_target_are_rejected(self):
        self.git(self.repo, "switch", "main")
        protected = self.helper("plan", "--base", "origin/main", check=False)
        self.assertNotEqual(0, protected.returncode)
        self.assertIn("protected branch", protected.stderr)

        self.git(self.repo, "switch", "feature/test")
        self.write("feature.txt", "one\n")
        self.commit("feat: add feature")
        self.git(self.repo, "checkout", "--detach")
        detached = self.helper("plan", "--base", "origin/main", check=False)
        self.assertIn("detached HEAD", detached.stderr)

        self.git(self.repo, "switch", "feature/test")
        self.git(self.repo, "switch", "-c", "side")
        self.write("side.txt", "side\n")
        self.commit("feat: add side")
        self.git(self.repo, "switch", "feature/test")
        self.git(self.repo, "merge", "--no-ff", "side", "-m", "chore: merge side")
        merge = self.helper("plan", "--base", "origin/main", check=False)
        self.assertIn("merge commits", merge.stderr)

        self.git(self.repo, "reset", "--hard", "HEAD~1")
        self.git(self.repo, "commit", "--allow-empty", "-m", "fixup! missing target")
        invalid = self.helper("plan", "--base", "origin/main", check=False)
        self.assertIn("outside the eligible range", invalid.stderr)

    def test_failed_verification_stops_before_push_and_abort_restores(self):
        old_remote = None
        self.make_fixup()
        old_remote = self.git(self.repo, "rev-parse", "origin/feature/test").stdout.strip()
        failed = self.helper(
            "apply", "--base", "origin/main", "--verify", "exit 9", check=False
        )
        self.assertNotEqual(0, failed.returncode)
        self.assertEqual(
            old_remote,
            self.git(self.repo, "rev-parse", "origin/feature/test").stdout.strip(),
        )
        self.helper("abort")
        self.assertFalse(autosquash.state_path(self.repo).exists())


if __name__ == "__main__":
    unittest.main()
