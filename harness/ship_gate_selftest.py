"""Ship-gate tests. Imported from score_selftest.py. No pytest. No network."""

from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import ship_gate

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parent
EXAMPLES = REPO_ROOT / "examples"
SAMPLE = EXAMPLES / "sample-run"


def _capture_main(argv: list[str], **kwargs) -> tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ship_gate.main(argv, **kwargs)
    return code, out.getvalue(), err.getvalue()


def _map_runner(names: str, blobs: dict[str, str] | None = None):
    blobs = blobs or {}

    def runner(_root: Path, args: list[str]) -> str:
        if args[:3] == ["diff", "--cached", "--name-only"]:
            return names
        if args[:1] == ["show"] and len(args) == 2 and args[1].startswith(":"):
            path = args[1][1:]
            if path not in blobs:
                raise ship_gate.GitError(128, f"not staged: {path}")
            return blobs[path]
        raise ship_gate.GitError(1, f"unexpected git args: {args}")

    return runner


def _init_git_work(tmp: Path) -> Path:
    work = tmp / "work"
    work.mkdir()
    subprocess.run(["git", "init"], cwd=work, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "ship-gate@test"],
        cwd=work,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ship-gate"],
        cwd=work,
        check=True,
        capture_output=True,
    )
    return work


def _env_runner(work: Path, env: dict[str, str]):
    def runner(root: Path, args: list[str]) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=work,
            capture_output=True,
            text=True,
            env=env,
        )
        if completed.returncode != 0:
            raise ship_gate.GitError(completed.returncode, completed.stderr)
        return completed.stdout

    return runner


