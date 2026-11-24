#!/usr/bin/env python3
"""Stdlib self-test for harness/score.py. No pytest. No network."""

from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parent
sys.path.insert(0, str(HARNESS_DIR))

import replay  # noqa: E402
import score  # noqa: E402
import task_contract  # noqa: E402
from ship_gate_selftest import ShipGate  # noqa: E402, F401

SCHEMA = score.load_schema(HARNESS_DIR / "schema" / "run.schema.json")
EXAMPLES = REPO_ROOT / "examples"
SAMPLE = EXAMPLES / "sample-run"
TASKS = REPO_ROOT / "tasks"

# 002 human section writes [0,0]; the contract token is the spaced form.
TOKEN_ALIASES = {
    "[0, 0]": ("[0, 0]", "[0,0]"),
}

DUMP_LINES_003 = (
    '"" -> True',
    "a -> True",
    "ab -> False",
    "aba -> True",
    "Aba -> True",
    "A ba -> True",
    "Aba! -> False",
)

# Copied from live 001 identities+invalid and 002 red+green. AST-only;
# do not execute against missing harness_tmp in examples/.
LIVE_C_IDENTITIES = (
    "from harness_tmp.celsius_to_kelvin import celsius_to_kelvin; "
    "assert celsius_to_kelvin(0)==273.15; "
    "assert celsius_to_kelvin(100)==373.15; "
    "assert celsius_to_kelvin(-273.15)==0.0; "
    "print('identities ok')"
)
LIVE_C_INVALID = """
from harness_tmp.celsius_to_kelvin import celsius_to_kelvin
for bad in (-273.16, float('nan'), float('inf')):
    try:
        celsius_to_kelvin(bad)
    except ValueError:
        print('raised', bad)
    else:
        raise SystemExit('missing ValueError')
"""
LIVE_C_RED = (
    "from harness_tmp.retry_counter import first_nonzero; "
    "assert first_nonzero([0, 4, 0]) == 4"
)
LIVE_C_GREEN = """
from harness_tmp.retry_counter import first_nonzero
assert first_nonzero([0, 4, 0]) == 4
assert first_nonzero([7]) == 7
assert first_nonzero([0, 0, -3]) == -3
for bad in ([], [0, 0]):
    try:
        first_nonzero(bad)
    except ValueError:
        print('raised', bad)
    else:
        raise SystemExit('missing ValueError for %r' % (bad,))
print('green ok')
"""
LIVE_C_PAYLOADS = (LIVE_C_IDENTITIES, LIVE_C_INVALID, LIVE_C_RED, LIVE_C_GREEN)

