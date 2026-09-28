#!/usr/bin/env python3
"""Thin wrapper around `grok -p` for a task file.

--dry-run writes mock artifacts and never calls the network or the model,
even if `grok` is installed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ("plan.md", "critic.md", "evidence.md", "score.json")
REPO_ROOT = Path(__file__).resolve().parent.parent


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")


def slug(task_path: Path) -> str:
    raw = re.sub(r"[^A-Za-z0-9._-]+", "-", task_path.stem)[:40].strip(".-")
    return raw or "task"


def write_text(path: Path, content: str) -> None:
    """Write a regular file. Do not follow a symlink that is already there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags, 0o644)
    except OSError as exc:
        raise OSError(f"refusing to follow symlink: {path}") from exc
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(content)


def run_directory(out_dir: Path, run_id: str) -> Path:
    if _RUN_ID.match(run_id) is None:
        raise ValueError(f"run id must be a single safe name, got {run_id!r}")
    parent = out_dir.expanduser().resolve()
    run_dir = (parent / run_id).resolve()
    try:
        run_dir.relative_to(parent)
    except ValueError as exc:
        raise ValueError(f"run directory escapes {parent}") from exc
    return run_dir


def dry_run_artifacts(run_dir: Path, task_path: Path, task_text: str) -> None:
    rel_task = os.path.relpath(task_path, REPO_ROOT)
    plan = f"""# Plan (dry-run mock)

Task: `{rel_task}`

This directory is a **local dry-run fixture**. `harness/run.py --dry-run`
did not call `grok`, the network, or the model.

## Files that a live run would touch

- `runs/<id>/plan.md`
- working tree diffs for the task
- `runs/<id>/critic.md`
- `runs/<id>/evidence.md`
- `runs/<id>/score.json`

## Verification a live run must execute

Commands listed in the task file under **Required verification**.

## Quit-early conditions

- declaring done before critic + score
- calling the task too hard without exhausting this plan
- silent scope cut
- stopping after one failed check

## Task excerpt

```markdown
{task_text.strip()[:2000]}
```
"""
    critic = """# Critic

## BLOCKERS
- none

## RISKS
- Dry-run mock: no real builder diffs exist in this folder.

## NITS
- Mock evidence is labeled synthetic so it cannot be mistaken for a live grok run.

## MISSING EVIDENCE
- none

## VERDICT
ACCEPT WITH WAIVERS
"""
    evidence = f"""DRY-RUN MOCK — not a live persist.
# Evidence (dry-run mock)

Skeptic notes: this folder was written by `python harness/run.py --dry-run`
without spawning a model.

## Commands

```
python harness/run.py --dry-run {rel_task}
python harness/score.py {run_dir}
```

## Output

Dry-run created:

- plan.md
- critic.md
- evidence.md
- score.json

No `grok` process was started. No sockets were opened.

## Diffs

None. Dry-run does not implement the task. Live mode would put diffs in the
working tree and quote `git diff` here.
"""
    score = {
        "schema_version": 1,
        "run_id": run_dir.name,
        "task": rel_task,
        "persistence": 0.0,
        "rigor": 0.0,
        "verdict": "ACCEPT WITH WAIVERS",
        "quit_early": False,
        "missing_evidence": False,
        "waivers": [
            {
                "id": "W-DRY-RUN",
                "reason": "No builder diffs; this run only proves the harness writes artifacts without calling the model.",
            }
        ],
        "artifacts": {
            "plan.md": True,
            "critic.md": True,
            "evidence.md": True,
            "score.json": True,
            "diffs": False,
        },
        "quit_early_markers": [],
        "notes": "Synthetic dry-run. Not a live grok session.",
    }
    write_text(run_dir / "plan.md", plan)
    write_text(run_dir / "critic.md", critic)
    write_text(run_dir / "evidence.md", evidence)
    write_text(run_dir / "score.json", json.dumps(score, indent=2) + "\n")


def grok_available() -> bool:
    return shutil.which("grok") is not None


def live_prompt(task_path: Path, run_dir: Path, task_text: str) -> str:
    rel_task = os.path.relpath(task_path, REPO_ROOT)
    rel_run = os.path.relpath(run_dir, REPO_ROOT)
    return f"""Follow AGENTS.md and the persist skill in this Dagz-Scaffold repo.

Task file: {rel_task}
Write all artifacts into: {rel_run}/
Required files: plan.md, critic.md, evidence.md, score.json plus real diffs.

Loop: plan first, then builder, then critic, then python harness/score.py {rel_run}, then python harness/ship_gate.py {rel_run} --git-checks.
If ship_gate.py exits non-zero, the run is not done. Do not skip this program.
REJECT returns to the builder. Do not quit early. Do not declare done without score.json.
Do not invent score.json override. Only a human may set override.by and override.reason, and only a human may pass --honor-override.

Task:
---
{task_text}
---
"""


