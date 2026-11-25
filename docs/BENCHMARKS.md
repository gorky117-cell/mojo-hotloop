> Historical v0.1.0 measurements are preserved below. They predate corrective semantic/ownership restrictions and must not be treated as current performance or compatibility promises. See [current candidate observations](CURRENT_BENCHMARKS.md).

# Benchmark Methodology and Results — mojo-hotloop v0.1.0

> **Canonical Dataset**: [`benchmarks/canonical_benchmarks_v0.1.0.json`](../benchmarks/canonical_benchmarks_v0.1.0.json)  
> **Baseline Git Commit**: `5de730c691cecd8a6e582ba61b8251ccc2f999ca`  
> **Date**: 2026-11-15  
> **Hardware**: Intel Core i5-8265U @ 1.60 GHz, 4 physical cores / 8 threads, 6 MiB L3 cache, 7.63 GiB RAM  
> **OS**: Ubuntu 24.04 LTS (WSL2 on Windows 11, kernel 6.6.87.2-microsoft-standard-WSL2)  
> **Python**: 3.12.16 (Clang 23.1.3)  
> **Mojo**: 1.2.0 (`2016d0cd`)

---

## Methodology

### What Is Measured

Each benchmark measures **end-to-end wall-clock time** of a single decorated function call, from Python call-site to result return, including:
- FFI boundary translation overhead (Python → Mojo C-ABI → Python)
- Native computation time inside the compiled `.so` kernel
- Result boxing and conversion to Python types

It does **not** measure one-time import overhead (such as `.so` dynamic library loading at module import time).

### Measurement Harness

Benchmarks are orchestrated via `benchmarks/run_hotloop_suite.py` and `benchmarks/run_competitive.py` using the following protocol:

```python
def measure(fn: Callable, args: tuple, iters: int, trials: int = 5) -> Dict[str, Any]:
    # 1. Warm-up to ensure stable instruction cache and thread affinity
    for _ in range(min(max(iters // 4, 2), 10)):
        res = fn(*args)
    
    # 2. Collect 5 batched trials with garbage collection disabled
    samples_ms: List[float] = []
    for _ in range(trials):
        gc.disable()
        t0 = time.perf_counter_ns()
        for _ in range(iters):
            res = fn(*args)
        t1 = time.perf_counter_ns()
        gc.enable()
        samples_ms.append((t1 - t0) / (iters * 1_000_000.0))
    
    # 3. Sort trials and calculate statistics
    s = sorted(samples_ms)
    return {
        "p50_ms": statistics.median(s),
        "p95_ms": s[-1],
        "mean_ms": statistics.mean(s),
        "stdev_ms": statistics.stdev(s),
    }
```

The **$p_{50}$ (median)** of the 5 batched runs is reported as the primary speedup metric. This prevents transient OS scheduler jitter from distorting steady-state performance.

### Statistical Equivalence Standard

> [!NOTE]
> **Provisional 10% Margin**: In micro-benchmarking, run-to-run variation on modern OS schedulers typically introduces ±3% to ±5% noise. Unless variability analysis or larger sample sizes show a definitive difference, performance measurements within a **10% margin** are characterized as **broadly comparable** rather than declaring one compiler unconditionally superior to another.

### Comparison Baselines & Toolchain Versions

| Baseline | Toolchain Version / Implementation | Description |
|----------|------------------------------------|-------------|
| **CPython 3.12** | CPython 3.12.16 (Clang 23.1.3) | The unmodified Python reference implementation |
| **Codon JIT** | Codon v0.17.0 / v0.20.6 (`@codon.jit`) | LLVM-based Python-to-native JIT compiler |
| **Codon Native** | Codon v0.17.0 / v0.20.6 (`codon build -release`) | Standalone native ahead-of-time executable |
| **Numba** | Numba 0.68.1 (`@njit(nopython=True)`) | LLVM-based JIT compiler for numerical numerical code |
| **NumPy** | NumPy 2.5.4 (C-BLAS SIMD) | Vectorized array operations with optimized SIMD kernels |
| **RapidFuzz** | RapidFuzz 3.14.6 | C++ Levenshtein / Myers bit-parallel difference library |
| **Regex** | CPython standard library `re` | Compiled regular expressions implemented in C |

