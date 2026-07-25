#!/usr/bin/env python3
"""Lay out an eval iteration for a skill from its evals/evals.json.

Every iteration needs one eval_metadata.json per test case, and every field in it
already exists in evals.json. Generating them removes the drift that comes from
editing an assertion in one place and forgetting the other.

    pnpm eval-init programming/peer-review 2

Creates skills/<skill>/evals/iteration-<N>/<eval-name>/eval_metadata.json plus the
with_skill and without_skill output directories the grader and viewer expect. Existing
metadata is overwritten so a change to evals.json propagates; captured run outputs are
left alone.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = REPO_ROOT / "skills"
CONFIGS = ("with_skill", "without_skill")


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


def init_iteration(skill: str, iteration: int) -> int:
    evals_dir = SKILLS_ROOT / skill / "evals"
    spec = load_spec(evals_dir)
    target = evals_dir / f"iteration-{iteration}"

    for case in spec["evals"]:
        case_dir = target / case["name"]
        for config in CONFIGS:
            (case_dir / config / "outputs").mkdir(parents=True, exist_ok=True)
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

    print(f"\n{target.relative_to(REPO_ROOT)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill", help="skill path relative to skills/, e.g. programming/peer-review")
    parser.add_argument("iteration", type=int, help="iteration number")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return init_iteration(args.skill, args.iteration)
    except EvalInitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
