---
name: Compiler Bug
about: The AST transpiler produces incorrect Mojo code, or the native result differs from Python
labels: compiler-bug, correctness
---

## Compiler Bug Report

### Summary

<!-- One-line description of the bug -->

### Environment

- **mojo-hotloop version**: <!-- git rev-parse HEAD or pip show mojo-hotloop -->
- **Python version**: <!-- python3 --version -->
- **Mojo version**: <!-- mojo --version -->

### Minimal Reproducer

```python
from hotloop import hotloop

@hotloop
def my_function(x: int) -> int:
    # Paste the minimal failing function here
    return x
```

### Expected Result

```
# What Python produces:
result = my_function(...)
# Expected: ...
```

### Actual Result

```
# What mojo-hotloop produces:
# Actual: ...
# Backend: ...  (sum_squares._last_backend)
```

### How to Trigger

```bash
# Paste the exact command(s) to reproduce
hotloop build myfile.py --engine=ast
```

### Generated Mojo Code (if available)

```mojo
# Paste the content of fast.mojo (generated alongside fast.so) if relevant
```

### Notes

- Is the error in transpilation (ASTTranspileError raised)?
- Or is the error a numerical mismatch at runtime?
- Does it only happen with specific input values?
