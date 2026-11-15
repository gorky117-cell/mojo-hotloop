# Changelog

All notable changes to mojo-hotloop are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-11-15 — Developer Preview

### Summary

First public release of mojo-hotloop. This is a **Developer Preview** release
intended for early adopters, researchers, and open-source contributors.
The API, CLI, and binary format may change before v1.0.0.

### Added

**Core Decorator**
- `@hotloop` decorator with zero-boilerplate, transparent fallback to Python
- `HotloopError`, `HotloopNativeExecutionError`, `HotloopFallbackWarning` exception hierarchy
- `strict=True` mode: raises `HotloopNativeExecutionError` if native binary missing or stale
- `force_native=True` mode: bypasses performance qualification heuristics
- `cache_check` policy control: `runtime` (default, 20 ms throttle), `import`, `always`, `off`
- Content-addressed SHA-256 manifest cache (`__mojocache__/`) with stale-binary detection
- Thread-safe concurrent call dispatch (global module cache with no GIL reliance)

**AST Transpiler** (`hotloop/ast_transpiler.py`)
- Deterministic, offline, no-network transpilation of annotated Python to Mojo 1.2.0
- Supported types: `int`, `float`, `bool`, `str`, `list[int]`, `list[float]`, `list[str]`, `list[bool]`
- Supported control flow: `for` (range/range2), `while`, `if/elif/else`, `return`, augmented assignment
- Supported operations: arithmetic (`+`, `-`, `*`, `/`, `//`, `%`, `**`), comparisons, boolean (`and`, `or`, `not`)
- Supported builtins: `len()`, `range()`, `ord()`, `abs()`, `min()`, `max()`, `str()`, `int()`, `float()`
- Supported stdlib: `math.sin`, `math.cos`, `math.sqrt`, `math.atan2`, `math.pi`, `math.e`, `math.log`, `math.exp`, `math.floor`, `math.ceil`
- Supported patterns: list `.append()`, list `.clear()`, string `+=` accumulation
- Checked 64-bit integer arithmetic with overflow detection and arbitrary-precision Python fallback
- Python-parity `ZeroDivisionError` and `ValueError` signaling across the FFI boundary

**Mojo Backend** (`hotloop/backends/mojo.py`)
- Mojo 1.2.0 shared-library compilation via `mojo build --emit shared-lib`
- C-ABI Python module export (`PyInit_<mod>`) with safe `PythonModuleBuilder`
- Optional Gemini LLM engine (requires `GEMINI_API_KEY`, max 5 self-correction attempts)
- Build manifest JSON written alongside `.so` for reproducibility

**CLI** (`hotloop build`)
- `hotloop build <file.py> --engine=ast|gemini|auto [--no-verify]`
- Runs `verify.py` automatically if present in the same directory

**Verified Use Cases (7/7, 7,220 total tests)**
- Quantitative Backtest: 1,117 tests, 66x speedup over Python
- PDF Text Cleaner: 1,020 tests, 2.85x speedup
- PII Scrubber: 1,019 tests, 2.96x speedup
- Geo Distance (Haversine): 1,014 tests, 2.95x speedup
- OCR Fuzzy Matcher: 1,020 tests, 2.84x speedup
- AR Spatial 3D Ray: 1,010 tests, 1.48x speedup
- RAG Document Chunker: 1,020 tests (safe Python fallback; FFI overhead dominates)

### Known Limitations

- Negative list indexing (`xs[-1]`) is accepted by the transpiler but produces incorrect Mojo code (use `xs[len(xs)-1]` as workaround)
- Chained comparisons (`a < b < c`) are accepted but may compile incorrectly (expand to `a < b and b < c`)
- `numpy` arrays, `dict`, `set`, `tuple` types are not supported
- No support for `lambda`, list comprehensions, generators, or `*args`/`**kwargs`
- Functions must have explicit PEP 526 type annotations on all arguments and return type
- Gemini engine requires network access and a valid `GEMINI_API_KEY`

### Security

- `.env` file containing `GEMINI_API_KEY` is git-ignored and never committed
- No credentials appear in source code or git history
- `subprocess` calls use list-form arguments only (no shell injection vector)
- No `eval()` or `exec()` on user data

---

## [Unreleased]

See `ROADMAP.md` for planned milestones.
