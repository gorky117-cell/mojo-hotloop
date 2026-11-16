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

All 7 use cases compile offline via `--engine=ast` (`-O3`) with 0 correctness mismatches
across 7,220 total tests:

| Use Case | Tests | Speedup vs Python |
|----------|-------|-------------------|
| Quantitative Backtest | 1,117 | **82.39x** (`1.14x` vs Numba) |
| AR Spatial 3D Ray (`ndarray`) | 1,010 | **40.60x** at 10k vertices (`0.73x` at 100v; `16.81x` vs NumPy) |
| Geo Distance (`ndarray`) | 1,014 | **8.56x** at 10k waypoints (`1.72x` at 100w) |
| PDF Text Cleaner | 1,020 | **6.16x–7.32x** (`2.94x–3.08x` vs Regex) |
| PII Scrubber | 1,019 | **3.22x–7.49x** (`1.27x–2.51x` vs Regex) |
| OCR Fuzzy Matcher | 1,020 | **3.62x–6.34x** (`0.23x–0.78x` vs RapidFuzz C) |
| RAG Document Chunker | 1,020 | (safe Python fallback on `list[str]` return) |

### ✅ Adversarial, Unfamiliar-Function & Security Test Suites

- `tests/test_compiler_adversarial.py`: **49/50 PASS, 1 expected rejection (`T42`), 0 unexpected failures**
- `tests/test_unfamiliar_functions.py`: **6/6 tests OK** across unfamiliar compiled functions (`12.12x` dot product, `18.11x` Welford variance, `3.28x` RLE compress, `7.03x` Caesar cipher) plus `audit/bench_generalization.py` (`8.56x` `mask_digits`, `66.39x` EMA, `57.17x` Chebyshev)
- `tests/test_runtime_security.py`: **6/6 tests OK** (OOB `IndexError` isolation, `ndarray` shape/stride/dtype safety, strict overflow, corrupted ELF `.so` / manifest resilience, concurrent compilation, 25k-iteration RSS stability)

### ✅ Clean pip Install with Zero Runtime Dependencies

Installing via `pip install mojo-hotloop` requires zero third-party runtime packages and works cleanly offline with or without Mojo. Functions fall back to Python automatically when `.so` is unavailable or unsupported. Full native acceleration requires Mojo 1.2.0 (`modular install mojo`).

### ✅ Security-Clean

- 100% offline compilation & execution; no network calls or AI API keys
- No `shell=True` subprocess calls and no `eval()`/`exec()` on user data
- ELF header validation (`\x7fELF`) before `dlopen` and atomic file replacement for manifests/binaries

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

1. **`dict`, `set`, `tuple`, list slicing (`xs[1:3]`), `break`/`continue`, `try`/`except`**: Rejected cleanly with `ASTTranspileError` (safe Python fallback).

2. **`numpy` pointer fast path scope**: Automatic zero-copy C-pointer dispatch applies to read-only 1-D C-contiguous `float64`/`int64` `ndarray` inputs; multi-dimensional, strided, or mutated arrays fall back safely.

3. **`list[str]` return types & tiny inputs**: C-ABI marshaling overhead on `list[str]` returns or ~100-element calls can exceed compute cost; heuristic auto-fallback routes collection-heavy signatures to Python unless `force_native=True` or `ndarray` is used.

4. **Linux / WSL2 only**: macOS and native Windows (outside WSL2) are not supported in v0.1.0.

5. **Mojo reserved keywords**: Using Mojo keywords (`fn`, `var`, `struct`, `mut`, `out`, etc.) as parameter or variable names raises `ASTTranspileError`.

6. **Mojo 1.2.0 only**: Tested against Mojo 1.2.0 (`2016d0cd`).

---

## Changelog Summary

See `CHANGELOG.md` for the full list of changes.

---

## Contributing

See `CONTRIBUTING.md`. DCO sign-off required. No CLA.

---

## License

Apache License 2.0. See `LICENSE`.
