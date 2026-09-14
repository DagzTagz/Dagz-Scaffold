# Contributing to Dagz-Scaffold

Thank you for your interest. This is an **open community effort** under the **DagzTagz** brand: a persistence harness so coding agents leave a folder a skeptic can audit.

**Unofficial DagzTagz project. Not an xAI product.** Live runs are **powered by Grok (xAI)** via the `grok` CLI under **your** account.

You do **not** need to be a professional programmer. Careful writing, trap ideas, and good bug reports all count.

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md).

---

## Before you start

1. Read the [README](README.md) for status and scope.
2. Run the smoke in [getting-started.md](getting-started.md) (`score.py` + `score_selftest.py` + hermetic `ship_gate.py`).
3. Check [open issues](https://github.com/DagzTagz/Dagz-Scaffold/issues).
4. For **large** changes (new architecture, new license, network in the scorer), open an issue first.

Small fixes (typos, docs clarity, obvious bugs) can go straight to a pull request.

---

## Ways to contribute

| Kind of help | Examples |
|--------------|----------|
| **Feedback & testing** | Run `/persist` on a trap; report what was confusing |
| **Documentation** | README, getting-started, `docs/` |
| **Trap tasks** | New `tasks/00N-*.md` with a `scorer-contract` — see [docs/tasks.md](docs/tasks.md) |
| **Fail fixtures** | Synthetic `examples/fail-*` that the scorer must reject |
| **Harness code** | `harness/` stdlib only; add tests in `score_selftest.py` |
| **Issues** | Bugs and ideas with secrets redacted |

---

## Ground rules

- Be respectful. Assume good intent.
- Prefer **truth-seeking** over hype: do not claim the scorer proved the science.
- Keep v0 **stdlib-only** for harness code. No surprise pip packages.
- **Never commit secrets**, live `runs/`, or Grok session dumps.
- Security issues → **private** report via [SECURITY.md](SECURITY.md).
- Do not submit generated walls of code with no explanation of intent.
- AI-assisted work is welcome when humans remain responsible (see below).

---

## Development setup

```bash
git clone https://github.com/DagzTagz/Dagz-Scaffold.git
cd Dagz-Scaffold
python3 harness/score.py examples/sample-run
python3 harness/score_selftest.py
python3 harness/ship_gate.py examples/sample-run
```

- Work on a **branch**, not `main`. Most people use a **fork + PR**.
- Keep the branch up to date with `main` before opening or updating a PR.
- Do not commit venv, live `runs/`, or editor junk. `.gitignore` already covers common cases.

Scorer internals: [docs/scorer.md](docs/scorer.md).

---

## Pull request process

### 1. Fork and branch

```bash
git checkout -b docs/fix-typo   # or fix/..., feat/..., etc.
```

Short names: `docs/security-link`, `fix/readme-typo`, `feat/task-006`.

### 2. Make focused changes

- One PR ≈ one concern.
- Match existing style.
- Update docs if usage changes.
- Add or adjust `score_selftest.py` when the scorer or fixtures change.

### 3. Commit messages

Present-tense summaries:

```text
docs: point ship-gate at the Python program
fix: deny git --git-dir in replay
feat: add task 006
```

Optional: signed commits (`git commit -S`). Not required for first-time contributors.

### 4. Open the pull request

Use [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md):

- **what** changed, **why**, how to **test**
- no secrets / no live `runs/`
- smoke commands (see template)
- If AI tools helped, say so briefly

### 5. Review and merge

Maintainers may ask for changes, split a PR, or decline work that fights v0 scope.

---

## Issues

### Bug reports

Include: what you did, what you expected, what happened, Python/`grok` versions, commands with **secrets redacted**. Prefer `examples/sample-run` and `--dry-run`.

### Trap / feature ideas

Describe the failure mode first, then a possible task. See [docs/tasks.md](docs/tasks.md).

### Security

Do **not** file public issues for vulnerabilities. Use [SECURITY.md](SECURITY.md).

---

## AI-assisted contributions

This project is built with transparent human–AI collaboration (including Grok Build).

You may use AI tools **if**:

1. **You understand** the change well enough to explain it.
2. **You review** every line for correctness, license, and secrets.
3. **You remain responsible** — tools do not own the commit.
4. For non-trivial PRs, **mention AI assistance** in the description.
5. Do not paste **private keys, tokens, live `runs/`, or personal data** into third-party AI tools.

Maintainers may request more human explanation on large AI-generated diffs.

---

## License

By contributing, you agree that your contributions are licensed under the same **MIT License** as this repository (see [LICENSE](LICENSE)).

You confirm that you have the right to submit the work.

---

## Questions

- Product / “where should I start?” → GitHub **issue**
- Security → [SECURITY.md](SECURITY.md) only
- Open PR → comment on that PR

Welcome aboard.
