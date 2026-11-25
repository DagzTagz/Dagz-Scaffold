"""Run git against this checkout only, never an enclosing repository.

ship_gate.py and task_contract.py use this. A copy of Dagz-Scaffold with no
`.git` of its own (a ZIP, a tarball, a vendored folder) that sits inside
another repository must not read that repository's index, HEAD, or config.
Same approach as the replay fix (2026-11-24): GIT_CEILING_DIRECTORIES stops
upward discovery, and `git rev-parse --show-toplevel` must be the checkout.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from enum import Enum
from pathlib import Path

# Variables that point git at a different repository, index, or object store.
# An inherited GIT_DIR would make the toplevel check below meaningless.
REPO_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_CEILING_DIRECTORIES",
    "GIT_DISCOVERY_ACROSS_FILESYSTEM",
    "GIT_CONFIG_PARAMETERS",
    "GIT_CONFIG_COUNT",
    "GIT_EXTERNAL_DIFF",
    "GIT_PAGER",
)
# Read-only lookups never need these. Command-line config wins over files.
CONFIG_OVERRIDES = (
    "core.fsmonitor=",
    "core.hooksPath=/dev/null",
    "diff.external=",
    "core.pager=cat",
    "maintenance.auto=false",
)


class CheckoutGit(Enum):
    """What git sees at the checkout root. Only OWN_REPO may be read."""

    OWN_REPO = "own_repo"  # the checkout is the top of its own work tree
    NO_REPO = "no_repo"  # no repository at or below the ceiling (ZIP, tarball)
    NOT_TOP = "not_top"  # a repository, but its top is not the checkout root
    GIT_MISSING = "git_missing"  # no git binary on PATH


def checkout_env(root: Path) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in REPO_ENV}
    for key in [k for k in env if k.startswith("GIT_CONFIG_KEY_") or k.startswith("GIT_CONFIG_VALUE_")]:
        env.pop(key)
    env["GIT_CEILING_DIRECTORIES"] = str(Path(root).resolve().parent)
    env["GIT_PAGER"] = "cat"
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def git_argv(args: list[str]) -> list[str]:
    git = shutil.which("git")
    if not git:
        raise FileNotFoundError("git")
    config: list[str] = []
    for item in CONFIG_OVERRIDES:
        config.extend(["-c", item])
    return [git, *config, *args]


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run git in the checkout root with repository discovery capped at it."""
    root = Path(root).resolve()
    return subprocess.run(
        git_argv(args),
        cwd=root,
        env=checkout_env(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def classify_checkout(root: Path) -> CheckoutGit:
    root = Path(root).resolve()
    try:
        completed = run_git(root, ["rev-parse", "--show-toplevel"])
    except FileNotFoundError:
        return CheckoutGit.GIT_MISSING
    if completed.returncode != 0:
        return CheckoutGit.NO_REPO
    top = completed.stdout.strip()
    if not top:
        return CheckoutGit.NOT_TOP
    try:
        same = Path(top).resolve() == root
    except OSError:
        return CheckoutGit.NOT_TOP
    return CheckoutGit.OWN_REPO if same else CheckoutGit.NOT_TOP
