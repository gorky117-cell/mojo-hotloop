# Mojo Hotloop Benchmark Report (Canonical Dataset v0.1.0)

## System Environment & Provenance
- **Dataset Version**: v0.1.0 (Canonical)
- **Baseline Git Commit**: `5de730c691cecd8a6e582ba61b8251ccc2f999ca`
- **CPU**: Intel(R) Core(TM) i5-8265U CPU @ 1.60GHz
- **RAM**: 7.63 GiB
- **Operating System**: Ubuntu 24.04 LTS (WSL2 on Windows 11, kernel 6.6.87.2-microsoft-standard-WSL2)
- **Python Version**: CPython 3.12.16 (Clang 23.1.3)
- **Mojo Version**: Mojo 1.2.0 (2016d0cd)
- **Toolchain Competitors**:
  - Numba: 0.68.1
  - NumPy: 2.5.4
  - RapidFuzz: 3.14.6
  - Codon JIT: 0.17.0 / 0.20.6
  - Codon Native: 0.17.0 / 0.20.6

## Primary Benchmark Matrix
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

## Workload Notes & Detailed Timings

### 1. Quantitative Backtest (100k ticks)
- **Pure Python 3.12**: 38.1521 ms (p95: 39.8520 ms, mean: 37.4889 ms, stdev: 1.8549 ms)
- **Numba `@njit`**: 0.5666 ms (p95: 0.5759 ms, mean: 0.5647 ms)
- **Codon JIT**: 0.4642 ms
- **Mojo Direct C-ABI**: 0.5636 ms
- **Mojo `@hotloop`**: 0.5502 ms (p95: 0.5621 ms, mean: 0.5486 ms)
- **Speedup vs Python**: **69.34×**
- **Analysis**: Mojo @hotloop and Numba are within a 3% provisional margin of error (0.550 ms vs 0.567 ms), representing broadly comparable performance on this stateful scalar loop. Codon JIT is slightly faster (0.464 ms).

### 2. AR Spatial 3D (10k vertices)
- **Pure Python**: 3.7947 ms
- **Mojo `@hotloop` (ndarray pointer)**: 0.1137 ms (**33.36× vs Python**)
- **Competitors**: Numba (0.0711 ms) and Codon Native (0.0511 ms) are faster than Mojo Hotloop due to LLVM SIMD autovectorization. Codon JIT is 0.1500 ms.

### 3. Geo Distance (10k waypoints)
- **Pure Python**: 11.0586 ms
- **Mojo `@hotloop` (ndarray pointer)**: 1.1357 ms (**9.74× vs Python**)
- **Competitors**: NumPy vectorized SIMD transcendentals (0.9004 ms) and Codon Native (0.8736 ms) outperform Mojo Hotloop by ~26%.

### 4. Text Processing (PDF Cleaner & PII Scrubber)
- **PDF Cleaner**: Mojo 4.691 ms vs Regex 11.931 ms (**2.54× faster than Regex**, **6.20× vs Python**).
- **PII Scrubber**: Mojo 15.328 ms vs Regex 26.685 ms (**1.74× faster than Regex**, **4.96× vs Python**).
- **Codon Comparison**: Codon JIT encounters $O(N^2)$ string concatenation overhead on large documents (7.7s and 12.3s), where Mojo Hotloop's `_PyStr` linear ASCII buffer completes in 4.7 ms and 15.3 ms.

### 5. Transparent Safety Fallback (OCR Matcher & RAG Chunker)
- **OCR Matcher**: Small collection conversion overhead leads default mode to execute pure Python (2.382 ms vs 2.331 ms). Forced native achieves 0.653 ms (3.57× vs Python). RapidFuzz C++ is fastest at 0.514 ms.
- **RAG Chunker**: Returning `list[str]` forces C-API allocation of thousands of Python string objects; forced native is 4.009 ms (~21× slower than Python's 0.193 ms). Mojo Hotloop detects collection return and safely routes to pure Python (0.191 ms), preventing performance regressions.
