#!/usr/bin/env python3
"""Score a Dagz-Scaffold run folder. Local files only. No network."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REQUIRED_FILES = ("plan.md", "critic.md", "evidence.md", "score.json")
VERDICTS = ("REJECT", "ACCEPT WITH WAIVERS", "ACCEPT")
CRITIC_HEADINGS = (
    "BLOCKERS",
    "RISKS",
    "NITS",
    "MISSING EVIDENCE",
    "VERDICT",
)
QUIT_EARLY_PATTERNS = (
    re.compile(r"\btoo hard\b", re.I),
    re.compile(r"\bshould work\b", re.I),
    re.compile(r"\bgave up\b", re.I),
    re.compile(r"\bwon'?t (?:do|implement|finish)\b", re.I),
    re.compile(r"\bdone before verif", re.I),
)


class ScoreError(Exception):
    """Local validation failure."""


def load_schema(schema_path: Path) -> dict:
    return json.loads(schema_path.read_text(encoding="utf-8"))


def _check_type(value: object, expected: str, path: str, errors: list[str]) -> bool:
    mapping = {
        "object": dict,
        "array": list,
        "string": str,
        "integer": int,
        "boolean": bool,
        "number": (int, float),
    }
    ok_types = mapping[expected]
    if expected == "integer" and isinstance(value, bool):
        errors.append(f"{path}: expected integer")
        return False
    if expected == "number" and isinstance(value, bool):
        errors.append(f"{path}: expected number")
        return False
    if not isinstance(value, ok_types):
        errors.append(f"{path}: expected {expected}")
        return False
    return True


def validate_schema(instance: object, schema: dict, path: str = "$") -> list[str]:
    errors: list[str] = []
    expected = schema.get("type")
    if expected and not _check_type(instance, expected, path, errors):
        return errors

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in {schema['enum']}")

    if isinstance(instance, str) and instance.strip() == "" and schema.get("minLength", 0) > 0:
        errors.append(f"{path}: empty string")
    if isinstance(instance, str) and len(instance) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than minLength")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")

    if schema.get("type") == "object" and isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}: missing required {key}")
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            if key in props:
                errors.extend(validate_schema(value, props[key], f"{path}.{key}"))
            elif additional is False:
                errors.append(f"{path}: unexpected property {key}")
            elif isinstance(additional, dict):
                errors.extend(validate_schema(value, additional, f"{path}.{key}"))

    if schema.get("type") == "array" and isinstance(instance, list):
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(instance):
                errors.extend(validate_schema(item, item_schema, f"{path}[{i}]"))
    return errors


def parse_critic(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for heading in CRITIC_HEADINGS:
        pattern = re.compile(
            rf"^##\s+{re.escape(heading)}\s*$",
            re.I | re.M,
        )
        if not pattern.search(text):
            raise ScoreError(f"critic.md missing heading ## {heading}")
    parts = re.split(r"^##\s+", text, flags=re.M)
    for part in parts[1:]:
        lines = part.splitlines()
        name = lines[0].strip().upper()
        body = "\n".join(lines[1:]).strip()
        found[name] = body
    return found


def critic_verdict(body: str) -> str:
    for line in body.splitlines():
        candidate = line.strip().strip("*").strip("`")
        if candidate in VERDICTS:
            return candidate
    raise ScoreError("critic.md VERDICT is not REJECT | ACCEPT WITH WAIVERS | ACCEPT")


def section_is_empty(body: str) -> bool:
    text = body.strip().lower()
    if text in {"", "- none", "none", "- n/a", "n/a"}:
        return True
    bullets = [ln for ln in body.splitlines() if ln.strip().startswith("-")]
    if bullets and all(re.match(r"^-\s*(none|n/a)\s*$", ln.strip(), re.I) for ln in bullets):
        return True
    return False


def scan_quit_early(text: str) -> list[str]:
    hits: list[str] = []
    for pattern in QUIT_EARLY_PATTERNS:
        hits.extend(m.group(0) for m in pattern.finditer(text))
    return sorted(set(hits))


def strip_markdown_fences(text: str) -> str:
    """Drop ```markdown ... ``` blocks (quoted task excerpts) before scanning evidence."""
    return re.sub(r"^```markdown\n.*?^```", "", text, flags=re.M | re.S)


def scan_quit_early_by_file(plan: str, evidence: str, critic: str) -> dict[str, list[str]]:
    return {
        "plan": scan_quit_early(plan),
        "evidence": scan_quit_early(strip_markdown_fences(evidence)),
        "critic": scan_quit_early(critic),
    }


def evidence_has_commands(text: str) -> bool:
    return bool(
        re.search(r"^(\$ |python3? |git |pytest |grok )", text, re.M)
    ) or "```" in text


def load_score(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ScoreError(f"score.json is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ScoreError("score.json must be an object")
    return data


def score_run(run_dir: Path, schema: dict) -> dict:
    missing = [name for name in REQUIRED_FILES if not (run_dir / name).is_file()]
    if missing:
        raise ScoreError(f"missing artifacts: {', '.join(missing)}")

    plan = (run_dir / "plan.md").read_text(encoding="utf-8")
    critic_text = (run_dir / "critic.md").read_text(encoding="utf-8")
    evidence = (run_dir / "evidence.md").read_text(encoding="utf-8")
    payload = load_score(run_dir / "score.json")

    schema_errors = validate_schema(payload, schema)
    if schema_errors:
        raise ScoreError("schema: " + "; ".join(schema_errors))

    sections = parse_critic(critic_text)
    parsed_verdict = critic_verdict(sections["VERDICT"])
    if parsed_verdict != payload["verdict"]:
        raise ScoreError(
            f"verdict mismatch: critic.md={parsed_verdict!r} score.json={payload['verdict']!r}"
        )

    if payload["verdict"] == "ACCEPT WITH WAIVERS" and not payload["waivers"]:
        raise ScoreError("ACCEPT WITH WAIVERS requires explicit waivers")
    if payload["verdict"] == "ACCEPT" and payload["waivers"]:
        raise ScoreError("ACCEPT cannot carry waivers; use ACCEPT WITH WAIVERS")

    artifacts = payload["artifacts"]
    for name in REQUIRED_FILES:
        if artifacts.get(name) is not True:
            raise ScoreError(f"artifacts.{name} must be true")

    blockers_empty = section_is_empty(sections["BLOCKERS"])
    if payload["verdict"] != "REJECT" and not blockers_empty:
        raise ScoreError("non-REJECT verdict with BLOCKERS present")
    if payload["verdict"] == "REJECT" and blockers_empty:
        raise ScoreError("REJECT requires at least one BLOCKER")

    missing_ev_section = not section_is_empty(sections["MISSING EVIDENCE"])
    commands_ok = evidence_has_commands(evidence)
    derived_missing = missing_ev_section or not commands_ok or not evidence.strip()
    if payload["missing_evidence"] != derived_missing and derived_missing:
        # Scorer is stricter than the file: treat as missing evidence.
        payload = dict(payload)
        payload["missing_evidence"] = True

    scans_quit_early = scan_quit_early_by_file(plan, evidence, critic_text)
    if scans_quit_early["evidence"]:
        payload = dict(payload)
        payload["quit_early"] = True

    fail_reasons: list[str] = []
    if payload["quit_early"]:
        fail_reasons.append("quit_early")
    if payload["verdict"] == "REJECT":
        fail_reasons.append("REJECT")
    if payload["missing_evidence"]:
        fail_reasons.append("missing_evidence")
    if not commands_ok:
        fail_reasons.append("evidence_has_no_commands")
        payload["missing_evidence"] = True

    first_line = next((ln.strip() for ln in evidence.splitlines() if ln.strip()), "")
    if first_line.startswith("DRY-RUN MOCK") or payload["notes"].startswith(
        "Synthetic dry-run"
    ):
        fail_reasons.append("dry_run")

    fail_reasons = list(dict.fromkeys(fail_reasons))

    summary = (
        f"{payload['verdict']} persistence={payload['persistence']} "
        f"rigor={payload['rigor']} quit_early={payload['quit_early']} "
        f"missing_evidence={payload['missing_evidence']}"
    )
    return {
        "ok": not fail_reasons,
        "fail_reasons": fail_reasons,
        "summary": summary,
        "score": payload,
        "critic_verdict": parsed_verdict,
        "run_dir": str(run_dir),
        "scans": {"quit_early": scans_quit_early},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a Dagz-Scaffold run folder")
    parser.add_argument("run_dir", type=Path, help="Path to a run folder")
    args = parser.parse_args(argv)

    run_dir = args.run_dir.resolve()
    if not run_dir.is_dir():
        print(f"error: not a directory: {run_dir}", file=sys.stderr)
        return 2

    schema_path = Path(__file__).resolve().parent / "schema" / "run.schema.json"
    try:
        result = score_run(run_dir, load_schema(schema_path))
    except ScoreError as exc:
        error_doc = {
            "ok": False,
            "fail_reasons": [str(exc)],
            "summary": f"INVALID {exc}",
            "run_dir": str(run_dir),
        }
        json.dump(error_doc, sys.stdout, indent=2)
        sys.stdout.write("\n")
        print(error_doc["summary"], file=sys.stderr)
        return 1

    json.dump(
        {
            k: result[k]
            for k in (
                "ok",
                "fail_reasons",
                "summary",
                "critic_verdict",
                "run_dir",
                "score",
                "scans",
            )
        },
        sys.stdout,
        indent=2,
    )
    sys.stdout.write("\n")
    print(result["summary"], file=sys.stderr)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
