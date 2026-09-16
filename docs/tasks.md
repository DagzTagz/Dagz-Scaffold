# Writing a public trap

The files under `tasks/` are not product features. They are **short exams** with a known way to cheat. We use them so you can see whether an agent still does a familiar failure: wrong units, quitting after the first red test, a test suite that is green while a required case was never run, quietly dropping an edge case, or saying “it passed” with no output.

If you want a new trap in the repo, this page is the how-to. There is also a GitHub issue form at `.github/ISSUE_TEMPLATE/task.yml`.

---

## What a good trap looks like

Write the goal in ordinary language. State the constraints (stdlib only, no network, and the real rules of the function). Then write the **hidden failure mode**: what a tired or overconfident agent will do instead of finishing. Then list the verification a skeptic must see in evidence.

Immediately under the “Required verification” heading, put a JSON block whose fence language is exactly `scorer-contract`. That is how the inspector knows which strings must appear in command/output fences, and whether a fenced failure-then-retry is required.

Example shape:

````markdown
## Required verification

```scorer-contract
{
  "must_appear": ["273.15", "373.15", "-273.15", "-273.16"],
  "red_then_green": false
}
```

1. `python -c` assertions for …
````

`must_appear` is the list of strings evidence has to show in the **right fences**, not in a bloggy paragraph. `red_then_green` is true when the sitting is worthless unless we see a fenced traceback (or `AssertionError`) **between** two command fences.

If you use dump-style tokens such as `ab -> False`, they match a **whole output line**. That way `aba -> True` cannot fake `a -> True`.

Do not paste the “hidden failure mode” paragraph into `evidence.md` as if it were a confession. Quoting the task inside a markdown fence is fine; the inspector strips that before looking for quit-early phrases.

---

## How to add one

Copy `tasks/001-units-trap.md` to something like `tasks/006-short-name.md`. Fill every human section: goal, constraints, hidden failure mode, required verification (including the JSON fence), pass/fail notes.

Keep the work local. No extra pip packages, no secrets, no “just hit this API.”

Then run:

```bash
python3 harness/score_selftest.py
```

That lints the contract against the human-readable part of the task (the strings you listed have to appear in the write-up too, so the JSON cannot drift from the prose).

You can dry-run the wrapper if you want a mock folder. Scoring that mock will fail with `dry_run`, which is expected:

```bash
python3 harness/run.py --dry-run tasks/006-short-name.md
```

More on how matching works: [scorer.md](scorer.md).

---

## What not to send in a pull request

Live `runs/` folders are gitignored on purpose. The `examples/` packets are synthetic. A PR that adds a task should not attach a real persist from your machine.
