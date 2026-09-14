#!/usr/bin/env python3
"""Parse and match a task's fenced JSON scorer-contract."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import NamedTuple

DUMP_ARROW = " -> "


class ContractError(Exception):
    """Malformed or unsafe task contract. Scorer maps this to ScoreError."""


class TaskContract(NamedTuple):
    path: Path
    must_appear: tuple[str, ...]
    red_then_green: bool


def extract_fences(text: str) -> list[tuple[str, str]]:
    """List of (info_string, body) in order. Info is the token after ```."""
    return re.findall(r"^```([^\n]*)\n(.*?)```", text, flags=re.M | re.S)


def fold_quotes(s: str) -> str:
    return s.replace("'", '"')


def fold_comma_ws(s: str) -> str:
    """Collapse whitespace after commas inside [...] and (...)."""

    def inner(m: re.Match[str]) -> str:
        return m.group(1) + re.sub(r",\s*", ", ", m.group(2).strip()) + m.group(3)

    return re.sub(r"([\(\[])([^()\[\]]*?)([\)\]])", inner, s)


def token_hits(token: str, lines: list[str]) -> bool:
    needle = fold_comma_ws(fold_quotes(token))
    folded = [fold_comma_ws(fold_quotes(ln.rstrip())) for ln in lines]
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


def load_task_contract(repo_root: Path, task_rel: str) -> TaskContract | None:
    repo_root = repo_root.resolve()
    tasks_root = (repo_root / "tasks").resolve()
    raw = Path(task_rel)
    resolved = raw.resolve() if raw.is_absolute() else (repo_root / raw).resolve()
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
    return parse_task_contract(resolved.read_text(encoding="utf-8"), resolved)
