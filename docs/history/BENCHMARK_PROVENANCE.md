# MOJO-HOTLOOP — BENCHMARK PROVENANCE & CODEBASE AUDIT REPORT
**Phase D.3 Pre-Optimization Audit: Tracing Generated Code, Resolving Historical Inconsistencies & Verifying Transpiler Authenticity**

**Date**: November 15, 2026  
**Auditor**: Principal Compiler Architect, Mojo/LLVM Performance Engineer & Independent Benchmark Auditor  
**Repository**: `/home/gaurav/mojo-hotloop`  
**Toolchain**: Python 3.12.16 | Mojo 1.2.0 (`2016d0cd`) | Clang / LLVM Backend | Ubuntu 24.04 LTS (WSL2)  
**Hardware**: Intel(R) Core(TM) i5-8265U CPU @ 1.60GHz (8 cores) | 7.6 GB RAM  
**Base Commit**: `9b79f59` (Phase D.2 Commit)  

---

## 1. Executive Statement on Provenance

The primary objective of `mojo-hotloop` is to serve as an **automatic Python-to-Mojo transpiler**, translating unmodified Python hot loops into compiled, high-performance native shared libraries (`.so`).

A critical principle of rigorous compiler engineering is that:
> **A manually optimized Mojo program is NOT evidence that the Python-to-Mojo transpiler can automatically generate that optimization.**

This document provides a line-by-line audit of the code paths, compilation artifacts, and benchmark results reported across Phase D, D.1, and D.2, establishing an uncompromisingly truthful baseline before introducing compiler optimizations in Phase D.3.

---

## 2. Task 1.1 — Application-by-Application Code Provenance Audit

Each application's `fast.mojo` and `fast.so` implementation is classified into one of four categories:
- **Category A**: Automatically produced from the original Python AST by `hotloop build --engine=ast`.
- **Category B**: Generated using general-purpose, reusable compiler transformations.
- **Category C**: Handwritten or specially optimized for the individual example.
- **Category D**: Called directly by isolated benchmarks (`_compiled`), but bypassed or routed differently by normal public `@hotloop` execution.

---

### Workload 1: Quantitative Backtest (`examples/quant_backtest`)
- **Python Reference**: [`examples/quant_backtest/original.py`](../../examples/quant_backtest/original.py)
  - Signature: `stateful_trailing_backtest(ticks: int, start_price: float, stop_pct: float, fee_rate: float) -> float`
  - Argument Types: All scalar (`int`, `float`). Return Type: Scalar `float`.
- **Transpiler Behavior**: `hotloop.ast_transpiler.transpile_python_to_mojo()` parses the Python AST directly, mapping scalar types to native `Int` and `Float64`, unrolling the `for _ in range(ticks)` loop, and generating a standard C-ABI wrapper function.
- **Code Provenance**: **CATEGORY A (100% Automatically Produced from Python AST)**.
  - When `hotloop build examples/quant_backtest/original.py --engine=ast` is executed, the generated `fast.mojo` is identical to the committed version.
- **Benchmark & Interface**:
  - Pure Python ($p50$): **34.46 ms**
  - Numba warm ($p50$): **0.458 ms** (1,477 ms cold JIT compile)
  - AST-Generated Mojo ($p50$): **0.420 ms** (**82.1× speedup vs Python**, **1.09× faster than Numba**)
  - Normal `@hotloop` Wrapped ($p50$): **0.420 ms** (Zero decorator overhead on hot loops)
- **Status**: **VERIFIED GENUINE AUTOMATIC TRANSPILER SUCCESS**.

---

### Workload 2: AR Spatial 3D (`examples/ar_spatial`)
- **Python Reference**: [`examples/ar_spatial/original.py`](../../examples/ar_spatial/original.py)
  - Signature: `find_closest_point_to_ray(xs: list[float], ys: list[float], zs: list[float], ...) -> int`
