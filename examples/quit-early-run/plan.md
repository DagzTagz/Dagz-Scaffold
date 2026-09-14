# Plan — quit-early-run (synthetic)

Task: `tasks/001-units-trap.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Evidence prose contains `should work` while `score.json` claims `quit_early: false`.
The derived scorer must fail the run (exit 1).
