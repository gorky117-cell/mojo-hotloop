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
- Types: `int`, `float`, `bool`, `str`, `list[int]`, `list[float]`, `list[str]`, `list[bool]`
- Control flow: `for i in range(...)`, `while`, `if/elif/else`, `return` (including early return)
- Arithmetic: `+`, `-`, `*`, `/`, `//`, `%`, `**`, bitwise operators
- Builtins: `len()`, `range()`, `ord()`, `abs()`, `min()`, `max()`, type conversion
- Math: `math.sin`, `math.cos`, `math.sqrt`, `math.atan2`, `math.pi`, and more
- Lists: `.append()`, `.clear()`, index read/write
- Strings: `+=` accumulation, `len()`, `ord(s[i])`

**Not supported**: `numpy`, `dict`, `set`, `tuple`, list comprehensions, `lambda`,
`break`, `continue`, `*args`/`**kwargs`, `try`/`except`.

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
| Quantitative Backtest | Financial simulation | **66x** | 1,117 |
| PII Scrubber | Text security | 2.96x | 1,019 |
| PDF Text Cleaner | Document processing | 2.85x | 1,020 |
| Geo Distance (Haversine) | Geospatial | 2.95x | 1,014 |
| OCR Fuzzy Matcher | String search | 2.84x | 1,020 |
| AR Spatial 3D Ray | Graphics/AR | 1.48x | 1,010 |
| RAG Document Chunker | LLM ingestion | Python fallback¹ | 1,020 |

¹ The RAG chunker returns `list[str]`. The FFI overhead of boxing each string
exceeds the native computation savings. `mojo-hotloop` detects this automatically
and falls back to Python — this is **correct behavior**, not a bug.

> [!IMPORTANT]
> These benchmarks reflect **this specific hardware and workload**. Your results
> will vary. The 66x speedup for the quant backtest is real but specific to that
> pattern (stateful simulation, no data-parallel structure). Do not expect
> universal 66x speedups.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOTLOOP_STRICT` | `0` | Set to `1` to raise `HotloopNativeExecutionError` instead of falling back |
| `HOTLOOP_FORCE_NATIVE` | `0` | Set to `1` to bypass performance qualification heuristics |
| `HOTLOOP_CACHE_CHECK` | `runtime` | Cache validation policy: `runtime`, `import`, `always`, `off` |
| `HOTLOOP_STRICT_PERF` | `0` | Set to `1` to raise an error for unaccelerated backends |
| `GEMINI_API_KEY` | (none) | Required for `--engine=gemini` only |
| `HOTLOOP_MODEL` | (none) | Gemini model name, required for `--engine=gemini` |

---

## Running Tests

```bash
# Adversarial compiler tests (no Mojo required, ~2 seconds)
.venv/bin/python tests/test_compiler_adversarial.py

# Build all 7 use cases (requires Mojo)
.venv/bin/python audit/test_ast_provenance.py

# Run all 7 verification suites (requires Mojo + pre-built .so files)
.venv/bin/python audit/run_all_verifications.py
```

---

## Reproducing Benchmarks

See [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) for the full methodology,
hardware specs, and measurement scripts.

---

## Known Limitations

1. **Negative list indexing** (`xs[-1]`): Accepted by the transpiler but may
   produce incorrect Mojo. Use `xs[len(xs) - 1]` instead.
2. **Chained comparisons** (`a < b < c`): May compile incorrectly. Use
   `a < b and b < c`.
3. **Linux only**: macOS and Windows (native) are not supported in v0.1.0.
4. **No `break`/`continue`**: Use early `return` instead.
5. **Mojo 1.2.0 only**: Not tested with other Mojo versions.
6. **`list[str]` return type**: FFI overhead may cause auto-fallback to Python.
7. **Functions must have full type annotations**: Unannotated parameters are rejected.

---

## Contributing

Contributions welcome! See [`CONTRIBUTING.md`](CONTRIBUTING.md).

- DCO sign-off required (`git commit -s`) — no CLA
- All new transpiler features need a test in `tests/test_compiler_adversarial.py`
- Performance claims need benchmark evidence (see `docs/BENCHMARKS.md`)

---

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

Copyright 2026 mojo-hotloop Contributors.
