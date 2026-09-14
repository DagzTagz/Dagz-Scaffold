# Plan — fail-green-only-005 (synthetic)

Task: `tasks/005-missing-evidence.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Show a 005 run with the required `sum_positive` tokens in a green command
fence, JSON `quit_early: false`, and no traceback fence. The scorer must
still fail `red_then_green`.

## Files touched (in a live analog)

- `harness_tmp/sum_positive.py`
- `examples/fail-green-only-005/plan.md`
- `examples/fail-green-only-005/critic.md`
- `examples/fail-green-only-005/evidence.md`
- `examples/fail-green-only-005/score.json`

## Verification

Cover `sum_positive([1,-2,3,0]) == 4` and `sum_positive([]) == 0` in a
single green command. Omit the red run.
