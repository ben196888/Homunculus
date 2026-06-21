#!/usr/bin/env python3
"""Vendor third-party Agent Skills into the Homunculus skills tree."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
MANIFEST_PATH = REPO_ROOT / "skill-aliases.yml"
LOCK_PATH = REPO_ROOT / "skill-aliases.lock.yml"
CACHE_ROOT = REPO_ROOT / ".cache" / "skill-aliases"
LOCK_VERSION = 1

ALIAS_SEGMENT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SOURCE_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
NAME_LINE_RE = re.compile(r"""^(?P<prefix>\s*name\s*:\s*)(?P<value>.*?)(?P<suffix>\s*)$""")
YAML_KEY = r"""["']?[A-Za-z0-9_./-]+["']?"""
SCALAR_RE = re.compile(rf"""^(?P<key>{YAML_KEY}):(?:\s*(?P<value>.*?))?\s*$""")
INDENTED_SCALAR_RE = re.compile(
    rf"""^  (?P<key>{YAML_KEY}):(?:\s*(?P<value>.*?))?\s*$"""
)
NESTED_SCALAR_RE = re.compile(r"""^    (?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*?)\s*$""")


class SkillAliasError(Exception):
    """Expected operational error."""


@dataclass(frozen=True)
class AliasConfig:
    alias: str
    source: str
    skill: str
    ref: str


@dataclass(frozen=True)
class Manifest:
    namespace: str
    aliases: dict[str, AliasConfig]


@dataclass(frozen=True)
class LockEntry:
    source: str
    skill: str
    ref: str
    commit: str
    upstream_path: str


def run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or exc.stdout.strip()
        rendered = " ".join(cmd)
        if detail:
            raise SkillAliasError(f"Command failed: {rendered}\n{detail}") from exc
        raise SkillAliasError(f"Command failed: {rendered}") from exc

    return result.stdout.strip()


def unquote_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def quote_scalar(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_./:-]+", value):
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SkillAliasError(f"Missing required file: {path.relative_to(REPO_ROOT)}")

    root: dict[str, Any] = {}
    current_map: str | None = None
    current_entry: str | None = None

    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if raw_line.startswith("    "):
            if current_map is None or current_entry is None:
                raise SkillAliasError(f"{path}:{line_number}: unexpected nested field")
            match = NESTED_SCALAR_RE.fullmatch(raw_line)
            if not match:
                raise SkillAliasError(f"{path}:{line_number}: unsupported YAML syntax")
            entry = root[current_map][current_entry]
            entry[match.group("key")] = unquote_scalar(match.group("value"))
            continue

        if raw_line.startswith("  "):
            if current_map is None:
                raise SkillAliasError(f"{path}:{line_number}: unexpected indented field")
            match = INDENTED_SCALAR_RE.fullmatch(raw_line)
            if not match:
                raise SkillAliasError(f"{path}:{line_number}: unsupported YAML syntax")
            key = unquote_scalar(match.group("key"))
            value = match.group("value")
            if value is not None and value.strip():
                root[current_map][key] = unquote_scalar(value)
                current_entry = None
            else:
                root[current_map][key] = {}
                current_entry = key
            continue

        match = SCALAR_RE.fullmatch(raw_line)
        if not match:
            raise SkillAliasError(f"{path}:{line_number}: unsupported YAML syntax")

        key = unquote_scalar(match.group("key"))
        value = match.group("value")
        if value is not None and value.strip():
            if value.strip() == "{}":
                root[key] = {}
                current_map = None
                current_entry = None
            else:
                root[key] = unquote_scalar(value)
                current_map = None
                current_entry = None
        else:
            root[key] = {}
            current_map = key
            current_entry = None

    return root


def write_lockfile(entries: dict[str, LockEntry]) -> None:
    lines = [f"version: {LOCK_VERSION}"]

    for alias in sorted(entries):
        entry = entries[alias]
        lines.extend(
            [
                "",
                f"{alias}:",
                f"  source: {quote_scalar(entry.source)}",
                f"  skill: {quote_scalar(entry.skill)}",
                f"  ref: {quote_scalar(entry.ref)}",
                f"  commit: {quote_scalar(entry.commit)}",
                f"  upstreamPath: {quote_scalar(entry.upstream_path)}",
            ]
        )

    LOCK_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_namespace(namespace: str) -> None:
    if not ALIAS_SEGMENT_RE.fullmatch(namespace):
        raise SkillAliasError(
            f"namespace must match {ALIAS_SEGMENT_RE.pattern}: {namespace!r}"
        )


def validate_alias(alias: str) -> None:
    if alias == "version":
        raise SkillAliasError("alias path 'version' is reserved by the lockfile format")
    if alias.startswith("/") or alias.endswith("/"):
        raise SkillAliasError(f"alias must be relative to skills/: {alias!r}")
    parts = alias.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SkillAliasError(f"alias contains an unsafe path segment: {alias!r}")
    for part in parts:
        if part.startswith("."):
            raise SkillAliasError(f"alias contains a hidden path segment: {alias!r}")
        if not ALIAS_SEGMENT_RE.fullmatch(part):
            raise SkillAliasError(
                f"alias segment must match {ALIAS_SEGMENT_RE.pattern}: {part!r}"
            )


def target_for_alias(alias: str) -> Path:
    validate_alias(alias)
    target = SKILLS_ROOT.joinpath(*alias.split("/"))
    try:
        target.relative_to(SKILLS_ROOT)
    except ValueError as exc:
        raise SkillAliasError(f"alias escapes skills/: {alias!r}") from exc
    return target


def generated_skill_name(namespace: str, alias: str) -> str:
    validate_namespace(namespace)
    validate_alias(alias)
    return f"{namespace}-{'-'.join(alias.split('/'))}"


def read_manifest() -> Manifest:
    data = parse_simple_yaml(MANIFEST_PATH)
    namespace = data.get("namespace")
    if not isinstance(namespace, str):
        raise SkillAliasError("skill-aliases.yml must define namespace")
    validate_namespace(namespace)

    raw_aliases = data.get("aliases")
    if not isinstance(raw_aliases, dict):
        raise SkillAliasError("skill-aliases.yml must define aliases")

    aliases: dict[str, AliasConfig] = {}
    for alias, raw_config in raw_aliases.items():
        validate_alias(alias)
        if not isinstance(raw_config, dict):
            raise SkillAliasError(f"alias {alias!r} must map to a configuration object")
        source = raw_config.get("source")
        skill = raw_config.get("skill")
        ref = raw_config.get("ref")
        if not all(isinstance(value, str) and value for value in [source, skill, ref]):
            raise SkillAliasError(
                f"alias {alias!r} must define non-empty source, skill, and ref"
            )
        if not SOURCE_RE.fullmatch(source):
            raise SkillAliasError(
                f"alias {alias!r} source must be GitHub owner/repo form: {source!r}"
            )
        aliases[alias] = AliasConfig(alias=alias, source=source, skill=skill, ref=ref)

    return Manifest(namespace=namespace, aliases=aliases)


def read_lockfile() -> dict[str, LockEntry]:
    data = parse_simple_yaml(LOCK_PATH)
    version = data.get("version")
    if str(version) != str(LOCK_VERSION):
        raise SkillAliasError(
            f"Unsupported lockfile version {version!r}; expected {LOCK_VERSION}"
        )

    entries: dict[str, LockEntry] = {}
    for alias, raw_entry in data.items():
        if alias == "version":
            continue
        validate_alias(alias)
        if not isinstance(raw_entry, dict):
            raise SkillAliasError(f"lockfile alias {alias!r} must map to an object")
        required = ["source", "skill", "ref", "commit", "upstreamPath"]
        missing = [key for key in required if not raw_entry.get(key)]
        if missing:
            raise SkillAliasError(
                f"lockfile alias {alias!r} missing field(s): {', '.join(missing)}"
            )
        entries[alias] = LockEntry(
            source=str(raw_entry["source"]),
            skill=str(raw_entry["skill"]),
            ref=str(raw_entry["ref"]),
            commit=str(raw_entry["commit"]),
            upstream_path=str(raw_entry["upstreamPath"]),
        )

    return entries


def ensure_clean_target(alias: str, lock_entries: dict[str, LockEntry]) -> Path:
    target = target_for_alias(alias)
    if not target.exists():
        return target

    if alias not in lock_entries:
        raise SkillAliasError(
            f"Refusing to overwrite unmanaged skill directory: {target.relative_to(REPO_ROOT)}"
        )

    status = run(["git", "status", "--porcelain", "--", str(target)], cwd=REPO_ROOT)
    if status:
        raise SkillAliasError(
            "Refusing to update target with uncommitted changes:\n" + status
        )

    return target


def source_cache_path(source: str) -> Path:
    owner, repo = source.split("/", 1)
    return CACHE_ROOT / owner / repo


def ensure_source_repo(source: str) -> Path:
    cache_path = source_cache_path(source)
    repo_url = f"https://github.com/{source}.git"

    if (cache_path / ".git").exists():
        run(["git", "fetch", "--tags", "--prune", "origin"], cwd=cache_path)
    else:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", repo_url, str(cache_path)], cwd=REPO_ROOT)

    return cache_path


def resolve_ref(repo_path: Path, ref: str) -> str:
    candidates = [
        ref,
        f"origin/{ref}",
        f"refs/tags/{ref}",
        f"refs/heads/{ref}",
        f"refs/remotes/origin/{ref}",
    ]
    for candidate in candidates:
        try:
            return run(["git", "rev-parse", f"{candidate}^{{commit}}"], cwd=repo_path)
        except SkillAliasError:
            continue
    raise SkillAliasError(f"Could not resolve ref {ref!r} in {repo_path}")


def checkout_commit(repo_path: Path, commit: str) -> None:
    run(["git", "checkout", "--detach", "--quiet", commit], cwd=repo_path)


def split_frontmatter(text: str, path: Path) -> tuple[list[str], str]:
    if not text.startswith("---\n"):
        raise SkillAliasError(f"{path}: missing YAML frontmatter")

    closing = text.find("\n---", 4)
    if closing == -1:
        raise SkillAliasError(f"{path}: unterminated YAML frontmatter")

    after_closing = closing + len("\n---")
    if after_closing < len(text) and text[after_closing] == "\r":
        after_closing += 1
    if after_closing < len(text) and text[after_closing] == "\n":
        after_closing += 1

    frontmatter = text[4:closing]
    body = text[after_closing:]
    return frontmatter.splitlines(), body


def frontmatter_name(skill_file: Path) -> str:
    lines, _body = split_frontmatter(skill_file.read_text(encoding="utf-8"), skill_file)
    for line in lines:
        match = NAME_LINE_RE.fullmatch(line)
        if match:
            return unquote_scalar(match.group("value"))
    raise SkillAliasError(f"{skill_file}: missing frontmatter name")


def rewrite_frontmatter_name(skill_file: Path, new_name: str) -> None:
    text = skill_file.read_text(encoding="utf-8")
    lines, body = split_frontmatter(text, skill_file)
    rewritten: list[str] = []
    changed = False

    for line in lines:
        match = NAME_LINE_RE.fullmatch(line)
        if match and not changed:
            rewritten.append(f"{match.group('prefix')}{quote_scalar(new_name)}{match.group('suffix')}")
            changed = True
        else:
            rewritten.append(line)

    if not changed:
        raise SkillAliasError(f"{skill_file}: missing frontmatter name")

    skill_file.write_text("---\n" + "\n".join(rewritten) + "\n---\n" + body, encoding="utf-8")


def locate_upstream_skill(repo_path: Path, skill: str) -> Path:
    matches: list[Path] = []
    for skill_file in repo_path.rglob("SKILL.md"):
        if ".git" in skill_file.parts:
            continue
        try:
            if frontmatter_name(skill_file) == skill:
                matches.append(skill_file.parent)
        except SkillAliasError:
            continue

    if not matches:
        raise SkillAliasError(f"Could not find upstream skill with name {skill!r}")
    if len(matches) > 1:
        rendered = "\n".join(
            f"- {match.relative_to(repo_path)}" for match in sorted(matches)
        )
        raise SkillAliasError(
            f"Found multiple upstream skills with name {skill!r}:\n{rendered}"
        )
    return matches[0]


def replace_directory(source_dir: Path, target_dir: Path) -> None:
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix=".skill-alias-", dir=target_dir.parent) as tmp:
        tmp_path = Path(tmp) / target_dir.name
        ignore = shutil.ignore_patterns(".git")
        shutil.copytree(source_dir, tmp_path, ignore=ignore)

        backup_path: Path | None = None
        if target_dir.exists():
            backup_path = Path(tmp) / f"{target_dir.name}.old"
            target_dir.rename(backup_path)
        tmp_path.rename(target_dir)


