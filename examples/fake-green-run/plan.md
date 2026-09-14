# Plan — fake-green-run (synthetic)

Task: `tasks/003-fake-green.md`
This folder is a **synthetic fail fixture**. It is not a live grok session.

## Goal

Tests claimed green while required dump token `ab -> False` is missing.
score.py must exit 1 (`required_verification`).
