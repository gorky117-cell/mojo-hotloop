---
name: Native Crash
about: The compiled Mojo shared library causes a segfault, abort, or other native crash
labels: native-crash, critical
---

## Native Crash Report

> [!CAUTION]
> Native crashes (SIGSEGV, abort) are **critical bugs**. Please provide as
> much detail as possible.

### Environment

- **mojo-hotloop version**: <!-- git rev-parse HEAD -->
- **Python version**: <!-- python3 --version -->
- **Mojo version**: <!-- mojo --version -->
- **OS / kernel**: <!-- uname -a -->

### Crash Description

```
# Paste the crash output / traceback:
```

### Minimal Reproducer

```python
from hotloop import hotloop, HotloopNativeExecutionError

@hotloop
def crashing_function(...) -> ...:
    # Minimal function that triggers the crash
    ...

crashing_function(...)
```

### Input Values

```python
# Paste the exact arguments that caused the crash
args = (...)
```

### Steps to Reproduce

```bash
1. hotloop build myfile.py --engine=ast
2. python myfile.py
# Crash occurs on call to crashing_function(...)
```

### Core Dump / Stack Trace

```
# If available, paste gdb bt output or Python traceback
```

### Additional Notes

- Does the crash happen on every call, or only specific inputs?
- Can you reproduce it with `HOTLOOP_FORCE_NATIVE=1` or different array dtypes/shapes?
- Does the Python fallback (remove `.so` / `__mojocache__/`) work correctly?
