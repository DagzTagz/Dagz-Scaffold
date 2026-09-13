# Plan — sample-run (synthetic)

Task: `tasks/001-units-trap.md`  
This folder is a **synthetic fixture**. It is not a live grok session.

## Goal

Show a complete persist loop a scorer can parse: plan → diffs → critic →
evidence → score, with an explicit waiver.

## Files touched (in a live analog)

- `harness_tmp/celsius_to_kelvin.py` (ephemeral; not in this fixture)
- `examples/sample-run/plan.md`
- `examples/sample-run/critic.md`
- `examples/sample-run/evidence.md`
- `examples/sample-run/score.json`

## Verification

```
python -c "from harness_tmp.celsius_to_kelvin import celsius_to_kelvin; ..."
python harness/score.py examples/sample-run
python harness/run.py --dry-run tasks/002-quit-early.md
git check-ignore -v .env runs/foo.json .venv/bin/python
```

## Quit-early conditions

- shipping without the identities `0 → 273.15`, `100 → 373.15`
- using offset `273`
- skipping `ValueError` cases

## Waivers planned

- W1: no exhaustive SI-brochure temperature table; identities + invalid inputs only.

## Git commit / push sequence (harness bootstrap)

1. Inspect remotes, `git ls-files`, secrets scan.
2. Stage only intended paths. Show `git status`, `git diff --cached --stat`, file list.
3. `git commit` with `feat: initial Dagz-Scaffold harness`. No `--no-verify`. No force.
4. Push to existing upstream only if the security review allows it. Do not create a GitHub repo. Do not change remotes.

## SECURITY REVIEW

See `evidence.md` for the filled gate. Commit/push are blocked until that
section says yes.
