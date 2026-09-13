# Hooks

v0 default: **no executable project hook**. Nothing in this directory runs on
edit, stop, or commit.

Grok Build can load project hooks from `.grok/hooks/*.json` after folder trust.
This repo does not ship those files.

## Rules if you add a local hook

- Keep it on this machine. Do not upload the repo, phone home, or POST diffs.
- Do not read parent directories outside this project (`$HOME`, `~/.grok/auth.json`, sibling repos).
- No network. Command hooks only. Review the script in the PR.
- Do not enable a hook that fires on every edit unless it is tiny, local, and reviewed.
- A Stop hook that blocks "done" until `python harness/score.py runs/<id>` passes is the only pattern worth considering. Even then, commit the JSON and the script together, and document the event in SECURITY.md.

Live `runs/` output and secrets must stay untracked. A hook that copies them
into git or a remote is a security bug.