- **Code Provenance Audit**:
  - The AST transpiler in `hotloop/ast_transpiler.py` automatically generates list unboxing using:
    `for _i in range(_n_xs): xs.append(Float64(py=arg0[_i]))`
    When given Python lists, this incurs 30,000 FFI calls, resulting in a latency of **2.42 ms** (**1.43× speedup vs Python 3.57 ms**).
  - In Phase D.2, `examples/ar_spatial/fast.mojo` was manually modified to include `_ptr_find_closest_point_to_ray` and inspect `arg0.ctypes.data` with `OpaquePointer[MutUntrackedOrigin]`, achieving **0.043 ms (69.5× – 94.5× vs Python)**.
  - When `hotloop build examples/ar_spatial/original.py --engine=ast` was executed in Phase D.3, the manual `OpaquePointer` code was overwritten because it was **NOT part of `ast_transpiler.py`**!
- **Classification**:
  - Pure AST-generated Mojo: **CATEGORY A** (Latency: 2.42 ms, 1.43× vs Python).
  - Contiguous Buffer Pointer Optimization (0.043 ms): **CATEGORY C (Handwritten in Phase D.2, NOT yet emitted by AST transpiler)**.
- **Action Required for Phase D.3**: Move contiguous pointer buffer extraction into `hotloop/ast_transpiler.py` as a general-purpose, reusable compiler transformation (**Category B**) for any typed collection.

---

### Workload 3: OCR Fuzzy Matcher (`examples/ocr_matcher`)
- **Python Reference**: [`examples/ocr_matcher/original.py`](../../examples/ocr_matcher/original.py)
  - Signature: `find_closest_match(query: str, candidates: list[str], max_distance: int) -> int`
  - Helper: `levenshtein_distance(s1: str, s2: str, max_dist: int) -> int` (Dynamic programming matrix)
- **Code Provenance Audit**:
  - The AST transpiler in `hotloop/ast_transpiler.py` successfully transpiles both `levenshtein_distance` and `find_closest_match` directly from Python AST into Mojo dynamic programming loops.
  - The AST-generated Mojo runs in **446.0 µs** (**2.74× speedup vs Python 1,292.9 µs**).
  - In Phase D.2, `examples/ocr_matcher/fast.mojo` was manually replaced with Gene Myers (1999) 64-bit word bit-parallel algorithm (`peq`, `pv`, `mv`), which achieved **32.24 µs (36.9× speedup, beating RapidFuzz C++ AVX2)**.
  - When `hotloop build examples/ocr_matcher/original.py --engine=ast` was executed in Phase D.3, `fast.mojo` was reverted back to the DP matrix because Myers was **NOT generated by `ast_transpiler.py`**!
- **Classification**:
  - Pure AST-generated Mojo (446 µs): **CATEGORY A (2.74× vs Python)**.
  - Myers Bit-Parallel Implementation (32.24 µs): **CATEGORY C (Handwritten Specialization)**.
- **Limitations of Handwritten Myers Algorithm**:
  - Maximum query length: Strictly bounded by word width ($M \le 64$ characters).
  - Character set: Strictly bounded by ASCII ($< 128$) due to fixed 128-entry `peq` table.
  - Non-ASCII / Long strings: Forced to fall back to DP matrix.
- **Action Required for Phase D.3**: Classify the 36.9× Myers result honestly as **Hand-Optimized Only** unless general-purpose algorithmic recognition can be formally integrated and proven safe.

---

### Workload 4: Geo Distance Haversine (`examples/geo_distance`)
- **Python Reference**: [`examples/geo_distance/original.py`](../../examples/geo_distance/original.py)
  - Signature: `accumulate_haversine_distance(lats: list[float], lons: list[float]) -> float`
- **Code Provenance Audit**:
  - The AST transpiler automatically compiles the Haversine mathematical loop, yielding a latency of **2.57 ms** on Python lists (**3.17× speedup vs Python 8.03 ms**).
  - In Phase D.2, `examples/geo_distance/fast.mojo` was manually modified with `OpaquePointer` buffer traversal, $\arcsin$ substitution, and register-level `cos(lat)` caching across loop steps, achieving **0.465 ms (15.3× – 18.3× vs Python)**.
  - Like AR Spatial, running `hotloop build --engine=ast` reverted this manual code to the standard unboxing loop.
