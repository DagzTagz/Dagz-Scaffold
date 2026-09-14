## What

-

## Checklist

- [ ] No secrets, tokens, `.env` files, keys, or live `runs/` artifacts
- [ ] `.gitignore` still ignores local runs and secrets (`git check-ignore -v .env runs/foo.json .venv/bin/python`)
- [ ] `python harness/run.py --dry-run tasks/002-quit-early.md` (writes files; no network, no model)
- [ ] Scoring that dry-run dir exits 1 with `dry_run` (do not treat it as a pass)
- [ ] `python harness/score.py examples/sample-run` exits 0
- [ ] `python harness/score_selftest.py` exits 0
- [ ] No GitHub Actions that check out untrusted PRs with write credentials
- [ ] No hooks that upload the repo, phone home, or read parent directories

## Task / score (if this PR is a harness change)

- Task file:
- Scorer result:
