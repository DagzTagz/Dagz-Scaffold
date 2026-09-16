# Dagz-Scaffold

Dagz-Scaffold is a small open-source tool for people who pair-program with **Grok Build** (the `grok` command in a terminal). After the agent says the code is done, this project asks a blunt question: **did it actually finish, or did it only talk like it finished?**

**Unofficial DagzTagz project. Not an xAI product.** When you run a live persist, Grok runs under **your** login and **your** xAI terms. This repo does not pay for that usage and is not endorsed by xAI.

It is the sister idea to [dagztagz-hypothesis-engine](https://github.com/DagzTagz/dagztagz-hypothesis-engine). That project checks scientific claims. This one checks **coding-agent work habits**.

**Status:** public **v0.1.0**. Experimental. History lives in [CHANGELOG.md](CHANGELOG.md).

---

## What problem this solves

If you have used an AI coding assistant, you have seen this: it writes a function, runs one happy test, the test is green, and it declares victory. Maybe the empty list still crashes. Maybe it used `273` instead of `273.15`. Maybe it never ran the check it was told to run. In the chat, it still sounds done.

Dagz-Scaffold treats that moment as an **inspection**, not a vibe check. The agent has to leave a **folder on disk** — a packet someone could open tomorrow without scrolling the conversation. Then two short Python programs grade that packet. If the packet is incomplete or dishonest, the gate says no. You do not merge to `main` on a confident paragraph.

The little puzzles in `tasks/` (Celsius to Kelvin, first non-zero number, palindromes) are **toys**. We are not shipping a weather app. We are testing whether **this AI, on this attempt**, persisted, showed proof, and survived a hostile second look.

## What “done” means here

A run is not done because the chat said so. It is done when a directory exists with:

- a **plan** (`plan.md`) — what it promised
- the **code it actually changed**
- **evidence** (`evidence.md`) — the commands it ran and what they printed
- a **critic** (`critic.md`) — a second pass whose job is to reject bad work
- a **score file** (`score.json`) — a machine-readable claim that those pieces exist

You then point the inspector at that folder. Details: [docs/find-a-run.md](docs/find-a-run.md).

The critic’s verdict is one of: `REJECT`, `ACCEPT WITH WAIVERS`, or `ACCEPT`. Reject means more work, not a polish pass. Waivers have to be named with an id and a reason; they are not a vibe.

## Who this is for

The intended user already has the [Grok Build CLI](https://github.com/xai-org/grok-cli). You start a persist in Grok, then grade the folder with Python.

The **grading** half (the inspector) is ordinary Python 3.11+ with **no extra packages**. Anyone who can produce the same folder shape can be graded. The **start button** in this repo (`/persist` and `harness/run.py`) calls `grok`. That is how the classroom is furnished, not a law of physics.

---

## Try this first (no Grok, no cost)

This only proves your copy of the repo is intact. It does not test an AI.

```bash
git clone https://github.com/DagzTagz/Dagz-Scaffold.git
cd Dagz-Scaffold
python3 harness/score.py examples/sample-run
python3 harness/test_score.py
python3 harness/score_selftest.py
python3 harness/ship_gate.py examples/sample-run
```

You should see a passing grade on the sample packet, tests that print `OK`, and `SHIP-GATE: PASS`. If any command fails, stop and fix the checkout before you involve Grok.

The full walk, including a real persist: **[getting-started.md](getting-started.md)**.

### Smoke versus a live run

The smoke commands and `--dry-run` never call the model. They cost nothing.

A live persist (`grok` in the repo, or `python3 harness/run.py` without `--dry-run`) uses **your** Grok account. It may send task text, diffs, and command output to xAI. This project does not cap that bill.

`--dry-run` writes a **fake** folder under `runs/`. Scoring that folder is **supposed** to fail (`dry_run`). That is not a successful persist.

---

## How a real sitting works

You give Grok a task file (for example `tasks/002-quit-early.md`: implement a function, let the first test fail on purpose, then fix it). Grok plans, writes code, has to show the red test and the green retry, and writes a critic file.

You open a second terminal, find the new folder under `runs/`, and run the inspector. Step-by-step for finding that folder: [docs/find-a-run.md](docs/find-a-run.md).

`score.py` is a cheap lie detector. It checks that files exist, that the critic and score file agree, that evidence has real commands, and that required phrases from the task showed up. It does **not** prove the science by itself. You still read the diff.

`ship_gate.py` is the bouncer at the door. If it prints `BLOCK`, you do not merge.

Optional `--replay` re-runs a **small allowlist** of commands from evidence on your machine. It is off by default. Do not replay evidence you have not read.

## Docs map

| If you want to… | Read |
|-----------------|------|
| Install and run a persist | [getting-started.md](getting-started.md) |
| Find `runs/<id>/` on your disk | [docs/find-a-run.md](docs/find-a-run.md) |
| Understand PASS vs BLOCK | [docs/scorer.md](docs/scorer.md) |
| Add a new trap task | [docs/tasks.md](docs/tasks.md) |
| Send a patch | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Report a vulnerability | [SECURITY.md](SECURITY.md) |

`AGENTS.md` is for coding agents working **in** this repo. Humans should start with getting-started, not that file.

---

## What is in the tree

The Grok skills (`persist`, `critic`, `ship-gate`) live under `.grok/skills/`. The Python inspector lives under `harness/`. Public traps are `tasks/001` through `005`. `examples/` holds a passing sample packet and several packets that **must** fail. Live work lands in `runs/`, which git ignores (except a placeholder so the folder exists).

## Roadmap, briefly

v0.1 already has the persist loop, fail-closed quit-early, task contracts, ship-gate, optional replay, derived scores, and read-only CI that never calls Grok.

We still want more public traps. We do **not** want to grade raw chat dumps under `~/.grok/sessions/`, call the model from `score.py`, or add pip packages to the harness.

## Contributing and license

You do not need to be a professional programmer. Clear writing, trap ideas, and “this page confused me” reports all count. See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

This repository is **MIT**. Hypothesis Engine is Apache-2.0; we have not changed licenses.

Thanks to the DagzTagz community, to xAI/Grok for the CLI this live path uses (again: **not** an official product), and to hypothesis-engine for the “verify, then leave evidence” pattern.

## Please remember

This is experimental community software. Prefer the free smoke test until you **mean** to run live Grok. Do not commit secrets or live `runs/` folders. Always glance at `evidence.md` yourself. The inspector catches a missing packet; it does not replace your judgment.

**Leave folders a skeptic can audit.**
