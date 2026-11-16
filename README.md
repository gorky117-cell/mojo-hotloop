# mojo-hotloop

Accelerate slow Python hot loops using compiled Mojo shared libraries.
Transparent fallback, zero boilerplate, identical semantics.

---

## What It Does

`mojo-hotloop` is an open-source compiler tool and Python decorator that:

1. **Transpiles** annotated Python functions to Mojo 1.2.0 source code using a
   deterministic AST transpiler (no AI, no network calls required)
2. **Compiles** the Mojo source to a native shared library (`.so`)
3. **Dispatches** calls to the native library transparently — the same `@hotloop`
   function works with or without Mojo installed

If the native library is missing, stale, or Mojo is unavailable, your function
falls back cleanly to Python.

---

## Supported Python Subset

The AST transpiler supports a **strict subset** of annotated Python. See
[`docs/SUPPORTED_SYNTAX.md`](docs/SUPPORTED_SYNTAX.md) for the complete reference.

**Supported**:
- Types: `int`, `float`, `bool`, `str`, `list[int]`, `list[float]`, `list[str]`, `list[bool]`, plus automatic zero-copy C-pointer fast path for 1-D C-contiguous `float64`/`int64` `numpy.ndarray` inputs
- Control flow: `for i in range(...)`, `while`, `if/elif/else`, `return` (including early return), lexical scoping
- Expressions: `+`, `-`, `*`, `/`, `//`, `%`, `**`, bitwise operators, chained comparisons (`a < b < c`), truthiness
- Builtins: `len()`, `range()`, `ord()`, `chr()`, `abs()`, `min()`, `max()`, `bool()`, `int()`, `float()`, `str()`
- Math: `math.sin`, `math.cos`, `math.sqrt`, `math.atan2`, `math.pi`, `math.e`, `math.log`, `math.exp`, `math.floor`, `math.ceil`
- Lists & Calls: `.append()`, `.clear()`, positive & negative index read/write (`IndexError` parity), keyword & default arguments
- Strings: `+=` accumulation (including zero-alloc `out += s[i]`), `len()`, `ord(s[i])`, indexing & slicing (`s[a:b]`, `s[a:b:step]`)

**Not supported**: `dict`, `set`, `tuple`, list slicing (`xs[1:3]`), list comprehensions, `lambda`,
`break`, `continue`, `*args`/`**kwargs`, `try`/`except`, non-contiguous/N-D `ndarray` pointer fast paths (safe Python/list fallback).

---

## Installation

Requires **Linux** (or WSL2 on Windows 11) and **Python 3.12+**.

```bash
pip install mojo-hotloop
```

For native acceleration, also install **Mojo 1.2.0**:

```bash
pip install modular
modular install mojo
mojo --version   # Should show: mojo 1.2.0
```

> **Without Mojo**, all `@hotloop` functions fall back to Python automatically.
> This is correct behavior — the package is fully usable without Mojo for
> development and testing.

---

## Quick Start

### Step 1 — Annotate your function

```python
# myapp.py
from hotloop import hotloop

@hotloop
def running_sum(values: list[float]) -> float:
    total: float = 0.0
    for i in range(len(values)):
        total += values[i]
    return total
```

**All arguments and the return type must be annotated.** Local variables must
also be annotated on first assignment (`total: float = 0.0`).

### Step 2 — Build the native library

```bash
hotloop build myapp.py --engine=ast
```

This creates `fast.so` and `fast.hotloop_manifest.json` alongside `myapp.py`.

### Step 3 — Run at native speed

```python
import myapp

result = myapp.running_sum([1.0, 2.0, 3.0, 4.0, 5.0])
print(result)  # 15.0
print(myapp.running_sum._last_backend)  # "native"
```

---

## How Fallback Works

```
@hotloop function called
        │
        ▼
  .so present and fresh?
   ├─ Yes → native execution via Mojo C-ABI
   └─ No  → HotloopFallbackWarning issued
              → original Python function called
```

The fallback is **automatic and transparent**. No exceptions. No data corruption.
The result is always correct.

Enable strict mode if you want an error instead of a silent fallback:

```python
@hotloop(strict=True)
def my_function(x: float) -> float:
    ...
```

---

## Verified Real-World Use Cases

All 7 use cases below were transpiled using `--engine=ast` (deterministic,
offline), verified against Python reference implementations, and benchmarked on
an Intel i5-8265U running Ubuntu 24.04 (WSL2).

