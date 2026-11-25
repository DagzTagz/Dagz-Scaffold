# Changelog

All notable changes to **Dagz-Scaffold** are documented here.

This project is **early, iterative open source** — not a finished product. We disclose privacy and security-relevant changes **up front**.

The format is based on [Keep a Changelog](https://keepachangelog.com/).  
Versions follow [Semantic Versioning](https://semver.org/) while pre-1.0 (`0.x` = public iterations; expect breaking changes until 1.0).

---

## [Unreleased]

### Security

- `score.py --replay`: a checkout with no `.git` of its own is now an explicit `NO_REPO` state, and git replay there is denied (`git_no_repo`) and counts as missing evidence. Before, git searched parent directories and could load an enclosing repository's config, including its clean filters. `replay_env` also sets `GIT_CEILING_DIRECTORIES`. See [docs/security/ADVISORY-2026-11-24-replay-enclosing-repo.md](docs/security/ADVISORY-2026-11-24-replay-enclosing-repo.md).
- Added the November 2026 implicit-state-machine audit: [docs/audits/2026-11-state-machine-audit.md](docs/audits/2026-11-state-machine-audit.md).
- The audit report now has a remediation status table. This repository's section of the disclosure is [docs/security/state-machine-audit-2026-11.md](docs/security/state-machine-audit-2026-11.md).

### Fixed

- **Breaking: the ship gate's git checks used an enclosing repository.** `ship_gate.py --git-checks` (and the live loop, which always uses it) and the task-file `HEAD` check ran plain `git` in the checkout. For a copy with no `.git` of its own inside another repository, they read the outer repository's index and `HEAD`: the gate reported another project's staged file names and missed a staged live run at a nested path such as `tools/Dagz-Scaffold/runs/...`. Both now run git through the new `harness/checkout_git.py`: `GIT_CEILING_DIRECTORIES` is the checkout's parent, inherited `GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE` and similar variables are dropped, and hooks, fsmonitor, external diff and textconv are off. `--git-checks` now blocks with `git_no_repo` or `git_not_checkout_root` unless `git rev-parse --show-toplevel` is the checkout, so staged paths are always relative to the checkout. A vendored copy inside another repository can no longer pass `--git-checks` or the live loop; use a real clone. The task-file check treats that layout like a tarball (no `HEAD` comparison). (Residual item S14 from the shared-compute review.)
- **Live runs skipped the ship gate (audit F3).** `harness/run.py` returned success once `score.py` passed. It now also runs `ship_gate` (with `--git-checks`) and exits 0 only when both pass. The retry prompt says which check failed and why. `attempts` is recorded before scoring, so the scored `score.json` is the final file.
- **Verdict rules in one place (audit F8).** `score.gate_passes` is the only override rule, and `ship_gate.py` uses it. Before, `ship_gate.py` had a looser copy.
- **One fence lexer (audit F9).** `task_contract.lex_fences` is the only reader of Markdown fences in the harness. Nested and inline backticks no longer split evidence differently between checks.

### Changed

- **Breaking:** a `score.json` with an `override` on `ACCEPT` or `ACCEPT WITH WAIVERS` is now invalid. `override` is only meaningful on `REJECT`.

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

### Changed

- A `REJECT` in `score.json` passes only when a person passes `--honor-override` and both `override.by` and `override.reason` are filled in. The file alone does not.

### Added

- Rewrite `docs/scorer.md` around PASS vs BLOCK and human meanings of fail reasons; put replay and task JSON in a skippable appendix
- Rewrite GitHub-facing docs in full sentences (README, getting-started, find-a-run, scorer, tasks, CONTRIBUTING) so a person can follow them without treating them as a machine checklist
- Redact local `$HOME` username from docs and sample-run evidence
- [docs/find-a-run.md](docs/find-a-run.md) — step-by-step: list `runs/`, copy the folder name, point score/ship-gate at it
- Live `run.py` scores after `grok -p` and retries once (cap 2); records `attempts`
- Named fail fixtures `examples/quit-early-run`, `reject-run`, `fake-green-run`
- `harness/test_score.py`; optional read-only CI (no grok, no secrets)
