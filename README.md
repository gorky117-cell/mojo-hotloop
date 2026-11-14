# mojo-hotloop

Accelerate slow Python hot loops using compiled Mojo shared libraries with identical semantics, zero boilerplate, and transparent fallback.

`mojo-hotloop` is an open-source compiler tool and decorator that transpiles Python hot loops into high-performance Mojo shared libraries (`.so`) using deterministic AST analysis.

---

## Key Features

- **Zero-Boilerplate Decorator**: Simply decorate your CPU-bound Python function with `@hotloop`.
- **Deterministic AST Transpiler**: Ahead-of-time (AOT) transpile numerical loops, Unicode string algorithms, and collection pipelines to native Mojo without AI hallucinations or external network calls.
- **Identical Semantics**: Preserves 100% Python behavior including checked 64-bit integer arithmetic, arbitrary-precision BigInt overflow fallback, `ZeroDivisionError` parity, and full Unicode/codepoint compliance.
- **Multi-Tiered Safety & Transparent Fallback**: If a shared library is missing or stale, `mojo-hotloop` safely falls back to executing your original Python function.
- **Strict Performance Mode**: Detects when per-element FFI conversion overhead would exceed pure Python execution time (e.g. naive Python list allocations) and defaults to Python or warns the developer.
- **CLI Tooling**: Build native shared libraries directly from the terminal via `hotloop build <file.py>`.

---

## Installation

Inside a Linux environment (or WSL2 Ubuntu):

```bash
# Install with standard pip
pip install .

# Or editable install for development
pip install -e .
```

Ensure Mojo 1.2.0 is installed in your virtual environment:

```bash
pip install modular
modular install mojo
```

---

## Quickstart

### 1. Write Python Code with `@hotloop`

```python
# app.py
from hotloop import hotloop

@hotloop
def vector_dot_product(xs: list[float], ys: list[float]) -> float:
    total: float = 0.0
    for i in range(len(xs)):
        total += xs[i] * ys[i]
    return total
```

### 2. Build Native Mojo Shared Library

```bash
hotloop build app.py --engine=ast
```

This generates `fast.so` alongside your code, verified with content-addressed SHA-256 manifests.

### 3. Run Your Application

```python
import app

# Executes natively at compiled C-ABI speed!
result = app.vector_dot_product([1.0, 2.0, 3.0], [10.0, 20.0, 30.0])
print(result) # 140.0
```

---

## Real-World Use Cases (Phase D Benchmarks)

All 7 real-world use cases have been built via AST transpilation, validated across 1,000+ tests each (7,220 total tests), and benchmarked on equivalent hardware:

| Workload | Domain | Python 3.12 | Best Alternative | Mojo @hotloop | Speedup vs Python | Status |
|---|---|---:|---:|---:|---:|---|
| **Quantitative Backtest** | Financial Math | 32.64 ms | 0.522 ms (Numba) | **0.493 ms** | **66.14x** | PASS (Native Win) |
| **PDF Text Cleaner** | Document Processing | 32.03 ms | 14.24 ms (Regex) | **11.23 ms** | **2.85x** | PASS (Native Win) |
| **PII Scrubber** | Text Security | 89.37 ms | 35.88 ms (Regex) | **30.20 ms** | **2.96x** | PASS (Native Win) |
| **Geo Distance (Haversine)** | Geospatial Analytics | 0.763 ms | 0.075 ms (Numba) | **0.258 ms** | **2.95x** | PASS (Native Win) |
| **OCR Fuzzy Matcher** | Text Search | 1.414 ms | 0.060 ms (RapidFuzz) | **0.497 ms** | **2.84x** | PASS (Native Win) |
| **AR Spatial 3D Ray** | 3D Graphics / AR | 0.348 ms | 0.007 ms (Numba) | **0.234 ms** | **1.48x** | PASS (Native Win) |
| **RAG Document Chunker** | LLM Ingestion | 0.210 ms | 0.210 ms (Python) | 4.286 ms | 0.05x | PASS (Safe Fallback) |

---

## Configuration & Environment Variables

- `HOTLOOP_STRICT=1`: Raise `HotloopNativeExecutionError` if a compiled `.so` is missing or stale instead of falling back to Python.
- `HOTLOOP_FORCE_NATIVE=1`: Force native execution even for standard Python collection workloads where FFI overhead is present.
- `HOTLOOP_CACHE_CHECK`: Control cache validation policy (`runtime` [default, throttled 20ms], `import`, `always`, or `off`).
- `HOTLOOP_STRICT_PERF=1`: Enforce strict performance qualification — raises an error if an unaccelerated backend would execute.

---

## License

Apache 2.0
