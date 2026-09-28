#!/usr/bin/env python3
"""Ship-gate a Dagz-Scaffold run folder. Local files only. No network.

`python harness/ship_gate.py` puts harness/ on sys.path, so `import score`
resolves. Do not pass replay= to score_run (PR4 adds that).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

from score import ScoreError, load_schema, score_run

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = Path(__file__).resolve().parent / "schema" / "run.schema.json"

SECRET_NAME = re.compile(
    r"(\.env$|\.envrc$|\.env\.[^.]+$|\.pem$|\.key$|\.p12$|\.pfx$|\.npmrc$|\.netrc$"
    r"|id_rsa|id_ed25519|id_ecdsa|auth\.json|credentials\.json)",
    re.I,
)
# [ \t] not \s after '=': a newline would let \S+ eat the next empty key name.
SECRET_CONTENT = re.compile(
    r"XAI_API_KEY[ \t]*=[ \t]*\S+|GITHUB_TOKEN[ \t]*=[ \t]*\S+"
    r"|BEGIN (?:OPENSSH |RSA |EC |DSA |ENCRYPTED )?PRIVATE KEY"
    r"|AKIA[0-9A-Z]{16}|xai-[A-Za-z0-9_-]{20,}"
    r"|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
)


class GitError(Exception):
    """Non-zero git exit. Not a clean index."""


def default_git_runner(root: Path, args: list[str]) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise GitError(completed.returncode, completed.stderr)
    return completed.stdout


def git_index_blocks(root: Path, *, runner) -> list[str]:
    """Staged names OR staged blobs. Fail closed if git is missing."""
    try:
        names = runner(root, ["diff", "--cached", "--name-only", "-z"])
    except FileNotFoundError:
        return ["git_missing"]
    except GitError:
        return ["git_error"]
    blocks: list[str] = []
    staged = [n for n in names.split("\0") if n]
    for n in staged:
        if n.startswith("runs/") and n != "runs/.gitkeep":
            blocks.append(f"staged live run: {n}")
        if SECRET_NAME.search(Path(n).name) and n != ".env.example":
            blocks.append(f"staged secret name: {n}")
    for n in staged:
        try:
            blob = runner(root, ["show", f":{n}"])
        except GitError:
            return ["git_error"]
        except FileNotFoundError:
            return ["git_missing"]
        if SECRET_CONTENT.search(blob):
            blocks.append(f"staged secret content: {n}")
    return blocks


def _read_nofollow(path: Path, limit: int = 1_000_000) -> str | None:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
    except OSError:
        return None
    with os.fdopen(fd, "r", encoding="utf-8", errors="replace") as handle:
        return handle.read(limit)


def run_folder_blocks(run_dir: Path) -> list[str]:
    """Secret material in the packet itself. Independent of the git index."""
    blocks: list[str] = []
    for path in sorted(run_dir.iterdir()):
        if path.is_symlink():
            blocks.append(f"symlink artifact: {path.name}")
            continue
        if not path.is_file():
            continue
        if SECRET_NAME.search(path.name):
            blocks.append(f"run secret name: {path.name}")
        text = _read_nofollow(path)
        if text is None:
            blocks.append(f"unreadable artifact: {path.name}")
            continue
        if SECRET_CONTENT.search(text):
            blocks.append(f"run secret content: {path.name}")
    return blocks


def main(argv: list[str] | None = None, *, git_runner=None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed on REJECT, missing evidence, secrets, staged runs/"
    )
    parser.add_argument("run_dir", type=Path, help="Path to a run folder")
    parser.add_argument(
        "--git-checks",
        action="store_true",
        help="Scan THIS clone's index. Off by default so sample-run smoke is hermetic.",
    )
    parser.add_argument(
        "--honor-override",
        action="store_true",
        help="Accept score.json override.by and override.reason. The file alone does not.",
    )
    args = parser.parse_args(argv)
    run_dir = args.run_dir.resolve()
    if not run_dir.is_dir():
        print(f"error: not a directory: {run_dir}", file=sys.stderr)
        return 2

    try:
        result = score_run(
            run_dir, load_schema(SCHEMA), honor_override=args.honor_override
        )
    except ScoreError as exc:
        result = {
            "ok": False,
            "fail_reasons": [str(exc)],
            "summary": f"INVALID {exc}",
            "run_dir": str(run_dir),
            "score": {},
        }

    blocks: list[str] = []
    if not result.get("ok"):
        blocks.extend(result.get("fail_reasons") or ["score_not_ok"])
    score = result.get("score") or {}
    if score.get("verdict") == "REJECT" and not args.honor_override:
        blocks.append("REJECT")
    elif score.get("verdict") == "REJECT":
        ov = score.get("override") if isinstance(score.get("override"), dict) else {}
        if not (str(ov.get("by") or "").strip() and str(ov.get("reason") or "").strip()):
            blocks.append("REJECT")
    blocks.extend(run_folder_blocks(run_dir))
    if args.git_checks:
        runner = git_runner if git_runner is not None else default_git_runner
        blocks.extend(git_index_blocks(REPO_ROOT, runner=runner))
    blocks = list(dict.fromkeys(blocks))
    if blocks:
        print("SHIP-GATE: BLOCK")
        for b in blocks:
            print(f"- {b}")
        return 1
    print("SHIP-GATE: PASS")
    print(result["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
