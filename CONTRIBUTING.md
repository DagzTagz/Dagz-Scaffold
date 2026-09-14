# Contributing

Unofficial DagzTagz project. Not an xAI product. You need the `grok` CLI for
live runs; dry-run and scoring use Python 3.11+ stdlib only.

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md).

## Do not submit live runs

`runs/` is gitignored on purpose. Do not attach live `runs/<id>/` trees, grok
session dumps, `.env` files, or secrets to issues or pull requests. Checked-in
run fixtures under `examples/` (`sample-run/` plus `fail-*/`) are synthetic.

## Add a task

Public tasks are **small traps**, not apps.

1. Copy `tasks/001-units-trap.md` to `tasks/00N-short-name.md`.
2. Fill every section:
   - **Goal**
   - **Constraints**
   - **Hidden failure mode** (scorer notes; still do the work)
   - **Required verification** — include a `scorer-contract` JSON fence
     (`must_appear`, `red_then_green`). `python harness/score_selftest.py`
     lints it against the human section.
   - **Pass / fail notes** for `score.py` / the critic
3. Keep the work local. No network, no extra pip packages, no secrets.
4. Run the dry-run path and the sample scorer before you open a PR:

```bash
python harness/run.py --dry-run tasks/00N-short-name.md
python harness/score.py examples/sample-run
python harness/score_selftest.py
```

Dry-run writes files and does not call the model. Scoring that dry-run
directory exits 1 with `dry_run` in `fail_reasons`; that is expected.

## Run the scorer

```bash
python harness/score.py examples/sample-run
python harness/score_selftest.py
python harness/score.py runs/<id>    # local only; do not commit
```

Exit code is non-zero on `quit_early`, `REJECT`, missing evidence, `dry_run`,
`required_verification`, or `task_contract_missing`.

`must_appear` tokens are matched in command fences and each command's paired
output fence only — not in prose, diff hunks, or python module bodies. A
paired output fence must have an empty info-string (unlabeled); `diff` /
`python` / `markdown` fences after a command do not count. Dump tokens
containing ` -> ` must be a whole output line. When `red_then_green` is
true, evidence needs two command fences and a fenced
`Traceback (most recent call last)` or `AssertionError` strictly between them.

`score.json` must validate against `harness/schema/run.schema.json`.
If the critic verdict is `ACCEPT WITH WAIVERS`, each waiver needs an `id`
and a `reason`. Empty waiver lists are only valid for `ACCEPT`.

## Pull requests

Use the PR template checklist:

- no secrets
- `.gitignore` still correct (`git check-ignore -v .env runs/foo.json`)
- `python harness/run.py --dry-run tasks/002-quit-early.md` (writes files; scoring that dir is `dry_run`)
- `python harness/score.py examples/sample-run`
- `python harness/score_selftest.py`

Do not add GitHub Actions that check out untrusted PRs with write credentials.
Do not add hooks that upload the tree or read `$HOME` outside this project.
