# Security advisory: `score.py --replay` can load an enclosing repository's git config

| | |
|---|---|
| **Component** | `harness/replay.py` (`ReplayGitDir`, `git_spawn`), used by `harness/score.py --replay` |
| **Audit priority** | High (see [audit rubric](../audits/2026-11-state-machine-audit.md#2-methodology)). No CVE or CVSS score has been assigned. |
| **Audited commit** | [`76edab4b4c93e199034ca1e8fa545c27b79a0a2d`](https://github.com/DagzTagz/Dagz-Scaffold/tree/76edab4b4c93e199034ca1e8fa545c27b79a0a2d) |
| **Status** | Fixed and merged on `main` in [Dagz-Scaffold#1](https://github.com/DagzTagz/Dagz-Scaffold/pull/1), merge [`4f09170`](https://github.com/DagzTagz/Dagz-Scaffold/commit/4f091704b708918de37594977cfb1ea73c282785) (2026-11-24) |
| **Published** | 2026-11-24 |
| **Default configuration affected?** | No. `--replay` is off unless you pass it. |

## Summary

`--replay` is documented to run git against a temporary git directory that "does not load the checkout's config" ([SECURITY.md L128](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/SECURITY.md#L128), [docs/scorer.md L101](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/docs/scorer.md#L101)). That holds when the Scaffold checkout has its own `.git`. When it does not, the replayed git command runs with no `GIT_DIR` set. Git then searches parent directories, and if the checkout sits inside another git work tree, git uses **that outer repository and its `.git/config`**. We confirmed that a `filter.<name>.clean` command defined in the outer repository's config runs during replay.

## Affected component

- `ReplayGitDir` uses `git_dir is None` for three different situations: not yet opened, closed, and "no `.git` found". [replay.py L661-L756](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L661-L756)
  - `_populate` returns without creating the temporary git dir when `.git` is absent: [L715-L718](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L715-L718)
  - `env_updates` then returns `{}`, so no `GIT_DIR` or `GIT_WORK_TREE` is set: [L673-L679](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L673-L679)
- `git_spawn` accepts that state and spawns git anyway: [L759-L778](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L759-L778), called from `replay_evidence` at [L861-L868](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L861-L868)
- `replay_env` sets no `GIT_CEILING_DIRECTORIES` and drops it from the caller's environment, so you cannot stop the upward search from outside: [L543-L555](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L543-L555), [`KEEP_ENV` L178](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L178)
- The `-c` overrides in [`GIT_CONFIG_OVERRIDES` L190-L199](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/replay.py#L190-L199) turn off fsmonitor, hooks, external diff, the pager and `core.sshCommand`, and `diff`/`show`/`log` get `--no-ext-diff --no-textconv`. None of these turns off `filter.*.clean`.
- Replay calls `replay_evidence` with `repo_root` set to the Scaffold checkout root: [score.py L515-L528](https://github.com/DagzTagz/Dagz-Scaffold/blob/76edab4b4c93e199034ca1e8fa545c27b79a0a2d/harness/score.py#L515-L528)

## Impact

**Confirmed:**
- A clean filter (`filter.<name>.clean` plus a matching `.gitattributes` rule) defined in the enclosing repository's local config ran during a replayed `git diff`. That is an arbitrary command configured in the outer repository, executed as the user running the scorer. The harness promises that this does not happen.
- The replayed git command reads and reports the **enclosing** repository's state, not the Scaffold checkout's.

**Possible, not demonstrated:**
- Other settings in the enclosing repository's config that the overrides above do not cover may also take effect. We tested only the clean filter.
- Because replay compares output against the wrong repository, a replay "match" or "mismatch" verdict can reflect unrelated repository state.

**Not affected:**
- Global and system git config. `replay_env` points both at `/dev/null`.
- Network access. Replay does not use the network.
- `python -c` replay, which does not use `ReplayGitDir`.

## Who is affected

You are affected only if **all** of these hold:

1. You run `python3 harness/score.py --replay ...`. Replay is off by default, and `run.py` and `ship_gate.py` never enable it.
2. Your Dagz-Scaffold copy has **no `.git` entry at its root**. This happens with a GitHub "Download ZIP", a release tarball, or a copied or vendored folder.
3. That copy sits **inside another git work tree**.
4. The evidence being replayed contains an allowlisted `git` command, and the enclosing repository's config defines something the overrides do not neutralize, such as a clean filter.

**Not affected:**
- A normal `git clone`. The checkout has its own `.git` directory, and replay uses the temporary git dir as designed. We verified this.
- A git submodule or worktree. Its `.git` is a pointer file, which `_locate` resolves.
- A copy with no enclosing repository. Git exits with an error, and replay records a mismatch, which fails closed as `missing_evidence`.

## How it was confirmed

At the audited commit, we built an outer git repository whose local config defines `filter.probe.clean` as a command that appends to a marker file, with `.gitattributes` set to `*.txt filter=probe`. Inside it, we placed a directory with **no** `.git` holding a modified tracked `.txt` file and a copy of `harness/`. We then called `ReplayGitDir.open(...)` → `git_spawn(["git", "diff"], ...)` → `_run(...)` on that directory.

- `git_dir` was `None`, and `env_updates()` returned `{}`.
- `git diff` succeeded against the **outer** repository.
- The marker file was written, which shows that the outer clean filter ran.

A control run, where the inner directory had its own `.git` and the filter was defined in that inner config, did **not** run the filter.

## Workarounds until fixed

Use any one of these:

- **Don't use `--replay`.** Scoring without it reads files and runs no commands.
- **Replay only from a real `git clone`.** Before replaying, confirm that git resolves to the Scaffold root itself:
  ```bash
  cd /path/to/Dagz-Scaffold
  test -e .git && [ "$(git rev-parse --show-toplevel)" = "$(pwd -P)" ] && echo "ok to replay"
  ```
  If `.git` is missing, or `--show-toplevel` prints a parent directory, do not replay.
- **Don't nest a ZIP or vendored copy inside another repository.** Move it to a directory that is not inside any git work tree.
- As always: **do not replay evidence you have not read.**

## Fix

**Status: fixed and merged on `main` in [Dagz-Scaffold#1](https://github.com/DagzTagz/Dagz-Scaffold/pull/1), merge [`4f09170`](https://github.com/DagzTagz/Dagz-Scaffold/commit/4f091704b708918de37594977cfb1ea73c282785).**

- `ReplayGitDir` now carries an explicit lifecycle, `GitDirState`: `UNOPENED`, `ISOLATED`, `NO_REPO`, `CLOSED`. `open()` ends in `ISOLATED` (the temporary git dir is ready) or `NO_REPO` (no `.git` at the checkout root), or raises `ReplayDenied`.
- `env_updates()`, which `git_spawn` calls before building the command, returns the isolated `GIT_DIR` / `GIT_WORK_TREE` only in `ISOLATED`. In `NO_REPO` it raises `ReplayDenied("git_no_repo")`, and in `CLOSED` `ReplayDenied("git_dir_closed")`, so git is never spawned. The denial marks the replay `unreplayable`, which `score.py` already turns into `missing_evidence`: the run fails closed.
- As defence in depth, `replay_env` now sets `GIT_CEILING_DIRECTORIES` to the checkout's parent directory, so git never searches above the checkout even if a future code path forgets the isolated `GIT_DIR`.
- `SECURITY.md`, `docs/scorer.md` and `AGENTS.md` now describe the no-`.git` case.
- New selftests in `harness/score_selftest.py`: an enclosing repository with a clean filter and a checkout with no `.git` (the filter must not run, both git pairs are denied with `git_no_repo`); the state transitions of `ReplayGitDir`; and `GIT_CEILING_DIRECTORIES` in the replay environment. The first test fails on the audited commit (the outer filter runs) and passes with the fix.

After the fix, the reproduction above denies both git commands with `git_no_repo`, and the outer clean filter runs 0 times (it ran 9 times across the same calls on the audited commit).

## Follow-up, 2026-11-25

Two related gaps were found after this fix. Both are **Open** (pull requests pending review):

- The same enclosing-repository problem still affected `ship_gate.py --git-checks` and the task-file `HEAD` check, which did not go through the replay path. Fix: [Dagz-Scaffold#5](https://github.com/DagzTagz/Dagz-Scaffold/pull/5).
- Replay still ran `from harness_tmp import ...` commands, which import a module from the checkout as you. Fix: [Dagz-Scaffold#4](https://github.com/DagzTagz/Dagz-Scaffold/pull/4), which refuses them unless you pass `--allow-harness-tmp`.

## Credit and methodology

Found during a self-audit by the DagzTagz maintainers, assisted by an AI agent, of the five public DagzTagz repositories at their default-branch HEADs. The audit looked for implicit state machines (lifecycles encoded as flags, `None` sentinels, or status strings). This issue is finding **F1**. High and Med findings were reproduced by running the code at the audited commit.

Full report: [docs/audits/2026-11-state-machine-audit.md](../audits/2026-11-state-machine-audit.md)

Related lower-priority findings in this repository (not security issues on their own): F3 (the live-run loop reports success without running `ship_gate`), F8, and F9. See the report.
