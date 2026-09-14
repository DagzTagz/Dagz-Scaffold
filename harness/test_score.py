#!/usr/bin/env python3
"""Stdlib tests SuperGrok named for the scorer + critic skill."""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCORE = ROOT / "harness" / "score.py"
CRITIC_SKILL = ROOT / ".grok" / "skills" / "critic" / "SKILL.md"
HEADINGS = (
    "BLOCKERS",
    "RISKS",
    "NITS",
    "MISSING EVIDENCE",
    "VERDICT",
)


def _score(folder: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCORE), str(ROOT / "examples" / folder)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


class TestScoreFixtures(unittest.TestCase):
    def test_sample_run_exits_0(self) -> None:
        completed = _score("sample-run")
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_quit_early_run_exits_1(self) -> None:
        completed = _score("quit-early-run")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("quit_early", completed.stdout)

    def test_reject_run_exits_1(self) -> None:
        completed = _score("reject-run")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("REJECT", completed.stdout)

    def test_fake_green_run_exits_1(self) -> None:
        completed = _score("fake-green-run")
        self.assertEqual(completed.returncode, 1, completed.stderr)
        self.assertIn("required_verification", completed.stdout)


class TestCriticSkill(unittest.TestCase):
    def test_frontmatter_and_headings_are_instructions(self) -> None:
        text = CRITIC_SKILL.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"), "missing YAML frontmatter")
        self.assertIn("name: critic", text)
        self.assertIn("/critic", text)
        for heading in HEADINGS:
            self.assertIn(f"## {heading}", text)
        sample = (ROOT / "examples" / "sample-run" / "critic.md").read_text(
            encoding="utf-8"
        )
        self.assertNotEqual(text.strip(), sample.strip())
        self.assertIn("Never invent a user override", text)


if __name__ == "__main__":
    unittest.main()
