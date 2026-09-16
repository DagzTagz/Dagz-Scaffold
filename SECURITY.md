# Security Policy

If you found something that could hurt people who clone this repo — a leaked key, a way to run unexpected commands, a path that uploads their work — please tell us **privately**. This page is the how-to. Ordinary bugs and “the docs confused me” belong in a normal GitHub issue.

Thank you for helping keep Dagz-Scaffold and its users safe. This is a DagzTagz community project. Live runs are powered by Grok (xAI) when you use the `grok` CLI. This is **not** an official product of xAI.

---

## Supported versions

| Version / branch | Supported |
|------------------|-----------|
| `main` / latest tag (currently **0.1.0+**) | Yes — security and privacy fixes land here |
| Forks / unknown snapshots | Best-effort only; report against current `main` |

This project is **iterative early open source** (pre-1.0). Privacy-relevant changes go in [CHANGELOG.md](CHANGELOG.md).

---

## What is in scope

Please report vulnerabilities that affect:

- This repository’s source, scripts, configs, and published artifacts
- Secret handling (accidental logging or commit of keys, tokens, live `runs/`)
- Path traversal, command injection, or unsafe subprocess use in `harness/` (especially `--replay`)
- Ways to abuse the scorer/ship-gate that create a **realistic** security impact (for example, replay spawning denied commands)
- Supply-chain issues in **this** project’s release process (v0 has no PyPI package)

## What is out of scope

Please **do not** open security reports for:

- An agent quitting early or a trap task “being too easy” (use a normal issue)
- Theoretical issues with no realistic exploit path
- Vulnerabilities only in VirtualBox, the `grok` CLI, or xAI (report those upstream)
- Social engineering of individual contributors
- Denial of service against public APIs you do not operate

If you are unsure, report it privately anyway.

---

## How to report a vulnerability

### Preferred: GitHub Security Advisories (private)

1. Open https://github.com/DagzTagz/Dagz-Scaffold  
2. **Security → Advisories → Report a vulnerability**  
   (or https://github.com/DagzTagz/Dagz-Scaffold/security/advisories/new )  
3. Include as much detail as you can (see below).

### Alternative: private email

**dagztagz369@proton.me**

Subject: `[SECURITY] Dagz-Scaffold …`

Do **not** send live keys in a public channel. If a key was exposed, say *that a key was exposed* and rotate it if you own it.

---

## What to include

1. **Summary** — one or two sentences  
2. **Impact** — who/what is affected  
3. **Affected component** — file, flag, commit if known  
4. **Steps to reproduce** — prefer `--dry-run` and `examples/`  
5. **Proof of concept** — only what is needed (no mass scanning)  
6. **Suggested fix** — optional  
7. **Your contact**  
8. **Disclosure timeline** — if you have a preferred date  

Strip keys, cookies, session dumps, and live `runs/` first.

---

## Our commitments

When you report in good faith, we will aim to:

- **Acknowledge** within **72 hours** (often sooner)
- **Triage** and confirm or ask questions
- **Keep you informed** of major status changes
- **Credit you** in the advisory or changelog if you want credit
- **Not take legal action** against good-faith, non-destructive research that follows this policy

We may decline reports that are out of scope or not security issues, and will try to explain why.

---

## Coordinated disclosure

- Default: up to **90 days** to investigate and ship a fix before public write-ups
- We may ask for more time; we may publish sooner if user risk is high
- Do **not** post exploit details in public issues or social media before we agree a date
- **Never** open a public issue that contains live secrets or private `runs/`

---

## Safe harbor (good-faith research)

Research under this policy is authorized for **this** project when you:

- Avoid privacy violations, service disruption, and data destruction
- Do not access data that is not yours beyond what is needed to demonstrate the issue
- Do not exploit the finding for any purpose other than reporting
- Report promptly through the private channels above

This does **not** cover attacks on infrastructure you do not own, spam, malware, or anything illegal.

---

## What is stored locally

| Path | What it is | Commit? |
|------|------------|---------|
| `runs/` | Live agent artifacts | **No** (gitignored except `.gitkeep`) |
| `.env` | Environment secrets | **No** |
| `.grok/sessions/`, `.grok/memory/`, `.grok/cache/` | Grok local state | **No** |
| `examples/` | Synthetic fixtures | Yes |
| `.env.example` | Dummy names, **empty** values | Yes |

`harness/run.py --dry-run` and `harness/score.py` (without `--replay`) read and write **local files only**. They must not call the network.

Live `run.py` (no `--dry-run`) shells out to `grok -p`, which may send repository context to xAI under **your** account.

`--replay` is a **local** subprocess of AST-allowlisted `python -c` and allowlisted `git`. Denied commands must not be spawned. Default **off**. Do not replay untrusted evidence.

This harness does not ship API keys. Do not copy `~/.grok/auth.json`, `~/.xai_api_key`, SSH keys, or cloud credentials into the repo.

---

## Hooks and CI

v0 ships **no** executable project hook that phones home.

**Allowed later:** a **read-only** GitHub Actions workflow that runs `python3 harness/score_selftest.py`, `score.py examples/sample-run`, and `ship_gate.py examples/sample-run` with **no** repository secrets and **no** `grok`. That is the same idea as hypothesis-engine’s offline CI.

Do **not** add Actions that check out untrusted PRs with **write** credentials.

Optional local hooks, if you add them, must stay reviewable and must not upload the repo or read parent directories outside this project. See [`.grok/hooks/README.md`](.grok/hooks/README.md).

---

## Security practices (maintainers and contributors)

- **Never commit secrets** (API keys, tokens, private keys, real `.env` values, live `runs/`)
- Keep `.env.example` as placeholders with empty values
- Prefer signed commits when practical
- If you accidentally committed a secret: **private** report, then rotate
- Document privacy-relevant default changes in **CHANGELOG.md**

See `.gitignore` for patterns we already try to keep out of the tree.

---

## Prefer GitHub features when available

- Private vulnerability reporting / Security Advisories
- Secret scanning and push protection
- Dependabot only if non-stdlib dependencies appear (v0 harness is stdlib-only)

Public issues remain the right place for non-security bugs and trap ideas.

---

## Export controls and live API use

- **Public open source:** MIT on this repository. Use of the **Grok / xAI** stack in live mode is subject to [xAI’s terms](https://x.ai/legal/terms-of-service) and applicable **US export and sanctions laws**. **You** are responsible for lawful use.
- **No circumvention:** Do **not** use this project to evade sanctions, export controls, or other applicable law.
- Live mode is **your** CLI and **your** account. This community project is **not** responsible for unexpected API or CLI usage charges.

---

## Questions

Non-sensitive policy questions → a normal GitHub issue.  
Anything that might be a vulnerability → private channels above.
