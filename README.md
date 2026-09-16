# Dagz-Scaffold

**An open-source persistence harness for agentic engineering.**  
**Unofficial DagzTagz project. Not an xAI product.** Powered by [Grok Build](https://github.com/xai-org/grok-cli) / the `grok` CLI under **your** account and terms.

Sister idea to [dagztagz-hypothesis-engine](https://github.com/DagzTagz/dagztagz-hypothesis-engine) (propose → adversarial verify → evidence). This repo does the same loop for **coding agents**, not scientific hypotheses.

> **Current status:** **v0.1.0** · public trap tasks 001–005 · stdlib-only scorer.  
> **Not a finished product** — iterative, disclosed early. History: [CHANGELOG.md](CHANGELOG.md).

---

## Why

Agents quit after the first red test, drop a constraint, and say they are done. A task here is **not done** until a folder a skeptic can audit exists:

1. `plan.md`
2. real diffs / code
3. `critic.md` with **BLOCKERS**, **RISKS**, **NITS**, **MISSING EVIDENCE**, **VERDICT**
4. `evidence.md` with commands and output
5. `score.json`

Verdicts: `REJECT` | `ACCEPT WITH WAIVERS` | `ACCEPT`.  
`REJECT` returns work to the builder. Waivers must be explicit objects with `id` and `reason`.

## What ships today

- **Plan → builder → critic → evidence → score** loop (`/persist`, `/critic`, `/ship-gate`)
- **Stdlib scorer** (`python harness/score.py`) — **derived** quit_early / missing_evidence / persistence / rigor; claims in `score.json` are hints
- **Live `run.py`** scores after `grok -p` and retries once on REJECT (cap 2 live calls). Dry-run never calls grok.
- **Fail-closed quit-early** on evidence phrases; task `scorer-contract` JSON; `ship_gate.py`
- **Optional `--replay`** — AST-allowlisted `python -c` and allowlisted `git` as a **local** subprocess (default **off**)
- **Public traps** in `tasks/` (units, quit-early, fake-green, scope-cut, missing evidence)
- **Synthetic fixtures** in `examples/` (pass + fail). Live `runs/` stay gitignored

Target users: people who already have the `grok` CLI, or anyone who wants to **score a persist folder** with Python 3.11+ and no pip.

## How it works

```text
task file  →  plan.md  →  builder diffs  →  critic.md  →  evidence.md  →  score.json
                 ↑                              | REJECT
                 └──────── retry with a new hypothesis ─┘
```

`score.py` is a cheap lie detector, not a scientist. It checks process (files, verdicts, required tokens, replay). Correctness still sits with you and the critic.

Full walkthrough: **[getting-started.md](getting-started.md)**.  
Find a live folder: **[docs/find-a-run.md](docs/find-a-run.md)**.  
Scorer details: **[docs/scorer.md](docs/scorer.md)**.  
Adding a trap: **[docs/tasks.md](docs/tasks.md)**.

---

## Getting started

> ### Smoke test first (no Grok, $0)
>
> ```bash
> git clone https://github.com/DagzTagz/Dagz-Scaffold.git
> cd Dagz-Scaffold
> python3 harness/score.py examples/sample-run
> python3 harness/test_score.py
> python3 harness/score_selftest.py
> python3 harness/ship_gate.py examples/sample-run
> ```
>
> You should see `ok: true` / `SHIP-GATE: PASS` and a self-test OK.  
> Then read **[getting-started.md](getting-started.md)** before a live `/persist`.

### Dry-run vs live

| Dry-run / score smoke | Live `grok` / `run.py` without `--dry-run` |
|----------------------|--------------------------------------------|
| No `grok` login | Requires your Grok CLI login |
| No model call | May send repo context to xAI |
| **$0** | **Your Grok / xAI account** |
| `--dry-run` writes a mock `runs/` folder that **scores as `dry_run` (exit 1)** | Real persist can `ACCEPT` |

`--dry-run` does **not** call the network or the model. Scoring that mock folder is **not** a pass.

### Disclosures

- **Not an official xAI product.** “Powered by Grok” means the live path can call the Grok CLI; it does not mean endorsement.
- **Your account, your terms.** Live runs use **your** Grok login. This project does not pay for usage.
- **Do not commit secrets or live `runs/`.** See [SECURITY.md](SECURITY.md).
- **Experimental.** Trap tasks are a gym for agents, not production apps.

---

## Contributing

Docs, trap ideas, failing fixtures, and harness patches are all useful. You do not need to be a professional programmer.

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Roadmap

### v0.1 — current

- [x] Persist / critic / ship-gate skills
- [x] Evidence-scoped quit-early + fail fixtures
- [x] Task `scorer-contract` (`must_appear`, `red_then_green`)
- [x] `ship_gate.py` (optional `--git-checks`)
- [x] Optional AST replay (`--replay`, default off)
- [x] Derived persistence/rigor printed; claims stay in `score.json`

### Next

- [ ] GitHub-facing docs at hypothesis-engine quality (this drop)
- [x] Read-only CI (`test_score.py` + sample-run) — no secrets, no `grok`
- [ ] More public traps; keep live `runs/` gitignored

### Non-goals

- Scoring raw `~/.grok/sessions/` chat dumps
- Calling the model from `score.py`
- Dashboards, extra pip packages, schema v2 for derived fields

## Layout

```text
.grok/skills/     persist, critic, ship-gate
.grok/agents/     builder + critic
harness/          run.py, score.py, replay.py, score_selftest.py, test_score.py, ship_gate.py, schema
tasks/            small public traps
examples/         sample-run plus synthetic fail-* fixtures
docs/             scorer + task authoring
runs/             live artifacts (gitignored)
```

## License

MIT. See [LICENSE](LICENSE).

Hypothesis Engine is Apache-2.0; this repo stays MIT unless maintainers decide otherwise.

## Acknowledgments

- **DagzTagz** community
- **xAI / Grok** — Grok Build CLI and pair-programming assistance (**not** an official product)
- [dagztagz-hypothesis-engine](https://github.com/DagzTagz/dagztagz-hypothesis-engine) — the documentation and verify-then-evidence pattern

## Disclaimer

**Dagz-Scaffold** is a community project and is **not** an official product of xAI.  
It is an experimental harness for agent engineering. Always read `evidence.md` yourself. Prefer the smoke commands above until you intentionally run live `grok`.

**Let’s leave folders a skeptic can audit.**
