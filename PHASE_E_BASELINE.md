# Phase E Baseline Reproduction Report (v0.2.0 Pre-Optimization)

**Date**: 2026-11-17  
**Branch**: `feat/phase-e-v0.2.0`  
**Git Commit SHA**: `07d5938a31a4002cb43b34b78ad9ab7147699038`  
**Base Tag / Frozen Reference**: `v0.1.0` (`b7d587e` / `5de730c691cecd8a6e582ba61b8251ccc2f999ca`)  

---

## 1. Environment & Hardware Specifications

- **CPU**: Intel(R) Core(TM) i5-8265U CPU @ 1.60GHz (4 physical cores, 8 logical threads, 6 MiB L3 cache)
- **RAM**: 7.63 GiB Total (7.0 GiB available)
- **OS / Kernel**: Ubuntu 24.04 LTS on Windows 11 (WSL2, kernel `6.6.87.2-microsoft-standard-WSL2`)
- **Python**: CPython 3.12.16 (Clang 23.1.3, via uv venv `/home/gaurav/mojo-hotloop/.venv`)
- **Mojo**: Mojo 1.2.0 (2016d0cd)
- **Numba**: 0.68.1
- **NumPy**: 2.5.4
- **RapidFuzz**: 3.14.6
- **Regex**: Python 3.12 standard library `re`

---

## 2. Methodology

- **Timing Boundary**: Call-site invocation of decorated `@hotloop` callable to return value, capturing cache lookup, dispatch qualification, C-ABI parameter marshalling, native Mojo kernel execution, and result unboxing.
- **Metric**: Median (p50) latency across 5 batched trials with garbage collection disabled (`gc.disable()`). Warmup performed prior to measurement.
- **Parity Verification**: Absolute tolerance $\le 10^{-6}$ for floating point results; exact equality (`==`) for integer, boolean, string, and list results.

---

## 3. Reproduced Baseline Measurements (7 Canonical Workloads)

| Workload | Dataset / Size | CPython p50 (ms) | Mojo Direct p50 (ms) | @hotloop p50 (ms) | Active Dispatch Mode | Speedup vs CPython | Correctness Verified |
|---|---|---|---|---|---|---|---|
| **Quant Backtest** | 100k ticks | 49.9891 | 0.7088 | 0.7111 | **Native** | **70.30×** | **TRUE** |
| **AR Spatial 3D** | Small (100 pts) | 0.0438 | 0.0401 | 0.0442 | Native | 0.99× | TRUE |
| | Medium (1,000 pts) | 0.3700 | 0.0416 | 0.0458 | Native | 8.09× | TRUE |
| | Large (10,000 pts) | 3.4287 | 0.0732 | 0.0786 | **Native** | **43.59×** | **TRUE** |
| **Geo Distance** | Short (100 pts) | 0.0770 | 0.0449 | 0.0510 | Native | 1.51× | TRUE |
| | Medium (1,000 pts) | 0.7188 | 0.0991 | 0.1088 | Native | 6.60× | TRUE |
| | Large (10,000 pts) | 6.6099 | 0.8872 | 0.9466 | **Native** | **6.98×** | **TRUE** |
| **PDF Text Cleaner** | Small (241 chars) | 0.3494 | 0.0412 | 0.0434 | Native | 8.05× | TRUE |
| | Medium (2,410 chars) | 3.7274 | 0.4352 | 0.4508 | Native | 8.27× | TRUE |
| | Large (24,100 chars) | 30.7186 | 3.9980 | 4.1316 | **Native** | **7.44×** | **TRUE** |
| **PII Scrubber** | Short (110 chars) | 0.0282 | 0.0076 | 0.0089 | Native | 3.16× | TRUE |
| | Medium (10,890 chars) | 5.3019 | 0.7420 | 0.7650 | Native | 6.93× | TRUE |
| | Large (108,900 chars) | 64.2215 | 9.0711 | 9.3138 | **Native** | **6.90×** | **TRUE** |
| **OCR Matcher** | Small (50 cands) | 0.1258 | 0.0204 | 0.1248 (def) / 0.0224 (forced) | Fallback (def) / Native (forced) | 1.01× (def) / **5.61×** (forced) | **TRUE** |
| | Medium (500 cands) | 1.4138 | 0.2011 | 1.2534 (def) / 0.2126 (forced) | Fallback (def) / Native (forced) | 1.13× (def) / **6.65×** (forced) | **TRUE** |
| | Large (1,000 cands) | 2.1996 | 0.5891 | 2.3292 (def) / 0.6090 (forced) | Fallback (def) / Native (forced) | 0.94× (def) / **3.61×** (forced) | **TRUE** |
| **RAG Chunker** | Small (300 chars) | 0.0043 | 0.0350 | 0.0091 (def) / 0.0381 (forced) | Fallback (def) / Native (forced) | 0.48× (def) / 0.11× (forced) | **TRUE** |
| | Medium (2,900 chars) | 0.0271 | 0.3712 | 0.0308 (def) / 0.3940 (forced) | Fallback (def) / Native (forced) | 0.88× (def) / 0.07× (forced) | **TRUE** |
| | Large (29,000 chars) | 0.1642 | 3.3980 | 0.1803 (def) / 3.5109 (forced) | Fallback (def) / Native (forced) | 0.91× (def) / 0.05× (forced) | **TRUE** |

