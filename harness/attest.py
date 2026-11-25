#!/usr/bin/env python3
"""Authenticate score.py output so a hand-written score-result.json is caught.

Stdlib only. No network.

`score.py --attest-key KEY RUN_DIR` adds an `attestation` object to its JSON:

    {
      "schema": "dagz-scaffold/score-attestation/v1",
      "alg": "hmac-sha256",
      "kid": first 16 hex chars of SHA-256(key),
      "inputs": {"plan.md": sha256, "evidence.md": ..., "critic.md": ..., "score.json": ...},
      "mac": hex HMAC-SHA256(key, canonical({"attestation": <the above without mac>,
                                              "result": <every other top-level field>}))
    }

canonical() is UTF-8 JSON with sort_keys=True, separators=(",", ":"),
ensure_ascii=False and allow_nan=False, the same rule vesper-runtime uses.

Trust assumption, stated plainly: this is a shared-secret MAC. Anyone who can
read the key file can make a valid attestation. It proves "someone holding the
scorer key scored exactly these four files and got this result". It only stops
an agent from forging a pass when the agent cannot read the key: keep the key
outside the checkout and outside the run folder, readable only by the account
that scores (and the account that binds). If the agent runs as that same OS
account, it can read the key and this adds nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import stat
import sys
from pathlib import Path

SCHEMA = "dagz-scaffold/score-attestation/v1"
ALG = "hmac-sha256"
INPUT_FILES = ("plan.md", "evidence.md", "critic.md", "score.json")
KEY_ENV = "DAGZ_SCORER_KEY_FILE"
ATTESTATION_FIELD = "attestation"
_KEY_MAX = 4096
_INPUT_MAX = 8 * 1024 * 1024


class AttestError(Exception):
    """The key or an attestation cannot be used. Fail closed."""


def canonical_bytes(obj: object) -> bytes:
    try:
        text = json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise AttestError("value is not canonical JSON") from exc
    return text.encode("utf-8")


def _read_nofollow(path: Path, limit: int) -> tuple[bytes, os.stat_result]:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise AttestError(f"cannot open {path.name} (missing, or a symlink)") from exc
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise AttestError(f"{path.name} is not a regular file")
        if info.st_size > limit:
            raise AttestError(f"{path.name} is too large")
        chunks: list[bytes] = []
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                break
            chunks.append(block)
        return b"".join(chunks), info
    finally:
        os.close(fd)


def read_key(path: Path) -> bytes:
    """Read a scorer key: a regular file you own, mode 0600 or 0400, hex text."""
    data, info = _read_nofollow(Path(path), _KEY_MAX)
    if hasattr(os, "geteuid") and info.st_uid != os.geteuid():
        raise AttestError("scorer key is not owned by this user")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise AttestError("scorer key must be mode 0600 or 0400 (group and others: no access)")
    try:
        key = bytes.fromhex(data.decode("ascii").strip())
    except (UnicodeDecodeError, ValueError) as exc:
        raise AttestError("scorer key is not hex text") from exc
    if len(key) < 32:
        raise AttestError("scorer key is shorter than 32 bytes")
    return key


def write_new_key(path: Path) -> str:
    """Create a new 32-byte key at path, mode 0600. Never overwrite."""
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        fd = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
    except FileExistsError as exc:
        raise AttestError(f"refusing to overwrite {path}") from exc
    try:
        os.fchmod(fd, 0o600)
        os.write(fd, (secrets.token_hex(32) + "\n").encode("ascii"))
    finally:
        os.close(fd)
    return key_id(read_key(path))


def key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def refuse_key_inside(key_path: Path, *dirs: Path) -> None:
    """A key the agent can write next to (checkout, run folder) proves nothing."""
    resolved = Path(key_path).resolve()
    for directory in dirs:
        try:
            resolved.relative_to(Path(directory).resolve())
        except ValueError:
            continue
        raise AttestError(
            f"scorer key must live outside {directory} (the agent can write there)"
        )


def input_digests(run_dir: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in INPUT_FILES:
        data, _info = _read_nofollow(Path(run_dir) / name, _INPUT_MAX)
        out[name] = hashlib.sha256(data).hexdigest()
    return out


def _mac(key: bytes, result: dict, header: dict) -> str:
    body = canonical_bytes({"attestation": header, "result": result})
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def attest(result: dict, run_dir: Path, key: bytes) -> dict:
    """Return the attestation object for this result. result must not have one."""
    if ATTESTATION_FIELD in result:
        raise AttestError("result already has an attestation")
    header = {
        "schema": SCHEMA,
        "alg": ALG,
        "kid": key_id(key),
        "inputs": input_digests(run_dir),
    }
    return {**header, "mac": _mac(key, result, header)}


def verify(document: dict, run_dir: Path, key: bytes) -> None:
    """Raise AttestError unless document carries a valid attestation for run_dir."""
    att = document.get(ATTESTATION_FIELD)
    if not isinstance(att, dict):
        raise AttestError("score result is not attested")
    if set(att) != {"schema", "alg", "kid", "inputs", "mac"}:
        raise AttestError("attestation fields are wrong")
    if att["schema"] != SCHEMA or att["alg"] != ALG:
        raise AttestError("attestation schema or alg is not supported")
    if not isinstance(att["kid"], str) or not hmac.compare_digest(att["kid"], key_id(key)):
        raise AttestError("attestation was made with a different scorer key")
    result = {k: v for k, v in document.items() if k != ATTESTATION_FIELD}
    header = {k: att[k] for k in ("schema", "alg", "kid", "inputs")}
    mac = att["mac"]
    if not isinstance(mac, str) or not hmac.compare_digest(mac, _mac(key, result, header)):
        raise AttestError("attestation MAC does not match (file edited or forged)")
    if att["inputs"] != input_digests(run_dir):
        raise AttestError("attested files changed after scoring")


def resolve_key_path(flag: str | None) -> Path | None:
    raw = flag if flag else os.environ.get(KEY_ENV)
    return Path(raw).expanduser() if raw else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scorer key and attestation helper")
    sub = parser.add_subparsers(dest="cmd", required=True)
    keygen = sub.add_parser("keygen", help="create a new scorer key (mode 0600)")
    keygen.add_argument("path", type=Path)
    check = sub.add_parser("verify", help="check RUN_DIR/score-result.json")
    check.add_argument("run_dir", type=Path)
    check.add_argument("--key", default=None, help=f"scorer key file (default: ${KEY_ENV})")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "keygen":
            kid = write_new_key(args.path)
            print(f"wrote scorer key {args.path} (kid {kid}, mode 0600)")
            print("Keep it outside the checkout and run folders, readable only by the scoring account.")
            return 0
        key_path = resolve_key_path(args.key)
        if key_path is None:
            print(f"error: pass --key or set {KEY_ENV}", file=sys.stderr)
            return 2
        key = read_key(key_path)
        data, _info = _read_nofollow(args.run_dir / "score-result.json", _INPUT_MAX)
        document = json.loads(data.decode("utf-8"))
        if not isinstance(document, dict):
            raise AttestError("score-result.json is not an object")
        verify(document, args.run_dir, key)
    except (AttestError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("attestation OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
