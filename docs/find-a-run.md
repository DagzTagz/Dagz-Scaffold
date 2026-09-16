# Find your run folder

After Grok claims the work is finished, the proof is not the chat. It is a **folder** on your computer. Documentation writes that path as `runs/<id>/`. The angle brackets are a placeholder. You replace them with the real directory name sitting on **your** disk.

This page is only about finding that folder and pointing the inspector at it. What PASS and BLOCK mean is in [scorer.md](scorer.md). First-time install is in [getting-started.md](../getting-started.md).

Unofficial DagzTagz project. Not an xAI product.

---

## What the folder is

Under the project root there is a directory named `runs/`. Each persist creates **one child folder** inside it. A name looks like this:

```text
runs/20260913T220306Z-002-quit-early/
```

The first half is the UTC time the sitting started. The second half is a short slug from the task file (`tasks/002-quit-early.md` became `002-quit-early`).

Inside a finished packet you should see at least four files: `plan.md`, `critic.md`, `evidence.md`, and `score.json`, plus whatever code the agent actually changed (often under `harness_tmp/`, which git also ignores).

That **whole directory** is the run. You pass that path to `score.py` and `ship_gate.py`. You do not pass a single file such as `score.json`.

`examples/sample-run/` is a fake packet we keep in git so the smoke test has something to grade. It is not your live persist. Do not run `--git-checks` on it.

---

## Step 1. Stand in the project folder

Open a terminal in the same clone where you ran `grok` or `harness/run.py`.

```bash
cd /path/to/Dagz-Scaffold
```

Use the path on **your** machine. A quick check: `ls harness/score.py` should print that filename. If it does not, you are in the wrong directory.

---

## Step 2. List what persist left behind

```bash
ls runs/
```

You might see several names:

```text
20260913T220306Z-002-quit-early
20260913T221239Z-001-units-trap
20260916T133802Z-002-quit-early
```

Each line is one sitting. For “the thing I just ran,” newest first:

```bash
ls -1t runs | head
```

**If `runs/` looks empty** (or only has a `.gitkeep` you cannot see with plain `ls`), persist has not written a live packet in this clone. Go back to [getting-started.md](../getting-started.md), run the smoke test, then `/persist` or `python3 harness/run.py` on a task.

**If the only new folder came from `--dry-run`**, it is a mock. Scoring it should fail with `dry_run`. That is not a pass.

---

## Step 3. Peek inside before you grade

Copy a name from the list and look at it:

```bash
ls runs/20260913T220306Z-002-quit-early
```

You want to see `plan.md`, `critic.md`, `evidence.md`, and `score.json`. If those are missing, the agent did not finish the packet. There is nothing honest to merge. Send it back to Grok.

---

## Step 4. Point the inspector at that folder

Use the **same** name in both commands. This example uses one real-looking timestamp; yours will differ.

```bash
python3 harness/score.py runs/20260913T220306Z-002-quit-early
python3 harness/ship_gate.py runs/20260913T220306Z-002-quit-early --git-checks
```

Paste from `ls`. Do not type the characters `<id>`. These will not work:

```bash
python3 harness/score.py runs/<id>
python3 harness/score.py runs/score.json
```

`--git-checks` looks at whether **this clone** has staged a live `runs/` folder or a secret-shaped file. Use it on a live packet. Skip it on `examples/sample-run`.

---

## Step 5. Read what it said

If ship-gate prints `SHIP-GATE: PASS` and both commands exit 0, the packet is complete enough to consider shipping. You should still open the diff. The inspector did not read your product the way a human reviewer does.

If it prints `SHIP-GATE: BLOCK`, or `score.py` exits 1, it is not shipped. The summary line will name reasons such as `quit_early`, `REJECT`, or `missing_evidence`. Give those back to Grok. Do not merge because the conversation was polite.

---

## Please do not

Git is configured to ignore live `runs/` folders (except a placeholder file). You should not `git add` them or attach them to GitHub issues.

Do not confuse `~/.grok/sessions/` with `runs/`. The first is a chat dump. The inspector cannot grade a chat dump. The second is the packet this project exists to create.

This should print an ignore rule, which is what you want:

```bash
git check-ignore -v runs/20260913T220306Z-002-quit-early/score.json
```

When you are ready to interpret PASS and BLOCK in more depth, read [scorer.md](scorer.md).
