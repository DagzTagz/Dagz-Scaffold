# Find a run folder and point the inspector at it

After Grok **claims** the work is done, the packet is a **folder**, not a single file. Docs write `runs/<id>/`. You replace `<id>` with the real directory name on **your** machine.

Unofficial DagzTagz project. Not an xAI product.

## What you are looking for

A directory under the **repo root** named like:

```text
runs/20260913T220306Z-002-quit-early/
```

Inside it you should see at least:

- `plan.md`
- `critic.md`
- `evidence.md`
- `score.json`

That whole directory is the “run.” Point `score.py` and `ship_gate.py` at **that path**.

`examples/sample-run/` is a **fixture** for smoke tests. It is not your live persist. Do not use `--git-checks` on it.

---

## Step 1 — Open a terminal in the repo

You must be in the clone, the same place you ran `grok` or `harness/run.py`.

```bash
cd /path/to/Dagz-Scaffold
```

On this project’s usual Linux VM that is:

```bash
cd /path/to/Dagz-Scaffold
```

If you cloned somewhere else, `cd` there instead. `ls harness/score.py` should succeed.

## Step 2 — List live run folders

```bash
ls runs/
```

Example output:

```text
20260913T220306Z-002-quit-early
20260913T221239Z-001-units-trap
20260916T133802Z-002-quit-early
```

Pick the folder for **this** attempt. Newest is usually last in `ls -1t`:

```bash
ls -1t runs | head
```

**Empty `runs/`?** Persist has not written a live packet yet (or you are in the wrong clone). Do the smoke in [getting-started.md](../getting-started.md) first, then `/persist tasks/002-quit-early.md` or `python3 harness/run.py tasks/002-quit-early.md`.

**Only a dry-run folder?** `python3 harness/run.py --dry-run …` writes a mock. Scoring it **exits 1** with `dry_run`. That is not a pass.

## Step 3 — Confirm it is a run packet

Replace the name with yours:

```bash
ls runs/20260913T220306Z-002-quit-early
```

You want `plan.md`, `critic.md`, `evidence.md`, `score.json`. If those are missing, the agent did not finish the packet. Do not merge.

## Step 4 — Point the inspector at that folder

Same name in both commands:

```bash
python3 harness/score.py runs/20260913T220306Z-002-quit-early
python3 harness/ship_gate.py runs/20260913T220306Z-002-quit-early --git-checks
```

Copy the directory name from `ls runs/`. Do not type the angle brackets. Wrong:

```bash
python3 harness/score.py runs/<id>          # placeholder, will fail
python3 harness/score.py runs/score.json    # a file, not the folder
```

## Step 5 — Read the gate

| Result | Meaning |
|--------|---------|
| `SHIP-GATE: PASS` and exit 0 | Packet is complete enough to consider merging. Still read the diff. |
| `SHIP-GATE: BLOCK` or scorer exit 1 | Not shipped. Send the blockers back to Grok. |

`--git-checks` looks at **this clone’s** git index (staged `runs/`, secret names). Use it on live `runs/<id>/`. Do not use it on `examples/sample-run`.

---

## Name pattern

```text
YYYYMMDDTHHMMSSZ-<task-slug>
```

Example: `20260913T220306Z-002-quit-early` is a persist of `tasks/002-quit-early.md` started at that UTC time.

## Do not

- `git add` the folder (`runs/` is gitignored except `.gitkeep`)
- Attach live `runs/` to GitHub issues or PRs
- Confuse `~/.grok/sessions/` (chat dump) with `runs/` (inspector packet). Chat dumps are **not** scoreable.

```bash
git check-ignore -v runs/20260913T220306Z-002-quit-early/score.json
```

That should print an ignore rule. Good.

## Next

What PASS/BLOCK mean: [scorer.md](scorer.md).  
First clone / persist: [getting-started.md](../getting-started.md).