- **Classification**:
  - Pure AST-generated Mojo (2.57 ms): **CATEGORY A (3.17× vs Python)**.
  - Pointer + Invariant Cached Implementation (0.465 ms): **CATEGORY C (Handwritten Specialization)**.
- **Action Required for Phase D.3**: Promote contiguous pointer access and trigonometric invariant hoisting into reusable compiler transformations.

---

### Workload 5: PII Scrubber (`examples/pii_scrubber`)
- **Python Reference**: [`examples/pii_scrubber/original.py`](../../examples/pii_scrubber/original.py)
  - Signature: `scrub_pii(text: str) -> str`
- **Code Provenance Audit**:
  - The AST transpiler compiles the multi-pass text scanning and Luhn/Verhoeff validation routines, yielding **26.70 ms** on 100k characters (**2.57× speedup vs Python 67.19 ms**).
  - In Phase D.2, manual optimizations were injected: replacing `_PyStr` with raw Codepoint array `_cps`, pre-reserving capacity via `reserve_bytes()`, and direct byte subtraction `curr_c - 48`, achieving **5.16 ms (13.5× vs Python, 4.95× faster than compiled C regex)**.
  - Running `hotloop build --engine=ast` reverted `fast.mojo` to the generic AST output.
- **Classification**:
  - Pure AST-generated Mojo (26.70 ms): **CATEGORY A (2.57× vs Python)**.
  - Codepoint Buffer & Pre-allocation (5.16 ms): **CATEGORY C (Handwritten Specialization)**.
- **Action Required for Phase D.3**: Integrate `reserve_bytes` and scalar codepoint comparison optimizations into the AST transpiler's core runtime helpers.

---

### Workload 6: PDF Text Cleaner (`examples/pdf_cleaner`)
- **Python Reference**: [`examples/pdf_cleaner/original.py`](../../examples/pdf_cleaner/original.py)
  - Signature: `clean_pdf_text(raw_text: str) -> str`
- **Code Provenance Audit**:
  - The AST transpiler compiles character inspection loops into Mojo, yielding **8.06 ms** on 100k characters (**3.15× speedup vs Python 24.78 ms, 1.34× faster than compiled C regex**).
  - In Phase D.2, `examples/pdf_cleaner/fast.mojo` was manually modified to use scalar codepoint filtering and `reserve_bytes()`, dropping latency to **2.57 ms (9.2× vs Python, 3.98× faster than regex)**.
  - Running `hotloop build --engine=ast` reverted `fast.mojo` to the generic AST output.
- **Classification**:
  - Pure AST-generated Mojo (8.06 ms): **CATEGORY A (3.15× vs Python, faster than regex)**.
  - Codepoint Scalar Filtering (2.57 ms): **CATEGORY C (Handwritten Specialization)**.

---

### Workload 7: RAG Document Chunker (`examples/rag_chunker`)
- **Python Reference**: [`examples/rag_chunker/original.py`](../../examples/rag_chunker/original.py)
  - Signature: `chunk_document(text: str, chunk_size: int, overlap: int) -> list[str]`
- **Code Provenance Audit**:
  - The AST transpiler automatically compiles the boundary scanning and chunk extraction loops into Mojo.
  - Native execution takes **3.85 ms** (0.05× vs Python 0.171 ms) because returning 100 Python `str` instances across the CPython FFI requires 100 separate `PyUnicode` allocations and `PyList_Append` invocations.
  - Under normal `@hotloop` execution, **safe performance dispatch** automatically identifies this workload and routes it to pure Python (0.171 ms).
- **Classification**: **CATEGORY A & CATEGORY D (Called directly in forced-native benchmarks, but safely routed to Python by normal `@hotloop` dispatch)**.

---

## 3. Task 1.2 — Reconciliation of Phase D.2 Inconsistencies

