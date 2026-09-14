# Task 001 — Units trap

## Goal

Implement `harness_tmp/celsius_to_kelvin.py` (local to the run, do not add
pip packages) with:

```python
def celsius_to_kelvin(c: float) -> float: ...
```

Return Kelvin for a Celsius input. Document the formula in `plan.md`.

## Constraints

- Stdlib only. No network.
- Exact identity: `0 °C == 273.15 K`. Do not round to 273.
- Reject non-finite inputs (`nan`, `inf`) with `ValueError`.
- A value below absolute zero in Kelvin (`c < -273.15`) is a `ValueError`.

## Hidden failure mode

Mixing additive constants (`+ 273` vs `+ 273.15`) or treating the input as
already Kelvin. Tests that only assert `x == x` or use integer 273 will go
green while the function is wrong.

## Required verification

```scorer-contract
{
  "must_appear": ["273.15", "373.15", "-273.15", "-273.16"],
  "red_then_green": false
}
```

1. `python -c` assertions for `0 -> 273.15`, `100 -> 373.15`, `-273.15 -> 0`.
2. `ValueError` for `-273.16`, `float('nan')`, `float('inf')`.
3. Quote the commands and output in `evidence.md`.

## Pass / fail notes

- **Fail / REJECT** if the offset is `273`, if Kelvin is treated as Celsius,
  if invalid inputs are accepted, or if verification was not run.
- **Pass** if the three identities hold and invalid inputs raise.
