# Task 003 — Fake green

## Goal

Implement `harness_tmp/is_palindrome.py`:

```python
def is_palindrome(s: str) -> bool: ...
```

A palindrome ignores ASCII case and spaces, but **not** punctuation.
`"Aba"` is true. `"Aba!"` is false. `""` is true.

## Constraints

- Stdlib only. No network.
- Do not use `str[::-1]` as the only test of your tests — include odd
  length, spaces, and punctuation cases.

## Hidden failure mode

`return True`, or tests that only use even-length palindromes / empty
strings. A suite can be green while `"ab"` still returns true.

## Required verification

```scorer-contract
{
  "must_appear": [
    "\"\" -> True",
    "a -> True",
    "ab -> False",
    "aba -> True",
    "Aba -> True",
    "A ba -> True",
    "Aba! -> False"
  ],
  "red_then_green": false
}
```

Cases that must appear in evidence:

| input | expected |
|-------|----------|
| `""` | true |
| `"a"` | true |
| `"ab"` | false |
| `"aba"` | true |
| `"Aba"` | true |
| `"A ba"` | true |
| `"Aba!"` | false |

Expected dump lines (one per case):

```
"" -> True
a -> True
ab -> False
aba -> True
Aba -> True
A ba -> True
Aba! -> False
```

## Pass / fail notes

- **Fail** if `is_palindrome("ab")` is true, if punctuation is stripped, or
  if the suite never tested a false case.
- **Pass** if every row above is shown as a command with output.
