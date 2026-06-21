#!/usr/bin/env python3
"""Validate Homunculus skill directory and public-name conventions."""

from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_RE = re.compile(r"""^name:\s*(?P<quote>["']?)(?P<name>[^"'\n]+)(?P=quote)\s*$""")


def extract_frontmatter_name(skill_file: Path) -> str | None:
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return None

    for line in lines[1:]:
        if line == "---":
            return None

        match = NAME_RE.match(line)
        if match:
            return match.group("name").strip()

    return None


def validate_skill_file(skill_file: Path) -> list[str]:
    errors: list[str] = []
    relative = skill_file.relative_to(REPO_ROOT)
    parts = relative.parts

    if len(parts) < 4 or parts[0] != "skills" or parts[-1] != "SKILL.md":
        return [f"{relative}: expected path skills/<subpath>/SKILL.md"]

    skill_path_parts = parts[1:-1]
    expected_name = f"homunculus-{'-'.join(skill_path_parts)}"

    for segment in skill_path_parts:
        if not KEBAB_RE.fullmatch(segment):
            errors.append(f"{relative}: path segment must be lowercase kebab-case: {segment}")

    actual_name = extract_frontmatter_name(skill_file)
    if actual_name is None:
        errors.append(f"{relative}: missing frontmatter name")
    elif actual_name != expected_name:
        errors.append(
            f"{relative}: expected frontmatter name {expected_name!r}, got {actual_name!r}"
        )

    return errors


def main() -> int:
    skill_files = sorted((REPO_ROOT / "skills").glob("**/SKILL.md"))

    if not skill_files:
        print("No SKILL.md files found.")
        return 1

    errors: list[str] = []
    seen_names: dict[str, Path] = {}

    for skill_file in skill_files:
        errors.extend(validate_skill_file(skill_file))

        actual_name = extract_frontmatter_name(skill_file)
        if actual_name:
            previous = seen_names.get(actual_name)
            if previous is not None:
                errors.append(
                    f"{skill_file.relative_to(REPO_ROOT)}: duplicate skill name "
                    f"{actual_name!r}; first seen in {previous.relative_to(REPO_ROOT)}"
                )
            else:
                seen_names[actual_name] = skill_file

    if errors:
        print("Skill naming validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"Validated {len(skill_files)} skill name(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