---

## 4. Comparison to v0.1.0 Frozen Baseline

| Workload | v0.1.0 Speedup | Current Reproduced Speedup | Status | Notes |
|---|---|---|---|---|
| Quant Backtest | 69.34× | 70.30× | Native | Highly consistent across runs |
| AR Spatial 3D (Large) | 33.36× | 43.59× | Native | Solid improvement with numpy ndarray pointers |
| Geo Distance (Large) | 9.74× | 6.98× | Native | Trigonometric operations bottleneck in Haversine |
| PDF Text Cleaner (Large) | 6.20× | 7.44× | Native | Single-pass string builder in Mojo |
| PII Scrubber (Large) | 4.96× | 6.90× | Native | Myers diff & Verhoeff checksum |
| OCR Fuzzy Matcher (Large) | 0.98× (Fallback) | 0.94× (Fallback) / 3.61× (Forced) | Fallback (Default) | Dispatched to fallback due to `list[str]` input heuristic |
| RAG Chunker (Large) | 1.01× (Fallback) | 0.91× (Fallback) / 0.05× (Forced) | Fallback (Default) | `list[str]` return type boxing overhead |

---

## 5. Key Findings for Phase E Optimization

1. **OCR Matcher is an immediate low-hanging fruit**: Forced native Mojo already runs at **3.61×–6.65×** speedup. The fallback heuristic in `_is_slower_workload` was over-conservative by rejecting all `list` arguments even when the function is read-only and returns a scalar `int`. Fixing the dispatch qualification will unlock instant 3.6×+ native gains for OCR without changing any kernel code.
2. **Geo Distance Haversine Loop**: The loop performs repetitive radian conversions and transcendental functions (`math.sin`, `math.cos`, `math.atan2`). Constant propagation and loop-invariant hoisting will reduce per-iteration CPU work.
3. **AR Spatial & Geo Distance**: ndarray passing currently relies on numpy pointer conversion. Contiguous ndarray specialization with direct raw buffer pointer passing eliminates C-ABI marshalling overhead.
4. **String Operations (PDF & PII)**: UTF-8 / ASCII fast path and avoiding intermediate allocations will speed up text scanning loops.
5. **RAG Chunker Architectural Limit**: Native string boxing (`List[String]` -> Python `list[str]`) requires constructing individual Python string objects for every chunk, which is $20\times$ slower than CPython's native slice allocation. An offset-based API (`chunk_document_offsets`) returning `(List[Int], List[Int])` will allow zero-copy reconstruction in Python.
