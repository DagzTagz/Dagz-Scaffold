# Plan — fail-fake-commands (synthetic)

Task: `tasks/003-fake-green.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Show a 003 run that prints six dump tokens and omits `ab -> False`.

## Files touched (in a live analog)

- `harness_tmp/is_palindrome.py`
- `examples/fail-fake-commands/plan.md`
- `examples/fail-fake-commands/critic.md`
- `examples/fail-fake-commands/evidence.md`
- `examples/fail-fake-commands/score.json`

## Verification

Dump six palindrome cases. Do not emit `ab -> False`.
