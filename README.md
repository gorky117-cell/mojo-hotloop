# mojo-hotloop

Automatic native acceleration for a supported, typed subset of Python using deterministic Python-to-Mojo translation and transparent fallback.

[![Python CI](https://github.com/gorky117-cell/mojo-hotloop/actions/workflows/ci.yml/badge.svg?branch=main&job=Python%20Tests%20(Python%203.12))](https://github.com/gorky117-cell/mojo-hotloop/actions/workflows/ci.yml)
[![Native CI](https://github.com/gorky117-cell/mojo-hotloop/actions/workflows/ci.yml/badge.svg?branch=main&job=Native%20Verification%20(Mojo%201.2.0,%20Python%203.12))](https://github.com/gorky117-cell/mojo-hotloop/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)
[![Classification](https://img.shields.io/badge/Release-Developer%20Preview%20(v0.2.0)-orange.svg)](https://github.com/gorky117-cell/mojo-hotloop/releases/tag/v0.2.0)

---

## What It Does

`mojo-hotloop` is an open-source compiler tool and Python decorator that:

1. **Transpiles** type-annotated Python functions into idiomatic Mojo 1.2.0 source code using a deterministic AST transpiler (completely offline; zero cloud or AI APIs).
2. **Compiles** the generated Mojo source into an optimized C-ABI native shared library (`.so`) via the local `mojo build` CLI.
3. **Dispatches** function calls to the native shared library when available, with automatic and transparent fallback to pure Python if Mojo is absent, compilation fails, or FFI conversion overhead exceeds computation time.

If Mojo is not installed, all `@hotloop` functions execute pure Python with identical semantics and emit a warning.

---

## Why Mojo Hotloop? How It Differs From Numba and Codon

| Dimension | Mojo Hotloop | Numba (`@njit`) | Codon (`@codon.jit` / native) |
| :--- | :--- | :--- | :--- |
| **Compilation Model** | Ahead-of-Time (AOT) to inspectable Mojo source (`fast.mojo`) + C-ABI `.so` | Just-in-Time (JIT) bytecode to LLVM machine code | JIT to LLVM IR or standalone native executable |
| **Startup Latency** | **Zero JIT lag** at runtime; 5–50 ms `.so` load at import | Cold-start JIT compilation latency (200 ms to 3+ seconds on first call) | JIT compilation lag (1–5 seconds per function on first call) |
| **Generated Artifacts** | Inspectable `.mojo` source and standard `.so` shared library | In-memory LLVM compiled functions | In-memory JIT or native executable binary |
| **Collection & FFI Overhead** | Zero-copy pointer fast-path for 1-D C-contiguous NumPy arrays; **safe fallback for boxed collections** | Native array handling with high optimization; slower object-mode fallback | Fast native execution; C-API boundary overhead on Python string translation |
| **String Processing** | Linear `_PyStr` ASCII buffer with zero-alloc char accumulation | Limited Python string support under nopython mode | Powerful native strings, but encounters $O(N^2)$ reallocation on large concatenations |
| **Fallback Contract** | **Transparent semantic fallback** to CPython reference; no crashes | Exception raised if `nopython` compilation fails | Exception or Python C-API fallback depending on configuration |

### Where Mojo Hotloop Performs Well
- **Stateful scalar loops**: Algorithmic loops with accumulator variables, conditional branching, and scalar arithmetic (e.g. Quantitative Backtest: **69.34× vs Python**; comparable to Numba without runtime JIT compilation pause).
- **1-D NumPy array operations**: Zero-copy pointer dispatch for numerical algorithms (e.g. AR Spatial 3D: **33.36× vs Python**; Geo Distance: **9.74× vs Python**).
- **Linear string scanning and scrubbing**: Fixed-buffer character inspection, ASCII filtering, and single-pass sanitization (e.g. PDF Text Cleaner: **6.20× vs Python, 2.54× faster than Regex**; PII Scrubber: **4.96× vs Python, 1.74× faster than Regex**).

### Where Competitors Perform Better
- **Vectorized SIMD transcendentals**: Numba and NumPy utilize vectorized libm/SIMD transcendentals (`math.sin`, `math.cos`, `math.atan2`), making them **1.26× to 1.60× faster** than Mojo Hotloop on large array operations (e.g., Geo Distance and AR Spatial 3D).
- **End-to-end typed pipelines**: Codon Native operating entirely on internal typed types without Python C-API interaction outperforms Mojo Hotloop by **1.30× to 2.22×** on standalone numeric workflows.
- **Hand-tuned C++ algorithms**: Specialized C++ libraries (such as RapidFuzz for Myers bit-parallel edit distance) are **1.27× faster** than Mojo Hotloop's general-purpose AST output on fuzzy string matching.

### Where Workloads Currently Fall Back
- **Small standard Python lists**: Passing small standard Python `list[float]` incurs per-element C-API boxing overhead exceeding execution time. Mojo Hotloop automatically detects this and routes execution to pure Python.
- **Collection returns**: Functions returning `list[str]` (such as the RAG Document Chunker) require boxing thousands of Python string objects across the C-API, creating a high allocation overhead floor (~21× slower if forced natively). Mojo Hotloop automatically detects collection returns and executes pure Python (**1.01×**), protecting overall application throughput.

---

## Supported Python Subset & Honest Limitations

The AST transpiler supports a **strict, statically typed subset** of Python 3.12. See [`docs/SUPPORTED_SYNTAX.md`](docs/SUPPORTED_SYNTAX.md) for the complete language construct reference.

### Supported Constructs
- **Primitive Types**: `int`, `float`, `bool`, `str`.
- **Arrays & Collections**: 1-D C-contiguous `float64`/`int64` `numpy.ndarray` (zero-copy pointer fast-path); `list[int]`, `list[float]`, `list[str]`, `list[bool]`.
- **Control Flow**: `for i in range(...)`, `while`, `if/elif/else`, early `return`, lexical scoping.
- **Operators & Arithmetic**: `+`, `-`, `*`, `/`, `//`, `%`, `**`, bitwise operators, chained comparisons (`a < b < c`), truthiness.
- **Built-in Functions**: `len()`, `range()`, `ord()`, `chr()`, `abs()`, `min()`, `max()`, `bool()`, `int()`, `float()`, `str()`.
- **Math Library**: `math.sin`, `math.cos`, `math.sqrt`, `math.atan2`, `math.pi`, `math.e`, `math.log`, `math.exp`, `math.floor`, `math.ceil`.
- **String Operations**: Linear `_PyStr` ASCII buffer, index reads (`s[i]`), `ord(s[i])`, slice indexing (`s[a:b]`, `s[a:b:step]`), zero-alloc single-character accumulation (`out += s[i]`).

### Present Restrictions & Limitations
- **Type Annotations**: All function parameters, return types, and **local variables on first assignment** must have explicit type annotations (e.g. `total: int = 0`). Untyped variables or dynamic duck typing are not supported.
- **Loop Control**: `break` statements inside loop bodies are supported in v0.2.0; `continue` statements are currently unsupported (use early `return` or boolean condition flags).
- **Negative Indexing**: Direct negative indexing on strings (`s[-i]`) is supported in v0.2.0; negative list indexing (`xs[-1]`) should use `xs[len(xs) - 1]`.
- **Unsupported Structures**: `dict`, `set`, `tuple`, list comprehensions, `lambda`, generator expressions, `*args`/`**kwargs`, and `try`/`except` blocks trigger clean, automatic Python fallback.
- **Platform Scope**: Linux x86-64 only (including Ubuntu 24.04 on WSL2). macOS and native Windows execution are not supported in v0.2.0.

---

## Installation & Environment

> [!IMPORTANT]
> **Verified Environment:** Linux x86-64 (or Ubuntu 24.04 LTS on WSL2), CPython 3.12, Mojo 1.2.0.
> Compatibility with other Python or Mojo versions is untested.

### 1. Set up a Python 3.12 virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install the Mojo compiler (for native acceleration)
Install Modular's standalone Mojo 1.2.0 compiler directly into your virtual environment:
```bash
pip install mojo==1.2.0
mojo --version   # Verify output: Mojo 1.2.0 (2016d0cd)
```

> [!NOTE]
> Always ensure your virtual environment is active (`source .venv/bin/activate`) so that `mojo` and `hotloop` CLI executables are available on your `PATH`.

### 3. Install mojo-hotloop v0.2.0
Install the official pre-release wheel directly from the GitHub v0.2.0 release:
```bash
pip install https://github.com/gorky117-cell/mojo-hotloop/releases/download/v0.2.0/mojo_hotloop-0.2.0-py3-none-any.whl
```
*(Or if developing from a local git repository: `pip install -e .`)*

> **Without Mojo:** All `@hotloop` functions automatically execute pure Python as a transparent fallback. The package is fully functional offline without Mojo for development, linting, and AST validation.

---

## Quick Start (Verified Native Execution)

### Step 1 — Write an annotated Python function

```python
# myapp.py
from hotloop import hotloop

@hotloop
def sum_squares(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i * i
    return total
```

**All parameters and return types must be type-annotated.** Local variables must also include explicit type annotations on first assignment (`total: int = 0`).

### Step 2 — Build the native shared library

```bash
hotloop build myapp.py --engine=ast
```

This creates `fast.so` and `fast.hotloop_manifest.json` directly alongside `myapp.py`.

### Step 3 — Run at native speed

```python
import myapp
from hotloop import inspect_dispatch

result = myapp.sum_squares(100_000)
print("Result:", result)                                      # 333328333350000
print("Execution backend:", myapp.sum_squares._last_backend)  # "native"

# Inspect runtime dispatch telemetry
info = inspect_dispatch(myapp.sum_squares)
print("Native calls:", info["call_count_native"])             # 1
print("Fallback calls:", info["call_count_fallback"])         # 0
```

> [!TIP]
> **Arrays and NumPy:** For array processing, pass a 1-D C-contiguous `numpy.ndarray` (`float64` or `int64`) to activate zero-copy native memory pointers. Plain Python `list[...]` inputs with small element counts automatically fall back to Python because per-element FFI conversion overhead exceeds computation time.

---

## How Fallback Works

```
@hotloop function called
        │
        ▼
  .so present, fresh, and qualified?
   ├─ Yes → native execution via Mojo C-ABI
   └─ No  → HotloopFallbackWarning issued
              → pure Python function executed
```

The fallback is **automatic, transparent, and semantically equivalent**. No data corruption; no crashes.

Enable strict mode if you want an explicit error instead of fallback:

```python
@hotloop(strict=True)
def my_function(x: float) -> float:
    ...
```

---

## Canonical Empirical Benchmark Matrix

Empirical timings measured under standardized, controlled conditions (Intel Core i5-8265U @ 1.60 GHz, Ubuntu 24.04 LTS on WSL2, 5 batched trials, median $p_{50}$ per-call latency). Timings measure end-to-end Python call-site to result return, including FFI translation and dispatch. Within a 10% provisional margin of error, measurements are considered broadly comparable.

| Workload | Input Scale | CPython $p_{50}$ | **Mojo `@hotloop` $p_{50}$** | Speedup vs Py | Fastest Competitor | Relative vs Fastest | Execution Mode |
| :--- | :--- | :--- | :--- | :---: | :--- | :---: | :---: |
| **Quant Backtest** | 100k ticks | 38.152 ms | **0.550 ms** | **69.34×** | Codon JIT: 0.464 ms | 0.84× (Numba: 1.03×) | Native |
| **AR Spatial 3D** | 10k vertices (`ndarray`) | 3.795 ms | **0.114 ms** | **33.36×** | Numba: 0.071 ms | 0.63× (Codon JIT: 1.32×) | Native |
| **Geo Distance** | 10k waypoints (`ndarray`) | 11.059 ms | **1.136 ms** | **9.74×** | NumPy: 0.900 ms | 0.79× (Codon JIT: 0.92×) | Native |
| **PDF Cleaner** | 100k chars | 29.094 ms | **4.691 ms** | **6.20×** | Regex: 11.931 ms | **2.54× faster** | Native |
| **PII Scrubber** | 100k chars | 76.065 ms | **15.328 ms** | **4.96×** | Regex: 26.685 ms | **1.74× faster** | Native |
| **OCR Matcher** | 1k words (`list[str]`) | 2.331 ms | **2.382 ms** | **0.98×** | RapidFuzz: 0.514 ms | 0.22× | **Fallback** |
| *(Forced Native)* | 1k words (`list[str]`) | 2.331 ms | *0.653 ms* | *3.57×* | RapidFuzz: 0.514 ms | *0.79×* | Native |
| **RAG Chunker** | 100k chars | 0.193 ms | **0.191 ms** | **1.01×** | Pure Python: 0.193 ms | 1.01× | **Fallback** |
| *(Forced Native)* | 100k chars | 0.193 ms | *4.009 ms* | *0.05×* | Pure Python: 0.193 ms | *0.05×* | Native |

> [!NOTE]
> All benchmark numbers are generated deterministically from the versioned machine-readable dataset [`benchmarks/canonical_benchmarks_v0.1.0.json`](benchmarks/canonical_benchmarks_v0.1.0.json).
> See [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) and [`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md) for per-tier numbers, compilation costs, and reproducibility scripts.

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

## Running Verification Suites

```bash
# 1. Offline adversarial compiler tests (runs without Mojo)
python tests/test_compiler_adversarial.py

# 2. Build all 7 use cases with Mojo (requires Mojo 1.2.0)
python audit/test_ast_provenance.py

# 3. Run all 7 domain verification suites (7,220 checks verified against CPython reference)
python audit/run_all_verifications.py

# 4. Run unfamiliar functions & runtime security/stability suites (requires Mojo 1.2.0)
python tests/test_unfamiliar_functions.py
python tests/test_runtime_security.py

# 5. Verify benchmark table consistency against canonical dataset
python benchmarks/generate_benchmark_reports.py --check
```

---

## Contributing & Community

Contributions are welcome from developers worldwide! Please review:
- **[Contribution Guide](CONTRIBUTING.md)** — Workflow, testing, and DCO sign-off policy (`git commit -s`)
- **[Code of Conduct](CODE_OF_CONDUCT.md)** — Contributor Covenant 2.1 standards
- **[Security Policy](SECURITY.md)** — Responsible private vulnerability reporting
- **[Supported Syntax Guide](docs/SUPPORTED_SYNTAX.md)** — Comprehensive language construct reference
- **[Benchmark Methodology](docs/BENCHMARKS.md)** — Transparent 5-trial median performance protocols
- **[Historical Engineering Records](docs/history/README.md)** — Archived phase reports and development notes

---

## License & Copyright

Mojo Hotloop is licensed under the **Apache License 2.0**. See [`LICENSE`](LICENSE) for the full text.

Copyright 2026 Gaurav Kumar Singh and mojo-hotloop contributors.

---

## Disclaimer & Trademark Notice

**Disclaimer:** Mojo Hotloop is an independent open-source project developed and maintained by Gaurav Kumar Singh and contributors. It is not affiliated with, operated by, sponsored by, or endorsed by Modular, Inc.

MAX® and Mojo® are trademarks of Modular, Inc. used under license.
(Attribution provided in accordance with Modular, Inc.'s published Trademark Policy at [modular.com/legal/trademark](https://www.modular.com/legal/trademark). See [`NOTICE`](NOTICE) and [`docs/THIRD_PARTY_NOTICES.md`](docs/THIRD_PARTY_NOTICES.md)).
