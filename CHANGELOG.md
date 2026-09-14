# Changelog

All notable changes to **Dagz-Scaffold** are documented here.

This project is **early, iterative open source** — not a finished product. We disclose privacy and security-relevant changes **up front**.

The format is based on [Keep a Changelog](https://keepachangelog.com/).  
Versions follow [Semantic Versioning](https://semver.org/) while pre-1.0 (`0.x` = public iterations; expect breaking changes until 1.0).

---

## [0.1.0] — 2026-09-14 — persistence harness, not a clipboard

First public line that is meant to **fail closed** on lying or lazy agent folders. Stdlib only. Live `runs/` stay gitignored.

### Added

- Persist / critic / ship-gate skills and builder/critic agents
- `harness/score.py` — local folder grade (schema v1)
- Evidence-scoped quit-early (plan/critic checklists do not fail)
- Task `scorer-contract` JSON (`must_appear`, `red_then_green`)
- `harness/ship_gate.py` with optional `--git-checks` (default off)
- Optional `score.py --replay` (default off): AST-allowlisted `python -c`, allowlisted `git`
- Derived persistence/rigor on the scorer summary; `score.json` values remain claims
- Synthetic fixtures: `examples/sample-run/` plus `examples/fail-*`
- Public traps `tasks/001`–`005`
- GitHub-facing docs aligned with hypothesis-engine: README front door, [getting-started.md](getting-started.md), [docs/scorer.md](docs/scorer.md), [docs/tasks.md](docs/tasks.md)

### Security / privacy

- `run.py --dry-run` and `score.py` without `--replay` do not call the network
- Denied replay commands are not spawned
- `--git-checks` can BLOCK staged `runs/*` and secret name/blob patterns
- Live artifacts and `.env` remain gitignored

### Upgrade

```bash
git pull
python3 harness/score.py examples/sample-run
python3 harness/score_selftest.py
python3 harness/ship_gate.py examples/sample-run
```

Scoring a `--dry-run` folder exits **1** (`dry_run`). That is expected.

---

## Unreleased

- Live `run.py` scores after `grok -p` and retries once (cap 2); records `attempts`
- Human-only `override: { by, reason }` may pass a REJECT through score/ship-gate
- Named fail fixtures `examples/quit-early-run`, `reject-run`, `fake-green-run`
- `harness/test_score.py`; optional read-only CI (no grok, no secrets)
