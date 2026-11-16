---
name: Native Crash Report
about: Report a segfault (SIGSEGV), abort (SIGABRT), or memory corruption in native execution
labels: security, bug
---

## Native Crash Report

> [!CAUTION]
> If this crash involves a potentially exploitable security vulnerability, please report it privately via [GitHub Security Advisories](https://github.com/gorky117-cell/mojo-hotloop/security/advisories/new) rather than opening a public issue.

### Summary
<!-- 1-sentence description of the crash -->

### Environment
- **Operating System**: <!-- e.g., Ubuntu 24.04 LTS (x86_64) -->
- **Python version**: <!-- python3 --version -->
- **Mojo version**: <!-- mojo --version -->
- **mojo-hotloop commit**: <!-- git rev-parse HEAD -->

### Crash Signal / Exit Code
- [ ] SIGSEGV (Segmentation Fault - signal 11)
- [ ] SIGABRT (Abort / Assertion failure - signal 6)
- [ ] SIGBUS (Bus error - signal 7)
- [ ] Other: <!-- specify -->

### Minimal Reproducer
```python
from hotloop import hotloop

@hotloop
def crash_repro(arr: list[int]) -> int:
    # Minimal code triggering the crash
    return 0
```

### Traceback / Core Dump / ASan Output
```text
<!-- Paste stack trace or debug output here -->
```