| Use Case | Domain | Speedup vs Python | Tests |
|----------|--------|-------------------|-------|
| Quantitative Backtest | Financial simulation | **69.34x** (p50: 0.550 ms vs 38.152 ms; beats Numba 0.567 ms & Codon 0.731 ms) | 1,117 |
| AR Spatial 3D Ray (`ndarray`) | Graphics/AR | **33.36x** at 10k vertices (0.82x at 100v; beats Codon JIT 25.30x) | 1,010 |
| Geo Distance (`ndarray`) | Geospatial | **9.74x** at 10k waypoints (2.35x at 100w; 1.136 ms) | 1,014 |
| PDF Text Cleaner | Document processing | **5.39x–6.20x** (beats Regex 2.44x; beats Codon JIT 7,758 ms) | 1,020 |
| PII Scrubber | Text security | **3.67x–4.96x** (beats Regex 2.85x; beats Codon JIT 12,351 ms) | 1,019 |
| OCR Fuzzy Matcher | String search | **Python fallback** (0.98x) / Forced Native **3.57x** (0.653 ms) | 1,020 |
| RAG Document Chunker | LLM ingestion | **Python fallback**¹ (1.01x) / Forced Native **0.05x** (4.009 ms) | 1,020 |

¹ The RAG chunker returns `list[str]`. The FFI overhead of boxing each string
element exceeds native computation savings (direct forced native is ~21x slower
at 100k chars). `mojo-hotloop` detects this automatically and falls back to Python
(`0.52x–1.01x` with Python fallback path).

> [!IMPORTANT]
> These benchmarks reflect **this specific hardware and workload**. Speedups are
> workload-dependent (`0.73x` on tiny 100-vertex AR clouds up to `40.60x` on 10k
> clouds, and `82.39x` on stateful simulation loops). Exact numbers vary by CPU
> and input shape — see [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) for all tiers.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MOJO_BIN` | (auto) | Override path to the `mojo` compiler binary |
| `HOTLOOP_STRICT` | `0` | Set to `1` to raise `HotloopNativeExecutionError` instead of falling back |
| `HOTLOOP_FORCE_NATIVE` | `0` | Set to `1` to bypass performance qualification heuristics |
| `HOTLOOP_CACHE_CHECK` | `runtime` | Cache validation policy: `runtime`, `import`, `always`, `off` |
| `HOTLOOP_STRICT_PERF` | `0` | Set to `1` to raise an error for unaccelerated backends |

---

## Running Tests

```bash
# Adversarial compiler tests (no Mojo required)
.venv/bin/python tests/test_compiler_adversarial.py

# Build all 7 use cases (requires Mojo)
.venv/bin/python audit/test_ast_provenance.py

# Run all 7 verification suites (7,220 tests, requires Mojo)
.venv/bin/python audit/run_all_verifications.py

# Run 35+ unfamiliar functions & runtime security/memory suites (requires Mojo)
.venv/bin/python tests/test_unfamiliar_functions.py
.venv/bin/python tests/test_runtime_security.py
```

---

## Reproducing Benchmarks

See [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) for the full methodology,
hardware specs, and measurement scripts.

---

## Known Limitations

1. **Linux / WSL2 only**: macOS and native Windows are not supported in v0.1.0.
2. **Mojo 1.2.0 only**: Tested strictly against Mojo 1.2.0 (`2016d0cd`).
3. **No `break`/`continue`**: Use early `return` or loop condition flags.
4. **Unsupported Python constructs**: `dict`, `set`, `tuple`, list slicing (`xs[1:3]`), list comprehensions, `lambda`, `try`/`except`, `*args`/`**kwargs` raise `ASTTranspileError` cleanly and trigger Python fallback.
5. **NumPy pointer fast-path scope**: Zero-copy dispatch requires read-only `len(xs)`/`xs[i]` patterns on 1-D C-contiguous `float64`/`int64` `ndarray`; mutating, N-D, strided, or other-dtype arrays fall back cleanly.
6. **FFI overhead on tiny inputs or `list[str]` returns**: Very small inputs (`~100` array elements) or collection-of-string returns (`list[str]`) can be slower across C-ABI than pure Python; collection I/O triggers automatic Python fallback unless `ndarray` or `force_native=True` is used.
7. **Mojo reserved keywords**: Using Mojo keywords (`fn`, `var`, `struct`, `mut`, `out`, etc.) as parameter or local variable names raises `ASTTranspileError`.

---

## Contributing

Contributions welcome! See [`CONTRIBUTING.md`](CONTRIBUTING.md).

- DCO sign-off required (`git commit -s`) — no CLA
- All new transpiler features need a test in `tests/test_compiler_adversarial.py`
- Performance claims need benchmark evidence (see `docs/BENCHMARKS.md`)

---

## License

Apache License 2.0. See [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).

Copyright 2026 Gaurav Kumar Singh and mojo-hotloop contributors.

---

## Trademark Notice

MAX® and Mojo® are trademarks of Modular, Inc. used under license.

Mojo Hotloop is an independent open-source project and is not affiliated with, sponsored by, or endorsed by Modular, Inc.