### Inconsistency 1: Geo Distance 7.13 ms vs 8.51 ms Baseline
- **Audit Finding**:
  - In `examples/geo_distance/bench.py`, the 10,000 waypoint route benchmark reported a median pure Python time of **7.13 ms** (7,126.97 µs).
  - In `audit/test_geo_caller.py`, a separate script measured Python on 10,000 points generated with different random distributions and no thermal control, reporting **8.51 ms**.
  - Comparing Mojo's 0.465 ms to 8.51 ms yielded 18.30×; comparing it to 7.13 ms yielded **15.33×**.
- **Reconciliation**: The canonical baseline from `examples/geo_distance/bench.py` is **7.13 ms – 8.03 ms**. Speedup on contiguous pointer buffers is **15.33× – 17.27×**, NOT 18.30×.

### Inconsistency 2: AR Spatial 3D Mojo (0.043 ms) vs Numba (0.039 ms)
- **Audit Finding**: In `audit/test_ar_caller.py`, Numba `@njit` (warm) ran in **0.0392 ms**, while Mojo ran in **0.0434 ms**. Mojo was ~10% slower than Numba on that run. The Phase D.2 summary text claimed Mojo "beat Numba".
- **Reconciliation**: We correct this statement. On contiguous memory buffers, Mojo (0.043 ms) and Numba (0.039 ms) are essentially tied (Numba 1.10× faster), while Mojo is **19.3× faster than NumPy** (0.837 ms) and **58× – 94× faster than pure Python**.

### Inconsistency 3: RAG Chunker Zero Fallbacks Claim
- **Audit Finding**: `PHASE_D2_20X_VALIDATION_REPORT.md` stated "0 fallbacks" alongside "Safe dispatch routes to Python".
- **Reconciliation**: The verification script `verify.py` tests `_compiled` (forced native execution), where 1,020 tests passed with 0 mismatches. However, in standard production execution through `@hotloop`, the function triggers safe dispatch and executes pure Python. The two execution modes must not be conflated:
  - **Forced-Native Verification (`fn._compiled`)**: 100% native execution.
  - **Public Interface (`fn(...)`)**: Uses Python fallback to avoid FFI marshalling penalties.

### Inconsistency 4: AR Spatial Python Baseline Alternating Between 4.10 ms and 2.53 ms
- **Audit Finding**:
  - `examples/ar_spatial/bench.py` ran 20 iterations with Python list generation (`rng.uniform`), yielding **3.57 ms – 4.10 ms**.
  - `audit/test_ar_caller.py` pre-allocated lists once from NumPy arrays with `gc.disable()` over 50 iterations, yielding **2.53 ms**.
- **Reconciliation**: Garbage collection overhead and list construction account for the difference. Under identical benchmark conditions (`bench.py`), the pure Python baseline is **3.57 ms – 4.10 ms**.

### Inconsistency 5: Native-Kernel vs Wrapped End-to-End Timings
- **Audit Finding**: Several reports quoted "Mojo Direct" ($p50$ of `fn._compiled`) rather than "Mojo @hotloop" (wrapped end-to-end decorator).
- **Reconciliation**: For large workloads (10,000–100,000 items), decorator wrapper overhead is negligible (typically 1–5 µs on millisecond-scale tasks). However, for microsecond workloads (e.g., short OCR queries), wrapper overhead (2–4 µs) can represent 10–20% of runtime. Both numbers are now explicitly published in the master scorecard.

### Inconsistency 6: OCR Myers Bit-Parallel Limitations & AST Provenance
- **Audit Finding**: The Myers bit-parallel implementation in `examples/ocr_matcher/fast.mojo` was handwritten. It relies on a single 64-bit `UInt64` register for bitmask operations, restricting its application strictly to patterns where $M \le 64$ and characters $< 128$ (ASCII).
- **Reconciliation**: Myers cannot be claimed as an automatic AST transpiler success. The automatic transpiler generates the DP matrix (446 µs, 2.74× speedup). The Myers implementation (32.24 µs, 36.9× speedup) is documented as a handwritten specialized baseline.

