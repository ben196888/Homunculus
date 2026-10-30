#!/usr/bin/env python3
"""Focused tests for skill alias helper behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_alias


class SkillAliasTests(unittest.TestCase):
    def test_generated_skill_name_uses_full_alias_path(self) -> None:
        self.assertEqual(
            skill_alias.generated_skill_name("homunculus", "productivity/article-editor"),
            "homunculus-productivity-article-editor",
        )

    def test_validate_alias_rejects_unsafe_paths(self) -> None:
        for alias in [
            "/productivity/article-editor",
            "productivity/../article-editor",
            "productivity//article-editor",
            "productivity/.hidden",
            "version",
            "Productivity/article-editor",
        ]:
            with self.subTest(alias=alias):
                with self.assertRaises(skill_alias.SkillAliasError):
                    skill_alias.validate_alias(alias)

    def test_rewrite_frontmatter_name_preserves_body(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_file = Path(tmp) / "SKILL.md"
            body = "# Title\n\nBody text.\n"
            skill_file.write_text(
                "---\n"
                "name: edit-article\n"
                "description: Existing description\n"
                "---\n"
                + body,
                encoding="utf-8",
            )

            skill_alias.rewrite_frontmatter_name(
                skill_file, "homunculus-productivity-article-editor"
            )

            updated = skill_file.read_text(encoding="utf-8")
            self.assertIn("name: homunculus-productivity-article-editor\n", updated)
            self.assertTrue(updated.endswith(body))

    def test_replace_directory_removes_stale_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            (source / "fresh.txt").write_text("fresh\n", encoding="utf-8")
            (target / "stale.txt").write_text("stale\n", encoding="utf-8")

            skill_alias.replace_directory(source, target)

            self.assertTrue((target / "fresh.txt").exists())
            self.assertFalse((target / "stale.txt").exists())

    def test_parse_simple_yaml_accepts_quoted_alias_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            yaml_file = Path(tmp) / "skill-aliases.yml"
            yaml_file.write_text(
                "namespace: homunculus\n"
                "\n"
                "aliases:\n"
                '  "productivity/article-editor":\n'
                "    source: mattpocock/skills\n"
                "    skill: edit-article\n"
                "    ref: main\n",
                encoding="utf-8",
            )

            parsed = skill_alias.parse_simple_yaml(yaml_file)

            self.assertIn("productivity/article-editor", parsed["aliases"])
            self.assertEqual(
                parsed["aliases"]["productivity/article-editor"]["skill"], "edit-article"
            )


    def test_validate_source_path_rejects_unsafe_paths(self) -> None:
        for source_path in [
            "/skills/ponytail",
            "skills/../ponytail",
            "skills//ponytail",
            "skills/.hidden",
            "skills/ponytail/",
        ]:
            with self.subTest(source_path=source_path):
                with self.assertRaises(skill_alias.SkillAliasError):
                    skill_alias.validate_source_path(source_path)

    def test_locate_upstream_skill_uses_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wanted = root / "skills" / "ponytail"
            duplicate = root / ".openclaw" / "skills" / "ponytail"
            for skill_dir in (wanted, duplicate):
                skill_dir.mkdir(parents=True)
                (skill_dir / "SKILL.md").write_text(
                    "---\nname: ponytail\ndescription: test\n---\nbody\n",
                    encoding="utf-8",
                )

            with self.assertRaises(skill_alias.SkillAliasError) as raised:
                skill_alias.locate_upstream_skill(root, "ponytail")
            self.assertIn("multiple upstream skills", str(raised.exception))

            located = skill_alias.locate_upstream_skill(
                root, "ponytail", path="skills/ponytail"
            )
            self.assertEqual(located, wanted.resolve())

    def test_locate_upstream_skill_path_must_match_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill_dir = root / "skills" / "ponytail"
            skill_dir.mkdir(parents=True)
            (skill_dir / "SKILL.md").write_text(
                "---\nname: other\ndescription: test\n---\nbody\n",
                encoding="utf-8",
            )
            with self.assertRaises(skill_alias.SkillAliasError) as raised:
                skill_alias.locate_upstream_skill(
                    root, "ponytail", path="skills/ponytail"
                )
            self.assertIn("expected 'ponytail'", str(raised.exception))

    def test_read_manifest_accepts_optional_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "skill-aliases.yml"
            manifest.write_text(
                "namespace: homunculus\n"
                "\n"
                "aliases:\n"
                "  programming/ponytail:\n"
                "    source: DietrichGebert/ponytail\n"
                "    skill: ponytail\n"
                "    ref: main\n"
                "    path: skills/ponytail\n",
                encoding="utf-8",
            )
            with (
                unittest.mock.patch.object(skill_alias, "MANIFEST_PATH", manifest),
                unittest.mock.patch.object(skill_alias, "REPO_ROOT", root),
            ):
                parsed = skill_alias.read_manifest()
            config = parsed.aliases["programming/ponytail"]
            self.assertEqual(config.path, "skills/ponytail")

if __name__ == "__main__":
    unittest.main()
