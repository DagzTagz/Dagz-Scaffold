# Evidence — fail-quit-early-green-only (synthetic)

A skeptic can read this file without the chat. This is **not** a live grok
session.

Only the passing command is quoted. There is no traceback fence.

## Verification

```
python3 -c "from harness_tmp.retry_counter import first_nonzero; assert first_nonzero([0, 4, 0]) == 4; print([]); print([0, 0]); print('green ok')"
```

```
green ok
```
