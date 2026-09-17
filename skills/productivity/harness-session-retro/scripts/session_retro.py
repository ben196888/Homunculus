#!/usr/bin/env python3
"""Build a privacy-preserving skill-maintenance report from Codex sessions."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = 1
SESSION_ID_RE = re.compile(r"([0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", re.I)
CORRECTION_RE = re.compile(
    r"\b(?:wrong|incorrect|you missed|not what I|lost the|regression|rework|"
    r"redo that|fix (?:that|this|the (?:report|result|skill|output)))\b",
    re.I,
)
MR_RE = re.compile(r"https?://[^\s)]+?/-/merge_requests/\d+", re.I)
JIRA_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")


@dataclass(frozen=True)
class WorkflowRule:
    key: str
    label: str
    pattern: str
    candidate: str
    primitive: str
    existing_terms: tuple[str, ...] = ()


WORKFLOW_RULES = (
    WorkflowRule(
        "mr_review",
        "Direct merge-request review",
        r"programming(?::|-)code-review|\breview (?:gitlab )?(?:mr|merge request)|"
        r"\breview !\d|\bvalidate (?:codebuddy|booking mr comment)|\bcompare mr",
        "Evidence-first merge-request review",
        "skill",
        ("code-review", "peer-review"),
    ),
    WorkflowRule(
        "mr_follow_through",
        "MR follow-through and CI recovery",
        r"(?:mr-assist|mr-babysit|mr-steward|resolve-review-thread)|\bpipeline\b|"
        r"failed ci|ci job|merge train|merge conflict|branch conflict|\brebase\b|"
        r"review threads|merge request status|continue .*merge request",
        "Merge-request steward and CI recovery",
        "stateful agent",
        ("mr-steward",),
    ),
    WorkflowRule(
        "ticket_delivery",
        "Ticket planning and implementation",
        r"implement\s+\[?(?:plan|PLAN)\.md|implement.*\bplan\b|"
        r"draft.*(?:implementation )?plan|draft .*solution|"
        r"create a new branch and MR|raise merge request|ticket-to-mr",
        "Ticket-to-MR delivery",
        "stateful agent",
        ("development-workflow",),
    ),
    WorkflowRule(
        "testing",
        "Tests, coverage, verification, or flakiness",
        r"\btests?\b|\bcoverage\b|\bflaky|flakiness|verification matrix",
        "Change-aware verification matrix",
        "stop hook plus skill",
        ("change-detection",),
    ),
    WorkflowRule(
        "investigation",
        "Investigation and cross-repository tracing",
        r"^(?:Investigate|Explore|Locate|Find|Inspect|Recap)\b|"
        r"\bexplore how\b|\btrace back\b|\btrace .* flow\b|"
        r"cross[- ]repositor|across .* repositor",
        "Cross-repository investigator",
        "skill",
    ),
    WorkflowRule(
        "skill_engineering",
        "Skill engineering and evaluation",
        r"(?:create|update|optimise|optimize|simplify|shorten|debug|fix|reorg).*skill|"
        r"skill.*(?:benchmark|eval|improv|conversion)|benchmark peer review|"
        r"reorg skills|session retro",
        "Skill maintainer and regression harness",
        "skill plus evaluator",
        ("session-retro",),
    ),
    WorkflowRule(
        "experiment_rollout",
        "Experiment or feature-flag rollout",
        r"\bexperiment\b|\bA[- ]side\b|\bB[- ]side\b|feature flag|Calculon|"
        r"allocation boolean|rollout safety",
        "Experiment rollout auditor",
        "skill plus stop hook",
    ),
    WorkflowRule(
        "worktree_routing",
        "Worktree and repository routing",
        r"manage-worktrees|worktree-manager|\bcreate worktree\b|"
        r"\bManage ws\b|\bManage repo\b|architecture(?::|-)add-repo",
        "Worktree and repository router",
        "router skill",
        ("wt-add", "wt-find", "wt-drop"),
    ),
    WorkflowRule(
        "slack_triage",
        "Slack and incident triage",
        r"slack\.com/archives|\bincident\b|\bon-call\b|\btriage\b",
        "Incident-to-runbook workflow",
        "stateful agent",
    ),
    WorkflowRule(
        "jira_grooming",
        "Jira grooming and backlog audit",
        r"Jira tickets before grooming|Review .* backlog|"
        r"(?:backlog|upcoming sprint).*(?:estimate|acceptance criteria|epic owner)|"
        r"(?:estimate|acceptance criteria|epic owner).*(?:backlog|upcoming sprint)",
        "Jira grooming auditor",
        "skill or automation",
    ),
)


@dataclass
class SkillInfo:
    name: str
    relative_path: str
    file: Path
    description: str
    content: str
    introduced_at: str | None = None


def load_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    try:
        handle = path.open(encoding="utf-8")
    except OSError:
        return
    with handle:
        for line in handle:
            try:
                item = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(item, dict):
                yield item


def text_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(
            part.get("text", "")
            for part in value
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return ""


def clean_prompt(text: str) -> str:
    text = text.strip()
    injected_prefixes = (
        "<recommended_plugins>",
        "<environment_context>",
        "<app-context>",
        "<permissions instructions>",
        "<skill>",
    )
    return "" if text.startswith(injected_prefixes) else text


def injected_skill_name(text: str) -> str | None:
    if not text.lstrip().startswith("<skill>"):
        return None
    match = re.search(r"<name>\s*([^<]+?)\s*</name>", text, flags=re.I)
    return match.group(1).strip() if match else None


def build_file_index(codex_dir: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for root_name in ("sessions", "archived_sessions"):
        root = codex_dir / root_name
        if not root.exists():
            continue
        for path in root.rglob("rollout-*.jsonl"):
            match = SESSION_ID_RE.search(path.name)
            if not match:
                continue
            session_id = match.group(1)
            previous = files.get(session_id)
            if previous is None or path.stat().st_mtime > previous.stat().st_mtime:
                files[session_id] = path
    return files


def load_index(codex_dir: Path, file_index: dict[str, Path]) -> list[dict[str, Any]]:
    index_path = codex_dir / "session_index.jsonl"
    unique: dict[str, dict[str, Any]] = {}
    if index_path.exists():
        for entry in load_jsonl(index_path):
            session_id = entry.get("id")
            if not isinstance(session_id, str):
                continue
            previous = unique.get(session_id)
            if previous is None or str(entry.get("updated_at", "")) > str(previous.get("updated_at", "")):
                unique[session_id] = entry
    for session_id, path in file_index.items():
        if session_id not in unique:
            unique[session_id] = {
                "id": session_id,
                "thread_name": "untitled session",
                "updated_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            }
    return sorted(unique.values(), key=lambda item: str(item.get("updated_at", "")), reverse=True)


def load_spawn_edges(codex_dir: Path) -> tuple[dict[str, str], list[str]]:
    edges: dict[str, str] = {}
    databases: list[str] = []
    candidates = (codex_dir / "state_5.sqlite", codex_dir / "sqlite" / "state_5.sqlite")
    for database in candidates:
        if not database.exists():
            continue
        try:
            with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
                rows = connection.execute(
                    "SELECT parent_thread_id, child_thread_id FROM thread_spawn_edges"
                )
                for parent_id, child_id in rows:
                    edges[str(child_id)] = str(parent_id)
            databases.append(str(database))
        except (sqlite3.Error, OSError):
            continue
    return edges, databases


def parse_session(path: Path) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    event_prompts: list[str] = []
    fallback_prompts: list[str] = []
    event_injections: list[str] = []
    fallback_injections: list[str] = []
    event_timeline: list[dict[str, str]] = []
    fallback_timeline: list[dict[str, str]] = []
    event_user_seen = False
    final_messages: list[str] = []
    tools: Counter[str] = Counter()
    tool_inputs: list[str] = []

    def add_user_record(
        target_prompts: list[str],
        target_injections: list[str],
        target_timeline: list[dict[str, str]],
        value: str,
    ) -> None:
        injection = injected_skill_name(value)
        if injection:
            target_injections.append(injection)
            target_timeline.append({"kind": "skill_injection", "text": injection})
            return
        value = clean_prompt(value)
        if value and value not in target_prompts:
            target_prompts.append(value)
            target_timeline.append({"kind": "prompt", "text": value})

    for record in load_jsonl(path):
        record_type = record.get("type")
        payload = record.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        payload_type = payload.get("type")
        if record_type == "session_meta":
            metadata = payload
        elif record_type == "event_msg" and payload_type == "user_message":
            event_user_seen = True
            add_user_record(
                event_prompts,
                event_injections,
                event_timeline,
                text_value(payload.get("message")),
            )
        elif (
            record_type == "response_item"
            and payload_type == "message"
            and payload.get("role") == "user"
        ):
            add_user_record(
                fallback_prompts,
                fallback_injections,
                fallback_timeline,
                text_value(payload.get("content")),
            )
        elif record_type == "event_msg" and payload_type == "agent_message":
            if payload.get("phase") == "final_answer":
                message = text_value(payload.get("message")).strip()
                if message:
                    final_messages.append(message)
        elif record_type == "response_item" and payload_type in {
            "function_call",
            "custom_tool_call",
            "tool_call",
        }:
            name = str(payload.get("name") or "unknown")
            raw_input = payload.get("arguments", payload.get("input", ""))
            if not isinstance(raw_input, str):
                raw_input = json.dumps(raw_input, ensure_ascii=False)
            tools[name] += 1
            for nested_name in re.findall(r"\btools\.([A-Za-z0-9_]+)\s*\(", raw_input):
                tools[nested_name] += 1
            tool_inputs.append(raw_input)

    prompts = event_prompts if event_user_seen else fallback_prompts
    injections = event_injections if event_user_seen else fallback_injections
    timeline = event_timeline if event_user_seen else fallback_timeline
    # Tool calls are kept as a separate use signal. Their exact interleaving is
    # not reconstructed because session formats differ across Codex versions.

    return {
        "originator": metadata.get("originator"),
        "source": metadata.get("source"),
        "cwd": metadata.get("cwd"),
        "prompts": prompts,
        "skill_injections": injections,
        "timeline": timeline,
        "final_messages": final_messages,
        "tools": dict(tools),
        "tool_inputs": tool_inputs,
    }


def parse_frontmatter(skill_file: Path) -> tuple[str | None, str]:
    content = skill_file.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, ""
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values.get("name"), values.get("description", "")


def git_introduced_at(repo: Path, skill_file: Path) -> str | None:
    try:
        relative = skill_file.relative_to(repo)
        result = subprocess.run(
            ["git", "log", "--follow", "--format=%cI", "--", str(relative)],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None
    dates = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return dates[-1] if dates else None


def load_skills(repo: Path) -> list[SkillInfo]:
    skills_root = repo / "skills"
    result: list[SkillInfo] = []
    if not skills_root.exists():
        return result
    for skill_file in sorted(skills_root.glob("**/SKILL.md")):
        name, description = parse_frontmatter(skill_file)
        if not name:
            continue
        relative_path = str(skill_file.parent.relative_to(skills_root))
        result.append(
            SkillInfo(
                name=name,
                relative_path=relative_path,
                file=skill_file,
                description=description,
                content=skill_file.read_text(encoding="utf-8"),
                introduced_at=git_introduced_at(repo, skill_file),
            )
        )
    return result


def normalize_skill_token(value: str) -> str:
    value = value.lower().strip().replace("_", "-")
    value = re.sub(r"[:/\\]+", "-", value)
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    return re.sub(r"-+", "-", value).strip("-")


def skill_aliases(skills: list[SkillInfo]) -> dict[str, set[str]]:
    basenames = Counter(skill.relative_path.rsplit("/", 1)[-1] for skill in skills)
    aliases: dict[str, set[str]] = {}
    for skill in skills:
        canonical = normalize_skill_token(skill.name)
        relative = normalize_skill_token(skill.relative_path)
        values = {canonical, relative}
        if canonical.startswith("homunculus-"):
            values.add(canonical.removeprefix("homunculus-"))
        basename = skill.relative_path.rsplit("/", 1)[-1]
        if basenames[basename] == 1:
            values.add(normalize_skill_token(basename))
        aliases[skill.name] = values
    return aliases


def referenced_tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for pattern in (
        r"\[\$([^\]]+)\]",
        r"(?<![\w[])\$([a-zA-Z0-9][a-zA-Z0-9_:/.-]+)",
        r"(?:^|[/\\])skills[/\\]([^\s\"')]+?)[/\\]SKILL\.md",
    ):
        for value in re.findall(pattern, text, flags=re.I | re.M):
            tokens.add(normalize_skill_token(value))
    return tokens


def text_mentions_skill(text: str, skill: SkillInfo, aliases: set[str]) -> bool:
    lowered = text.lower()
    if re.search(rf"(?<![a-z0-9-]){re.escape(skill.name.lower())}(?![a-z0-9-])", lowered):
        return True
    tokens = referenced_tokens(text)
    return bool(tokens & aliases)


def instruction_loads_skill(text: str, skill: SkillInfo, aliases: set[str]) -> bool:
    if "skill.md" not in text.lower():
        return False
    if skill.name.lower() in text.lower():
        return True
    return bool(referenced_tokens(text) & aliases)


def injection_matches_skill(value: str, aliases: set[str]) -> bool:
    return normalize_skill_token(value) in aliases


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def session_kind(session: dict[str, Any]) -> str:
    originator = str(session.get("originator") or "").lower()
    source = str(session.get("source") or "").lower()
    first_prompt = (session.get("prompts") or [""])[0]
    title = str(session.get("title") or "").lower()
    if "claude code" in originator:
        return "stop_gate"
    if session.get("is_spawned_child"):
        return "spawned_child"
    if (
        first_prompt.startswith("Automation:")
        or title.startswith(("scheduled ", "automation:"))
        or "automation" in source
        or "cron" in source
    ):
        return "automation"
    return "primary"


def collect_sessions(
    codex_dir: Path,
    limit: int,
    exclude_ids: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    file_index = build_file_index(codex_dir)
    entries = [entry for entry in load_index(codex_dir, file_index) if entry.get("id") not in exclude_ids]
    selected = entries[:limit]
    spawn_edges, state_databases = load_spawn_edges(codex_dir)
    sessions: list[dict[str, Any]] = []
    missing: list[str] = []
    for rank, entry in enumerate(selected, 1):
        session_id = str(entry.get("id"))
        path = file_index.get(session_id)
        if path is None:
            missing.append(session_id)
            continue
        parsed = parse_session(path)
        session = {
            "rank": rank,
            "id": session_id,
            "title": entry.get("thread_name") or entry.get("title") or "untitled session",
            "updated_at": entry.get("updated_at"),
            "parent_id": spawn_edges.get(session_id),
            "is_spawned_child": session_id in spawn_edges,
            **parsed,
        }
        session["kind"] = session_kind(session)
        sessions.append(session)
    coverage = {
        "requested": limit,
        "selected": len(selected),
        "parsed": len(sessions),
        "missing": len(missing),
        "newest": selected[0].get("updated_at") if selected else None,
        "oldest": selected[-1].get("updated_at") if selected else None,
        "spawn_state_available": bool(state_databases),
    }
    return sessions, coverage


def sample_titles(sessions: list[dict[str, Any]], maximum: int) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for session in sessions:
        title = str(session.get("title") or "untitled session")
        if title not in seen:
            result.append(title)
            seen.add(title)
        if len(result) >= maximum:
            break
    return result


def analyze(
    codex_dir: Path,
    repo: Path,
    limit: int = 400,
    exclude_ids: set[str] | None = None,
    min_sessions: int = 3,
    min_retirement_exposure: int = 50,
    max_samples: int = 3,
) -> dict[str, Any]:
    sessions, coverage = collect_sessions(codex_dir, limit, exclude_ids or set())
    primary = [session for session in sessions if session["kind"] == "primary"]
    skills = load_skills(repo)
    aliases = skill_aliases(skills)
    population = dict(Counter(session["kind"] for session in sessions))
    population = {kind: population.get(kind, 0) for kind in ("stop_gate", "spawned_child", "automation", "primary")}

    workflow_signals: list[dict[str, Any]] = []
    for rule in WORKFLOW_RULES:
        pattern = re.compile(rule.pattern, re.I)
        matched = [
            session
            for session in primary
            if pattern.search("\n".join([str(session.get("title") or ""), *(session.get("prompts") or [])]))
        ]
        matched.sort(key=lambda session: not bool(pattern.search(str(session.get("title") or ""))))
        existing = sorted(
            skill.name
            for skill in skills
            if any(term in skill.name.lower() for term in rule.existing_terms)
        )
        workflow_signals.append(
            {
                "key": rule.key,
                "label": rule.label,
                "count": len(matched),
                "samples": sample_titles(matched, max_samples),
                "candidate": rule.candidate,
                "primitive": rule.primitive,
                "existing_skills": existing,
                "action_signal": "improve-or-compose" if existing else "create",
            }
        )

    skill_signals: list[dict[str, Any]] = []
    for skill in skills:
        prompt_sessions = [
            session
            for session in sessions
            if any(text_mentions_skill(prompt, skill, aliases[skill.name]) for prompt in session["prompts"])
        ]
        load_sessions = [
            session
            for session in sessions
            if any(instruction_loads_skill(value, skill, aliases[skill.name]) for value in session["tool_inputs"])
        ]
        injection_sessions = [
            session
            for session in sessions
            if any(injection_matches_skill(value, aliases[skill.name]) for value in session["skill_injections"])
        ]
        observed_by_id = {
            session["id"]: session
            for session in [*prompt_sessions, *injection_sessions, *load_sessions]
        }
        observed = list(observed_by_id.values())

        def has_correction_after_use(session: dict[str, Any]) -> bool:
            timeline = session["timeline"]
            for index, event in enumerate(timeline):
                used = (
                    event["kind"] == "skill_injection"
                    and injection_matches_skill(event["text"], aliases[skill.name])
                ) or (
                    event["kind"] == "prompt"
                    and text_mentions_skill(event["text"], skill, aliases[skill.name])
                )
                if not used:
                    continue
                following = next(
                    (item["text"] for item in timeline[index + 1 :] if item["kind"] == "prompt"),
                    None,
                )
                if following and CORRECTION_RE.search(following):
                    return True
            return False

        correction_sessions = [session for session in observed if has_correction_after_use(session)]
        dependants = sorted(
            other.name
            for other in skills
            if other.name != skill.name
            and (
                skill.name.lower() in other.content.lower()
                or skill.relative_path.lower() in other.content.lower()
            )
        )
        introduced = parse_time(skill.introduced_at)
        exposure = sum(
            1
            for session in primary
            if introduced is not None
            and (session_time := parse_time(session.get("updated_at"))) is not None
            and session_time >= introduced
        )
        last_observed = max((str(session.get("updated_at") or "") for session in observed), default=None)
        retirement_review = (
            not observed
            and not dependants
            and introduced is not None
            and exposure >= min_retirement_exposure
        )
        skill_signals.append(
            {
                "name": skill.name,
                "path": f"skills/{skill.relative_path}/SKILL.md",
                "prompt_mentions": len({session["id"] for session in prompt_sessions}),
                "harness_injections": len({session["id"] for session in injection_sessions}),
                "instruction_loads": len({session["id"] for session in load_sessions}),
                "observed_sessions": len(observed),
                "correction_signals": len(correction_sessions),
                "last_observed": last_observed,
                "introduced_at": skill.introduced_at,
                "eligible_primary_exposure": exposure,
                "dependants": dependants,
                "samples": sample_titles(observed, max_samples),
                "retirement_review": retirement_review,
            }
        )

    all_primary_text = ["\n".join(session.get("prompts") or []) for session in primary]
    mr_counts = Counter(match.group(0).rstrip(".,") for text in all_primary_text for match in MR_RE.finditer(text))
    jira_counts = Counter(ticket for text in all_primary_text for ticket in set(JIRA_RE.findall(text)))
    stop_gate = [session for session in sessions if session["kind"] == "stop_gate"]
    artifacts = {
        "sessions_with_gitlab_mr": sum(bool(MR_RE.search(text)) for text in all_primary_text),
        "distinct_gitlab_mrs": len(mr_counts),
        "sessions_with_slack_link": sum("slack.com/archives" in text.lower() for text in all_primary_text),
        "distinct_jira_tickets": len(jira_counts),
        "stop_gate_without_tool_calls": sum(not sum(session["tools"].values()) for session in stop_gate),
    }

    create_or_extend = [signal for signal in workflow_signals if signal["count"] >= min_sessions]
    improve = [signal for signal in skill_signals if signal["observed_sessions"] > 0]
    retirement = [signal for signal in skill_signals if signal["retirement_review"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "coverage": coverage,
        "population": population,
        "artifact_signals": artifacts,
        "workflow_signals": workflow_signals,
        "skill_signals": skill_signals,
        "action_signals": {
            "create_or_extend": create_or_extend,
            "improve_or_keep": improve,
            "retirement_review": retirement,
        },
        "privacy": {
            "raw_prompts_persisted": False,
            "transcripts_persisted": False,
            "session_titles_persisted": True,
        },
    }


def cell(value: Any) -> str:
    if value is None or value == "":
        return "—"
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value) or "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_report(data: dict[str, Any]) -> str:
    coverage = data["coverage"]
    population = data["population"]
    lines = [
        "# Harness session retrospective evidence",
        "",
        "This deterministic evidence report is an input to a human or agent decision. Counts in the workflow table overlap.",
        "",
        "## Coverage",
        "",
        f"- Requested: {coverage['requested']} recent completed sessions",
        f"- Selected / parsed / missing: {coverage['selected']} / {coverage['parsed']} / {coverage['missing']}",
        f"- Window: {cell(coverage['oldest'])} to {cell(coverage['newest'])}",
        f"- Spawn-edge state available: {'yes' if coverage['spawn_state_available'] else 'no'}",
        "- Privacy: raw prompts and transcripts were analyzed in memory but were not persisted",
        "",
        "## Session population",
        "",
        "| Population | Sessions |",
        "| --- | ---: |",
        f"| Stop-gate runs | {population['stop_gate']} |",
        f"| Spawned or delegated children | {population['spawned_child']} |",
        f"| Scheduled automations | {population['automation']} |",
        f"| Primary user-led sessions | {population['primary']} |",
        "",
        "## Repeated workflow signals",
        "",
        "| Workflow | Primary sessions | Candidate | Primitive | Current overlap | Representative task titles |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for signal in data["workflow_signals"]:
        lines.append(
            "| " + " | ".join(
                cell(value)
                for value in (
                    signal["label"],
                    signal["count"],
                    signal["candidate"],
                    signal["primitive"],
                    signal["existing_skills"],
                    signal["samples"],
                )
            ) + " |"
        )

    lines.extend(
        [
            "",
            "## Current skill evidence",
            "",
            "| Skill | Prompt mentions | Harness injections | Instruction loads | Correction signals | Last observed | Eligible exposure | Dependants |",
            "| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |",
        ]
    )
    for signal in sorted(data["skill_signals"], key=lambda item: (-item["observed_sessions"], item["name"])):
        lines.append(
            "| " + " | ".join(
                cell(value)
                for value in (
                    signal["name"],
                    signal["prompt_mentions"],
                    signal["harness_injections"],
                    signal["instruction_loads"],
                    signal["correction_signals"],
                    signal["last_observed"],
                    signal["eligible_primary_exposure"],
                    signal["dependants"],
                )
            ) + " |"
        )

    lines.extend(["", "## Action signals", "", "### Create or extend"])
    candidates = data["action_signals"]["create_or_extend"]
    if candidates:
        for signal in candidates:
            lines.append(
                f"- **{signal['candidate']}** — {signal['action_signal']}; "
                f"{signal['count']} matching primary sessions; overlap: {cell(signal['existing_skills'])}."
            )
    else:
        lines.append("- No repeated workflow crossed the configured minimum-session threshold.")

    lines.extend(["", "### Improve or keep"])
    observed = data["action_signals"]["improve_or_keep"]
    if observed:
        for signal in sorted(observed, key=lambda item: (-item["correction_signals"], -item["observed_sessions"], item["name"])):
            disposition = "inspect correction evidence" if signal["correction_signals"] else "benchmark before changing"
            lines.append(
                f"- **{signal['name']}** — {signal['observed_sessions']} observed sessions, "
                f"{signal['correction_signals']} correction signals; {disposition}."
            )
    else:
        lines.append("- No current skill use was directly observable in this window.")

    lines.extend(["", "### Retirement review"])
    retirement = data["action_signals"]["retirement_review"]
    if retirement:
        for signal in retirement:
            lines.append(
                f"- **{signal['name']}** — no observed prompt mention, harness injection, or instruction load across "
                f"{signal['eligible_primary_exposure']} eligible primary sessions and no current dependant. "
                "Verify implicit and low-frequency value before merge or retirement."
            )
    else:
        lines.append("- No skill met the conservative retirement-review threshold.")

    artifacts = data["artifact_signals"]
    lines.extend(
        [
            "",
            "## Artifact signals",
            "",
            f"- Sessions with a GitLab MR URL: {artifacts['sessions_with_gitlab_mr']}",
            f"- Distinct GitLab MR URLs: {artifacts['distinct_gitlab_mrs']}",
            f"- Sessions with a Slack link: {artifacts['sessions_with_slack_link']}",
            f"- Distinct Jira ticket keys: {artifacts['distinct_jira_tickets']}",
            f"- Stop-gate runs with no tool call: {artifacts['stop_gate_without_tool_calls']}",
            "",
            "## Interpretation limits",
            "",
            "- Prompt mentions, harness injections, and instruction loads are observable signals, not complete skill invocation telemetry.",
            "- Workflow categories overlap and use deliberately broad regular expressions; inspect representative sessions before acting.",
            "- A retirement-review signal is not authorization to delete a skill.",
            "",
        ]
    )
    return "\n".join(lines)


def write_output(path_value: str | None, content: str) -> None:
    if not path_value or path_value == "-":
        print(content)
        return
    path = Path(path_value).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="repository containing skills/")
    parser.add_argument(
        "--codex-dir",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser(),
    )
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--min-sessions", type=int, default=3)
    parser.add_argument("--min-retirement-exposure", type=int, default=50)
    parser.add_argument("--max-samples", type=int, default=3)
    parser.add_argument("--exclude-session", action="append", default=[])
    parser.add_argument("--report", default="-", help="Markdown output path, or - for stdout")
    parser.add_argument("--json", dest="json_path", help="optional aggregate JSON output path")
    args = parser.parse_args()

    if args.limit < 1 or args.min_sessions < 1 or args.min_retirement_exposure < 1:
        parser.error("limits and thresholds must be positive")
    codex_dir = args.codex_dir.expanduser().resolve()
    repo = args.repo.expanduser().resolve()
    if not codex_dir.exists():
        parser.error(f"Codex directory does not exist: {codex_dir}")
    if not (repo / "skills").is_dir():
        parser.error(f"skill repository has no skills/ directory: {repo}")

    exclude_ids = set(args.exclude_session)
    for key in ("CODEX_SESSION_ID", "CODEX_THREAD_ID"):
        if value := os.environ.get(key):
            exclude_ids.add(value)
    data = analyze(
        codex_dir=codex_dir,
        repo=repo,
        limit=args.limit,
        exclude_ids=exclude_ids,
        min_sessions=args.min_sessions,
        min_retirement_exposure=args.min_retirement_exposure,
        max_samples=args.max_samples,
    )
    write_output(args.report, render_report(data))
    if args.json_path:
        write_output(args.json_path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    if data["coverage"]["parsed"] == 0:
        print("No session records were parsed.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
