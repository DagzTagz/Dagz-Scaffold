---
name: ship-gate
description: Block shipping a Dagz-Scaffold run on REJECT, missing evidence, unrun verification, or quit-early markers. Use when the user runs /ship-gate, asks if the work is done, or is about to commit/push/declare success.
---

# /ship-gate

Gate, do not celebrate. Read the run folder and the scorer. Do not trust chat memory.

## Fail closed (block) if any of these hold

1. **Missing artifacts** in `runs/<id>/`: `plan.md`, `critic.md`, `evidence.md`, `score.json`, or no diffs/code changes described.
2. **Critic `VERDICT` is `REJECT`** or the heading/value is missing.
3. **Missing evidence:** `score.json` has `missing_evidence: true`, critic `MISSING EVIDENCE` is not `- none`, or `evidence.md` has no commands with output a skeptic can replay.
4. **Unrun verification:** required checks from the task/plan are not in `evidence.md`.
5. **Quit-early markers** in the run or the session:
   - declared done before critic/score
   - "too hard" / "won't do" without exhausting the plan
   - silent scope cut (constraint dropped, no waiver)
   - stopped after one failed check
   - a check the critic found was never attempted
6. **`python harness/score.py runs/<id>`** exits non-zero, or was not run.
7. **Secrets:** tracked `.env`, keys, tokens, live runs other than `examples/sample-run`.

`ACCEPT WITH WAIVERS` passes the gate only when every waiver has an `id` and a `reason` in `score.json`.

## Pass

Say **SHIP-GATE: PASS** plus verdict, persistence, rigor, and the scorer one-liner.

## Fail

Say **SHIP-GATE: BLOCK** plus the failing bullets. Tell the builder what to attempt next. Do not mark the task complete.
