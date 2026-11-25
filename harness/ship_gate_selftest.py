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
from unittest import mock

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

    def runner(root: Path, args: list[str]) -> str:
        if args == ["rev-parse", "--show-toplevel"]:
            return f"{root}\n"
        if args[:3] == ["diff", "--cached", "--name-only"]:
            return names
        if args[:2] == ["show", "--no-textconv"] and len(args) == 3 and args[2].startswith(":"):
            path = args[2][1:]
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

    def test_sample_run_evidence_blob_is_not_secret_content(self) -> None:
        blob = (SAMPLE / "evidence.md").read_text(encoding="utf-8")
        self.assertIsNone(ship_gate.SECRET_CONTENT.search(blob))
        rel = "examples/sample-run/evidence.md"
        runner = _map_runner(rel + "\0", {rel: blob})
        self.assertEqual(ship_gate.git_index_blocks(REPO_ROOT, runner=runner), [])
        code, out, _ = _capture_main(
            [str(SAMPLE), "--git-checks"], git_runner=runner
        )
        self.assertEqual(code, 0, out)
        self.assertIn("SHIP-GATE: PASS", out)

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
        def runner(root: Path, args: list[str]) -> str:
            if args == ["rev-parse", "--show-toplevel"]:
                return f"{root}\n"
            raise ship_gate.GitError(128, "fatal: bad index")

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

    # S14: the gate's git calls must not use an enclosing repository.

    def _monorepo(self, base: Path) -> tuple[Path, Path]:
        """gate_repro.py layout: a Scaffold copy with no .git inside another repo."""
        outer = base / "org-monorepo"
        inner = outer / "tools" / "Dagz-Scaffold"
        inner.mkdir(parents=True)
        for args in (
            ["git", "init", "-q"],
            ["git", "config", "user.email", "a@b"],
            ["git", "config", "user.name", "n"],
        ):
            subprocess.run(args, cwd=outer, check=True, capture_output=True)
        (outer / "README").write_text("x", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=outer, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-qm", "i"], cwd=outer, check=True, capture_output=True)
        (outer / "other-team").mkdir()
        (outer / "other-team" / ".env").write_text("K=1\n", encoding="utf-8")
        (inner / "runs" / "live1").mkdir(parents=True)
        (inner / "runs" / "live1" / "evidence.md").write_text("x\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "other-team/.env", "tools/Dagz-Scaffold/runs/live1/evidence.md"],
            cwd=outer,
            check=True,
            capture_output=True,
        )
        return outer, inner

    def test_vendored_copy_in_monorepo_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _outer, inner = self._monorepo(Path(tmp).resolve())
            blocks = ship_gate.git_index_blocks(inner, runner=ship_gate.default_git_runner)
        self.assertEqual(blocks, [ship_gate.NO_REPO_BLOCK])
        # Before the fix: ['staged secret name: other-team/.env'], and the
        # staged live run under tools/Dagz-Scaffold/runs/ was missed.
        self.assertFalse(any("other-team" in b for b in blocks))

    def test_inherited_git_dir_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            outer, inner = self._monorepo(Path(tmp).resolve())
            with mock.patch.dict(
                os.environ,
                {"GIT_DIR": str(outer / ".git"), "GIT_WORK_TREE": str(outer)},
            ):
                blocks = ship_gate.git_index_blocks(inner, runner=ship_gate.default_git_runner)
        self.assertEqual(blocks, [ship_gate.NO_REPO_BLOCK])

    def test_real_clone_still_checked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _init_git_work(Path(tmp).resolve())
            (work / "runs" / "live1").mkdir(parents=True)
            (work / "runs" / "live1" / "evidence.md").write_text("x\n", encoding="utf-8")
            (work / ".env").write_text("XAI_API_KEY=notempty\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "-f", "runs/live1/evidence.md", ".env"],
                cwd=work,
                check=True,
                capture_output=True,
            )
            blocks = ship_gate.git_index_blocks(work, runner=ship_gate.default_git_runner)
        self.assertIn("staged live run: runs/live1/evidence.md", blocks)
        self.assertIn("staged secret name: .env", blocks)
        self.assertIn("staged secret content: .env", blocks)

    def test_subdirectory_of_a_clone_is_not_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work = _init_git_work(Path(tmp).resolve())
            sub = work / "nested"
            sub.mkdir()
            runner = lambda root, args: f"{work}\n"  # noqa: E731
            blocks = ship_gate.git_index_blocks(sub, runner=runner)
        self.assertEqual(blocks, [ship_gate.NOT_TOP_BLOCK])

    def test_live_run_path_rule(self) -> None:
        self.assertTrue(ship_gate.is_live_run_path("runs/x/evidence.md"))
        self.assertFalse(ship_gate.is_live_run_path("runs/.gitkeep"))
        self.assertFalse(ship_gate.is_live_run_path("examples/runs-notes.md"))
        self.assertFalse(ship_gate.is_live_run_path("runsheet.md"))

    def test_task_contract_ignores_enclosing_repo(self) -> None:
        import task_contract

        with tempfile.TemporaryDirectory() as tmp:
            outer, inner = self._monorepo(Path(tmp).resolve())
            (inner / "tasks").mkdir()
            task = REPO_ROOT / "tasks" / "001-units-trap.md"
            (inner / "tasks" / task.name).write_text(task.read_text(encoding="utf-8"), encoding="utf-8")
            # The outer repo commits a different file at its own tasks/ path.
            (outer / "tasks").mkdir()
            (outer / "tasks" / task.name).write_text("decoy\n", encoding="utf-8")
            subprocess.run(["git", "add", "tasks"], cwd=outer, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-qm", "decoy"], cwd=outer, check=True, capture_output=True)
            self.assertFalse(task_contract._git_repo(inner))
            contract = task_contract.load_task_contract(inner, f"tasks/{task.name}")
        self.assertIsNotNone(contract)

