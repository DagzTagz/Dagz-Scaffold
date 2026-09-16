# Getting Started — Dagz-Scaffold

This guide runs the **Dagz-Scaffold** harness: plan → builder → critic → evidence → score.

**Unofficial DagzTagz project. Not an xAI product.**  
Live path is **powered by Grok (xAI)** via the `grok` CLI under **your** account. Scoring and dry-run do not call the model.

## Requirements

- Python **3.11+** (stdlib only — **no pip** for the harness)
- Git
- `grok` CLI **only** for live `/persist` or `harness/run.py` without `--dry-run`

Use `python3` if `python` is not on `PATH`.

## 1. Get the code

```bash
git clone https://github.com/DagzTagz/Dagz-Scaffold.git
cd Dagz-Scaffold
```

Already have a clone? `cd` into it and `git pull`.

ZIP download: unzip, then `cd` into the folder (it may be named `Dagz-Scaffold-main`).

## 2. Smoke test (no Grok, $0)

From the **repo root**:

```bash
python3 --version    # 3.11 or newer
git --version

python3 harness/score.py examples/sample-run
python3 harness/test_score.py
python3 harness/score_selftest.py
python3 harness/ship_gate.py examples/sample-run
```

**Success:** `score.py` prints JSON and a one-line `ACCEPT WITH WAIVERS …` with `ok` implied by exit 0. Self-test prints `OK`. Ship-gate prints `SHIP-GATE: PASS` and exit 0.

If any of those commands exit non-zero, stop — the checkout is incomplete.

Do **not** pass `--git-checks` on `examples/sample-run`. That flag reads **this clone’s git index**. Do **not** pass `--replay` on the smoke; default off means a local-files read with no subprocess.

Linux packages if `python3` is missing (Ubuntu):

```bash
sudo apt update && sudo apt install -y python3 git
```

## 3. Optional dry-run of the wrapper

```bash
python3 harness/run.py --dry-run tasks/002-quit-early.md
```

This prints `skipped grok` and writes a folder under `runs/` (gitignored).  
**Scoring that folder exits 1** with `dry_run` in `fail_reasons`. That is expected. It is a mock, not a live persist.

## 4. Interactive persist (recommended)

Install and log in to the [Grok Build CLI](https://github.com/xai-org/grok-cli) on this machine first.

From the repo root:

```bash
grok
```

In the session:

1. `/persist tasks/002-quit-early.md` (or another file under `tasks/`).
2. The agent writes `runs/<id>/plan.md`, implements, records **commands + output** in `evidence.md`.
3. A **critic** writes `critic.md`. `REJECT` means more work, not a polish pass.
4. Before you call it done, run the **program** (another terminal, same repo):

```bash
ls runs/
python3 harness/score.py runs/<id>
python3 harness/ship_gate.py runs/<id> --git-checks
```

`<id>` is a **folder name**, not a file. How to find it on your machine: **[docs/find-a-run.md](docs/find-a-run.md)**. Example on one Linux clone: `runs/20260913T220306Z-002-quit-early`.

`SHIP-GATE: BLOCK` or scorer exit 1 → not done. Do not skip `ship_gate.py`.

The `/ship-gate` skill is a reminder. The gate that counts is the Python program.

## 5. Headless live run

Calls `grok -p`. Usage follows **your** Grok account.

```bash
python3 harness/run.py tasks/002-quit-early.md
python3 harness/score.py runs/<the-new-id>
python3 harness/ship_gate.py runs/<the-new-id> --git-checks
```

## Cost and privacy

- Smoke + `--dry-run` + `score.py` without `--replay`: **no model call, $0**.
- Live `grok` / `run.py`: may send task text, diffs, and command output to xAI under **your** login. This project does not cap your bill.
- Optional `python3 harness/score.py --replay runs/<id>`: **local** subprocess of allowlisted commands only. Default **off**. Never `--replay` on untrusted evidence you have not read.
- Live `runs/` stay on **your** disk (gitignored). Do not attach them to issues or PRs.

Full policy: [SECURITY.md](SECURITY.md).

## Do not commit

- `runs/` (except `runs/.gitkeep`)
- `.env` (template is `.env.example` with **empty** values)
- keys, tokens, `auth.json`, Grok session dumps (`.grok/sessions/`, `.grok/memory/`, `.grok/cache/`)

```bash
git check-ignore -v .env runs/foo.json
```

## Next reading

| Doc | When |
|-----|------|
| [docs/find-a-run.md](docs/find-a-run.md) | Locate `runs/<id>/` and point score/ship-gate at it |
| [docs/scorer.md](docs/scorer.md) | What `ok` / `fail_reasons` / derived scores mean |
| [docs/tasks.md](docs/tasks.md) | Adding a public trap |
| [CONTRIBUTING.md](CONTRIBUTING.md) | PRs, AI-assisted work |
| [AGENTS.md](AGENTS.md) | Rules for coding agents in this repo |

## Disclaimer

Experimental community harness. Not established engineering process. Not an official xAI product. Read `evidence.md` yourself.