def retry_prompt(task_path: Path, run_dir: Path, task_text: str) -> str:
    rel_task = os.path.relpath(task_path, REPO_ROOT)
    rel_run = os.path.relpath(run_dir, REPO_ROOT)
    critic = ""
    critic_path = run_dir / "critic.md"
    if critic_path.is_file():
        critic = critic_path.read_text(encoding="utf-8")[:8000]
    return f"""REJECT returns to the builder. Do not bargain the verdict down.
Do not invent score.json override. Do not pass --honor-override.

The previous persist of {rel_task} did not pass score.py / ship-gate.
Write artifacts into {rel_run}/. Fix the blockers and re-run verification.

Critic (blockers):
---
{critic or "(no critic.md yet)"}
---

Task:
---
{task_text}
---
"""


def _score_dir(run_dir: Path) -> dict:
    from score import ScoreError, load_schema, score_run

    schema = load_schema(Path(__file__).resolve().parent / "schema" / "run.schema.json")
    try:
        return score_run(run_dir, schema, replay=False)
    except ScoreError as exc:
        return {
            "ok": False,
            "fail_reasons": [str(exc)],
            "summary": f"INVALID {exc}",
            "score": {},
        }


def _record_attempts(run_dir: Path, n: int) -> None:
    path = run_dir / "score.json"
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    if not isinstance(data, dict):
        return
    data["attempts"] = int(n)
    try:
        write_text(path, json.dumps(data, indent=2) + "\n")
    except OSError as exc:
        print(f"error: not recording attempts: {exc}", file=sys.stderr)


def run_live(task_path: Path, run_dir: Path, task_text: str) -> int:
    if not grok_available():
        print(
            "error: grok CLI not found on PATH. Install grok, or use --dry-run.",
            file=sys.stderr,
        )
        return 2
    run_dir.mkdir(parents=True, exist_ok=True)
    max_calls = 2
    for call in range(1, max_calls + 1):
        prompt = (
            live_prompt(task_path, run_dir, task_text)
            if call == 1
            else retry_prompt(task_path, run_dir, task_text)
        )
        cmd = ["grok", "-p", prompt, "--cwd", str(REPO_ROOT)]
        print("exec:", "grok", "-p", "<prompt>", "--cwd", str(REPO_ROOT), file=sys.stderr)
        subprocess.run(cmd, check=False)
        result = _score_dir(run_dir)
        _record_attempts(run_dir, call)
        missing = [name for name in REQUIRED if not (run_dir / name).is_file()]
        ok = bool(result.get("ok")) and not missing
        verdict = (result.get("score") or {}).get("verdict")
        if ok:
            print(result.get("summary", "ok"), file=sys.stderr)
            return 0
        print(
            "live persist not ok:",
            result.get("summary") or result.get("fail_reasons") or missing,
            file=sys.stderr,
        )
        if verdict == "REJECT" and call < max_calls:
            print("REJECT returns to builder; retrying grok -p once", file=sys.stderr)
            continue
        if call < max_calls:
            print("score failed; retrying grok -p once", file=sys.stderr)
            continue
    print(
        "error: live persist did not pass score after 2 grok calls; not claiming success",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Dagz-Scaffold task via grok -p")
    parser.add_argument("task", type=Path, help="Path to a task markdown file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write mock artifacts. Never call grok or the network.",
    )
    parser.add_argument("--run-id", help="Optional run directory name under --out-dir")
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "runs",
        help="Parent directory for run folders (default: runs/)",
    )
    args = parser.parse_args(argv)

    task_path = args.task.expanduser()
    if not task_path.is_absolute():
        task_path = (Path.cwd() / task_path).resolve()
    if not task_path.is_file():
        print(f"error: task not found: {task_path}", file=sys.stderr)
        return 2

    task_text = task_path.read_text(encoding="utf-8")
    run_id = args.run_id or f"{utc_stamp()}-{slug(task_path)}"
    try:
        run_dir = run_directory(args.out_dir, run_id)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        try:
            dry_run_artifacts(run_dir, task_path, task_text)
        except OSError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        missing = [name for name in REQUIRED if not (run_dir / name).is_file()]
        if missing:
            print(f"error: dry-run failed to write {missing}", file=sys.stderr)
            return 1
        print(f"dry-run wrote {run_dir}")
        print("skipped grok: --dry-run does not call the model")
        return 0

    return run_live(task_path, run_dir, task_text)


if __name__ == "__main__":
    sys.exit(main())