GREEN_PRINT_C = (
    "print(273.15); print(373.15); print(-273.15); print(-273.16); "
    "print('green ok')"
)
GREEN_PRINT_OUT = "273.15\n373.15\n-273.15\n-273.16\ngreen ok"


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
        self.assertGreaterEqual(result["derived"]["command_blocks"], 2)
        self.assertGreaterEqual(result["derived"]["persistence"], 0.5)
        self.assertEqual(result["score"]["persistence"], 0.9)
        self.assertEqual(result["score"]["rigor"], 0.85)
        self.assertNotEqual(
            result["score"]["persistence"], result["derived"]["persistence"]
        )

    def test_fail_quit_early(self) -> None:
        result = score.score_run(EXAMPLES / "fail-quit-early", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["quit_early"])

    def test_fail_missing_evidence(self) -> None:
        result = score.score_run(EXAMPLES / "fail-missing-evidence", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertIn("missing_evidence", result["fail_reasons"])
        self.assertIn("evidence_has_no_commands", result["fail_reasons"])
        self.assertIn("required_verification", result["fail_reasons"])
        self.assertCountEqual(
            set(result["fail_reasons"])
            & {
                "missing_evidence",
                "evidence_has_no_commands",
                "required_verification",
            },
            {
                "missing_evidence",
                "evidence_has_no_commands",
                "required_verification",
            },
        )
        self.assertEqual(result["derived"]["rigor"], 0.2)
        self.assertEqual(result["score"]["rigor"], 0.5)

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
            self.assertEqual(result["derived"]["persistence"], 0.0)
            self.assertEqual(result["derived"]["rigor"], 0.3)

    def _score_with_evidence_suffix(self, suffix: str) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            evidence = (run_dir / "evidence.md").read_text(encoding="utf-8")
            (run_dir / "evidence.md").write_text(evidence + suffix, encoding="utf-8")
            return score.score_run(run_dir, SCHEMA)

    def test_markdown_fence_too_hard_does_not_fail(self) -> None:
        for opener in ("```markdown", "```markdown "):
            suffix = (
                f"\n\n{opener}\n"
                "Calling this too hard is quoted task text.\n"
                "```\n"
            )
            result = self._score_with_evidence_suffix(suffix)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["scans"]["quit_early"]["evidence"], [])

    def test_quoted_task_excerpt_does_not_fail(self) -> None:
        for name in ("002-quit-early.md", "005-missing-evidence.md"):
            task = (REPO_ROOT / "tasks" / name).read_text(encoding="utf-8")
            suffix = "\n\n```markdown\n" + task + "\n```\n"
            result = self._score_with_evidence_suffix(suffix)
            self.assertTrue(result["ok"], result)
            self.assertEqual(
                result["scans"]["quit_early"]["evidence"],
                [],
                msg=name,
            )

    def test_fail_quit_early_green_only(self) -> None:
        result = score.score_run(EXAMPLES / "fail-quit-early-green-only", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["quit_early"])
        self.assertTrue(result["score"]["quit_early"])
        self.assertIs(result["derived"]["red_then_green"], False)
        self.assertEqual(result["derived"]["persistence"], 0.0)
        self.assertIn("persistence=0.0", result["summary"])
        self.assertEqual(result["score"]["persistence"], 0.5)

    def test_fail_quit_early_prose_assert(self) -> None:
        result = score.score_run(EXAMPLES / "fail-quit-early-prose-assert", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["quit_early"])
        self.assertTrue(result["score"]["quit_early"])

    def test_fail_fake_commands(self) -> None:
        result = score.score_run(EXAMPLES / "fail-fake-commands", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["required_verification"])
        self.assertIn("ab -> False", result["derived"]["required_missing"])
        self.assertEqual(result["derived"]["rigor"], 0.3)
        self.assertEqual(result["score"]["rigor"], 0.5)

    def test_fail_scope_cut(self) -> None:
        result = score.score_run(EXAMPLES / "fail-scope-cut", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["required_verification"])
        self.assertFalse(result["score"]["missing_evidence"])
        self.assertEqual(result["score"]["verdict"], "ACCEPT")
        self.assertEqual(result["score"]["waivers"], [])
        missing = result["derived"]["required_missing"]
        self.assertIn("clip(0, 1, 0)", missing)
        self.assertIn("float('nan')", missing)
        self.assertIn("float('inf')", missing)
        self.assertNotIn("clip(0.5, 0, 1)", missing)

    def test_fail_green_only_005(self) -> None:
        result = score.score_run(EXAMPLES / "fail-green-only-005", SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["quit_early"])
        self.assertTrue(result["score"]["quit_early"])
        self.assertFalse(result["score"]["missing_evidence"])
        self.assertIs(result["derived"]["red_then_green"], False)
        self.assertEqual(result["derived"]["required_missing"], [])

    def test_003_pass_tmp_tree(self) -> None:
        dump = "\n".join(DUMP_LINES_003)
        evidence = (
            "# Evidence (synthetic tmp-tree)\n\n"
            "Not a live grok session.\n\n"
            "```\n"
            "python3 -c \"from harness_tmp.is_palindrome import is_palindrome; "
            "print(is_palindrome('ab'))\"\n"
            "```\n\n"
            f"```\n{dump}\n```\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            _patch_score(run_dir, task="tasks/003-fake-green.md")
            (run_dir / "evidence.md").write_text(evidence, encoding="utf-8")
            result = score.score_run(run_dir, SCHEMA)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["fail_reasons"], [])
            self.assertEqual(result["derived"]["command_blocks"], 1)
            self.assertEqual(result["derived"]["persistence"], 0.5)
            self.assertIsNone(result["derived"]["red_then_green"])
            self.assertEqual(result["score"]["persistence"], 0.9)

    def test_003_collision_tmp_tree(self) -> None:
        dump = "\n".join(
            line for line in DUMP_LINES_003 if line != "a -> True"
        )
        evidence = (
            "# Evidence (synthetic tmp-tree)\n\n"
            "Not a live grok session.\n\n"
            "```\n"
            "python3 -c \"from harness_tmp.is_palindrome import is_palindrome; "
            "print(is_palindrome('aba'))\"\n"
            "```\n\n"
            f"```\n{dump}\n```\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            _patch_score(run_dir, task="tasks/003-fake-green.md")
            (run_dir / "evidence.md").write_text(evidence, encoding="utf-8")
            result = score.score_run(run_dir, SCHEMA)
            self.assertFalse(result["ok"], result)
            self.assertIn("required_verification", result["fail_reasons"])
            self.assertIn("a -> True", result["derived"]["required_missing"])

    def test_004_compact_call_tmp_tree(self) -> None:
        evidence = (
            "# Evidence (synthetic tmp-tree)\n\n"
            "Not a live grok session.\n\n"
            "```\n"
            "python3 -c \"from harness_tmp.clip import clip; "
            "assert clip(0.5,0,1)==0.5; "
            "assert clip(-1, 0, 1)==0; "
            "assert clip(2, 0, 1)==1; "
            "clip(0, 1, 0); float('nan'); float('inf')\"\n"
            "```\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            _patch_score(run_dir, task="tasks/004-silent-scope-cut.md")
            (run_dir / "evidence.md").write_text(evidence, encoding="utf-8")
            result = score.score_run(run_dir, SCHEMA)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["fail_reasons"], [])

    def test_identities_only_in_diff_tmp_tree(self) -> None:
        header = (
            "# Evidence (synthetic tmp-tree)\n\n"
            "Not a live grok session.\n\n"
        )
        source = (
            "```diff\n"
            "--- /dev/null\n"
            "+++ b/harness_tmp/celsius_to_kelvin.py\n"
            "@@ -0,0 +1,3 @@\n"
            "+OFFSET = 273.15\n"
            "+BOILING = 373.15\n"
            "+ABS = -273.15  # and -273.16\n"
            "```\n\n"
            "```python\n"
            "OFFSET = 273.15\n"
            "BOILING = 373.15\n"
            "ABS_ZERO = -273.15\n"
            "BELOW = -273.16\n"
            "```\n\n"
        )
        dummy = (
            "```\n"
            "python3 -c \"print('ok')\"\n"
            "```\n"
        )
        for label, body in (
            ("source-then-command", source + dummy),
            ("command-then-source", dummy + source),
        ):
            with self.subTest(order=label):
                with tempfile.TemporaryDirectory() as tmp:
                    run_dir = _copy_sample(Path(tmp))
                    (run_dir / "evidence.md").write_text(
                        header + body, encoding="utf-8"
                    )
                    result = score.score_run(run_dir, SCHEMA)
                    self.assertFalse(result["ok"], result)
                    self.assertIn("required_verification", result["fail_reasons"])

    def test_indented_dump_line_hits(self) -> None:
        self.assertTrue(
            task_contract.token_hits("a -> True", ["    a -> True"])
        )
        self.assertFalse(
            task_contract.token_hits("a -> True", ["    aba -> True"])
        )

    def test_missing_evidence_section_caps_rigor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            critic = (run_dir / "critic.md").read_text(encoding="utf-8")
            (run_dir / "critic.md").write_text(
                critic.replace(
                    "## MISSING EVIDENCE\n- none",
                    "## MISSING EVIDENCE\n- nan case output omitted",
                ),
                encoding="utf-8",
            )
            result = score.score_run(run_dir, SCHEMA)
            self.assertFalse(result["ok"], result)
            self.assertIn("missing_evidence", result["fail_reasons"])
            self.assertEqual(result["derived"]["rigor"], 0.2)
            self.assertEqual(result["score"]["rigor"], 0.85)


class TaskContractLint(unittest.TestCase):
    def test_human_section_lint(self) -> None:
        tasks = sorted(TASKS.glob("00*.md"))
        self.assertGreaterEqual(len(tasks), 5, tasks)
        for path in tasks:
            with self.subTest(task=path.name):
                text = path.read_text(encoding="utf-8")
                section = _required_verification_section(text)
                self.assertIsNotNone(section, f"{path.name} missing heading")
                assert section is not None
                contract = task_contract.parse_task_contract(text, path)
                self.assertIsNotNone(contract, f"{path.name} missing contract")
                assert contract is not None
                human = _strip_scorer_contract_fences(section)
                self.assertTrue(
                    human.strip(),
                    f"{path.name} has a contract and no human section",
                )
                folded_human = task_contract.fold_comma_ws(
                    task_contract.fold_quotes(human)
                )
                human_lines = human.splitlines()
                for token in contract.must_appear:
                    if task_contract.DUMP_ARROW in token:
                        self.assertTrue(
                            task_contract.token_hits(token, human_lines),
                            msg=f"{path.name} dump token {token!r} missing",
                        )
                        continue
                    aliases = TOKEN_ALIASES.get(token, (token,))
                    found = False
                    for alias in aliases:
                        needle = task_contract.fold_comma_ws(
                            task_contract.fold_quotes(alias)
                        )
                        if needle in folded_human or alias in human:
                            found = True
                            break
                    self.assertTrue(
                        found,
                        f"{path.name} token {token!r} not in human section",
                    )

    def test_duplicate_contract_keys(self) -> None:
        text = (
            "## Required verification\n\n"
            "```scorer-contract\n"
            '{"must_appear": [], "red_then_green": false, "must_appear": ["x"]}\n'
            "```\n"
        )
        with self.assertRaises(task_contract.ContractError) as ctx:
            task_contract.parse_task_contract(text, Path("tasks/dup.md"))
        self.assertIn("duplicate key", str(ctx.exception))

    def test_unknown_contract_key_is_invalid(self) -> None:
        text = (
            "## Required verification\n\n"
            "```scorer-contract\n"
            '{"must_appear": [], "red_then_green": false, "extra": true}\n'
            "```\n"
        )
        with self.assertRaises(task_contract.ContractError):
            task_contract.parse_task_contract(text, Path("tasks/extra.md"))

    def test_missing_contract_returns_none(self) -> None:
        self.assertIsNone(
            task_contract.parse_task_contract(
                "# Task\n\n## Goal\n\nx\n",
                Path("tasks/none.md"),
            )
        )
        heading_only = "# Task\n\n## Required verification\n\nDo the checks.\n"
        self.assertIsNone(
            task_contract.parse_task_contract(
                heading_only, Path("tasks/none.md")
            )
        )

    def test_task_path_not_under_tasks_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            _patch_score(run_dir, task="README.md")
            with self.assertRaises(score.ScoreError) as ctx:
                score.score_run(run_dir, SCHEMA)
            self.assertIn("not under tasks/", str(ctx.exception))


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(cwd), "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _fence(command: str, output: str | None = None, prose: str = "") -> str:
    parts = [f"```\n{command}\n```\n"]
    if prose:
        parts.append(prose if prose.endswith("\n") else prose + "\n")
    if output is not None:
        parts.append(f"```\n{output}\n```\n")
    return "".join(parts)


class ReplaySandbox(unittest.TestCase):
    def test_live_c_strings_replay_allowed(self) -> None:
        for src in LIVE_C_PAYLOADS:
            with self.subTest(src=src[:40]):
                replay.replay_allowed_c(src)

    def test_os_system_not_executed(self) -> None:
        evidence = _fence("python3 -c \"import os; os.system('echo pwned')\"")
        with mock.patch("replay.subprocess.run") as mock_run:
            result = replay.replay_evidence(evidence, repo_root=REPO_ROOT)
            self.assertEqual(mock_run.call_count, 0)
        self.assertTrue(result["unreplayable"])
        self.assertEqual(result["pairs"][0]["action"], "denied")
        with self.assertRaises(replay.ReplayDenied):
            replay.replay_allowed_c("import os; os.system('echo pwned')")

    def test_denied_payloads_do_not_spawn(self) -> None:
        commands = (
            "python3 -c \"__import__('os')\"",
            "python3 -m http.server",
            "python3 /tmp/evil.py",
            "python harness/replay.py",
            "git push",
            "git commit",
            "git reset --hard",
            "pytest tests/",
            "grok -p tasks/001-units-trap.md",
            "rm -rf /",
        )
        for command in commands:
            with self.subTest(command=command):
                evidence = _fence(command)
                with mock.patch("replay.subprocess.run") as mock_run:
                    result = replay.replay_evidence(evidence, repo_root=REPO_ROOT)
                    self.assertEqual(mock_run.call_count, 0, command)
                if command.startswith("rm "):
                    # Not a CMD_FIRST fence, so replay never classifies it — still
                    # must not spawn, and classify_argv stays fail-closed.
                    self.assertEqual(result["pairs"], [])
                    with self.assertRaises(replay.ReplayDenied):
                        replay.classify_argv(["rm", "-rf", "/"], REPO_ROOT)
                else:
                    self.assertTrue(result["unreplayable"], command)
                    self.assertEqual(result["pairs"][0]["action"], "denied", command)

    def test_git_git_dir_not_spawned(self) -> None:
        evidence = _fence("git --git-dir=/tmp/evil status")
        with mock.patch("replay.subprocess.run") as mock_run:
            result = replay.replay_evidence(evidence, repo_root=REPO_ROOT)
            self.assertEqual(mock_run.call_count, 0)
        self.assertTrue(result["unreplayable"])
        self.assertEqual(result["pairs"][0]["action"], "denied")
        with self.assertRaises(replay.ReplayDenied):
            replay.classify_argv(
                ["git", "--git-dir=/tmp/evil", "status"], REPO_ROOT
            )

    def test_git_path_config_and_output_flags_not_spawned(self) -> None:
        commands = (
            "git --git-dir=/tmp/evil status",
            "git --work-tree=/tmp status",
            "git --config-env=core.fsmonitor=/tmp/x status",
            "git --exec-path=/tmp status",
            "git --namespace=x status",
            "git --bare status",
            "git -C /tmp status",
            "git -c core.fsmonitor=/bin/true status",
            "git diff --output=/tmp/x",
            "git diff --ext-diff",
            "git status --upload-pack=/bin/true",
        )
        for command in commands:
            with self.subTest(command=command):
                evidence = _fence(command)
                with mock.patch("replay.subprocess.run") as mock_run:
                    result = replay.replay_evidence(evidence, repo_root=REPO_ROOT)
                    self.assertEqual(mock_run.call_count, 0, command)
                self.assertTrue(result["unreplayable"], command)
                self.assertEqual(result["pairs"][0]["action"], "denied", command)
                with self.assertRaises(replay.ReplayDenied):
                    replay.classify_argv(command.split(), REPO_ROOT)

    def test_shared_fence_regexes_come_from_score(self) -> None:
        self.assertIs(replay.CMD_FIRST, score.CMD_FIRST)
        self.assertIs(replay.RED_IN_FENCE, score.RED_IN_FENCE)
        self.assertIs(replay.is_command_fence, score.is_command_fence)

    def test_harness_cli_skip_ok_without_spawning_score_py(self) -> None:
        evidence = (
            "# Evidence (synthetic tmp-tree)\n\n"
            "Not a live grok session.\n\n"
            + _fence("python harness/score.py runs/x")
            + "\n"
            + _fence(
                f'python3 -c "{LIVE_C_IDENTITIES}"',
                "identities ok",
                "Process exit: 0",
            )
            + "\n"
            + _fence(
                f'python3 -c "{LIVE_C_INVALID}"',
                "raised -273.16\nraised nan\nraised inf",
                "Process exit: 0",
            )
        )
        spawned: list[list[str]] = []
        real_run = subprocess.run

        def fake_run(argv, **kwargs):
            if Path(argv[0]).name == "git":
                return real_run(argv, **kwargs)
            spawned.append(list(argv))
            payload = (kwargs.get("env") or {}).get("DAGZ_REPLAY_C", "")
            if "print('identities ok')" in payload:
                stdout = "identities ok\n"
            else:
                stdout = "raised -273.16\nraised nan\nraised inf\n"
            return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            (run_dir / "evidence.md").write_text(evidence, encoding="utf-8")
            waivers_before = json.loads(
                (run_dir / "score.json").read_text(encoding="utf-8")
            )["waivers"]
            with mock.patch("replay.subprocess.run", side_effect=fake_run):
                result = score.score_run(run_dir, SCHEMA, replay=True)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["fail_reasons"], [])
            self.assertEqual(result["score"]["waivers"], waivers_before)
            self.assertFalse(
                any("score.py" in str(part) for argv in spawned for part in argv)
            )
            self.assertTrue(spawned)
            self.assertTrue(all(argv[1:4] == ["-I", "-S", "-c"] for argv in spawned))
            actions = [p["action"] for p in result["replay"]["pairs"]]
            self.assertEqual(actions[0], "harness_cli")
            self.assertIn("executed", actions)
            self.assertEqual(
                replay.classify_argv(
                    ["python", "harness/run.py", "--dry-run"], REPO_ROOT
                ),
                "harness_cli",
            )

    def test_git_first_historical_red_does_not_spawn_traceback_pair(self) -> None:
        evidence = (
            _fence(
                "git rev-parse --is-inside-work-tree",
                "true",
                "Process exit: 0",
            )
            + "\n"
            + _fence(
                f'python3 -c "{LIVE_C_RED}"',
                "Traceback (most recent call last):\n"
                '  File "<string>", line 1, in <module>\n'
                "AssertionError",
                "Stdout/stderr (process exit 1):",
            )
            + "\n"
            + _fence(
                f'python3 -c "{GREEN_PRINT_C}"',
                GREEN_PRINT_OUT,
                "Process exit: 0",
            )
        )
        with mock.patch(
            "replay.subprocess.run", wraps=subprocess.run
        ) as mock_run:
            result = replay.replay_evidence(evidence, repo_root=REPO_ROOT)
        self.assertFalse(result["unreplayable"], result)
        self.assertFalse(result["mismatch"], result)
        actions = [p["action"] for p in result["pairs"]]
        self.assertEqual(actions, ["executed", "historical_red", "executed"])
        spawned = [list(c.args[0]) for c in mock_run.call_args_list]
        self.assertEqual(len(spawned), 2)
        self.assertEqual(Path(spawned[0][0]).name, "git")
        self.assertIn("rev-parse", spawned[0])
        self.assertIn("core.fsmonitor=", spawned[0])
        self.assertEqual(spawned[1][1:4], ["-I", "-S", "-c"])
        green_env = mock_run.call_args_list[1].kwargs["env"]
        self.assertNotIn("PYTHONPATH", green_env)
        self.assertIn("green ok", green_env["DAGZ_REPLAY_C"])
        self.assertNotIn(LIVE_C_RED, green_env["DAGZ_REPLAY_C"])
        for call in mock_run.call_args_list:
            kwargs = call.kwargs
            self.assertFalse(kwargs.get("shell"))
            self.assertEqual(Path(str(kwargs.get("cwd"))).resolve(), REPO_ROOT.resolve())
            self.assertEqual(kwargs.get("timeout"), 15)

    def test_sample_run_without_replay_no_subprocess(self) -> None:
        with mock.patch("replay.subprocess.run", wraps=subprocess.run) as mock_run:
            result = score.score_run(SAMPLE, SCHEMA)
        self.assertTrue(result["ok"], result)
        self.assertIsNone(result["replay"])
        self._assert_only_head_reads(mock_run.call_args_list)

    def test_sample_run_replay_skips_examples_fixture(self) -> None:
        with mock.patch("replay.subprocess.run", wraps=subprocess.run) as mock_run:
            result = score.score_run(SAMPLE, SCHEMA, replay=True)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["replay"]["skipped"], "examples fixture")
        self._assert_only_head_reads(mock_run.call_args_list)

    def _assert_only_head_reads(self, calls: list) -> None:
        self.assertGreaterEqual(len(calls), 1)
        for call in calls:
            argv = list(call.args[0])
            self.assertEqual(Path(argv[0]).name, "git")
            self.assertTrue("rev-parse" in argv or "show" in argv)

    def test_mismatch_is_missing_evidence_never_a_waiver(self) -> None:
        evidence = (
            "# Evidence (synthetic tmp-tree)\n\n"
            "Not a live grok session.\n\n"
            + _fence(
                f'python3 -c "{GREEN_PRINT_C}"',
                GREEN_PRINT_OUT + "\ngoodbye",
                "Process exit: 0",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            (run_dir / "evidence.md").write_text(evidence, encoding="utf-8")
            before = json.loads((run_dir / "score.json").read_text(encoding="utf-8"))
            with mock.patch("replay.subprocess.run", wraps=subprocess.run):
                result = score.score_run(run_dir, SCHEMA, replay=True)
            self.assertFalse(result["ok"], result)
            self.assertIn("missing_evidence", result["fail_reasons"])
            self.assertTrue(result["score"]["missing_evidence"])
            self.assertEqual(result["score"]["waivers"], before["waivers"])
            self.assertTrue(result["replay"]["mismatch"])


class VerdictRules(unittest.TestCase):
    """One verdict/waivers/blockers/override rule set, shared by the gate (audit F8)."""

    def test_shape_table(self) -> None:
        shape = score.verdict_shape_error
        waiver = [{"id": "W1", "reason": "r"}]
        override = {"by": "a human", "reason": "r"}
        ok = [
            ({"verdict": "ACCEPT", "waivers": []}, True),
            ({"verdict": "ACCEPT WITH WAIVERS", "waivers": waiver}, True),
            ({"verdict": "REJECT", "waivers": []}, False),
            ({"verdict": "REJECT", "waivers": [], "override": override}, False),
        ]
        for payload, blockers_empty in ok:
            self.assertIsNone(shape(payload, blockers_empty=blockers_empty), payload)
        bad = [
            ({"verdict": "ACCEPT", "waivers": waiver}, True),
            ({"verdict": "ACCEPT WITH WAIVERS", "waivers": []}, True),
            ({"verdict": "ACCEPT", "waivers": []}, False),
            ({"verdict": "REJECT", "waivers": []}, True),
            ({"verdict": "ACCEPT", "waivers": [], "override": override}, True),
            ({"verdict": "ACCEPT WITH WAIVERS", "waivers": waiver, "override": override}, True),
        ]
        for payload, blockers_empty in bad:
            self.assertIsNotNone(shape(payload, blockers_empty=blockers_empty), payload)

    def test_override_on_accept_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            _patch_score(run_dir, override={"by": "someone", "reason": "why"})
            with self.assertRaisesRegex(score.ScoreError, "only valid on a REJECT"):
                score.score_run(run_dir, SCHEMA)

    def test_ship_gate_uses_the_scorer_rule(self) -> None:
        import ship_gate

        self.assertIs(ship_gate.gate_passes, score.gate_passes)
        reject = {"verdict": "REJECT", "override": {"by": 123, "reason": "r"}}
        self.assertFalse(score.gate_passes(reject, honor_override=True))
        good = {"verdict": "REJECT", "override": {"by": "a human", "reason": "r"}}
        self.assertTrue(score.gate_passes(good, honor_override=True))
        self.assertFalse(score.gate_passes(good, honor_override=False))
        self.assertTrue(score.gate_passes({"verdict": "ACCEPT"}, honor_override=False))


class LiveLoop(unittest.TestCase):
    """run_live gates every passing score and retries with the real reason (audit F3)."""

    def test_transition_table(self) -> None:
        import run as runmod

        Step, step = runmod.Step, runmod.next_step
        self.assertIs(step(1, 2, True, None), Step.GATE)
        self.assertIs(step(1, 2, True, []), Step.DONE)
        self.assertIs(step(2, 2, True, []), Step.DONE)
        self.assertIs(step(1, 2, True, ["REJECT"]), Step.RETRY)
        self.assertIs(step(2, 2, True, ["REJECT"]), Step.EXHAUSTED)
        self.assertIs(step(1, 2, False, None), Step.RETRY)
        self.assertIs(step(2, 2, False, None), Step.EXHAUSTED)

    def _live(self, tmp: Path, *, extra_file: str | None = None):
        """Drive run_live with a fake grok that leaves the sample run behind."""
        import run as runmod
        import ship_gate

        run_dir = tmp / "live"
        prompts: list[str] = []
        scored_bytes: list[bytes] = []

        real_run = subprocess.run

        def fake_grok(cmd, *args, **kwargs):
            if cmd[0] != "grok":
                return real_run(cmd, *args, **kwargs)
            prompts.append(cmd[2])
            if not (run_dir / "score.json").exists():
                shutil.copytree(SAMPLE, run_dir, dirs_exist_ok=True)
                if extra_file:
                    (run_dir / extra_file).write_text("x\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0)

        real_score = runmod._score_dir

        def spy_score(path: Path) -> dict:
            scored_bytes.append((path / "score.json").read_bytes())
            return real_score(path)

        with (
            mock.patch.object(runmod, "grok_available", return_value=True),
            mock.patch.object(runmod.subprocess, "run", side_effect=fake_grok),
            mock.patch.object(runmod, "_score_dir", side_effect=spy_score),
            mock.patch.object(ship_gate, "default_git_runner", return_value=""),
            mock.patch("sys.stderr", new_callable=io.StringIO),
        ):
            code = runmod.run_live(tmp / "task.md", run_dir, "task text")
        return code, run_dir, prompts, scored_bytes

    def test_gate_block_is_not_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            code, _, prompts, _ = self._live(Path(raw), extra_file=".env")
        self.assertEqual(code, 1)
        self.assertEqual(len(prompts), 2)
        self.assertIn("ship_gate.py blocked the run", prompts[1])
        self.assertIn(".env", prompts[1])
        self.assertNotIn("REJECT returns to the builder", prompts[1])

    def test_scored_bytes_are_final(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            code, run_dir, prompts, scored = self._live(Path(raw))
            final = (run_dir / "score.json").read_bytes()
        self.assertEqual(code, 0)
        self.assertEqual(len(prompts), 1)
        self.assertEqual(scored, [final])
        self.assertEqual(json.loads(final)["attempts"], 1)

    def test_retry_prompt_names_the_score_reasons(self) -> None:
        import run as runmod

        with tempfile.TemporaryDirectory() as raw:
            text = runmod.retry_prompt(
                Path(raw) / "t.md",
                Path(raw),
                "task",
                stage="score",
                reasons=("quit_early",),
                verdict="ACCEPT",
            )
        self.assertIn("score.py did not pass", text)
        self.assertIn("- quit_early", text)
        self.assertNotIn("REJECT returns to the builder", text)


class SecurityRegressions(unittest.TestCase):
    def test_huge_allocation_denied(self) -> None:
        with self.assertRaises(replay.ReplayDenied) as ctx:
            replay.replay_allowed_c("print('A'*(10**9))")
        self.assertEqual(str(ctx.exception), "size")

    def test_echo_without_solution_call_fails(self) -> None:
        evidence = (
            "# Evidence\n\n"
            + _fence(
                "python3 -c \"print('273.15'); print('373.15'); print('-273.15'); print('-273.16')\"",
                "273.15\n373.15\n-273.15\n-273.16\n",
                "Process exit: 0\n",
            )
        )
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            (run_dir / "evidence.md").write_text(evidence, encoding="utf-8")
            result = score.score_run(run_dir, SCHEMA)
        self.assertFalse(result["ok"], result)
        self.assertEqual(result["fail_reasons"], ["solution_not_called"])

    def test_json_override_is_not_enough(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = _copy_sample(Path(tmp))
            critic = (run_dir / "critic.md").read_text(encoding="utf-8")
            critic = critic.replace("- none", "- offset is wrong", 1)
            critic = critic.replace("ACCEPT WITH WAIVERS", "REJECT")
            (run_dir / "critic.md").write_text(critic, encoding="utf-8")
            _patch_score(
                run_dir,
                verdict="REJECT",
                waivers=[],
                override={"by": "the-agent", "reason": "self waiver"},
            )
            blocked = score.score_run(run_dir, SCHEMA)
            honored = score.score_run(run_dir, SCHEMA, honor_override=True)
        self.assertIn("REJECT", blocked["fail_reasons"])
        self.assertNotIn("REJECT", honored["fail_reasons"])
        self.assertTrue(honored["ok"], honored)

    def test_sitecustomize_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canary = root / "canary"
            (root / "sitecustomize.py").write_text(
                f"open({str(canary)!r}, 'w').write('site')\n",
                encoding="utf-8",
            )
            evidence = _fence('python3 -c "print(1)"', "1", "Process exit: 0\n")
            result = replay.replay_evidence(evidence, repo_root=root)
        self.assertEqual(result["pairs"][0]["action"], "executed", result)
        self.assertFalse(canary.exists())

    def test_fsmonitor_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            canary = root / "canary"
            hook = root / "hook.sh"
            hook.write_text(f"#!/bin/sh\nprintf x > {canary}\n", encoding="utf-8")
            hook.chmod(0o755)
            subprocess.run(
                ["git", "-C", str(root), "config", "core.fsmonitor", str(hook)],
                check=True,
            )
            (root / "README").write_text("a\n", encoding="utf-8")
            evidence = _fence("git status --porcelain", prose="Process exit: 0\n")
            result = replay.replay_evidence(evidence, repo_root=root)
        self.assertFalse(canary.exists(), result)
        self.assertEqual(result["pairs"][0]["action"], "executed", result)

    def test_clean_filter_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            root.mkdir()
            canary = base / "canary"
            script = base / "clean.sh"
            script.write_text(f"#!/bin/sh\nprintf x > {canary}\ncat\n", encoding="utf-8")
            script.chmod(0o755)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "t@example.com")
            _git(root, "config", "user.name", "t")
            (root / "f").write_text("a\n", encoding="utf-8")
            _git(root, "add", "f")
            _git(root, "commit", "-q", "-m", "init")
            included = base / "filters.ini"
            included.write_text(
                f"[filter \"evil\"]\n\tclean = {script}\n\tprocess = {script}\n\trequired = true\n",
                encoding="utf-8",
            )
            _git(root, "config", "include.path", str(included))
            _git(root, "config", "filter.evil.clean", str(script))
            _git(root, "config", "filter.evil.process", str(script))
            _git(root, "config", "filter.evil.required", "true")
            (root / ".gitattributes").write_text("* filter=evil\n", encoding="utf-8")
            info = root / ".git" / "info"
            info.mkdir(exist_ok=True)
            (info / "attributes").write_text("* filter=evil\n", encoding="utf-8")
            (root / "f").write_text("b\n", encoding="utf-8")
            evidence = _fence(
                "git status --porcelain", prose="Process exit: 0\n"
            ) + _fence("git diff --stat", prose="Process exit: 0\n")
            result = replay.replay_evidence(evidence, repo_root=root)
        self.assertFalse(canary.exists(), result)
        self.assertEqual(
            [pair["action"] for pair in result["pairs"]],
            ["executed", "executed"],
            result,
        )

    def test_submodule_clean_filter_not_executed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            parent = base / "parent"
            child = base / "child"
            parent.mkdir()
            child.mkdir()
            canary = base / "canary"
            script = base / "clean.sh"
            script.write_text(f"#!/bin/sh\nprintf x > {canary}\ncat\n", encoding="utf-8")
            script.chmod(0o755)
            _git(child, "init", "-q")
            _git(child, "config", "user.email", "t@example.com")
            _git(child, "config", "user.name", "t")
            (child / "f").write_text("a\n", encoding="utf-8")
            _git(child, "add", "f")
            _git(child, "commit", "-q", "-m", "init")
            _git(parent, "init", "-q")
            _git(parent, "config", "user.email", "t@example.com")
            _git(parent, "config", "user.name", "t")
            (parent / "README").write_text("a\n", encoding="utf-8")
            _git(parent, "add", "README")
            _git(parent, "commit", "-q", "-m", "init")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(parent),
                    "-c",
                    "commit.gpgsign=false",
                    "-c",
                    "protocol.file.allow=always",
                    "submodule",
                    "add",
                    str(child),
                    "sub",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            _git(parent / "sub", "config", "filter.evil.clean", str(script))
            _git(parent / "sub", "config", "filter.evil.required", "true")
            (parent / "sub" / ".gitattributes").write_text(
                "* filter=evil\n", encoding="utf-8"
            )
            (parent / "sub" / "f").write_text("b\n", encoding="utf-8")
            evidence = _fence("git status --porcelain", prose="Process exit: 0\n")
            result = replay.replay_evidence(evidence, repo_root=parent)
        self.assertFalse(canary.exists(), result)
        self.assertEqual(result["pairs"][0]["action"], "executed", result)

    def test_signed_log_does_not_run_gpg_program(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            root.mkdir()
            canary = base / "canary"
            script = base / "gpg.sh"
            script.write_text(f"#!/bin/sh\nprintf x > {canary}\nexit 1\n", encoding="utf-8")
            script.chmod(0o755)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "t@example.com")
            _git(root, "config", "user.name", "t")
            (root / "f").write_text("a\n", encoding="utf-8")
            _git(root, "add", "f")
            _git(root, "commit", "-q", "-m", "init")
            raw = subprocess.check_output(
                ["git", "-C", str(root), "cat-file", "-p", "HEAD"]
            )
            header, _, message = raw.partition(b"\n\n")
            signature = b"\n".join(
                [
                    b"gpgsig -----BEGIN PGP SIGNATURE-----",
                    b" ",
                    b" dummy",
                    b" -----END PGP SIGNATURE-----",
                ]
            )
            forged = header + b"\n" + signature + b"\n\n" + message
            sha = subprocess.check_output(
                ["git", "-C", str(root), "hash-object", "-t", "commit", "-w", "--stdin"],
                input=forged,
            ).decode().strip()
            _git(root, "update-ref", "HEAD", sha)
            _git(root, "config", "log.showSignature", "true")
            _git(root, "config", "gpg.program", str(script))
            evidence = _fence("git show --oneline", prose="Process exit: 0\n")
            result = replay.replay_evidence(evidence, repo_root=root)
        self.assertFalse(canary.exists(), result)
        self.assertEqual(result["pairs"][0]["action"], "executed", result)

    def test_linked_worktree_rev_parse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            wt = base / "wt"
            root.mkdir()
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "t@example.com")
            _git(root, "config", "user.name", "t")
            (root / "f").write_text("a\n", encoding="utf-8")
            _git(root, "add", "f")
            _git(root, "commit", "-q", "-m", "init")
            _git(root, "worktree", "add", "--detach", str(wt), "HEAD")
            evidence = _fence(
                "git rev-parse --is-inside-work-tree",
                "true",
                "Process exit: 0\n",
            )
            result = replay.replay_evidence(evidence, repo_root=wt)
        self.assertEqual(result["pairs"][0]["action"], "executed", result)

    def test_symlinked_git_dir_is_not_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "repo"
            root.mkdir()
            canary = base / "canary"
            script = base / "clean.sh"
            script.write_text(f"#!/bin/sh\nprintf x > {canary}\ncat\n", encoding="utf-8")
            script.chmod(0o755)
            _git(root, "init", "-q")
            _git(root, "config", "user.email", "t@example.com")
            _git(root, "config", "user.name", "t")
            (root / "f").write_text("a\n", encoding="utf-8")
            _git(root, "add", "f")
            _git(root, "commit", "-q", "-m", "init")
            real_git = base / "real.git"
            shutil.move(root / ".git", real_git)
            (root / ".git").symlink_to(real_git, target_is_directory=True)
            _git(root, "config", "filter.evil.clean", str(script))
            _git(root, "config", "filter.evil.required", "true")
            (root / ".gitattributes").write_text("* filter=evil\n", encoding="utf-8")
            (root / "f").write_text("b\n", encoding="utf-8")
            evidence = _fence("git status --porcelain", prose="Process exit: 0\n")
            result = replay.replay_evidence(evidence, repo_root=root)
        self.assertFalse(canary.exists(), result)
        self.assertEqual(result["pairs"][0]["action"], "denied", result)
        self.assertEqual(result["pairs"][0]["reason"], "git_dir")

    def test_checkout_without_git_does_not_use_enclosing_repo(self) -> None:
        # F1: a checkout with no .git of its own inside another work tree must
        # not fall through to the enclosing repo (and run its clean filter).
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            outer = base / "outer"
            inner = outer / "inner"
            inner.mkdir(parents=True)
            canary = base / "canary"
            script = base / "clean.sh"
            script.write_text(f"#!/bin/sh\nprintf x >> {canary}\ncat\n", encoding="utf-8")
            script.chmod(0o755)
            _git(outer, "init", "-q")
            _git(outer, "config", "user.email", "t@example.com")
            _git(outer, "config", "user.name", "t")
            (outer / ".gitattributes").write_text("*.txt filter=probe\n", encoding="utf-8")
            (inner / "f.txt").write_text("a\n", encoding="utf-8")
            _git(outer, "add", ".gitattributes", "inner/f.txt")
            _git(outer, "commit", "-q", "-m", "init")
            _git(outer, "config", "filter.probe.clean", str(script))
            (inner / "f.txt").write_text("b\n", encoding="utf-8")
            evidence = _fence(
                "git status --porcelain", prose="Process exit: 0\n"
            ) + _fence("git diff --stat", prose="Process exit: 0\n")
            result = replay.replay_evidence(evidence, repo_root=inner)
            self.assertFalse(canary.exists(), result)
        self.assertEqual(
            [(pair["action"], pair["reason"]) for pair in result["pairs"]],
            [("denied", "git_no_repo"), ("denied", "git_no_repo")],
            result,
        )
        self.assertTrue(result["unreplayable"], result)

    def test_replay_git_dir_states_are_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bare = base / "no-repo"
            bare.mkdir()
            no_repo = replay.ReplayGitDir.open(bare)
            self.assertIs(no_repo.state, replay.GitDirState.NO_REPO)
            with self.assertRaisesRegex(replay.ReplayDenied, "^git_no_repo$"):
                no_repo.env_updates()
            no_repo.close()
            self.assertIs(no_repo.state, replay.GitDirState.CLOSED)

            root = base / "repo"
            root.mkdir()
            _git(root, "init", "-q")
            isolated = replay.ReplayGitDir.open(root)
            self.assertIs(isolated.state, replay.GitDirState.ISOLATED)
            env = isolated.env_updates()
            self.assertEqual(env["GIT_WORK_TREE"], str(root.resolve()))
            self.assertTrue(Path(env["GIT_DIR"]).is_dir())
            self.assertNotEqual(Path(env["GIT_DIR"]), (root / ".git").resolve())
            isolated.close()
            self.assertIs(isolated.state, replay.GitDirState.CLOSED)
            self.assertFalse(Path(env["GIT_DIR"]).exists())
            with self.assertRaisesRegex(replay.ReplayDenied, "^git_dir_closed$"):
                isolated.env_updates()

    def test_replay_env_stops_git_discovery_at_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve() / "repo"
            root.mkdir()
            env = replay.replay_env(root)
        self.assertEqual(env["GIT_CEILING_DIRECTORIES"], str(root.parent))

    def test_run_id_cannot_escape_out_dir(self) -> None:
        import run as runmod

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            out.mkdir()
            code = runmod.main(
                [
                    "--dry-run",
                    "--out-dir",
                    str(out),
                    "--run-id",
                    "../escape",
                    str(REPO_ROOT / "tasks" / "001-units-trap.md"),
                ]
            )
            self.assertEqual(code, 2)
            self.assertFalse((Path(tmp) / "escape").exists())


def _required_verification_section(text: str) -> str | None:
    match = re.search(r"^##[ \t]+Required verification[ \t]*$", text, re.M)
    if match is None:
        return None
    rest = text[match.end() :]
    next_heading = re.search(r"^##[ \t]+", rest, re.M)
    if next_heading is not None:
        rest = rest[: next_heading.start()]
    return rest


def _strip_scorer_contract_fences(section: str) -> str:
    return re.sub(
        r"^```scorer-contract\n.*?^```",
        "",
        section,
        flags=re.M | re.S,
    )


if __name__ == "__main__":
    unittest.main()