---

## Master Competitive Benchmark Matrix (Seven Real-World Applications)

The table below presents the canonical scorecard across all seven real-world business use cases, generated from [`benchmarks/canonical_benchmarks_v0.1.0.json`](../benchmarks/canonical_benchmarks_v0.1.0.json):

| Workload | Input Scale & Type | Output Contract | Execution Mode | CPython 3.12 $p_{50}$ | Auto Mojo Kernel $p_{50}$ | **Mojo `@hotloop` $p_{50}$** | Codon JIT 0.17.0 $p_{50}$ | Codon Native 0.17.0 $p_{50}$ | Best Alternative $p_{50}$ | **Mojo Speedup vs Py** | Correctness Verified |
| :--- | :--- | :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **Quant Backtest** | 100k ticks (scalars) | `float` | **Native** | 38.152 ms | 0.5636 ms | **0.5502 ms** | 0.4642 ms | 0.7309 ms | Numba: 0.5666 ms | **69.34×** | ✅ 0 mismatches |
| **AR Spatial 3D** | 10k vertices (`ndarray[float64]`) | `float` | **Native** | 3.7947 ms | 0.1011 ms | **0.1137 ms** | 0.1500 ms | 0.0511 ms | Numba: 0.0711 ms | **33.36×** | ✅ 0 mismatches |
| **Geo Distance** | 10k waypoints (`ndarray[float64]`) | `float` | **Native** | 11.0586 ms | 1.1226 ms | **1.1357 ms** | 1.0396 ms | 0.8736 ms | NumPy: 0.9004 ms | **9.74×** | ✅ 0 mismatches |
| **PDF Cleaner** | 100k chars (`str`) | `str` | **Native** | 29.0944 ms | 4.1718 ms | **4.6911 ms** | 7757.75 ms | 4136.78 ms | Regex: 11.9306 ms | **6.20×** | ✅ 0 mismatches |
| **PII Scrubber** | 100k chars (`str`) | `str` | **Native** | 76.0653 ms | 10.5845 ms | **15.3276 ms** | 12351.30 ms | 5666.94 ms | Regex: 26.6853 ms | **4.96×** | ✅ 0 mismatches |
| **OCR Matcher** | 1k words (`list[str]`) | `str` | **Fallback** | 2.3310 ms | 0.6393 ms | **2.3824 ms** | 0.3242 ms | 0.2887 ms | RapidFuzz: 0.5137 ms | **0.98× (Fallback)** | ✅ 0 mismatches |
| *(Forced Native)* | 1k words (`list[str]`) | `str` | *Native* | 2.3310 ms | 0.6393 ms | *0.6526 ms* | 0.3242 ms | 0.2887 ms | RapidFuzz: 0.5137 ms | *3.57×* | ✅ 0 mismatches |
| **RAG Chunker** | 100k chars (`str`) | `list[str]` | **Fallback** | 0.1926 ms | 4.1643 ms | **0.1911 ms** | 0.9958 ms | 0.0243 ms* | Pure Py: 0.1926 ms | **1.01× (Fallback)** | ✅ 0 mismatches |
| *(Forced Native)* | 100k chars (`str`) | `list[str]` | *Native* | 0.1926 ms | 4.1643 ms | *4.0088 ms* | 0.9958 ms | 0.0243 ms* | Pure Py: 0.1926 ms | *0.05×* | ✅ 0 mismatches |

---

## Detailed Reconciliation of Discrepancies

### 1. Quantitative Backtest
- **Codon JIT vs Mojo Hotloop**: In the standardized matrix, Codon JIT achieves **0.464 ms**, which is **1.18× faster than Mojo Hotloop (0.550 ms)**. Codon Native takes 0.731 ms. Early drafts that claimed Mojo "beat Codon" compared Mojo against Codon Native while overlooking Codon JIT.
- **Mojo Hotloop vs Numba**: Mojo Hotloop takes **0.550 ms** while warmed Numba takes **0.567 ms**. The difference is ~3%, which is within our 10% provisional margin of error. They are **broadly comparable** in steady-state execution, though Mojo Hotloop avoids Numba's 1,916 ms JIT cold-start compilation overhead.
- **Historical 82.4× vs Canonical 69.34×**: An exploratory, single-suite run recorded Python at 43.78 ms and Mojo at 0.531 ms (82.39×). In the standardized multi-tool benchmark run, Python ran at 38.15 ms and Mojo ran at 0.550 ms (69.34×). The canonical artifact records the controlled 69.34× figure.

