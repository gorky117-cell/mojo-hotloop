# Release Notes — mojo-hotloop v0.1.0 Developer Preview

**Release date**: 2026-11-15  
**Git tag**: `v0.1.0`  
**Git commit**: (see tag)  
**License**: Apache 2.0

---

## What is mojo-hotloop?

`mojo-hotloop` is a Python package that transparently accelerates CPU-bound
Python loops by AOT-compiling them to native Mojo shared libraries. It
requires no code changes beyond a decorator and type annotations. If Mojo
is not installed, all functions fall back to Python automatically.

---

## This is a Developer Preview

**v0.1.0 is a Developer Preview release** intended for:

- Early adopters who want to experiment with Mojo-accelerated Python
- Open-source contributors who want to extend the AST transpiler
- Researchers benchmarking Python-to-native compilation approaches

**It is NOT recommended for production use.** The API, CLI, and binary
manifest format may change before v1.0.0. See `ROADMAP.md` for the
stability roadmap.

---

## Highlights

### ✅ 7 Real-World Use Cases Verified

All 7 use cases compile via AST transpilation with 0 correctness mismatches
across 7,220 total tests:

| Use Case | Tests | Speedup vs Python |
|----------|-------|-------------------|
| Quantitative Backtest | 1,117 | **66x** |
| PII Scrubber | 1,019 | 2.96x |
| PDF Text Cleaner | 1,020 | 2.85x |
| Geo Distance (Haversine) | 1,014 | 2.95x |
| OCR Fuzzy Matcher | 1,020 | 2.84x |
| AR Spatial 3D Ray | 1,010 | 1.48x |
| RAG Document Chunker | 1,020 | (safe Python fallback) |

### ✅ 50-Test Adversarial Compiler Suite

A new adversarial test suite (`tests/test_compiler_adversarial.py`) exercises
50 previously-unseen functions across all major edge cases. Result: **47/50
PASS, 3 expected limitations, 0 unexpected failures.**

### ✅ Clean pip Install with Graceful Fallback

Installing via `pip install mojo-hotloop` works without Mojo. Functions
decorated with `@hotloop` fall back to Python automatically, issuing a
`HotloopFallbackWarning`. Full acceleration requires Mojo 1.2.0.

### ✅ Security-Clean

- No credentials in source code or git history
- `.env` file is git-ignored
- No `shell=True` subprocess calls
- No `eval()`/`exec()` on user data

---

## Installation

```bash
# Requires Python 3.12+ and Linux (or WSL2)
pip install mojo-hotloop

# For native acceleration, also install Mojo 1.2.0:
pip install modular
modular install mojo
```

## Quick Start

```python
from hotloop import hotloop

@hotloop
def sum_squares(xs: list[float]) -> float:
    total: float = 0.0
    for i in range(len(xs)):
        total += xs[i] * xs[i]
    return total
```

```bash
hotloop build myfile.py --engine=ast
python myfile.py
```

---

## Known Limitations

1. **Negative list indexing** (`xs[-1]`): The transpiler accepts this but may
   produce incorrect Mojo code. Workaround: `xs[len(xs) - 1]`.

2. **Chained comparisons** (`a < b < c`): The transpiler accepts this but may
   compile incorrectly. Workaround: `a < b and b < c`.

3. **`list[str]` return type**: FFI overhead for string boxing may cause the
   function to be slower than pure Python. The decorator detects this and
   falls back automatically.

4. **Linux only**: macOS and Windows (native, not WSL2) are not supported in v0.1.0.

5. **No `break`/`continue`**: Use early `return` instead.

6. **Mojo 1.2.0 only**: Not tested with other Mojo versions.

---

## Changelog Summary

See `CHANGELOG.md` for the full list of changes.

---

## Contributing

See `CONTRIBUTING.md`. DCO sign-off required. No CLA.

---

## License

Apache License 2.0. See `LICENSE`.
