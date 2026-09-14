# Plan — fail-reject (synthetic)

Task: `tasks/001-units-trap.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Show a run whose critic verdict is REJECT with a non-empty BLOCKERS
section. Evidence quotes the identities and has no forbidden phrases.

## Files touched (in a live analog)

- `harness_tmp/celsius_to_kelvin.py`
- `examples/fail-reject/plan.md`
- `examples/fail-reject/critic.md`
- `examples/fail-reject/evidence.md`
- `examples/fail-reject/score.json`

## Verification

Identities `0 → 273.15`, `100 → 373.15`, `-273.15 → 0`, and `ValueError` for
`-273.16`.
