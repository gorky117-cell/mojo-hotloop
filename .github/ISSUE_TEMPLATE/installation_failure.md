---
name: Installation Failure
about: Report a failure to install mojo-hotloop or build a native shared library
labels: installation, bug
---

## Installation Failure Report

### Environment

- **OS**: <!-- e.g., Ubuntu 24.04, macOS 14, WSL2 on Windows 11 -->
- **Python version**: <!-- python3 --version -->
- **Mojo version**: <!-- mojo --version (if installed) -->
- **pip version**: <!-- pip --version -->
- **Install method**: <!-- pip install mojo-hotloop / pip install -e . / other -->

### Steps to Reproduce

```bash
# Paste the exact commands you ran, e.g.:
python3 -m venv .venv
.venv/bin/pip install mojo-hotloop
```

### Expected Behavior

<!-- What did you expect to happen? -->

### Actual Behavior

```
# Paste the full error output here
```

### Additional Context

- Did `pip install` succeed but the import fail?
- Did `hotloop build` fail? If so, paste the full CLI output.
- Is Mojo installed? (`which mojo`)
- Is `.venv/bin/mojo` present? (`ls -la .venv/bin/mojo`)
