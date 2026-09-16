# Contributing

Thank you for wanting to help. Dagz-Scaffold is a community project under the DagzTagz name. The point is simple: when a coding agent says it is finished, it should leave a folder a skeptical human can audit.

**Unofficial DagzTagz project. Not an xAI product.** Live persists use the Grok CLI on **your** account.

You do not need to be a professional programmer. If you can write clearly, try a trap and tell us where you got stuck, or spot a typo, that is already useful.

Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Security problems go through [SECURITY.md](SECURITY.md), not a public issue.

---

## Before you change code

Read the [README](README.md) so the scope is not a surprise. Run the smoke test in [getting-started.md](getting-started.md) (`score.py`, the two test files, and ship-gate on `examples/sample-run`). Glance at [open issues](https://github.com/DagzTagz/Dagz-Scaffold/issues).

Small fixes — wording, obvious bugs — can go straight to a pull request. Large changes (new architecture, a license switch, anything that makes the scorer call the network) should be an issue first so nobody is surprised.

---

## Ways people help

Some people run `/persist` on a trap and report what was confusing. Some improve these docs. Some add a new public trap (see [docs/tasks.md](docs/tasks.md)) or a synthetic packet under `examples/` that the inspector **must** reject. Some patch `harness/` itself; that code stays Python stdlib, and tests go in `score_selftest.py` or `test_score.py`.

Whatever you send, do not commit secrets, live `runs/` folders, or Grok session dumps. Do not claim the scorer “proved the science.” It proved the packet.

---

## A local setup

```bash
git clone https://github.com/DagzTagz/Dagz-Scaffold.git
cd Dagz-Scaffold
python3 harness/score.py examples/sample-run
python3 harness/test_score.py
python3 harness/score_selftest.py
python3 harness/ship_gate.py examples/sample-run
```

Work on a **branch**, not on `main`. Most people fork, push the branch, and open a pull request. Keep the branch current with `main` before you ask for review. `.gitignore` already covers virtualenvs, live runs, and editor junk.

How the inspector thinks: [docs/scorer.md](docs/scorer.md).

---

## Pull requests

Name the branch after the change (`docs/find-a-run`, `fix/readme-typo`, `feat/task-006`). Keep one concern per PR. Match the style of nearby files. If you change how people run the tool, update the docs in the same PR. If you change the scorer or fixtures, add or adjust tests.

Commit messages in the present tense help (`docs: explain how to find a run folder`). Signed commits are welcome and not required.

The pull request template asks what changed, why, and how you tested it. Paste the smoke commands. Do not attach live `runs/`. If an AI tool helped, say so in a sentence. You remain responsible for every line.

Maintainers may ask for changes, split a PR, or decline work that fights v0 (no mystery pip packages, no model calls from `score.py`).

---

## Issues

For bugs, write what you did, what you expected, what happened, and Python / Grok versions. Redact secrets. Prefer reproducing with `examples/sample-run` or `--dry-run`.

For a new trap, describe the failure mode first, then a possible task. [docs/tasks.md](docs/tasks.md) has the shape.

Vulnerabilities are **private** only. See [SECURITY.md](SECURITY.md).

---

## AI-assisted work

This project is itself a human–AI collaboration, including Grok Build. You may use AI tools if you understand the change, you review every line (correctness, license, secrets), and you do not paste private keys, tokens, live run folders, or personal data into third-party tools. For a non-trivial PR, mention the assistance. Maintainers may ask for more human explanation on a giant generated diff.

---

## License

By contributing you agree your work is licensed under the same **MIT License** as this repository ([LICENSE](LICENSE)), and that you have the right to submit it.

Questions about “where do I start?” can be a normal GitHub issue. Security stays on the private path. Discussion of an open PR belongs on that PR.

Welcome aboard.