def update_alias(config: AliasConfig, manifest: Manifest, lock_entries: dict[str, LockEntry]) -> LockEntry:
    target = ensure_clean_target(config.alias, lock_entries)
    repo_path = ensure_source_repo(config.source)
    commit = resolve_ref(repo_path, config.ref)
    checkout_commit(repo_path, commit)
    upstream_dir = locate_upstream_skill(repo_path, config.skill)

    with tempfile.TemporaryDirectory(prefix="skill-alias-copy-") as tmp:
        staged_dir = Path(tmp) / "skill"
        shutil.copytree(upstream_dir, staged_dir, ignore=shutil.ignore_patterns(".git"))
        rewrite_frontmatter_name(
            staged_dir / "SKILL.md", generated_skill_name(manifest.namespace, config.alias)
        )
        replace_directory(staged_dir, target)

    entry = LockEntry(
        source=config.source,
        skill=config.skill,
        ref=config.ref,
        commit=commit,
        upstream_path=str(upstream_dir.relative_to(repo_path)),
    )
    lock_entries[config.alias] = entry
    print(f"Updated {config.alias} from {config.source}@{commit[:12]}")
    return entry


def update_command(alias: str | None) -> int:
    manifest = read_manifest()
    lock_entries = read_lockfile()

    if alias is not None:
        validate_alias(alias)
        config = manifest.aliases.get(alias)
        if config is None:
            raise SkillAliasError(f"Alias not found in manifest: {alias}")
        selected = [config]
    else:
        selected = [manifest.aliases[key] for key in sorted(manifest.aliases)]

    for config in selected:
        update_alias(config, manifest, lock_entries)

    write_lockfile(lock_entries)
    if not selected:
        print("No skill aliases configured.")
    return 0


