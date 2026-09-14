# AGENTS.md

Unofficial DagzTagz project. Not an xAI product. Powered by the grok CLI.

Humans: start at [getting-started.md](getting-started.md), not this file.

You are doing agentic engineering in this repo. A task is not done because you
feel done. It is done when the artifacts exist and the critic has signed off.

## Non-negotiable loop

For any non-trivial work (more than a one-line fix or a pure question):

1. **Plan mode first.** Write `runs/<id>/plan.md` before editing product code.
   The plan names files, verification steps, and what would count as quit-early.
2. **Build** against that plan. Put diffs in the working tree. Quote them in
   `runs/<id>/evidence.md`.
3. **Critic before ship.** Spawn the `critic` agent (hostile, prefer read-only)
   and write `runs/<id>/critic.md` with exactly these headings:
   `BLOCKERS`, `RISKS`, `NITS`, `MISSING EVIDENCE`, `VERDICT`.
4. **Score.** `python harness/score.py runs/<id>` must run. Refuse to finish
   without `runs/<id>/score.json`.
5. **Ship-gate.** Run `python harness/ship_gate.py runs/<id> --git-checks`. If
   it exits non-zero, the run is not done. Do not skip this program. `REJECT`
   returns work to the builder. The run cannot complete on `REJECT`.
   `ACCEPT WITH WAIVERS` requires explicit waivers in `score.json`.

Invoke `/persist` to run this loop. Invoke `/ship-gate` before you say done.

## Artifacts

Write every run into `runs/<id>/` (gitignored except `.gitkeep`):

- `plan.md`
- `critic.md`
- `evidence.md`
- `score.json`

`examples/sample-run/` is the synthetic fixture. Do not copy live runs into git.

## Forbidden completions

These are quit-early. Do not ship them:

- "should work" / "looks good" without commands and output in `evidence.md`
- declaring done before critic + score
- calling the task too hard without exhausting the plan
- silently dropping a constraint
- stopping after one failed check
- skipping a check the critic later names under `MISSING EVIDENCE`

Failed checks produce a **new hypothesis** and another attempt until the budget
is used or the critic verdict is `ACCEPT` / `ACCEPT WITH WAIVERS`.

## Skills

- `persist` — user-facing workflow (`/persist`)
- `critic` — hostile review (`/critic`)
- `ship-gate` — block on REJECT, missing evidence, unrun verification, quit-early (`/ship-gate`)

## Runtime

- Python 3.11+, **stdlib only** for harness code. No surprise pip packages.
- `harness/run.py --dry-run` must not call the network or the model.
- `harness/score.py` reads local files; `--replay` is local subprocess, no network.
- Keep `--replay` default off.
- Do not commit `runs/`, `.env`, keys, or Grok session state.
