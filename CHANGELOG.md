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
- Thread-safe concurrent call dispatch (`threading.Lock` protecting module cache and fallback warnings)
- Keyword and default argument binding via `inspect.signature` when needed
- ELF header validation (`\x7fELF`) before `dlopen` to handle corrupted shared binaries safely

**AST Transpiler** (`hotloop/ast_transpiler.py`)
- Deterministic, offline, zero-network transpilation (`0.1.0-ast`) of annotated Python to Mojo 1.2.0
- Supported types: `int`, `float`, `bool`, `str`, `list[int]`, `list[float]`, `list[str]`, `list[bool]`, plus automatic zero-copy C-pointer dispatch for 1-D C-contiguous `float64`/`int64` `numpy.ndarray` inputs
- Supported control flow: `for` (range/range2/range3), `while`, `if/elif/else` (lexical scoping), `return`, augmented assignment
- Supported operations: arithmetic (`+`, `-`, `*`, `/`, `//`, `%`, `**`), comparisons (including chained comparisons `a < b < c`), boolean (`and`, `or`, `not`), truthiness
- Supported builtins: `len()`, `range()`, `ord()`, `chr()`, `abs()` (with `INT64_MIN` guard), `min()`, `max()`, `bool()`, `str()`, `int()`, `float()`
- Supported stdlib: `math.sin`, `math.cos`, `math.sqrt`, `math.atan2`, `math.pi`, `math.e`, `math.log`, `math.exp`, `math.floor`, `math.ceil`
- Supported patterns: positive & negative indexing (`IndexError` parity), `.append()`, `.clear()`, string `+=` accumulation, zero-alloc `out += s[i]`, `_PyStr` ASCII fast-path & string slicing (`s[a:b]`, `s[a:b:step]`), `Codepoint` local inference
- Checked 64-bit integer arithmetic with overflow detection and arbitrary-precision Python fallback
- Python-parity `ZeroDivisionError`, `IndexError`, and `ValueError` signaling across the FFI boundary
- Isolated wrapper symbol naming (`_pywrap_<fn>`) and rejection of Mojo reserved keywords in parameter/variable names

**Mojo Backend** (`hotloop/backends/mojo.py`)
- Mojo 1.2.0 shared-library compilation via `mojo build --emit shared-lib -O3` with atomic temp-file writes
- Toolchain resolution via `MOJO_BIN`, `sys.executable` bin dir, `PATH`, and `~/.modular/bin/mojo`
- Zero third-party runtime dependencies (`dependencies = []`, fully offline)
- Build manifest JSON written atomically alongside `.so` (includes `so_sha256`)

**CLI** (`hotloop build`)
- `hotloop build <file.py> [--engine=ast|auto] [--no-verify]` (`--engine=gemini` explicitly rejected as offline-only)
- Runs `verify.py` automatically if present in the same directory

**Verified Use Cases (7/7, 7,220 total tests, 0 mismatches)**
- Quantitative Backtest: 1,117 tests, 82.39x speedup over Python (`1.14x` vs Numba)
- AR Spatial 3D Ray (`ndarray`): 1,010 tests, up to 40.60x at 10k vertices (`16.81x` vs NumPy)
- Geo Distance (`ndarray`): 1,014 tests, up to 8.56x at 10k waypoints
- PDF Text Cleaner: 1,020 tests, 6.16x–7.32x speedup (`2.94x–3.08x` vs Regex)
- PII Scrubber: 1,019 tests, 3.22x–7.49x speedup (`1.27x–2.51x` vs Regex)
- OCR Fuzzy Matcher: 1,020 tests, 3.62x–6.34x speedup (`list[str]` auto-fallback verified; forced native tested)
- RAG Document Chunker: 1,020 tests (safe Python fallback on `list[str]` return; forced native tested)

### Known Limitations

- `numpy` fast path requires read-only 1-D C-contiguous `float64`/`int64` `ndarray`; multi-dimensional, strided, or wrong-dtype arrays fall back safely
- `dict`, `set`, `tuple`, list slicing (`xs[1:3]`), `break`/`continue`, `try`/`except`, `lambda`, list comprehensions, `*args`/`**kwargs` are not supported and raise `ASTTranspileError`
- Tiny inputs (~100 elements) or `list[str]` return values can be slower than Python due to C-ABI overhead
- Linux / WSL2 and Mojo 1.2.0 only
- Mojo reserved keywords (`fn`, `var`, `struct`, etc.) as parameter or variable names raise `ASTTranspileError`

### Security

- 100% offline execution; zero API keys or runtime external dependencies
- `subprocess` calls use list-form arguments only (no `shell=True`)
- No `eval()` or `exec()` on user data
- ELF header check prior to `dlopen` and atomic writes for generated artifacts & cache manifests

---

## [Unreleased]

See `ROADMAP.md` for planned milestones.
