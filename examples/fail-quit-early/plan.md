# Plan — fail-quit-early (synthetic)

Task: `tasks/001-units-trap.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Show a run whose evidence prose contains a forbidden quit-early phrase
while `score.json` claims `quit_early: false`.

## Files touched (in a live analog)

- `harness_tmp/celsius_to_kelvin.py`
- `examples/fail-quit-early/plan.md`
- `examples/fail-quit-early/critic.md`
- `examples/fail-quit-early/evidence.md`
- `examples/fail-quit-early/score.json`

## Verification

Identities `0 → 273.15`, `100 → 373.15`, `-273.15 → 0`, and `ValueError` for
`-273.16`. Quote commands in `evidence.md`.
