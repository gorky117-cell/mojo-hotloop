# Mojo Hotloop v0.2.0 Release Notes
## Developer Preview — General Optimization Passes, Syntax Expansion & Subprocess Isolation

**Release Tag:** `v0.2.0` (Release Candidate)  
**Release Date:** November 17, 2026  
**License:** Apache License 2.0  
**Classification:** Open-Source Developer Preview  
**Target Platform:** Linux x86-64 / Ubuntu 24.04 LTS (WSL2 / Bare Metal), CPython 3.12, Mojo 1.2.0  

---

## 1. What Is New in v0.2.0

### 1.1 Five General Compiler Optimization Passes
Mojo Hotloop v0.2.0 introduces five reusable, syntax-driven AST optimization passes. These passes operate on general Python AST patterns without benchmark-specific heuristics or function-name matching:

1. **Redundant Bounds-Check Elimination & In-Bounds Hoisting:** Loop iterations over proven ranges `range(len(arr))` bypass redundant runtime bounds checks, compiling to direct pointer dereferences.
2. **Loop-Invariant Expression Hoisting (`_collect_and_hoist_invariants`):** Subexpressions inside loop bodies that depend exclusively on variables unmodified within the loop (e.g. `1.0 - fee_rate`, `1.0 - stop_pct`, `1.0 / float(w)`) are automatically lifted above the loop header.
3. **String Buffer Pre-Allocation (`reserve_bytes`):** Output string allocations derived from input text lengths pre-allocate memory in native string buffers, eliminating geometric reallocations.
4. **Fast Codepoint & Ordinal Access (`_PyStr`, `get_cp_fast`, `get_ord_fast`):** Implements a dedicated `_PyStr` struct enabling single-byte indexing for ASCII text while preserving negative indexing and UTF-8 multi-byte decoding semantics.
5. **Dispatch Qualifier Caching & Smart Fallback:** Input argument types, shapes, and qualifiers are cached in `_DISPATCH_QUALIFIER_CACHE`. The decorator detects when per-element FFI object conversion would exceed execution time (e.g. returning large collections of strings) and automatically executes pure Python fallback.

### 1.2 Python Syntax Expansions
- **`break` Statement Support:** Loop `break` statements are now fully supported with correct lexical scoping and invariant preservation.
- **Negative String Indexing:** Negative indices on strings (`s[-i]`) compile to direct reverse codepoint indexing matching Python semantics.
- **Zero-Copy Offset Chunking API (`chunk_document_offsets`):** Provides an experimental zero-copy API returning paired integer slice boundaries `[start0, end0, start1, end1, ...]` for document chunking, eliminating FFI string boxing overhead.

### 1.3 Diagnostics & Telemetry
- **Public `inspect_dispatch(fn)` API:** Allows developers to inspect dispatch status, execution backend, native call counts, fallback call counts, and qualification diagnostics directly from Python.

### 1.4 Subprocess Environment Isolation & Pytest Unification
- **Environment Sanitization:** Resolved a critical issue where Mojo 1.2.0 C-runtime initialization during `dlopen` mutated `PYTHONEXECUTABLE` in the host process. `hotloop` now preserves and restores environment variables around native module execution, ensuring child processes and virtualenv tools execute without `ModuleNotFoundError`.
- **Unified Test Workflow:** All 86 project tests now run together reliably in a single standard `pytest tests/` invocation.

---

## 2. What Was Verified

Every claim in v0.2.0 is supported by reproducible engineering evidence:

- **7,220 Application Checks Verified:** All 7 canonical business domains passed with 100% mathematical and string parity (0 mismatches, 0 errors across 538,662 data points):
  - Quantitative Backtest: 1,117 checks
  - AR Spatial 3D: 1,010 checks
  - Geo Distance: 1,014 checks
  - OCR Matcher: 1,020 checks
  - PDF Cleaner: 1,020 checks
  - PII Scrubber: 1,019 checks
  - RAG Chunker: 1,020 checks
- **86 Pytest Tests:** 100% pass rate in a single command (`pytest tests/ -q`).
- **77 Unfamiliar Functions:** 77 diverse, unseen functions (52 in Phase E.6 + 25 in Phase E.8 holdout) spanning DSP, cryptography, finance, text parsing, and geometry verified with 100% correctness parity and zero compiler modifications.
- **10 Optimization Safety Stress Tests:** Verified bounds-check safety with empty inputs and aliased arrays, loop invariant hoisting across zero iterations and early breaks, Unicode handling (Devanagari, accented European, 4-byte SMP emojis), and dynamic dispatch cache drift.
- **Clean-Room Packaging:** Built wheel (`.whl`) and source distribution (`.tar.gz`) verified in an isolated virtual environment outside the repository for metadata, licensing, pure Python fallback, CLI compilation, and native execution.

