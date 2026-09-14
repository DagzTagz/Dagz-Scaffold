#!/usr/bin/env python3
"""Stdlib self-test for harness/score.py. No pytest. No network."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parent
sys.path.insert(0, str(HARNESS_DIR))

import score  # noqa: E402

SCHEMA = score.load_schema(HARNESS_DIR / "schema" / "run.schema.json")
EXAMPLES = REPO_ROOT / "examples"
SAMPLE = EXAMPLES / "sample-run"


def _patch_score(run_dir: Path, **updates: object) -> None:
    path = run_dir / "score.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data.update(updates)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _copy_sample(tmp: Path) -> Path:
    run_dir = tmp / "run"
    shutil.copytree(SAMPLE, run_dir)
    return run_dir


def _too_hard_evidence_tree(tmp: Path) -> Path:
    run_dir = _copy_sample(tmp)
    evidence = (run_dir / "evidence.md").read_text(encoding="utf-8")
    (run_dir / "evidence.md").write_text(
        evidence + "\n\nThe conversion was too hard to finish properly.\n",
        encoding="utf-8",
    )
    _patch_score(run_dir, quit_early=False)
    return run_dir


class ScoreFixtures(unittest.TestCase):
    def test_sample_run_ok(self) -> None:
        result = score.score_run(SAMPLE, SCHEMA)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["fail_reasons"], [])
        self.assertEqual(result["scans"]["quit_early"]["evidence"], [])
        self.assertFalse(result["score"]["notes"].startswith("Synthetic dry-run"))

    def test_fail_quit_early(self) -> None:
        result = score.score_run(EXAMPLES / "fail-quit-early", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["quit_early"])

    def test_fail_missing_evidence(self) -> None:
        result = score.score_run(EXAMPLES / "fail-missing-evidence", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(
            result["fail_reasons"],
            ["missing_evidence", "evidence_has_no_commands"],
        )

    def test_fail_reject(self) -> None:
        result = score.score_run(EXAMPLES / "fail-reject", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["REJECT"])

    def test_session_dump_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp) / "session"
            dump.mkdir()
            (dump / "transcript.txt").write_text("not a persist folder\n", encoding="utf-8")
            with self.assertRaises(score.ScoreError) as ctx:
                score.score_run(dump, SCHEMA)
            self.assertIn("missing artifacts", str(ctx.exception))

    def test_python3_line_counts_as_command(self) -> None:
        self.assertTrue(score.evidence_has_commands("python3 -c 'print(1)'\n"))
        self.assertTrue(score.evidence_has_commands("python -c 'print(1)'\n"))
        self.assertFalse(score.evidence_has_commands("python3.12 -c 'print(1)'\n"))
        self.assertFalse(score.evidence_has_commands("tests passed, no commands\n"))

    def test_plan_too_hard_does_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            plan = (run_dir / "plan.md").read_text(encoding="utf-8")
            (run_dir / "plan.md").write_text(
                plan + "\n\nCalling this too hard is a checklist item.\n",
                encoding="utf-8",
            )
            critic = (run_dir / "critic.md").read_text(encoding="utf-8")
            (run_dir / "critic.md").write_text(
                critic.replace(
                    "## NITS",
                    "- Plan lists too hard as a quit-early condition.\n\n## NITS",
                ),
                encoding="utf-8",
            )
            result = score.score_run(run_dir, SCHEMA)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["fail_reasons"], [])
            self.assertTrue(result["scans"]["quit_early"]["plan"])
            self.assertTrue(result["scans"]["quit_early"]["critic"])
            self.assertEqual(result["scans"]["quit_early"]["evidence"], [])

    def test_evidence_too_hard_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = score.score_run(_too_hard_evidence_tree(Path(tmp)), SCHEMA)
            self.assertFalse(result["ok"], result)
            self.assertIn("quit_early", result["fail_reasons"])
            self.assertTrue(result["score"]["quit_early"])
            self.assertTrue(result["scans"]["quit_early"]["evidence"])

    def test_json_cannot_override_evidence_hit(self) -> None:
        self.test_evidence_too_hard_fails()

    def test_json_self_report_quit_early(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            _patch_score(run_dir, quit_early=True)
            result = score.score_run(run_dir, SCHEMA)
            self.assertFalse(result["ok"], result)
            self.assertIn("quit_early", result["fail_reasons"])
            self.assertEqual(result["scans"]["quit_early"]["evidence"], [])

    def test_dry_run_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            evidence = (run_dir / "evidence.md").read_text(encoding="utf-8")
            (run_dir / "evidence.md").write_text(
                "DRY-RUN MOCK — not a live persist.\n" + evidence,
                encoding="utf-8",
            )
            result = score.score_run(run_dir, SCHEMA)
            self.assertFalse(result["ok"], result)
            self.assertIn("dry_run", result["fail_reasons"])


if __name__ == "__main__":
    unittest.main()
