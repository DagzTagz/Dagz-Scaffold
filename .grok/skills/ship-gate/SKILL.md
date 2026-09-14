---
name: ship-gate
description: Block shipping a Dagz-Scaffold run on REJECT, missing evidence, unrun verification, quit-early, secrets, or staged live runs. Use when the user runs /ship-gate, asks if the work is done, or is about to commit/push/declare success.
---

# /ship-gate

Gate, do not celebrate. Do not trust chat memory.

Run `python harness/ship_gate.py runs/<id> --git-checks`. If it exits non-zero, the run is not done. Do not skip this program.

`--git-checks` is off by default so `python harness/ship_gate.py examples/sample-run` is hermetic (it does not read the operator index). Persist and this skill always pass `--git-checks`.

## Fail closed (block) if the program prints `SHIP-GATE: BLOCK`

The program blocks on:

1. **Score not ok** — `fail_reasons` from `score_run` (REJECT, missing_evidence, quit_early, required_verification, dry_run, missing artifacts, …).
2. **Verdict `REJECT`** — uniq with score fail reasons.
3. **`--git-checks`:** staged `runs/*` except `runs/.gitkeep`; staged secret names (`.env`, `.pem`, `.key`, `id_rsa`, `id_ed25519`, `auth.json`, `credentials.json`); staged blobs matching `XAI_API_KEY=` / `GITHUB_TOKEN=` / OpenSSH / `AKIA…` / `xai-` patterns; `git_missing`; `git_error`. Empty `.env.example` values do not match `\S+` after `=` and are OK.

`ACCEPT WITH WAIVERS` passes the gate only when the scorer already accepted explicit waivers.

`REJECT` passes **only** when `score.json` has a human `override` with both `by` and `reason`. The model must not fill `override`.

Derived `persistence` / `rigor` / `attempts` / `recovered_after_failure` come from `score.py` stdout (`derived`), not from self-reported claims.

## Pass

The program prints **SHIP-GATE: PASS** plus the scorer summary. Repeat that. Do not add a second checklist.

## Fail

The program prints **SHIP-GATE: BLOCK** plus bullets. Tell the builder what to attempt next. Do not mark the task complete.
