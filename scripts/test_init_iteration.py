#!/usr/bin/env python3
"""Focused tests for eval iteration scaffolding."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import init_iteration


class InitIterationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = [
            {"id": 0, "name": "first"},
            {"id": 1, "name": "second"},
            {"id": 2, "name": "third"},
        ]

    def test_allocate_run_ports_is_unique_per_eval_and_configuration(self) -> None:
        allocations = init_iteration.allocate_run_ports(self.cases, 3500)

        self.assertEqual(
            allocations,
            {
                (0, "with_skill"): (3500, 3501),
                (0, "without_skill"): (3502, 3503),
                (1, "with_skill"): (3504, 3505),
                (1, "without_skill"): (3506, 3507),
                (2, "with_skill"): (3508, 3509),
                (2, "without_skill"): (3510, 3511),
            },
        )

    def test_prompt_for_run_replaces_shared_port_pair(self) -> None:
        prompt = "Review the PR. Ports 3432/3433 are free if you need servers."

        self.assertEqual(
            init_iteration.prompt_for_run(prompt, (3502, 3503)),
            "Review the PR. ports 3502/3503 are free if you need servers.",
        )

    def test_prompt_for_run_appends_ports_when_prompt_has_none(self) -> None:
        self.assertEqual(
            init_iteration.prompt_for_run("Review the PR.", (3500, 3501)),
            "Review the PR. Use ports 3500/3501 if you need to boot servers.",
        )

    def test_allocate_run_ports_rejects_overflow(self) -> None:
        with self.assertRaises(init_iteration.EvalInitError):
            init_iteration.allocate_run_ports(self.cases, 65530)

    def test_init_iteration_writes_distinct_run_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            skills_root = repo_root / "skills"
            evals_dir = skills_root / "programming" / "peer-review" / "evals"
            evals_dir.mkdir(parents=True)
            (evals_dir / "evals.json").write_text(
                json.dumps(
                    {
                        "port_start": 3500,
                        "evals": [
                            {
                                "id": 0,
                                "name": "focus-trap",
                                "prompt": "Review it; ports 3432/3433 are free.",
                                "assertions": [],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with (
                mock.patch.object(init_iteration, "REPO_ROOT", repo_root),
                mock.patch.object(init_iteration, "SKILLS_ROOT", skills_root),
            ):
                init_iteration.init_iteration("programming/peer-review", 3)

            iteration_dir = evals_dir / "iteration-3" / "focus-trap"
            with_skill = json.loads(
                (iteration_dir / "with_skill" / "run_metadata.json").read_text()
            )
            without_skill = json.loads(
                (iteration_dir / "without_skill" / "run_metadata.json").read_text()
            )

            self.assertEqual(with_skill["ports"], [3500, 3501])
            self.assertEqual(without_skill["ports"], [3502, 3503])
            self.assertIn("ports 3500/3501", with_skill["prompt"])
            self.assertIn("ports 3502/3503", without_skill["prompt"])


if __name__ == "__main__":
    unittest.main()
