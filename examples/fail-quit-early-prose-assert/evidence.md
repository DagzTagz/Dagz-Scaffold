# Evidence — fail-quit-early-prose-assert (synthetic)

A skeptic can read this file without the chat. This is **not** a live grok
session.

The first attempt raised AssertionError (omitted). Then the green runs:

```
python3 -c "from harness_tmp.retry_counter import first_nonzero; assert first_nonzero([0, 4, 0]) == 4"
```

```
python3 -c "from harness_tmp.retry_counter import first_nonzero; print([]); print([0, 0]); print('green ok')"
```
