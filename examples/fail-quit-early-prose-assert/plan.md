# Plan — fail-quit-early-prose-assert (synthetic)

Task: `tasks/002-quit-early.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Show a 002 run that mentions AssertionError only in prose, with green
command fences and no fenced traceback between them.

## Files touched (in a live analog)

- `harness_tmp/retry_counter.py`
- `examples/fail-quit-early-prose-assert/plan.md`
- `examples/fail-quit-early-prose-assert/critic.md`
- `examples/fail-quit-early-prose-assert/evidence.md`
- `examples/fail-quit-early-prose-assert/score.json`

## Verification

Cover `[0, 4, 0]`, `[]`, `[0, 0]`. Do not fence a traceback.
