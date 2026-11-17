# Phase E Profiling Report: Dispatch Latency & Execution Breakdown

**Date**: 2026-11-17  
**Branch**: `feat/phase-e-v0.2.0`  
**Tool**: `benchmarks/profile_dispatch.py`  
**Environment**: Ubuntu 24.04 (WSL2), Python 3.12.16, Mojo 1.2.0  

---

## 1. Executive Summary

We instrumented `@hotloop` decorator invocation and execution across all 7 canonical workloads to measure the time spent in:
1. **Cache / Staleness verification** (`os.path.getmtime` / SHA-256 checks)
2. **Dispatch Qualification** (`_is_slower_workload`, inspect signature, surrogate verification)
3. **C-ABI Parameter Marshalling & Native Kernel** (`_compiled(*args)`)
4. **Return Value Boxing & Output Reconstruction**

---

## 2. Profiling Data Matrix

| Workload | Dataset | Total @hotloop ($\mu$s) | Native Kernel $\_compiled$ ($\mu$s) | Pure Python $\_original$ ($\mu$s) | Dispatch Overhead ($\mu$s) | Dispatch Overhead (%) | Dominant Bottleneck |
|---|---|---|---|---|---|---|---|
| **Quant Backtest** | 100k ticks | 573.28 | 467.48 | 37,004.91 | 105.80 | 18.46% | Mojo integer arithmetic & loop branch |
| **AR Spatial 3D** | 10k points | 163.44 | 120.05 | 21,193.05 | 43.38 | 26.54% | Array indexing bounds check + float math |
| **Geo Distance** | 10k points | 906.53 | 898.52 | 14,682.90 | 8.01 | 0.88% | Transcendental math (`sin`, `cos`, `atan2`) |
| **PDF Text Cleaner** | 24.1k chars | 3,636.91 | 3,230.95 | 28,646.87 | 405.96 | 11.16% | UTF-8 scanning & string concatenation |
| **PII Scrubber** | 108.9k chars | 10,388.12 | 9,051.07 | 57,742.69 | 1,337.05 | 12.87% | Myers diff & Verhoeff nested loops |
| **OCR Matcher** | 1,000 cands | 683.22 | 635.37 | 2,151.47 | 47.85 | 7.00% | Levenshtein DP matrix allocations |
| **RAG Chunker** | 29k chars | 4,476.45 | 3,517.98 | 156.19 | 958.47 | 21.41% | `List[String]` $\to$ Python `list[str]` boxing |

---

## 3. Component Latency Analysis

Isolated component microbenchmarking ($N=10,000$ iterations):

| Dispatch Component | Median Cost (ns) | Analysis & Impact |
|---|---|---|
| **Argument count / keyword binding check** | ~25–31 ns | Negligible. Fast path avoids `inspect.Signature.bind()`. |
| **Dispatch Qualification (`_is_slower_workload`)** | ~400–1,780 ns | Iterates through input arguments checking `isinstance(a, (list, set))`. Overly conservative: blocks OCR matcher from native execution. |
| **Surrogate Codepoints Check** | ~350–5,000 ns | Scales with length of string inputs (`a.isascii()` check). For large strings (PDF, PII, RAG), takes ~3–5 $\mu$s. |
| **Filesystem Stale Check (`os.path.getmtime`)** | ~2,200–3,100 ns | System call overhead in WSL2. Throttled by default (`check_interval=0.02s`), but when fired adds ~2.5 $\mu$s. |

---

## 4. Workload Bottlenecks & Optimization Opportunities

### 4.1 Numerical & Spatial (Quant, AR Spatial, Geo Distance)
- **Bottleneck**: In Geo Distance, Haversine computes constant conversions (`rad_factor = 3.141592653589793 / 180.0`) inside the loop, and evaluates `sin`, `cos` redundantly.
- **Opportunity**:
  - **Loop-invariant hoisting**: Precompute invariant expressions outside loop bodies.
  - **Constant propagation**: Fold constant math expressions at transpile time.
  - **Redundant bounds-check elimination**: In range loops (`for i in range(1, n)`), array access `arr[i]` and `arr[i-1]` is provably in-bounds. Emit unchecked pointer dereferencing (`[unsafe_offset=...]`).
  - **Contiguous ndarray specialization**: Ensure direct raw pointer pass-through without copying.

### 4.2 Text & String Scanning (PDF Cleaner, PII Scrubber)
- **Bottleneck**: Character-by-character string iteration decodes UTF-8 codepoints one by one. In PDF Cleaner and PII, repeated string concatenation or dynamic string buffer growth triggers reallocation.
- **Opportunity**:
  - **ASCII fast path**: When scanning ASCII text, use direct byte-level pointer iteration (`s._as_ptr()` / byte indexing) without codepoints iterator overhead.
  - **String buffer pre-allocation**: Detect `result = ""; for ...: result += ...` and pre-allocate or reserve buffer capacity to eliminate $O(N^2)$ reallocations.

### 4.3 Dispatch & FFI (OCR Matcher, RAG Chunker)
- **Bottleneck**:
  - `_is_slower_workload()` in `hotloop/decorator.py` rejects ANY function with a `list` argument, forcing OCR Matcher into Python fallback despite native being **3.61× faster**.
  - RAG Chunker returns `list[str]`. In Mojo, creating a Python `list` of `str` requires boxing every string slice through `PythonObject(s)`, which is $22\times$ slower than Python's in-memory string slicing.
- **Opportunity**:
  - **Smart Dispatch**: Qualify functions with `list` input as native if the return type is NOT a list (i.e. scalar return like `int`, `float`, `bool`), and cache dispatch decisions in `dispatch_qualifier_cache`.
  - **Zero-copy Offset Chunking**: Provide an offset-based API `chunk_document_offsets` returning integer slice boundaries `(List[Int], List[Int])` so Python reconstructs slices zero-copy.
