---
name: persist
description: Persistence loop for Dagz-Scaffold engineering tasks. Create a run folder, demand a plan, spawn builder then critic, and refuse to finish without score.json. Use when the user runs /persist, asks to persist through a hard task, or wants the plan → build → critic → evidence → score loop.
---

# /persist

Unofficial DagzTagz workflow. Not an xAI product.

A task is not done until `runs/<id>/` contains `plan.md`, diffs, `critic.md`, `evidence.md`, and `score.json`.

## Steps

1. **Allocate a run id.** Create `runs/<id>/` (id: UTC `YYYYMMDDTHHMMSSZ` plus a short slug from the task filename). Copy or quote the task file in the plan. Live artifacts stay in `runs/`; never git-add them.

2. **Plan first.** For non-trivial work, write `runs/<id>/plan.md` before product edits. The plan lists files, verification commands, quit-early conditions, and the security-relevant bits if git/secrets are involved. If the user skipped planning, stop and write the plan.

3. **Builder.** Spawn the `builder` agent (`.grok/agents/builder.md`) against that plan. It implements, runs the required checks, and records commands + output in `runs/<id>/evidence.md`. Failed checks are a new hypothesis and another attempt, not a stop.

4. **Critic.** After the builder claims the checks passed, spawn the `critic` agent (`.grok/agents/critic.md`, persona `critic`) with read-only investigation. It attacks the work. It does not polish. It writes `runs/<id>/critic.md` with exactly:

   - `## BLOCKERS`
   - `## RISKS`
   - `## NITS`
   - `## MISSING EVIDENCE`
   - `## VERDICT`

   Verdict line is one of `REJECT` | `ACCEPT WITH WAIVERS` | `ACCEPT`.

5. **REJECT → builder.** On `REJECT`, return the blockers to the builder. The run cannot complete. Do not bargain the verdict down.

6. **Score.** Run `python harness/score.py runs/<id>` (or write `score.json` that the scorer accepts). Persistence and rigor are 0–1. Waivers must be explicit objects with `id` and `reason`.

7. **Ship-gate.** Run `python harness/ship_gate.py runs/<id> --git-checks`. If it exits non-zero, the run is not done. Do not skip this program. `/persist` cannot skip this program.

## Refuse to finish when

- `score.json` is missing
- critic verdict is `REJECT` or missing
- evidence would not convince a skeptic who was not in this session
- verification commands were not run
- any quit-early marker fired (done-before-verify, "too hard", silent scope cut, stop after one failed check, skipped check)
- `python harness/ship_gate.py runs/<id> --git-checks` exits non-zero

## Output

Tell the user the run directory, verdict, scores, and the one-line scorer summary. Point at the files. Do not claim the tests "should work".
