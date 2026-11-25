"""Scorer attestation tests. Imported from score_selftest.py. No pytest. No network."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import attest

HARNESS_DIR = Path(__file__).resolve().parent
REPO_ROOT = HARNESS_DIR.parent
SAMPLE = REPO_ROOT / "examples" / "sample-run"

# Shared with vesper-bind's tests: both sides must compute the same MAC.
VECTOR_KEY = bytes(range(32))
VECTOR_RESULT = {
    "ok": True,
    "fail_reasons": [],
    "summary": "ACCEPT",
    "score": {"rigor": 0.85, "verdict": "ACCEPT", "note": "caf\u00e9"},
}
VECTOR_KID = "630dcd2966c43366"
VECTOR_MAC = "efee91859d66fb5bf0858b9cac0522c38cbd05b0067e00f39fcfe50811940e40"


def _score(run_dir: Path, *extra: str, env: dict[str, str] | None = None):
    return subprocess.run(
        [sys.executable, str(HARNESS_DIR / "score.py"), *extra, str(run_dir)],
        capture_output=True,
        text=True,
        env=env,
    )


class Attestation(unittest.TestCase):
    """S7: a hand-written score-result.json must not look like the scorer's."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name).resolve()
        self.run_dir = base / "run"
        shutil.copytree(SAMPLE, self.run_dir)
        self.key_path = base / "keys" / "scorer.key"
        attest.write_new_key(self.key_path)
        self.key = attest.read_key(self.key_path)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _attested(self) -> dict:
        completed = _score(self.run_dir, "--attest-key", str(self.key_path))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        doc = json.loads(completed.stdout)
        (self.run_dir / "score-result.json").write_text(completed.stdout, encoding="utf-8")
        return doc

    def test_vector(self) -> None:
        header = {
            "schema": attest.SCHEMA,
            "alg": attest.ALG,
            "kid": attest.key_id(VECTOR_KEY),
            "inputs": {name: "0" * 64 for name in attest.INPUT_FILES},
        }
        self.assertEqual(header["kid"], VECTOR_KID)
        self.assertEqual(attest._mac(VECTOR_KEY, VECTOR_RESULT, header), VECTOR_MAC)

    def test_keygen_mode_and_no_overwrite(self) -> None:
        self.assertEqual(os.stat(self.key_path).st_mode & 0o777, 0o600)
        with self.assertRaises(attest.AttestError):
            attest.write_new_key(self.key_path)

    def test_loose_or_symlinked_key_refused(self) -> None:
        os.chmod(self.key_path, 0o644)
        with self.assertRaises(attest.AttestError):
            attest.read_key(self.key_path)
        os.chmod(self.key_path, 0o600)
        link = self.key_path.parent / "link.key"
        link.symlink_to(self.key_path)
        with self.assertRaises(attest.AttestError):
            attest.read_key(link)

    def test_score_attests_and_verifies(self) -> None:
        doc = self._attested()
        self.assertTrue(doc["ok"])
        att = doc["attestation"]
        self.assertEqual(att["schema"], attest.SCHEMA)
        self.assertEqual(att["kid"], attest.key_id(self.key))
        attest.verify(doc, self.run_dir, self.key)
        check = subprocess.run(
            [sys.executable, str(HARNESS_DIR / "attest.py"), "verify", str(self.run_dir),
             "--key", str(self.key_path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(check.returncode, 0, check.stderr)

    def test_env_var_key(self) -> None:
        env = dict(os.environ, **{attest.KEY_ENV: str(self.key_path)})
        completed = _score(self.run_dir, env=env)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("attestation", json.loads(completed.stdout))

    def test_no_key_no_attestation(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != attest.KEY_ENV}
        completed = _score(self.run_dir, env=env)
        self.assertNotIn("attestation", json.loads(completed.stdout))

    def test_hand_written_result_rejected(self) -> None:
        forged = {"ok": True, "fail_reasons": [], "score": {}, "critic_verdict": "ACCEPT"}
        with self.assertRaisesRegex(attest.AttestError, "not attested"):
            attest.verify(forged, self.run_dir, self.key)

    def test_edited_result_rejected(self) -> None:
        doc = self._attested()
        doc["fail_reasons"] = []
        doc["summary"] = doc["summary"] + " edited"
        with self.assertRaisesRegex(attest.AttestError, "MAC"):
            attest.verify(doc, self.run_dir, self.key)

    def test_swapped_evidence_rejected(self) -> None:
        doc = self._attested()
        (self.run_dir / "evidence.md").write_text("I did nothing. Trust me.\n", encoding="utf-8")
        with self.assertRaisesRegex(attest.AttestError, "changed after scoring"):
            attest.verify(doc, self.run_dir, self.key)

    def test_other_key_rejected(self) -> None:
        doc = self._attested()
        other = self.key_path.parent / "other.key"
        attest.write_new_key(other)
        with self.assertRaisesRegex(attest.AttestError, "different scorer key"):
            attest.verify(doc, self.run_dir, attest.read_key(other))

    def test_key_inside_checkout_or_run_refused(self) -> None:
        inside_run = self.run_dir / "scorer.key"
        attest.write_new_key(inside_run)
        completed = _score(self.run_dir, "--attest-key", str(inside_run))
        self.assertEqual(completed.returncode, 2)
        self.assertIn("must live outside", completed.stderr)
        with self.assertRaises(attest.AttestError):
            attest.refuse_key_inside(REPO_ROOT / "harness" / "x.key", REPO_ROOT)


if __name__ == "__main__":
    unittest.main()
