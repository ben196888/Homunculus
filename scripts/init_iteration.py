#!/usr/bin/env python3
"""Lay out an eval iteration for a skill from its evals/evals.json.

Every iteration needs one eval_metadata.json per test case, and every field in it
already exists in evals.json. Generating them removes the drift that comes from
editing an assertion in one place and forgetting the other.

    pnpm eval-init programming/peer-review 2 --port-start 3500

Creates skills/<skill>/evals/iteration-<N>/<eval-name>/eval_metadata.json plus the
with_skill and without_skill output directories the grader and viewer expect. When a
port block is configured, each config also gets run_metadata.json with a unique prompt
and two-port pair. Existing metadata is overwritten so a change to evals.json
propagates; captured run outputs are left alone.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
CONFIGS = ("with_skill", "without_skill")
PORT_PAIR_PATTERN = re.compile(r"\bports?\s+\d+\s*/\s*\d+\b", re.IGNORECASE)


class EvalInitError(Exception):
    pass


def load_spec(evals_dir: Path) -> dict:
    spec_path = evals_dir / "evals.json"
    if not spec_path.is_file():
        raise EvalInitError(
            f"Missing {spec_path.relative_to(REPO_ROOT)}. A skill needs an evals/evals.json "
            "before an iteration can be laid out."
        )
    try:
        spec = json.loads(spec_path.read_text())
    except json.JSONDecodeError as exc:
        raise EvalInitError(f"{spec_path.relative_to(REPO_ROOT)} is not valid JSON: {exc}") from exc

    cases = spec.get("evals")
    if not cases:
        raise EvalInitError(f"{spec_path.relative_to(REPO_ROOT)} has no evals.")

    for index, case in enumerate(cases):
        missing = [field for field in ("id", "name", "prompt") if field not in case]
        if missing:
            raise EvalInitError(f"eval #{index} is missing {', '.join(missing)}.")
    return spec


def allocate_run_ports(cases: list[dict], port_start: int) -> dict[tuple[int, str], tuple[int, int]]:
    run_count = len(cases) * len(CONFIGS)
    port_end = port_start + run_count * 2 - 1
    if port_start < 1 or port_end > 65535:
        raise EvalInitError(
            f"Port block {port_start}-{port_end} is outside the valid range 1-65535."
        )

    allocations = {}
    for case_index, case in enumerate(cases):
        for config_index, config in enumerate(CONFIGS):
            offset = (case_index * len(CONFIGS) + config_index) * 2
            allocations[(case["id"], config)] = (port_start + offset, port_start + offset + 1)
    return allocations


def prompt_for_run(prompt: str, ports: tuple[int, int]) -> str:
    replacement = f"ports {ports[0]}/{ports[1]}"
    if PORT_PAIR_PATTERN.search(prompt):
        return PORT_PAIR_PATTERN.sub(replacement, prompt)
    return f"{prompt.rstrip()} Use {replacement} if you need to boot servers."


def init_iteration(skill: str, iteration: int, port_start: int | None = None) -> int:
    evals_dir = SKILLS_ROOT / skill / "evals"
    spec = load_spec(evals_dir)
    target = evals_dir / f"iteration-{iteration}"
    effective_port_start = port_start if port_start is not None else spec.get("port_start")
    allocations = (
        allocate_run_ports(spec["evals"], effective_port_start)
        if effective_port_start is not None
        else {}
    )

    for case in spec["evals"]:
        case_dir = target / case["name"]
        for config in CONFIGS:
            config_dir = case_dir / config
            (config_dir / "outputs").mkdir(parents=True, exist_ok=True)
            if allocations:
                ports = allocations[(case["id"], config)]
                (config_dir / "run_metadata.json").write_text(
                    json.dumps(
                        {
                            "eval_id": case["id"],
                            "eval_name": case["name"],
                            "configuration": config,
                            "prompt": prompt_for_run(case["prompt"], ports),
                            "ports": list(ports),
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        (case_dir / "eval_metadata.json").write_text(
            json.dumps(
                {
                    "eval_id": case["id"],
                    "eval_name": case["name"],
                    "prompt": case["prompt"],
                    "assertions": case.get("assertions", []),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )
        print(f"{case['name']}: {len(case.get('assertions', []))} assertions")

    if allocations:
        print(
            f"Allocated unique per-run ports "
            f"{effective_port_start}-{effective_port_start + len(allocations) * 2 - 1}"
        )
    print(f"\n{target.relative_to(REPO_ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", help="skill path relative to skills/, e.g. programming/peer-review")
    parser.add_argument("iteration", type=int, help="iteration number")
    parser.add_argument(
        "--port-start",
        type=int,
        help="first port in a unique two-port block allocated per (eval, configuration)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return init_iteration(args.skill, args.iteration, args.port_start)
    except EvalInitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
