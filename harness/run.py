#!/usr/bin/env python3
"""Thin wrapper around `grok -p` for a task file.

--dry-run writes mock artifacts and never calls the network or the model,
even if `grok` is installed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = ("plan.md", "critic.md", "evidence.md", "score.json")
REPO_ROOT = Path(__file__).resolve().parent.parent


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def slug(task_path: Path) -> str:
    return task_path.stem.replace(" ", "-")[:40]


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


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
    evidence = f"""# Evidence (dry-run mock)

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
        "persistence": 1.0,
        "rigor": 0.7,
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

Loop: plan first, then builder, then critic, then python harness/score.py {rel_run}.
REJECT returns to the builder. Do not quit early. Do not declare done without score.json.

Task:
---
{task_text}
---
"""


def run_live(task_path: Path, run_dir: Path, task_text: str) -> int:
    if not grok_available():
        print(
            "error: grok CLI not found on PATH. Install grok, or use --dry-run.",
            file=sys.stderr,
        )
        return 2
    run_dir.mkdir(parents=True, exist_ok=True)
    prompt = live_prompt(task_path, run_dir, task_text)
    cmd = ["grok", "-p", prompt, "--cwd", str(REPO_ROOT)]
    print("exec:", "grok", "-p", "<prompt>", "--cwd", str(REPO_ROOT), file=sys.stderr)
    completed = subprocess.run(cmd, check=False)
    return int(completed.returncode)


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
    run_dir = (args.out_dir.expanduser().resolve() / run_id)

    if args.dry_run:
        dry_run_artifacts(run_dir, task_path, task_text)
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
