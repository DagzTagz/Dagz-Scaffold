# What the inspector actually checks

When you run `python3 harness/score.py` on a folder, you are not asking Grok another question. You are asking a small local program: **does this packet look complete and honest enough to count as a sitting?**

It does not call the network. It does not call the model. (The optional `--replay` flag is the exception: it can re-run a **narrow** list of commands on your machine. Leave it off unless you trust the evidence.)

First clone and persist: [getting-started.md](../getting-started.md). Finding the folder: [find-a-run.md](find-a-run.md).

---

## What you will see

The program prints a JSON blob (the detailed grade) and a one-line summary on the side. The **exit code** is the part to watch:

- **0** — the packet passed the mechanical checks (`ok` is true).
- **1** — the packet failed, or it was malformed (`INVALID`).
- **2** — you pointed it at something that is not a directory.

`ok` is about **process**, not about whether Celsius conversion is scientifically interesting. The numbers labeled persistence and rigor in the summary are **derived** from the packet (how many command blocks, whether a red test was followed by a green one, whether evidence is missing). The same fields inside `score.json` are the agent’s **self-report**. If the file says “I did not quit” but the evidence says “this should work,” the inspector believes the evidence.

`ship_gate.py` is the same idea with a friendlier PASS/BLOCK line. On a live folder you usually add `--git-checks` so it also looks at whether you accidentally staged secrets or a live `runs/` directory. Do not add `--git-checks` when you are only grading `examples/sample-run`.

If ship-gate says **BLOCK**, or `score.py` exits 1, the sitting is not done. If it says **PASS**, a skeptic could reconstruct the sitting from the folder. You still read the code.

---

## Why a packet fails

These names show up in `fail_reasons`. They are meant to be readable, not mysterious.

**quit_early.** The evidence talks like the agent bailed (“should work,” “too hard,” “gave up”), or the task required a failing test then a retry and only the green run is there, or there are no commands at all. The **plan** and **critic** are allowed to mention “too hard” as a thing to avoid. Evidence is not, except when it is quoting the task inside a markdown fence.

**REJECT.** The critic voted reject, and no **human** filled in an override. An override needs both `by` and `reason` in `score.json`. Grok is not allowed to invent that.

**missing_evidence** / **evidence_has_no_commands.** The critic listed missing evidence, or the evidence file has no command-looking content (no `python` lines, no fenced blocks). A story without output is not a sitting.

**dry_run.** This folder was written by `run.py --dry-run`. Failing is the correct answer.

**required_verification.** The task asked for specific strings (for example `273.15`, or a whole line `ab -> False`) to appear in the **command and output fences**. They were not there. Prose in the margin does not count, and a source dump in a `python` fence does not count either.

**task_contract_missing.** The task file never declared those required strings in a `scorer-contract` JSON fence. Public traps in this repo should not hit that.

---

## Task contracts, in plain language

Each public task includes a small JSON block under “Required verification.” It lists strings that must show up in evidence, and whether the sitting must include a fenced failure then a later command (`red_then_green`).

The inspector looks only in **command fences** and the **plain output fence that follows a command**. That stops an agent from hiding the required text in a comment or a diff.

If a required token looks like `a -> True`, it has to be a **whole line** of output. `aba -> True` does not count as `a -> True`.

How to write a new trap: [tasks.md](tasks.md).

---

## Derived numbers

The summary line’s persistence and rigor are caps computed from the packet, not a personality score for Grok.

If the agent quit early, persistence is zero. One command block without a required retry is at most half. A dry-run mock is marked as such. Missing evidence pulls rigor down. Those numbers **do not by themselves** flip `ok`. The fail reasons above do.

The JSON wrapper also reports `attempts` (how many command fences) and `recovered_after_failure` (whether a fenced traceback sits between commands).

---

## Replay, if you turn it on

```bash
python3 harness/score.py --replay runs/YOUR-FOLDER
```

Default is off. Fixtures under `examples/` are never executed this way.

When it is on, only a tight `python -c` shape (imports from `harness_tmp`) and a short list of **read-only-ish git** subcommands are allowed. Things like `os.system`, `python -m`, extra files, `git push`, and `git --git-dir=` are refused **and not started**. A traceback that is clearly the historical red run is skipped so we do not re-run a broken function against the already-fixed file.

If replay disagrees with the transcript, that is missing evidence, not a waiver.

`ship_gate.py` will replay live folders (not `examples/`). It has no `--replay` flag of its own.

---

## Practice packets in git

`examples/sample-run/` should pass. Several `examples/fail-*` and `examples/quit-early-run`, `reject-run`, `fake-green-run` should fail, each for a named reason. Those folders are synthetic. Live work belongs in `runs/`, which git ignores. Do not copy live packets into a pull request.
