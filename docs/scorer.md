# Reading the inspector

You already have a run folder (see [find-a-run.md](find-a-run.md)). You type two commands. This page is what those commands are trying to tell you, in ordinary language.

You are not asking Grok another question. You are asking a program on your computer: **did the agent leave enough proof that a stranger could reconstruct the work?**

First-time setup: [getting-started.md](../getting-started.md).

---

## The only two outcomes you need

After:

```bash
python3 harness/score.py runs/YOUR-FOLDER
python3 harness/ship_gate.py runs/YOUR-FOLDER --git-checks
```

**PASS** (both commands succeed, ship-gate prints `SHIP-GATE: PASS`) means the folder looks complete: a plan, evidence with real commands, a critic vote, a score file, and no “I quit” language in the evidence. You may treat the sitting as finished enough to consider merging. You should still open the diff. This tool does not replace reading the code.

**Not passed** (ship-gate prints `SHIP-GATE: BLOCK`, or the first command stops with an error) means do not merge. The chat may have sounded done. The folder is not. Scroll up: there will be a short reason. Give that reason back to Grok.

If the first command says the path is not a directory, you pointed it at a file or a typo. Use the folder name from `ls runs/`, not `score.json` by itself.

You can skip `--git-checks` when you are only practicing on `examples/sample-run`. Use `--git-checks` on a live folder so it also looks for secrets or a `runs/` directory accidentally staged for commit.

---

## What the two programs are

`score.py` is the picky reader. It opens the four files in the folder and checks they agree with each other and with the task.

`ship_gate.py` is the same check with a yes/no line you can read from across the room. On a live folder it can also look at git (the `--git-checks` part).

Neither one calls Grok. Neither one calls the internet. They only read what is already on disk (unless you later turn on `--replay`, which is optional and described at the bottom).

---

## What “the folder looks complete” actually means

Imagine a take-home exam. The inspector does not re-grade the math from scratch. It checks that the exam was filled in:

- There is a plan.
- There is evidence that includes **commands** (the kind of thing you could paste into a terminal) and, usually, what those commands printed.
- There is a critic file with a clear vote: accept, accept with named exceptions, or reject.
- The score file’s vote matches the critic. You cannot have the critic say reject and the score file say accept.
- If the critic listed blockers, the vote has to be reject (unless a **human** wrote an override — Grok is not allowed to write that).
- If the task said “you must show `273.15`” or “you must show a failing test then a passing one,” that proof has to appear in the evidence **as command output**, not as a sentence in the margin.

If the agent wrote “this should work” or “this was too hard” in the evidence, the inspector treats that as quitting, even if the score file claims otherwise. The plan is allowed to say “do not quit because it is too hard.” That is a warning to the agent, not a confession.

---

## If it failed, what the short reason usually means

The summary may print a machine name. Here is the human version.

**It looks like they quit (`quit_early`).** The evidence sounds like they stopped (“should work,” “too hard,” “gave up”), or the task required a first failing test and a later fix and only the success is there, or there are no commands at all.

**The critic said no (`REJECT`).** A second pass found a blocker. You can only force a pass with a human override that names who overrode and why. Do not let the model fill that in.

**There is no proof (`missing_evidence` or `evidence_has_no_commands`).** The evidence file is a story, or the critic said required checks were never run. A sitting without output is not a sitting.

**This was a fake persist (`dry_run`).** You scored a folder from `run.py --dry-run`. It is supposed to fail. Run a real persist if you meant to test the AI.

**A required example is missing (`required_verification`).** The task asked for specific output (a temperature, a line like `ab -> False`). It did not show up where commands and their printed results live. Hiding it in a comment does not count.

If the folder is missing files or the critic headings are wrong, the inspector will say the packet is malformed instead of grading it. That is also a fail. Send Grok back to write the four files properly.

---

## The numbers on the summary line

You will see words like persistence and rigor with values between 0 and 1. Those are **not** a score for how smart Grok is. They are a rough read of the folder: did they retry after a failure, did they show more than one command, is evidence thin.

They do **not** decide PASS vs BLOCK by themselves. The reasons in the previous section do. If the file claims persistence `1.0` and the evidence shows a quit, you still fail.

You can ignore the JSON blob if the one-line summary and PASS/BLOCK are enough. The JSON is there if you want the details.

---

## You can stop here

For everyday use — persist, find the folder, run the two commands, merge or don’t — that is the whole inspector.

The rest of this page is only if you turn on extra options or you write new tasks.

---

## Optional: re-running the commands (`--replay`)

```bash
python3 harness/score.py --replay runs/YOUR-FOLDER
```

This is **off** unless you ask for it. It tries to run some of the commands in the evidence again on your machine, to see if the transcript was fake.

Leave it off if you do not trust the folder, and leave it off for `examples/sample-run`. Only a small kind of `python -c` and a few `git` lookups are allowed. Dangerous-looking commands are refused and are not started.

If replay disagrees with what the evidence claimed, that counts as missing proof.

Ship-gate, on a **live** folder, may replay on its own. Practice folders under `examples/` are never executed this way.

---

## If you write tasks

Public traps include a small JSON list of strings the evidence must show, plus whether a failing test then a retry is required. Matching is picky on purpose: the string has to appear in the command/output area, and lines like `a -> True` must be a whole line so `aba -> True` cannot fake them.

How to add a trap: [tasks.md](tasks.md).
