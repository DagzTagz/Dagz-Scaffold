#!/usr/bin/env python3
"""Parse and match a task's fenced JSON scorer-contract."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import NamedTuple

DUMP_ARROW = " -> "


class ContractError(Exception):
    """Malformed or unsafe task contract. Scorer maps this to ScoreError."""


class TaskContract(NamedTuple):
    path: Path
    must_appear: tuple[str, ...]
    red_then_green: bool


class Fence(NamedTuple):
    """One top-level backtick fence. start/end are offsets into the text:
    start is the opener line's first character, end is just past the
    closer's backticks (before its newline)."""

    info: str
    body: str
    start: int
    end: int
    ticks: int


_FENCE_LINE = re.compile(r"^( {0,3})(`{3,})[ \t]*(.*)$")


def parse_fence_line(line: str) -> tuple[int, str] | None:
    """Return (tick_count, info) for a backtick fence line, else None."""
    m = _FENCE_LINE.match(line.rstrip("\r\n"))
    if m is None or "`" in m.group(3):
        return None
    return len(m.group(2)), m.group(3).strip()


def _is_closer(line: str, ticks: int) -> bool:
    fence = parse_fence_line(line)
    return fence is not None and fence[1] == "" and fence[0] >= ticks


def lex_fences(text: str) -> list[Fence]:
    """The one Markdown fence lexer the harness uses (audit F9).

    Line mode, two states:
    - OUTSIDE: a line of 3+ backticks (up to 3 spaces of indent) whose info
      has no backtick opens a fence.
    - INSIDE(ticks): a line of >= ticks backticks with no info closes it.
      Backticks anywhere else, including mid-line, are body text.

    A ``markdown`` fence quotes a document, so a fence with an info string
    inside it is skipped as a unit and cannot close the outer one. A fence
    that never closes is not a fence, and lexing stops there.
    """
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    fences: list[Fence] = []
    i = 0
    while i < len(lines):
        opener = parse_fence_line(lines[i])
        if opener is None:
            i += 1
            continue
        ticks, info = opener
        quoted = info.split(" ", 1)[0] == "markdown"
        j = i + 1
        while j < len(lines) and not _is_closer(lines[j], ticks):
            inner = parse_fence_line(lines[j]) if quoted else None
            j += 1
            if inner is not None and inner[1] != "":
                while j < len(lines) and not _is_closer(lines[j], inner[0]):
                    j += 1
                j += 1
        if j >= len(lines):
            break
        closer = lines[j]
        end = offsets[j] + len(closer.rstrip("\r\n"))
        body = "".join(lines[i + 1 : j])
        fences.append(Fence(info, body, offsets[i], end, ticks))
        i = j + 1
    return fences


def extract_fences(text: str) -> list[tuple[str, str]]:
    """List of (info_string, body) in order, from lex_fences."""
    return [(f.info, f.body) for f in lex_fences(text)]


def fold_quotes(s: str) -> str:
    return s.replace("'", '"')


def fold_comma_ws(s: str) -> str:
    """Collapse whitespace after commas inside [...] and (...)."""

    def inner(m: re.Match[str]) -> str:
        return m.group(1) + re.sub(r",\s*", ", ", m.group(2).strip()) + m.group(3)

    return re.sub(r"([\(\[])([^()\[\]]*?)([\)\]])", inner, s)


def token_hits(token: str, lines: list[str]) -> bool:
    needle = fold_comma_ws(fold_quotes(token))
    folded = [fold_comma_ws(fold_quotes(ln.strip())) for ln in lines]
    if DUMP_ARROW in needle:
        return needle in folded
    return any(needle in ln for ln in folded)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    # json.loads last-wins on duplicates; the contract must not be ambiguous.
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f"task contract duplicate key: {key}")
        out[key] = value
    return out


def _required_verification_section(text: str) -> str | None:
    match = re.search(r"^##[ \t]+Required verification[ \t]*$", text, re.M)
    if match is None:
        return None
    rest = text[match.end() :]
    next_heading = re.search(r"^##[ \t]+", rest, re.M)
    if next_heading is not None:
        rest = rest[: next_heading.start()]
    return rest


def parse_task_contract(text: str, path: Path) -> TaskContract | None:
    section = _required_verification_section(text)
    if section is None:
        return None
    contract_body = None
    for info, body in extract_fences(section):
        if info.strip() == "scorer-contract":
            contract_body = body
            break
    if contract_body is None:
        return None
    try:
        data = json.loads(contract_body, object_pairs_hook=_reject_duplicate_keys)
    except ContractError:
        raise
    except json.JSONDecodeError as exc:
        raise ContractError(f"task contract is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ContractError("task contract must be a JSON object")
    allowed = {"must_appear", "red_then_green"}
    missing = allowed - data.keys()
    extra = data.keys() - allowed
    if missing:
        raise ContractError(
            "task contract missing keys: " + ", ".join(sorted(missing))
        )
    if extra:
        raise ContractError(
            "task contract unexpected keys: " + ", ".join(sorted(extra))
        )
    must_appear = data["must_appear"]
    if not isinstance(must_appear, list) or not all(
        isinstance(item, str) for item in must_appear
    ):
        raise ContractError("task contract must_appear must be an array of strings")
    red_then_green = data["red_then_green"]
    if not isinstance(red_then_green, bool):
        raise ContractError("task contract red_then_green must be a JSON boolean")
    return TaskContract(
        path=path,
        must_appear=tuple(must_appear),
        red_then_green=red_then_green,
    )


def _git_repo(repo_root: Path) -> bool:
    git = shutil.which("git")
    if not git:
        return False
    completed = subprocess.run(
        [git, "-c", "core.fsmonitor=", "-c", "core.hooksPath=/dev/null", "rev-parse", "--is-inside-work-tree"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    return completed.returncode == 0 and completed.stdout.strip() == "true"


def _head_task_text(repo_root: Path, rel: str) -> str | None:
    git = shutil.which("git")
    if not git:
        return None
    completed = subprocess.run(
        [
            git,
            "-c",
            "core.fsmonitor=",
            "-c",
            "core.hooksPath=/dev/null",
            "show",
            f"HEAD:{rel}",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout


def load_task_contract(repo_root: Path, task_rel: str) -> TaskContract | None:
    repo_root = repo_root.resolve()
    tasks_root = (repo_root / "tasks").resolve()
    raw = Path(task_rel)
    candidate = raw if raw.is_absolute() else (repo_root / raw)
    if candidate.is_symlink():
        raise ContractError(f"task path is a symlink: {task_rel}")
    resolved = candidate.resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ContractError(f"task path escapes repo: {task_rel}") from exc
    try:
        resolved.relative_to(tasks_root)
    except ValueError as exc:
        raise ContractError(f"task path is not under tasks/: {task_rel}") from exc
    if not resolved.is_file():
        raise ContractError(f"task path is not a file: {task_rel}")
    text = resolved.read_text(encoding="utf-8")
    rel = resolved.relative_to(repo_root).as_posix()
    if _git_repo(repo_root):
        head = _head_task_text(repo_root, rel)
        if head is None:
            raise ContractError(f"task file is not committed at HEAD: {task_rel}")
        if head.replace("\r\n", "\n") != text.replace("\r\n", "\n"):
            raise ContractError(f"task file differs from HEAD: {task_rel}")
    return parse_task_contract(text, resolved)
