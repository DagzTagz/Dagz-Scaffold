# State-machine audit, November 2026: Dagz-Scaffold

This page covers the Dagz-Scaffold part of the full disclosure for the November 2026 implicit-state-machine audit of the DagzTagz repositories.

- The complete report is [docs/audits/2026-11-state-machine-audit.md](../audits/2026-11-state-machine-audit.md). It has every finding, how each one was reproduced, and the remediation status of all 13 findings across the four repositories.
- Audited commit: [`76edab4`](https://github.com/DagzTagz/Dagz-Scaffold/tree/76edab4b4c93e199034ca1e8fa545c27b79a0a2d).

| Finding | Priority | What was wrong | Fix | Status |
|---|---|---|---|---|
| F1 | **High** | `score.py --replay` in a checkout with no `.git` of its own found an enclosing repository and ran its git config, including clean filters. **Reproduced.** Advisory: [ADVISORY-2026-11-24-replay-enclosing-repo.md](ADVISORY-2026-11-24-replay-enclosing-repo.md). | [Dagz-Scaffold#1](https://github.com/DagzTagz/Dagz-Scaffold/pull/1), merge [`4f09170`](https://github.com/DagzTagz/Dagz-Scaffold/commit/4f091704b708918de37594977cfb1ea73c282785) (fix [`7c84ca3`](https://github.com/DagzTagz/Dagz-Scaffold/commit/7c84ca3)) | Merged |
| F3 | Med | `harness/run.py` reported success as soon as `score.py` passed and never ran `ship_gate.py`. Its retry prompt did not say what failed, and it wrote `attempts` into `score.json` after scoring. | [Dagz-Scaffold#2](https://github.com/DagzTagz/Dagz-Scaffold/pull/2), merge [`2574c1e`](https://github.com/DagzTagz/Dagz-Scaffold/commit/2574c1e40d9b0f17130b0169ddf6f49e7610a864) (fix [`4183724`](https://github.com/DagzTagz/Dagz-Scaffold/commit/4183724)) | Merged |
| F8 | Low | The verdict, waiver, blocker and override rules were written twice, and the two copies had drifted. `ship_gate.py` accepted a non-string `override.by`. An override on an `ACCEPT` was accepted without comment. | [Dagz-Scaffold#2](https://github.com/DagzTagz/Dagz-Scaffold/pull/2), merge [`2574c1e`](https://github.com/DagzTagz/Dagz-Scaffold/commit/2574c1e40d9b0f17130b0169ddf6f49e7610a864) (fix [`bd2c4df`](https://github.com/DagzTagz/Dagz-Scaffold/commit/bd2c4df)) | Merged |
| F9 | Low | Three Markdown fence lexers read the same `evidence.md` in different ways during one scoring pass. **Reproduced** with nested and inline backticks. | [Dagz-Scaffold#2](https://github.com/DagzTagz/Dagz-Scaffold/pull/2), merge [`2574c1e`](https://github.com/DagzTagz/Dagz-Scaffold/commit/2574c1e40d9b0f17130b0169ddf6f49e7610a864) (fix [`4032f05`](https://github.com/DagzTagz/Dagz-Scaffold/commit/4032f05)) | Merged |

F2 and F13 are in vesper-bind, which reads Scaffold runs. F2 was **High** and was fixed in [vesper-bind PR #1](https://github.com/DagzTagz/vesper-bind/pull/1). See [vesper-bind's section](https://github.com/DagzTagz/vesper-bind/blob/main/docs/security/state-machine-audit-2026-11.md).

## What changed in Dagz-Scaffold#2

- **F3:**
  - `run_live` follows an explicit transition table, `Step`/`next_step`: Scoring → Gating → Done. Otherwise it goes to Retry, or to Exhausted when no calls are left.
  - It runs the same gate the agent is told to run (`ship_gate.gate_run` with `--git-checks`). It exits 0 only when both checks pass.
  - The retry prompt names the program that stopped the run and lists that program's reasons.
  - `attempts` is written before scoring, so the bytes that are scored and hashed are the bytes left on disk.
- **F8:**
  - `score.verdict_shape_error` is the single list of allowed verdict, waiver, blocker and override combinations.
  - `score.gate_passes` is the single override rule, and `ship_gate.py` imports it.
  - An `override` on a non-REJECT verdict is now invalid.
- **F9:**
  - `task_contract.lex_fences` is the only fence lexer. It works line by line and matches tick counts.
  - The contract parser, command pairing, replay and the quit-early scan all use it.
  - Scores for all 12 example runs, and the parsed contracts of all 5 tasks, are unchanged.

## Do I need to do anything?

- If a `score.json` you wrote by hand has an `override` on `ACCEPT` or `ACCEPT WITH WAIVERS`, remove it. It is now refused.
- `harness/run.py` live runs can now end with exit 1 when `ship_gate` blocks a run that `score.py` passed. That is the intended behaviour.

## Follow-up, 2026-11-25: residual items

A follow-up review of shared-compute setups found three more items in this repository. The full list, including vesper-bind and vesper-runtime, is in [section 7 of the report](../audits/2026-11-state-machine-audit.md#7-addendum-2026-11-25-residual-items-from-the-shared-compute-review).

| Item | What was left | Pull request | Status |
|---|---|---|---|
| S13 | `--replay` ran `from harness_tmp import ...` commands, so a planted `harness_tmp.py` ran as the scorer. | [Dagz-Scaffold#4](https://github.com/DagzTagz/Dagz-Scaffold/pull/4). **Breaking:** refused unless `--allow-harness-tmp`. | Open |
| S14 | `ship_gate.py --git-checks` and the task-file check used an enclosing repository's index and `HEAD` for a copy with no `.git`. | [Dagz-Scaffold#5](https://github.com/DagzTagz/Dagz-Scaffold/pull/5). **Breaking:** `--git-checks` needs a real clone. | Open |
| S7 | Nothing let vesper-bind tell the scorer's output from a hand-written `score-result.json`. | [Dagz-Scaffold#6](https://github.com/DagzTagz/Dagz-Scaffold/pull/6) adds `score.py --attest-key`. vesper-bind starts requiring it in [vesper-bind#4](https://github.com/DagzTagz/vesper-bind/pull/4). | Open |

