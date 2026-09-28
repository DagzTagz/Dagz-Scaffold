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

### Security

- `score.py --replay` starts Python with `-I -S` from the interpreter that launched the scorer, and does not put the repo on `PYTHONPATH` before startup. A `sitecustomize.py` in the checkout is not imported for an allowlisted `python -c`.
- Replay pins `git` to a binary outside the repo and overrides hook, fsmonitor, pager, and external-diff config for that command. `git diff` / `show` / `log` also pass `--no-ext-diff` and `--no-textconv`.
- `score.json` `override` no longer passes a `REJECT` by itself. A person has to pass `--honor-override`.
- Ship-gate reads the run folder for secret-shaped text and symlink artifacts. It still does not re-run evidence. The scorer doc used to say it might.
- `run.py --run-id` must be one plain name under `--out-dir`. Writes do not follow an existing symlink.
- The task file scored for a git checkout must match `HEAD`. A symlink under `tasks/` is rejected.
- Evidence that only prints the required strings, without calling the imported `harness_tmp` function, fails as `solution_not_called`. A pasted traceback does not count as that call.
- Replay refuses oversized `**` and string-multiply literals in `python -c`.
- Replay no longer loads the checkout's git config. Clean filters, included config, and `gpg.program` are not started. `git status` and `git diff` do not enter submodules. A symlinked `.git` is refused.

- Rewrite `docs/scorer.md` around PASS vs BLOCK and human meanings of fail reasons; put replay and task JSON in a skippable appendix
- Rewrite GitHub-facing docs in full sentences (README, getting-started, find-a-run, scorer, tasks, CONTRIBUTING) so a person can follow them without treating them as a machine checklist
- Redact local `$HOME` username from docs and sample-run evidence
- [docs/find-a-run.md](docs/find-a-run.md) — step-by-step: list `runs/`, copy the folder name, point score/ship-gate at it
- Live `run.py` scores after `grok -p` and retries once (cap 2); records `attempts`
- Human-only `override: { by, reason }` may pass a REJECT through score/ship-gate
- Named fail fixtures `examples/quit-early-run`, `reject-run`, `fake-green-run`
- `harness/test_score.py`; optional read-only CI (no grok, no secrets)
