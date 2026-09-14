## What

<!-- One or two sentences. What changed, and why. -->

## How to test

```bash
python3 harness/score.py examples/sample-run
python3 harness/score_selftest.py
python3 harness/ship_gate.py examples/sample-run
```

## Checklist

- [ ] No secrets, tokens, `.env` files, keys, or live `runs/` artifacts
- [ ] `.gitignore` still ignores local runs and secrets (`git check-ignore -v .env runs/foo.json`)
- [ ] Smoke commands above exit 0
- [ ] If I used `--dry-run`, I did **not** treat scoring that folder as a pass (`dry_run` / exit 1)
- [ ] Docs updated if usage changed ([getting-started.md](../getting-started.md), [docs/](../docs/))
- [ ] No GitHub Actions that check out untrusted PRs with **write** credentials
- [ ] No hooks that upload the repo, phone home, or read parent directories

## Task / harness (if this PR changes the scorer or a trap)

- Task file:
- `score_selftest.py`:
- AI assistance (if any):
