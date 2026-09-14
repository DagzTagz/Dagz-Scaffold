# Evidence — quit-early-run (synthetic)

A skeptic can read this file without the chat. This is **not** a live grok
session.

The identities below were checked once. This should work without another
attempt.

## Verification

```
python3 -c "from harness_tmp.celsius_to_kelvin import celsius_to_kelvin; assert celsius_to_kelvin(0)==273.15; assert celsius_to_kelvin(100)==373.15; assert celsius_to_kelvin(-273.15)==0.0; print('identities ok')"
```

```
python3 -c "from harness_tmp.celsius_to_kelvin import celsius_to_kelvin; celsius_to_kelvin(-273.16)"
```

raised ValueError for -273.16
