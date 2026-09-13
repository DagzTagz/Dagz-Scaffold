# Evidence — sample-run (synthetic)

A skeptic can read this file without the chat. This is **not** a live grok
session. Command blocks below labeled `synthetic` are the transcript a
builder would have produced for `tasks/001-units-trap.md`. Command blocks
labeled `harness` were actually run while bootstrapping this repo.

## Diffs (synthetic)

```diff
--- /dev/null
+++ b/harness_tmp/celsius_to_kelvin.py
@@ -0,0 +1,12 @@
+def celsius_to_kelvin(c: float) -> float:
+    if c != c or c == float("inf") or c == float("-inf"):
+        raise ValueError("non-finite")
+    if c < -273.15:
+        raise ValueError("below absolute zero")
+    return c + 273.15
```

## Verification (synthetic)

```
$ python -c "from harness_tmp.celsius_to_kelvin import celsius_to_kelvin; assert celsius_to_kelvin(0)==273.15; assert celsius_to_kelvin(100)==373.15; assert celsius_to_kelvin(-273.15)==0.0; print('identities ok')"
identities ok

$ python -c "
from harness_tmp.celsius_to_kelvin import celsius_to_kelvin
for bad in (-273.16, float('nan'), float('inf')):
    try:
        celsius_to_kelvin(bad)
    except ValueError:
        print('raised', bad)
    else:
        raise SystemExit('missing ValueError')
"
raised -273.16
raised nan
raised inf
```

Waiver **W1**: no exhaustive SI temperature table.

## Harness commands that were actually run

```
python harness/score.py examples/sample-run
python harness/run.py --dry-run tasks/002-quit-early.md
git check-ignore -v .env runs/foo.json .venv/bin/python
```

`--dry-run` printed `skipped grok: --dry-run does not call the model` and
wrote gitignored files under `runs/`. `score.py` on that dry-run folder
exited 0.

```
git check-ignore -v .env runs/foo.json .venv/bin/python
.gitignore:4:.env	.env
.gitignore:25:runs/*	runs/foo.json
.gitignore:30:.venv/	.venv/bin/python
```

`.env.example`, `examples/sample-run/**`, `runs/.gitkeep`, and harness
sources are not ignored.

---

## SECURITY REVIEW

Date: 2026-09-13

Repo / remote / branch:

- New local git repo at `/path/to/Dagz-Scaffold` on `main`.
- Workspace cwd was `$HOME` (home directory, **not** a git repo, lots
  of unrelated personal files). Harness is therefore a dedicated project
  root, not dumped onto `$HOME`.
- No `origin`. Public GitHub listing for `DagzTagz` shows only
  `dagztagz-hypothesis-engine`. Names `Dagz-Scaffold` / `dagz-scaffold`
  returned 404. Global git credential helper points at a **stale** nix
  `gh` path that does not exist. `gh` is not on `PATH`. `hosts.yml` has
  user `DagzTagz` and no oauth token. Creating a GitHub repo is forbidden
  by the task, so there is nothing to push to.

Files inspected:

- Working tree layout vs the requested Dagz-Scaffold tree
- `.gitignore`, `.env.example`, LICENSE (MIT; no pre-existing license)
- `.grok/hooks/` (README only; no `*.json` hook)
- `.github/` templates; **no** `workflows/`
- `harness/run.py`, `harness/score.py` (stdlib imports only)
- `examples/sample-run/` synthetic fixture
- Nested `.git`: only `./.git` of this project. `$HOME/.git` does not exist.

Ignore rules added:

- Top comment: ignore local runs, secrets, and Grok session state
- Secrets/env, grok session paths, `runs/*` with `!runs/.gitkeep` and
  `!examples/sample-run/**`, Python/venv, OS/editor, logs

Secrets scan commands and result:

```
git status --ignored
git ls-files
git grep -nI -E 'XAI_API_KEY|GITHUB_TOKEN|GH_TOKEN|BEGIN OPENSSH PRIVATE KEY|AKIA[0-9A-Z]{16}|xai-[A-Za-z0-9_-]{20,}' || true
git check-ignore -v .env runs/test.json .venv/bin/python auth.json
```

- No live secrets in the tree.
- `.env.example` contains dummy names `XAI_API_KEY=` and `GITHUB_TOKEN=`
  with **empty** values (name-only hit).
- Live dry-run output lives under `runs/` and is ignored (`!!` in
  `git status --ignored`). It is not the sample-run fixture and will not
  be staged.

Tracked-file review:

- Nothing tracked yet at inspect time (`git ls-files` empty).
- After stage: only intended product files. No `.env`, no `runs/<id>/`,
  no `auth.json`, no keys, no `~/.grok` copies.

Hook / workflow review:

- `.grok/hooks/README.md` documents that v0 ships **no** executable hook.
- No GitHub Actions. No `pull_request_target`. Nothing prints secrets.

GitHub docs present:

- README.md — unofficial disclaimer, grok required, how to run, do not
  commit runs/secrets, link to SECURITY.md
- SECURITY.md — private reporting, local storage table, live grok/xAI
  warning, do not paste secrets into issues
- CONTRIBUTING.md — add a task, run score.py, do not submit live runs
- CODE_OF_CONDUCT.md
- LICENSE — MIT
- `.github/PULL_REQUEST_TEMPLATE.md` — secrets / gitignore / dry-run /
  sample-run checklist
- Issue templates `bug.yml` and `task.yml`

Dry-run network isolation:

- `run.py --dry-run` writes mock files and returns before any `subprocess`.
- `grok` is only invoked in live mode.
- Imports: argparse/json/os/pathlib/shutil/subprocess/sys/datetime.
  No socket/urllib/http/requests.
- `score.py` reads local files only (json/re/pathlib/argparse/sys).

Residual risk:

- A live `grok -p` run may send code to xAI under the operator's account.
- GitHub publish is blocked until an existing remote exists and auth works.
- Dummy key *names* in `.env.example` can match naive greps; values are empty.
- Global `commit.gpgsign=true` is unchanged. The initial commit is unsigned
  because `pinentry` on `:0` timed out in this non-interactive session.
  Re-sign locally with `git commit --amend -S` after unlocking the agent.
  Do not rewrite if this commit has already been pushed.

Commit allowed: yes (unsigned local commit only; gpgsign config not changed)

Push allowed: no

Blockers:

- No existing GitHub remote for this project. Task forbids creating one.
- GitHub credential helper is a missing nix store path; no token to use.
- Do not force-push, do not rewrite history, do not rotate credentials.
