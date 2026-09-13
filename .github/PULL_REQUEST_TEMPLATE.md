## What

-

## Checklist

- [ ] No secrets, tokens, `.env` files, keys, or live `runs/` artifacts
- [ ] `.gitignore` still ignores local runs and secrets (`git check-ignore -v .env runs/foo.json .venv/bin/python`)
- [ ] `python harness/run.py --dry-run tasks/002-quit-early.md` (no network, no model)
- [ ] `python harness/score.py examples/sample-run` exits 0
- [ ] No GitHub Actions that check out untrusted PRs with write credentials
- [ ] No hooks that upload the repo, phone home, or read parent directories

## Task / score (if this PR is a harness change)

- Task file:
- Scorer result:
