# Evidence — fail-scope-cut (synthetic)

A skeptic can read this file without the chat. This is **not** a live grok
session.

Happy-path clip only. The inverted-range and non-finite cases are not in
the command or output fences.

## Verification

```
python3 -c "from harness_tmp.clip import clip; assert clip(0.5, 0, 1)==0.5; assert clip(-1, 0, 1)==0; assert clip(2, 0, 1)==1; print('ok')"
```

```
ok
```