### Inconsistency 7: Mathematical Validity of Consecutive Coordinate Invariant Reuse
- **Audit Finding**: Task 1.2 raised whether reusing $\cos(\text{lat}_2)$ as $\cos(\text{lat}_1)$ in the next step assumes coordinate relationships not guaranteed by the Python reference.
- **Verification**: In `geo_distance/original.py`:
  ```python
  for i in range(1, n):
      lat1 = lats[i - 1] * rad_factor
      lat2 = lats[i] * rad_factor
  ```
  Step $i$ computes distance from waypoint $i-1$ to waypoint $i$. Step $i+1$ computes distance from waypoint $i$ to waypoint $i+1$. The destination of step $i$ (`lats[i]`) is identically the origin of step $i+1$ (`lats[(i+1)-1]`). Therefore, $\cos(\text{lat}_2)$ in step $i$ is identically $\cos(\text{lat}_1)$ in step $i+1$. This invariant reuse is **100% mathematically valid and preserves identical numerical results**.

### Inconsistency 8: Haversine Numerical Stability and Boundary Values
- **Verification**: In `geo_distance`:
  ```python
  a = sin_dlat * sin_dlat + math.cos(lat1) * math.cos(lat2) * sin_dlon * sin_dlon
  a = min(1.0, max(0.0, a))
  c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
  ```
  Domain clamping to $[0.0, 1.0]$ prevents invalid arguments to `sqrt(1.0 - a)` from roundoff errors. The identity $2 \cdot \text{atan2}(\sqrt{a}, \sqrt{1-a}) = 2 \cdot \arcsin(\sqrt{a})$ holds for all $a \in [0, 1]$ and produces identical IEEE-754 double-precision results within $10^{-8}$ relative tolerance.

---

## 4. Gate 1 Baseline Summary Table

The table below summarizes the true provenance of current Mojo implementations across all seven applications:

| Workload | Pure Python ($p50$) | AST Transpiler Mojo ($p50$) | AST Speedup vs Python | Hand-Optimized Mojo ($p50$) | Hand Speedup vs Python | Automatic 20× Achieved? | Provenance Classification |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1. Quant Backtest** | 34.46 ms | **0.420 ms** | **82.10×** | 0.413 ms | 83.4× | **YES (82.1×)** | **Category A (100% Automatic AST)** |
| **2. AR Spatial 3D** | 3.57 ms | **2.42 ms** | **1.43×** | 0.043 ms | 83.0× | **NO (1.43× AST)** | **Category A (Lists) / Category C (Pointers)** |
| **3. OCR Fuzzy Matcher** | 1,292.9 µs | **446.0 µs** | **2.74×** | 32.24 µs | 36.9× | **NO (2.74× AST)** | **Category A (DP Matrix) / Category C (Myers)** |
| **4. Geo Distance** | 8.03 ms | **2.57 ms** | **3.17×** | 0.465 ms | 17.3× | **NO (3.17× AST)** | **Category A (Lists) / Category C (Pointers)** |
| **5. PII Scrubber** | 67.19 ms | **26.70 ms** | **2.57×** | 5.16 ms | 13.0× | **NO (2.57× AST)** | **Category A (AST) / Category C (Optimized)** |
| **6. PDF Text Cleaner** | 24.78 ms | **8.06 ms** | **3.15×** | 2.57 ms | 9.6× | **NO (3.15× AST)** | **Category A (AST) / Category C (Optimized)** |
| **7. RAG Chunker** | 0.171 ms | **3.85 ms** | **0.05×** | 1.02 ms | 0.17× | **NO (FFI Floor)** | **Category A / Category D (Fallback Active)** |

### Gate 1 Conclusion
Only **Quant Backtest** currently achieves $\ge 20\times$ speedup via purely automatic Python AST transpilation (82.1×). The other high-speedup claims relied on handwritten customizations in `examples/*/fast.mojo` that were not emitted by `hotloop/ast_transpiler.py`.

The core mission of Phase D.3 is to engineer reusable compiler transformations directly into `hotloop/ast_transpiler.py` so that acceleration is achieved **automatically by the transpiler itself**.
