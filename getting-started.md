# Getting started

This page walks a person through Dagz-Scaffold from a blank machine to a graded persist. You do not need to memorize the internals first. Commands are here so you can copy them; the paragraphs around them say **what should happen** and **what it means if it does not**.

**Unofficial DagzTagz project. Not an xAI product.** Scoring and dry-run stay on your computer and do not call Grok. A **live** persist uses the `grok` CLI under **your** account.

---

## What you need

You need **Python 3.11 or newer** and **git**. The harness is stdlib only: you should not `pip install` anything to score a folder.

You need the **Grok Build CLI** only when you want a live persist (`grok` in this repo, or `python3 harness/run.py` without `--dry-run`). The smoke test below does not need Grok.

On many Linux machines the Python binary is `python3`. If `python3 --version` fails:

```bash
sudo apt update && sudo apt install -y python3 git
```

---

## 1. Get a copy of the project

```bash
git clone https://github.com/DagzTagz/Dagz-Scaffold.git
cd Dagz-Scaffold
```

If you already cloned it earlier, `cd` into that folder and run `git pull` so you are on current `main`.

If you downloaded a ZIP from GitHub, unzip it and `cd` into the folder (it may be named `Dagz-Scaffold-main`). You should be able to run `ls harness/score.py` and see the file.

---

## 2. Smoke test (no Grok, no bill)

Stay in the project folder. Run these four commands. They only read files that already ship in the repo.

```bash
python3 --version
git --version

python3 harness/score.py examples/sample-run
python3 harness/test_score.py
python3 harness/score_selftest.py
python3 harness/ship_gate.py examples/sample-run
```

**What “good” looks like.** `score.py` prints a block of JSON and, on the last line of its summary, something like `ACCEPT WITH WAIVERS` with `quit_early=False`. The two test commands print `OK`. Ship-gate prints `SHIP-GATE: PASS`. Each of those four Python commands should exit successfully (in bash, `echo $?` after a command should be `0`).

**If something fails.** Your checkout is incomplete or Python is too old. Fix that before you invite Grok in. Do not add `--git-checks` on `examples/sample-run`: that flag inspects **your git staging area**, not the sample packet. Do not add `--replay` here; the default is off, which means “read the files, do not execute them.”

`examples/sample-run` is a **practice packet** we wrote by hand. It is not a live AI sitting. Grading it only proves the inspector still works.

---

## 3. Optional: dry-run of the wrapper

This checks that `run.py` can write a mock folder **without** calling Grok.

```bash
python3 harness/run.py --dry-run tasks/002-quit-early.md
```

You should see `skipped grok` and a new directory under `runs/`. That directory is labeled as a mock. If you point `score.py` at it, it should **fail** with `dry_run` in the reasons. That failure is correct. You have not tested an AI yet; you have tested that the wrapper does not pretend a fake persist is a real one.

---

## 4. A real persist (this is the actual exam)

Install and log in to [Grok Build](https://github.com/xai-org/grok-cli) on this machine first. Live mode can send the task, the diffs, and command output to xAI as **your** user. This project does not pay for it.

Open a terminal **in the repo**:

```bash
cd /path/to/Dagz-Scaffold
grok
```

When Grok is ready, type a persist against one of the public traps. Trap 002 is a good first sitting: the first implementation is **supposed** to fail, then the agent has to retry.

```text
/persist tasks/002-quit-early.md
```

You can use `001-units-trap.md`, `003-fake-green.md`, `004-silent-scope-cut.md`, or `005-missing-evidence.md` the same way.

**What Grok should do.** It writes a plan, implements (including the deliberate first failure on 002), records the exact commands and their output in `evidence.md`, and runs a critic whose job is to attack the work. It should produce a folder under `runs/` whose name looks like a timestamp plus the task slug.

**What you do.** Open a **second** terminal in the same repo. Do not skip this. The `/ship-gate` line in chat is a sticky note. The program that counts is Python.

How to find the folder name on your machine is written out in [docs/find-a-run.md](docs/find-a-run.md). In short: `ls runs/`, copy the directory name, then:

```bash
python3 harness/score.py runs/20260913T220306Z-002-quit-early
python3 harness/ship_gate.py runs/20260913T220306Z-002-quit-early --git-checks
```

Use **your** folder name, not the example, and not the letters `<id>`.

**PASS** (exit 0, `SHIP-GATE: PASS`) means the packet is complete enough that a stranger could reconstruct the sitting. You may consider merging. You should still read the diff; the inspector is not a substitute for looking at the code.

**BLOCK** or a scorer exit of 1 means it is not shipped. Paste the blockers back into Grok. Do not merge because the chat sounded sure.

---

## 5. Headless live run (no interactive Grok UI)

Same cost and privacy as section 4. This calls `grok -p` for you, scores the folder, and will retry **once** if the first sitting fails (two Grok calls maximum).

```bash
python3 harness/run.py tasks/002-quit-early.md
ls -1t runs | head
python3 harness/score.py runs/<the-new-folder>
python3 harness/ship_gate.py runs/<the-new-folder> --git-checks
```

Replace `<the-new-folder>` with the name `ls` printed. Again, [docs/find-a-run.md](docs/find-a-run.md) if that sentence is unclear.

---

## Money, privacy, and git

Smoke, dry-run, and `score.py` without `--replay` do not call the model.

Live Grok is your account. Optional `python3 harness/score.py --replay runs/YOUR-FOLDER` re-runs a **small allowlist** of commands locally. Leave it off unless you trust that evidence. Never replay a packet you have not read.

Live folders stay on **your** disk. Git is set to ignore `runs/` (except a tiny placeholder). Do not `git add` them, do not paste them into GitHub issues, and do not commit `.env`, keys, or Grok session dumps.

```bash
git check-ignore -v .env runs/foo.json
```

That should show ignore rules. Good. Full policy: [SECURITY.md](SECURITY.md).

---

## If you want to read more

- [docs/find-a-run.md](docs/find-a-run.md) — locating the folder after a persist  
- [docs/scorer.md](docs/scorer.md) — what PASS and BLOCK are actually checking  
- [docs/tasks.md](docs/tasks.md) — writing another trap  
- [CONTRIBUTING.md](CONTRIBUTING.md) — sending a change  
- [AGENTS.md](AGENTS.md) — rules for agents **inside** this repository  

This is experimental. Read `evidence.md` yourself. The inspector catches a missing or quit-early packet; it does not certify that the product is correct.
