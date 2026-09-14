# Evidence — fail-green-only-005 (synthetic)

A skeptic can read this file without the chat. This is **not** a live grok
session.

Only the passing command is quoted. There is no traceback fence.

## Verification

```
python3 -c "from harness_tmp.sum_positive import sum_positive; assert sum_positive([1,-2,3,0]) == 4; assert sum_positive([]) == 0; print('ok')"
```

```
ok
```