class ShipGate(unittest.TestCase):
    def test_sample_run_without_git_checks_pass(self) -> None:
        def runner(_root: Path, _args: list[str]) -> str:
            raise RuntimeError("git runner must not run without --git-checks")

        code, out, err = _capture_main([str(SAMPLE)], git_runner=runner)
        self.assertEqual(code, 0, err)
        self.assertIn("SHIP-GATE: PASS", out)
        self.assertNotIn("SHIP-GATE: BLOCK", out)
        self.assertIn("ACCEPT WITH WAIVERS", out)

    def test_cli_sample_run_pass(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                str(HARNESS_DIR / "ship_gate.py"),
                str(SAMPLE),
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("SHIP-GATE: PASS", completed.stdout)

    def test_fail_reject_block(self) -> None:
        code, out, err = _capture_main([str(EXAMPLES / "fail-reject")])
        self.assertEqual(code, 1, err)
        self.assertIn("SHIP-GATE: BLOCK", out)
        self.assertIn("- REJECT", out)
        self.assertEqual(out.count("- REJECT"), 1)

    def test_staged_live_run_blocks(self) -> None:
        runner = _map_runner(
            "runs/foo/plan.md\0",
            {"runs/foo/plan.md": "# Plan\n"},
        )
        blocks = ship_gate.git_index_blocks(REPO_ROOT, runner=runner)
        self.assertIn("staged live run: runs/foo/plan.md", blocks)
        code, out, _ = _capture_main(
            [str(SAMPLE), "--git-checks"], git_runner=runner
        )
        self.assertEqual(code, 1)
        self.assertIn("SHIP-GATE: BLOCK", out)
        self.assertIn("- staged live run: runs/foo/plan.md", out)

    def test_gitkeep_is_not_a_live_run(self) -> None:
        runner = _map_runner("runs/.gitkeep\0", {"runs/.gitkeep": ""})
        blocks = ship_gate.git_index_blocks(REPO_ROOT, runner=runner)
        self.assertEqual(blocks, [])

    def test_git_error_blocks(self) -> None:
        def runner(_root: Path, _args: list[str]) -> str:
            raise ship_gate.GitError(128, "fatal: not a git repository")

        blocks = ship_gate.git_index_blocks(REPO_ROOT, runner=runner)
        self.assertEqual(blocks, ["git_error"])
        code, out, _ = _capture_main(
            [str(SAMPLE), "--git-checks"], git_runner=runner
        )
        self.assertEqual(code, 1)
        self.assertIn("SHIP-GATE: BLOCK", out)
        self.assertIn("- git_error", out)

    def test_staged_env_secret_blocks(self) -> None:
        runner = _map_runner(
            ".env\0",
            {".env": "XAI_API_KEY=notempty\n"},
        )
        blocks = ship_gate.git_index_blocks(REPO_ROOT, runner=runner)
        self.assertIn("staged secret name: .env", blocks)
        self.assertIn("staged secret content: .env", blocks)
        code, out, _ = _capture_main(
            [str(SAMPLE), "--git-checks"], git_runner=runner
        )
        self.assertEqual(code, 1)
        self.assertIn("SHIP-GATE: BLOCK", out)
        self.assertTrue(
            "staged secret name: .env" in out or "staged secret content: .env" in out
        )

    def test_env_example_empty_values_no_secrets_block(self) -> None:
        runner = _map_runner(
            ".env.example\0",
            {".env.example": "XAI_API_KEY=\nGITHUB_TOKEN=\n"},
        )
        blocks = ship_gate.git_index_blocks(REPO_ROOT, runner=runner)
        self.assertEqual(blocks, [])
        code, out, _ = _capture_main(
            [str(SAMPLE), "--git-checks"], git_runner=runner
        )
        self.assertEqual(code, 0, out)
        self.assertIn("SHIP-GATE: PASS", out)

    def test_git_missing_blocks(self) -> None:
        def runner(_root: Path, _args: list[str]) -> str:
            raise FileNotFoundError("git")

        blocks = ship_gate.git_index_blocks(REPO_ROOT, runner=runner)
        self.assertEqual(blocks, ["git_missing"])
        code, out, _ = _capture_main(
            [str(SAMPLE), "--git-checks"], git_runner=runner
        )
        self.assertEqual(code, 1)
        self.assertIn("SHIP-GATE: BLOCK", out)
        self.assertIn("- git_missing", out)

    def test_default_git_runner_nonzero_raises_git_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _init_git_work(Path(tmp))
            with self.assertRaises(ship_gate.GitError):
                ship_gate.default_git_runner(work, ["show", ":does-not-exist"])

    def test_tmp_git_dir_staged_live_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _init_git_work(Path(tmp))
            (work / "runs" / "foo").mkdir(parents=True)
            (work / "runs" / "foo" / "plan.md").write_text("# plan\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "runs/foo/plan.md"],
                cwd=work,
                check=True,
                capture_output=True,
            )
            git_dir = work / ".git"
            env = os.environ.copy()
            env["GIT_DIR"] = str(git_dir)
            env["GIT_INDEX_FILE"] = str(git_dir / "index")
            runner = _env_runner(work, env)
            blocks = ship_gate.git_index_blocks(work, runner=runner)
            self.assertIn("staged live run: runs/foo/plan.md", blocks)

    def test_tmp_git_dir_env_and_example(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _init_git_work(Path(tmp))
            (work / ".env").write_text("XAI_API_KEY=notempty\n", encoding="utf-8")
            (work / ".env.example").write_text(
                "XAI_API_KEY=\nGITHUB_TOKEN=\n", encoding="utf-8"
            )
            subprocess.run(
                ["git", "add", "-f", ".env", ".env.example"],
                cwd=work,
                check=True,
                capture_output=True,
            )
            git_dir = work / ".git"
            env = os.environ.copy()
            env["GIT_DIR"] = str(git_dir)
            env["GIT_INDEX_FILE"] = str(git_dir / "index")
            runner = _env_runner(work, env)
            blocks = ship_gate.git_index_blocks(work, runner=runner)
            self.assertTrue(
                any(b.startswith("staged secret") and ".env" in b for b in blocks)
            )
            self.assertFalse(any(".env.example" in b for b in blocks))
