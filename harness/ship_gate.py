#!/usr/bin/env python3
"""Ship-gate a Dagz-Scaffold run folder. Local files only. No network.

`python harness/ship_gate.py` puts harness/ on sys.path, so `import score`
resolves. Do not pass replay= to score_run (PR4 adds that).
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path, PurePosixPath

import checkout_git
from score import ScoreError, gate_passes, load_schema, score_run

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


NO_REPO_BLOCK = (
    "git_no_repo: --git-checks needs a git clone of Dagz-Scaffold, and this "
    "checkout has no .git of its own. Git is not allowed to use an enclosing "
    "repository."
)
NOT_TOP_BLOCK = (
    "git_not_checkout_root: git's work tree top is not this checkout, so its "
    "index is not this checkout's index."
)


def default_git_runner(root: Path, args: list[str]) -> str:
    """git in the checkout only: no upward discovery, no inherited GIT_DIR."""
    completed = checkout_git.run_git(root, args)
    if completed.returncode != 0:
        raise GitError(completed.returncode, completed.stderr)
    return completed.stdout


def checkout_blocks(root: Path, *, runner) -> list[str]:
    """Refuse unless git's top-level directory is exactly this checkout."""
    try:
        top = runner(root, ["rev-parse", "--show-toplevel"]).strip()
    except FileNotFoundError:
        return ["git_missing"]
    except GitError:
        return [NO_REPO_BLOCK]
    try:
        same = bool(top) and Path(top).resolve() == Path(root).resolve()
    except OSError:
        same = False
    return [] if same else [NOT_TOP_BLOCK]


def is_live_run_path(name: str) -> bool:
    """True for a staged path under the checkout's runs/, except the placeholder.

    Paths come from a repository whose top is the checkout (checkout_blocks),
    so they are relative to the checkout root.
    """
    parts = PurePosixPath(name).parts
    return bool(parts) and parts[0] == "runs" and parts != ("runs", ".gitkeep")


def git_index_blocks(root: Path, *, runner) -> list[str]:
    """Staged names OR staged blobs. Fail closed if git is missing.

    Fails closed, before reading any index, when the checkout is not the top
    of its own repository (a ZIP or vendored copy inside another repo).
    """
    preflight = checkout_blocks(root, runner=runner)
    if preflight:
        return preflight
    try:
        names = runner(root, ["diff", "--cached", "--name-only", "-z"])
    except FileNotFoundError:
        return ["git_missing"]
    except GitError:
        return ["git_error"]
    blocks: list[str] = []
    staged = [n for n in names.split("\0") if n]
    for n in staged:
        if is_live_run_path(n):
            blocks.append(f"staged live run: {n}")
        if SECRET_NAME.search(Path(n).name) and n != ".env.example":
            blocks.append(f"staged secret name: {n}")
    for n in staged:
        try:
            blob = runner(root, ["show", "--no-textconv", f":{n}"])
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

    blocks, result = gate_run(
        run_dir,
        honor_override=args.honor_override,
        git_checks=args.git_checks,
        git_runner=git_runner,
    )
    if blocks:
        print("SHIP-GATE: BLOCK")
        for b in blocks:
            print(f"- {b}")
        return 1
    print("SHIP-GATE: PASS")
    print(result["summary"])
    return 0


def gate_run(
    run_dir: Path,
    *,
    honor_override: bool = False,
    git_checks: bool = False,
    git_runner=None,
) -> tuple[list[str], dict]:
    """Return (blocks, score result). An empty block list means PASS.

    harness/run.py calls this too, so the live loop and the CLI gate a run
    the same way.
    """
    try:
        result = score_run(
            run_dir, load_schema(SCHEMA), honor_override=honor_override
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
    if not gate_passes(score, honor_override=honor_override):
        blocks.append("REJECT")
    blocks.extend(run_folder_blocks(run_dir))
    if git_checks:
        runner = git_runner if git_runner is not None else default_git_runner
        blocks.extend(git_index_blocks(REPO_ROOT, runner=runner))
    return list(dict.fromkeys(blocks)), result


if __name__ == "__main__":
    sys.exit(main())
