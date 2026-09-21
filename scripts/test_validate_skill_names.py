"""Regression coverage for flat and nested skill paths."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate_skill_names as validator


class SkillNameTests(unittest.TestCase):
    def test_supported_depths_and_name_matching(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(validator, "REPO_ROOT", root):
                for subpath in ("create-printable-html", "productivity/edit-article"):
                    with self.subTest(subpath=subpath):
                        file = root / "skills" / subpath / "SKILL.md"
                        file.parent.mkdir(parents=True)
                        name = "homunculus-" + subpath.replace("/", "-")
                        file.write_text(f"---\nname: {name}\n---\n", encoding="utf-8")
                        self.assertEqual(validator.validate_skill_file(file), [])
                        file.write_text("---\nname: wrong-name\n---\n", encoding="utf-8")
                        self.assertTrue(validator.validate_skill_file(file))

    def test_skill_requires_subdirectory(self):
        file = validator.REPO_ROOT / "skills" / "SKILL.md"
        self.assertIn("expected path", validator.validate_skill_file(file)[0])