def prune_command() -> int:
    manifest = read_manifest()
    lock_entries = read_lockfile()
    stale_aliases = sorted(set(lock_entries) - set(manifest.aliases))

    for alias in stale_aliases:
        target = target_for_alias(alias)
        if target.exists():
            status = run(["git", "status", "--porcelain", "--", str(target)], cwd=REPO_ROOT)
            if status:
                raise SkillAliasError(
                    f"Refusing to prune target with uncommitted changes: {alias}\n{status}"
                )
            shutil.rmtree(target)
            print(f"Pruned {target.relative_to(REPO_ROOT)}")
        del lock_entries[alias]

    write_lockfile(lock_entries)
    if not stale_aliases:
        print("No stale skill aliases to prune.")
    return 0


def validate_command() -> int:
    manifest = read_manifest()
    lock_entries = read_lockfile()

    for alias in manifest.aliases:
        target_for_alias(alias)
        generated_skill_name(manifest.namespace, alias)

    for alias, entry in lock_entries.items():
        target_for_alias(alias)
        if alias in manifest.aliases:
            config = manifest.aliases[alias]
            mismatched = [
                field
                for field, expected, actual in [
                    ("source", config.source, entry.source),
                    ("skill", config.skill, entry.skill),
                    ("ref", config.ref, entry.ref),
                ]
                if expected != actual
            ]
            if mismatched:
                raise SkillAliasError(
                    f"lockfile alias {alias!r} differs from manifest field(s): "
                    + ", ".join(mismatched)
                )

    print(
        f"Validated {len(manifest.aliases)} alias manifest entr"
        f"{'y' if len(manifest.aliases) == 1 else 'ies'} "
        f"and {len(lock_entries)} lockfile entr"
        f"{'y' if len(lock_entries) == 1 else 'ies'}."
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser("update", help="vendor one or all aliases")
    update_parser.add_argument("alias", nargs="?", help="alias path relative to skills/")

    subparsers.add_parser("prune", help="remove locked aliases missing from the manifest")
    subparsers.add_parser("validate", help="validate alias manifest and lockfile")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "update":
            return update_command(args.alias)
        if args.command == "prune":
            return prune_command()
        if args.command == "validate":
            return validate_command()
    except SkillAliasError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1


if __name__ == "__main__":
    os.chdir(REPO_ROOT)
    raise SystemExit(main())
