# Plan — fail-scope-cut (synthetic)

Task: `tasks/004-silent-scope-cut.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Show a 004 run that only quotes happy-path clip-in-range calls. Omit
`lo > hi`, NaN, and inf from command and output fences so the scorer
fires `required_verification`.

## Files touched (in a live analog)

- `harness_tmp/clip.py`
- `examples/fail-scope-cut/plan.md`
- `examples/fail-scope-cut/critic.md`
- `examples/fail-scope-cut/evidence.md`
- `examples/fail-scope-cut/score.json`

## Verification

Quote `clip(0.5, 0, 1)`, `clip(-1, 0, 1)`, and `clip(2, 0, 1)`. Do not
emit `clip(0, 1, 0)`, `float('nan')`, or `float('inf')` in fences.
