# Dagz-Scaffold

**Unofficial DagzTagz project. Not an xAI product.** Powered by [Grok Build](https://github.com/xai-org/grok-cli) / the `grok` CLI under **your** account and terms.

Sister idea to [dagztagz-hypothesis-engine](https://github.com/DagzTagz/dagztagz-hypothesis-engine) (propose → adversarial verify → evidence), but this repo is a persistence + self-check harness for **agentic engineering work**, not science hypotheses.

Target users: people who already have the `grok` CLI installed.

## Why

Agents quit early on hard tasks and declare done without checking their work. A task here is **not done** until all of these exist:

1. `plan.md`
2. diffs / code changes
3. `critic.md` with **BLOCKERS**, **RISKS**, **NITS**, **MISSING EVIDENCE**, and **VERDICT**
4. `evidence.md` that a skeptic can read without the chat
5. `score.json`

Verdicts: `REJECT` | `ACCEPT WITH WAIVERS` | `ACCEPT`.  
`REJECT` returns work to the builder. The run cannot complete on `REJECT`. Waivers must be explicit.

## Requirements

- Python **3.11+** (stdlib only for v0 — no pip packages)
- `grok` CLI for live runs (`grok -p`)
- Git

`--dry-run` does **not** call the network or the model.

## The loop (under 2 minutes)

```text
task file  →  plan.md  →  builder diffs  →  critic.md  →  evidence.md  →  score.json
                 ↑                              | REJECT
                 └──────── retry with a new hypothesis ─┘
```

1. Open this repo in `grok` (or run the harness).
2. Invoke **`/persist`** on a task. That creates `runs/<id>/`, demands a plan, then builder → critic.
3. Critic is hostile. `REJECT` means more work, not a polish pass.
4. Write `evidence.md` so someone who was **not** in the session can still believe you.
5. Score the run locally:

```bash
python harness/score.py examples/sample-run
```

Live wrapper (calls `grok -p` unless you pass `--dry-run`):

```bash
python harness/run.py --dry-run tasks/002-quit-early.md
python harness/run.py tasks/002-quit-early.md          # requires grok
python harness/score.py runs/<id>
```

`score.py` prints JSON plus one line, and exits non-zero on `quit_early`, `REJECT`, or missing evidence.

## Persistence vs quit-early

**Quit-early** if the agent:

- declares done before verification
- calls the task too hard without exhausting the plan
- silently shrinks the problem
- stops after one failed check
- never attempts a check the critic later finds

**Persistent** if it:

- follows the plan through verification
- turns failed checks into a new hypothesis and another attempt
- uses the budget or reaches signed-off done
- leaves evidence that would convince a skeptic who was not in the session

Scores: `persistence` (0–1) and `rigor` (0–1).

## Layout

```text
.grok/skills/     persist, critic, ship-gate
.grok/agents/     builder + critic
harness/          run.py, score.py, schema
tasks/            small public traps
examples/sample-run/   synthetic fixture only
runs/             live artifacts (gitignored)
```

## Do not commit

- `runs/` (except `runs/.gitkeep`)
- secrets, `.env`, keys, tokens, `auth.json`, `credentials.json`
- Grok session dumps (`.grok/sessions/`, `.grok/memory/`, `.grok/cache/`)

See [SECURITY.md](SECURITY.md). Report vulnerabilities privately; do not paste secrets into issues.

## License

MIT. See [LICENSE](LICENSE).
