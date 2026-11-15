# Third-Party Notices — mojo-hotloop v0.1.0

This document lists all third-party Python dependencies, their licenses,
and notes on algorithmic provenance.

---

## Runtime Dependencies

**None.** `mojo-hotloop` v0.1.0 has zero third-party Python runtime dependencies (`dependencies = []` in `pyproject.toml`). Only the Python 3.12+ standard library is required at runtime.

---

## Optional Dependencies (not installed by default)

### numpy

- **Package**: `numpy`
- **License**: BSD 3-Clause
- **Usage**: Zero-copy 1-D C-contiguous `float64`/`int64` `ndarray` pointer fast-path
  in AST-generated C-ABI wrappers (`hotloop/ast_transpiler.py`) and runtime
  qualification checks (`hotloop/decorator.py`). Activated automatically when a
  compatible `numpy.ndarray` is passed at runtime.
- **Source**: https://github.com/numpy/numpy

---

## Build Dependencies

### setuptools

- **Package**: `setuptools >= 61.0`
- **License**: MIT
- **Usage**: Package build backend (`pyproject.toml`)

---

## Compiler / Runtime (Not Python Packages)

### Mojo 1.2.0

- **Provider**: Modular, Inc.
- **License**: Modular Community License (not open source)
- **Usage**: Compiles generated `.mojo` source to shared libraries (`.so`)
- **Source**: https://www.modular.com/mojo

Mojo is a **build-time and runtime dependency** but is NOT bundled with
the mojo-hotloop distribution. Users must install it separately.

---

## Algorithmic Provenance

The following algorithms are **implemented from scratch** in Python and
transpiled to Mojo by the AST transpiler. They are based on well-known
published algorithms. No third-party source code has been wholesale copied
into the mojo-hotloop distribution.

### Myers Edit Distance (OCR Fuzzy Matcher)

- **Algorithm**: Myers, E.W. (1986). "An O(ND) difference algorithm and its
  variations." *Algorithmica*, 1(1-4), 251–266.
- **Implementation**: Original Python implementation in
  `examples/ocr_matcher/original.py`. Translated to Mojo via AST transpiler.
- **Status**: Algorithm is in the public domain. Implementation is original.

### Luhn Algorithm (PII Scrubber — credit card validation)

- **Algorithm**: Luhn, H.P. (1960). US Patent 2,950,048.
  The patent has long since expired. The algorithm is in the public domain.
- **Implementation**: Original Python implementation in
  `examples/pii_scrubber/original.py`.
- **Status**: Algorithm is public domain. Implementation is original.

### Verhoeff Algorithm (PII Scrubber — numeric checksum)

- **Algorithm**: Verhoeff, J. (1969). "Error Detecting Decimal Codes."
  Mathematical Centre Tract 29, Amsterdam.
- **Implementation**: Original Python implementation using the standard
  Verhoeff multiplication table (d₅), permutation table (p₅), and
  inverse table. Tables are mathematical constants, not copyrightable.
- **Status**: Algorithm is public domain. Tables are mathematical constants.
  Implementation is original.

### Haversine Formula (Geo Distance)

- **Formula**: Standard spherical trigonometry formula. No copyright claim
  possible on a mathematical formula.
- **Implementation**: Original Python implementation in
  `examples/geo_distance/original.py`.

### LCG Pseudo-Random Number Generator (Quant Backtest)

- **Algorithm**: Linear Congruential Generator with parameters from
  Numerical Recipes (Knuth): a=1664525, c=1013904223, m=2^32.
  These parameters are mathematical constants in the public domain.
- **Implementation**: Original Python simulation in
  `examples/quant_backtest/original.py`.

### Möller–Trumbore Ray-Triangle Intersection (AR Spatial)

- **Algorithm**: Möller, T. & Trumbore, B. (1997). "Fast, Minimum Storage
  Ray-Triangle Intersection." *Journal of Graphics Tools*, 2(1), 21–28.
- **Implementation**: Original Python implementation in
  `examples/ar_spatial/original.py`.
- **Status**: Algorithm is published in academic literature.
  Implementation is original.

---

## Statement of No Wholesale Code Copying

> No third-party source code has been copied wholesale into the mojo-hotloop
> distributed source (Python files in `hotloop/`, `examples/`).
>
> All implementations listed above are original Python code that implement
> published, public-domain algorithms. The corresponding Mojo code is generated
> automatically by the mojo-hotloop AST transpiler from that Python source.
>
> If a future audit identifies any code that was inadvertently copied from
> a third-party source, please report it via a GitHub Security Advisory so
> it can be properly attributed or replaced.

---

*Last updated: 2026-11-15*
