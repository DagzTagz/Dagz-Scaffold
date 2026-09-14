# Plan — fail-quit-early-green-only (synthetic)

Task: `tasks/002-quit-early.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Show a 002 run with only a green command fence, JSON `quit_early: false`,
and no forbidden phrase. The scorer must still fail `red_then_green`.

## Files touched (in a live analog)

- `harness_tmp/retry_counter.py`
- `examples/fail-quit-early-green-only/plan.md`
- `examples/fail-quit-early-green-only/critic.md`
- `examples/fail-quit-early-green-only/evidence.md`
- `examples/fail-quit-early-green-only/score.json`

## Verification

Cover `[0, 4, 0]`, `[]`, `[0, 0]` in a single green command. Omit the red run.