### Same-Run Benchmark Summary (Intel Core i5-8265U, Python 3.12, Mojo 1.2.0)
| Workload | Input Scale | Backend Mode | Same-Run Speedup | Competitor Comparison |
|---|---|---|---|---|
| **Quant Backtest** | 100k scalar ticks | Native | **67.8× – 76.1×** | Comparable to Numba without JIT compile lag |
| **AR Spatial 3D** | 10k vertices (`ndarray`) | Native | **33.4×** | Numba / Codon Native faster via SIMD vectorization |
| **Geo Distance** | 10k waypoints (`ndarray`) | Native | **9.7×** | NumPy vectorized SIMD transcendentals ~26% faster |
| **PDF Cleaner** | 100k chars (`str`) | Native | **6.2×** | **2.5× faster than Python Regex** |
| **PII Scrubber** | 100k chars (`str`) | Native | **5.0×** | **1.7× faster than Python Regex** |
| **OCR Matcher** | 1k words (`list[str]`) | Fallback (Default) | **1.0× (Fallback)** | RapidFuzz C++ is 1.27× faster than forced native (3.6×) |
| **RAG Chunker** | 100k chars (`str`) | Fallback (Default) | **1.0× (Fallback)** | Avoids 20–25× FFI boxing penalty; offset API is 4.6× faster |

*(Note: The 112.5× Quant Backtest figure cited in preliminary audits was a synthetic cross-run calculation and is not advertised as a measured benchmark.)*

---

## 3. Known Limitations

- **Statically Typed Subset Only:** Parameters, return types, and local variables on first assignment must have explicit type annotations (e.g. `x: int = 0`). Dynamic duck-typing and untyped variables are not supported.
- **Loop Control Restrictions:** `break` is supported; `continue` inside loop bodies is currently unsupported in v0.2.0 (use early `return` or boolean flags).
- **Collection Boxing Overhead:** Passing small Python `list[float]` or returning `list[str]` incurs per-element C-API conversion overhead. Contiguous 1-D NumPy arrays should be used for numeric vectors; collection returns automatically fall back to pure Python to preserve throughput.
- **No Vectorized SIMD Transcendentals:** Mojo Hotloop currently compiles scalar transcendental math loops (`sin`, `cos`, `atan2`); libraries with hand-tuned C++/SIMD kernels (NumPy, RapidFuzz) outperform Hotloop on those specific kernels.
- **Platform Scope:** Linux x86-64 only (including Ubuntu 24.04 on WSL2). macOS and Windows native execution are not supported in v0.2.0.
- **Mojo Compiler Requirement:** Local Mojo 1.2.0 is required for compiling native `.so` binaries. When absent, code runs via transparent pure Python fallback.
- **Stability Expectations:** This is an open-source **Developer Preview**. APIs, CLI flags, and compiled binary layouts may evolve before v1.0.0.

---

## 4. Upgrade Instructions

### Upgrading from v0.1.0 to v0.2.0

1. **Install the v0.2.0 distribution:**
   ```bash
   pip install --upgrade mojo_hotloop-0.2.0-py3-none-any.whl
   ```
   *(Or install from local source: `pip install -e .`)*

2. **Rebuild Existing Modules:**
   Because v0.2.0 introduces new code generation patterns and `_PyStr` structs, existing `.so` shared libraries should be recompiled:
   ```bash
   hotloop build my_module.py --engine=ast
   ```

3. **Backward Compatibility:**
   - All valid v0.1.0 decorated functions compile and execute under v0.2.0 without source code modifications.
   - New features (`break`, string negative indexing, `inspect_dispatch`) are strictly additive.

---

## 5. Security & Legal Notice

- **Offline Transpilation:** Mojo Hotloop operates 100% offline. Zero network calls, zero telemetry, zero cloud AI API dependencies.
- **Licensing:** Licensed under the Apache License, Version 2.0. See `LICENSE` and `NOTICE` for full terms and Modular trademark attribution.
- **Reporting Vulnerabilities:** Report security vulnerabilities privately through the GitHub Security Advisory tab.
