# Scorer and ship-gate

`python harness/score.py RUN_DIR` grades a persist folder. It does **not** call the network or the model (unless you pass `--replay`, which is local subprocess only).

Walkthrough of a first clone: [getting-started.md](../getting-started.md).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | `ok: true` — mechanical checks passed |
| 1 | `ok: false` or `INVALID` (shape broken) |
| 2 | path is not a directory |

Stdout is JSON. Stderr is a one-line summary.

## What `ok` is

`ok` is **mechanical**. Persistence and rigor numbers in the summary are **derived caps**. Values inside `score.json` are the builder’s **claims** and do not flip `ok` by themselves.

Typical `fail_reasons`:

| Reason | Meaning |
|--------|---------|
| `quit_early` | Evidence has a forbidden phrase, JSON `quit_early: true`, or `red_then_green` failed |
| `REJECT` | Critic verdict is reject |
| `missing_evidence` | No commands, critic missing-evidence section, or replay mismatch |
| `evidence_has_no_commands` | No `$ ` / `python` / fences |
| `dry_run` | Mock from `run.py --dry-run` |
| `required_verification` | Task `must_appear` tokens missing from command/output fences |
| `task_contract_missing` | Task file has no `scorer-contract` fence |

Plan and critic **may** mention “too hard” as a checklist. **Evidence** may not, except inside a ` ```markdown ` task excerpt.

## Task contracts

Each public task has a fenced JSON block under `## Required verification` with info-string `scorer-contract`:

```json
{
  "must_appear": ["273.15", "373.15"],
  "red_then_green": false
}
```

- `must_appear` is searched in **command fences** and each command’s **paired unlabeled output** fence only — not prose, not ` ```diff `, not ` ```python ` module bodies.
- Dump tokens containing ` -> ` match as a **whole output line** (`a -> True` is not satisfied by `aba -> True`).
- `red_then_green: true` requires two command fences and a fenced traceback / `AssertionError` **between** them. Unfenced prose does not count.

Authoring: [tasks.md](tasks.md).

## Derived scores

The summary line uses derived `persistence` / `rigor` (0–1). Examples:

- `quit_early` → persistence 0.0
- one command fence → persistence ≤ 0.5
- missing evidence → rigor ≤ 0.2
- `dry_run` → 0.0 / 0.3

Mismatch between claims and derived does **not** fail `ok`.

## Replay (`--replay`)

Default **off**.

```bash
python3 harness/score.py --replay runs/<id>
```

- `examples/` is never auto-executed (`replay.skipped: examples fixture`).
- Only AST-allowlisted `python -c` (imports under `harness_tmp`) and a small **git** subcommand list.
- `os.system`, `python -m`, extra files, `git push`, `git --git-dir=` are **denied and not spawned**.
- Historical red (output fence looks like a traceback) is skipped, not re-run against the current tree.
- Mismatch → `missing_evidence`, not a waiver.

`ship_gate.py` auto-replays paths **not** under `examples/`. There is no `--replay` flag on ship-gate.

## Ship-gate

```bash
python3 harness/ship_gate.py examples/sample-run          # hermetic smoke
python3 harness/ship_gate.py runs/<id> --git-checks       # live persist
```

`--git-checks` (default **off**) scans **this clone’s** index for staged `runs/*` (except `.gitkeep`) and secret name/blob patterns. Non-zero git → `git_error`.

`SHIP-GATE: BLOCK` or exit 1 → the run is not done. Do not skip this program.

## Fixtures

| Folder | After a current scorer |
|--------|------------------------|
| `examples/sample-run/` | `ok: true` |
| `examples/fail-quit-early/` | `quit_early` |
| `examples/fail-missing-evidence/` | missing evidence + no commands (+ contract miss) |
| `examples/fail-reject/` | `REJECT` |
| `examples/fail-quit-early-green-only/` | `quit_early` (no red fence) |
| `examples/fail-fake-commands/` | `required_verification` |

Live `runs/` are gitignored. Do not copy them into git.
