# Security Policy

This is an **unofficial DagzTagz** project. It is **not an xAI product**.
Live `grok` runs use the Grok Build / xAI stack under **your** account and terms.

## Report vulnerabilities privately

Do **not** open a public issue for a security bug. Do **not** paste secrets,
API keys, tokens, private diffs, or live `runs/` output into GitHub issues,
pull requests, or chat.

Preferred:

1. If this repository is on GitHub with Security Advisories enabled, use
   **Security → Advisories → Report a vulnerability**.
2. Otherwise email **dagztagz369@proton.me** with enough detail to reproduce.

Include: affected files, what you expected, what happened, and a redacted
proof. Strip keys, cookies, and session dumps first.

## What is stored locally

| Path | What it is | Commit? |
|------|------------|---------|
| `runs/` | Live agent artifacts (`plan.md`, diffs, critic, evidence, scores) | **No** (gitignored) |
| `.env` | Environment secrets | **No** |
| `.grok/sessions/`, `.grok/memory/`, `.grok/cache/` | Grok local state | **No** |
| `examples/sample-run/` | Synthetic fixture only | Yes |
| `.env.example` | Dummy names, empty values | Yes |

`harness/run.py --dry-run` and `harness/score.py` read and write **local files
only**. They must not call the network. Live `run.py` (no `--dry-run`) shells
out to `grok -p`, which may send repository context to xAI under your account.

## Live grok runs

A live run may send code, task text, diffs, and command output to xAI.
That is your CLI, your account, your terms. Do not put secrets in task files,
prompts, `runs/`, or issues.

This harness does not ship API keys. Do not copy `~/.grok/auth.json`,
`~/.xai_api_key`, SSH keys, or cloud credentials into the repo.

## Hooks and CI

v0 ships **no** executable project hook and **no** GitHub Actions workflow.
Optional hooks, if you add them, must stay local, be reviewable, and must not
upload the repo, phone home, or read parent directories outside this project.
See [`.grok/hooks/README.md`](.grok/hooks/README.md).

## Supported versions

Only `main` (this v0 tree) is supported. Forks and copies are best-effort.