### 2. AR Spatial 3D
- **Competitor Performance**: On 10,000 vertices with 1-D C-contiguous `ndarray` inputs, Mojo Hotloop achieves **0.114 ms (33.36× vs Python)**. However, **Numba (0.071 ms, 1.60× faster than Mojo)** and **Codon Native (0.051 ms, 2.22× faster than Mojo)** are faster due to LLVM auto-vectorized SIMD inner loops.
- **Codon JIT Comparison**: Mojo Hotloop outperforms Codon JIT (0.150 ms, **1.32× faster than Codon JIT**).

### 3. Geo Distance
- **Vectorized Transcendentals**: NumPy vectorized SIMD operations take **0.900 ms (1.26× faster than Mojo's 1.136 ms)**, and Codon Native takes **0.874 ms**. Mojo Hotloop achieves **9.74× vs pure Python (11.059 ms)** and is within 10% of Codon JIT (1.040 ms).

### 4. Text Processing (PDF Cleaner & PII Scrubber)
- **Regex Comparison**: Mojo Hotloop outperforms compiled CPython regex:
  - PDF Text Cleaner: **4.691 ms vs 11.931 ms (2.54× faster than Regex)**.
  - PII Scrubber: **15.328 ms vs 26.685 ms (1.74× faster than Regex)**.
- **Codon String Concatenation Bottleneck**: Codon encounters an $O(N^2)$ reallocation behavior when concatenating characters on 100k-character strings, taking 7.7s and 12.3s. Mojo Hotloop's `_PyStr` linear ASCII buffer completes in 4.7 ms and 15.3 ms (**806× to 1,654× faster than Codon JIT**).
- **Historical 7.49× vs Canonical 4.96×**: An early Phase B trial using a non-standard 100k test text recorded 7.49× based on mean timings. Standardized testing on the canonical corpus yields a consistent 4.96× ($p_{50}$).

### 5. Transparent Fallback (OCR Matcher & RAG Chunker)
- **OCR Matcher**: Small candidate collections (`list[str]`) incur C-API FFI overhead that exceeds native speedup in default mode (2.382 ms vs 2.331 ms Python). When forced native, Mojo Hotloop runs in **0.653 ms (3.57× vs Python)**. Hand-tuned C++ RapidFuzz is fastest at **0.514 ms**.
- **RAG Chunker**: Returning thousands of strings in `list[str]` requires boxing each string into a Python object across the C-API. Direct forced native execution takes 4.009 ms (~21× slower than Python). Mojo Hotloop detects collection returns and transparently falls back to pure Python (**0.191 ms**), protecting system performance.

---

## Reproducing Benchmarks

All benchmarks are fully reproducible using the repository scripts:

```bash
# 1. Activate verified virtual environment
source .venv/bin/activate

# 2. Build native shared libraries for all 7 use cases
python audit/test_ast_provenance.py

# 3. Verify all 7 suites (7,220 passing checks, 0 mismatches)
python audit/run_all_verifications.py

# 4. Run the complete competitive benchmark suite
python benchmarks/run_competitive.py canonical

# 5. Verify consistency against canonical JSON
python benchmarks/generate_benchmark_reports.py --check
```

---

## Limitations & Experimental Notes

1. **WSL2 Virtualization**: Measurements were collected under WSL2 on Windows 11. Linux-native bare-metal execution typically reduces scheduling jitter by ±5%.
2. **Single-Threaded Execution**: All workloads run on a single CPU thread. Mojo Hotloop does not inject multi-threaded runtime parallelization.
3. **Compiler Optimization Flags**: Native shared libraries are compiled with `mojo build --emit shared-lib -O3`.
4. **Import-Time Overhead**: Dynamic library loading via `ctypes.CDLL` (5–50 ms at initial import) is not included in steady-state per-call latency.
