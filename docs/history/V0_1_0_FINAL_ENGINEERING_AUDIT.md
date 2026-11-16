# MOJO-HOTLOOP v0.1.0 — Final Principal Engineering Audit Report

**Verdict**: **READY FOR OWNER APPROVAL — v0.1.0 DEVELOPER PREVIEW**

**Branch**: `v0.1.0-final-engineering`  
**Preserved Baseline Commit (`master`)**: `bd388058de6cf490779f709fd0fca6231b43d04e` (untouched)  
**Target Toolchain**: Python 3.12.16 (Clang 23.1.3), Mojo 1.2.0 (`2016d0cd`), Ubuntu 24.04 LTS (WSL2, Intel Core i5-8265U @ 1.60 GHz, 4 cores / 8 threads, 7.63 GiB RAM)

---

## 1. Original Engineering Weaknesses

Inspecting the baseline source code (`bd388058de6cf490779f709fd0fca6231b43d04e`) and re-running tests revealed the following concrete defects:

1. **Out-of-Bounds / Negative Indexing Crash Risk (`SIGILL`)**: Generated Mojo emitted raw indexing `xs[idx]`, triggering fatal `SIGILL` aborts on negative or out-of-bounds indices instead of raising Python `IndexError` (`T05_neg_index` failed at baseline).
2. **Unsound / Unverified NumPy Pointer Fast-Path**: Pointer acceleration assumed buffer compatibility without validating `ndim == 1`, `dtype.name`, `flags.c_contiguous`, or read-only safety in the AST, and dropped return boxing (`ret_elem_type`) when `_has_ctypes` was active (`T18_return_list_float` failed).
3. **AST Transpiler Semantic Bugs**:
   - Reassigning function parameters inside Mojo `def` bodies failed compilation (`T36`, `T38`).
   - Chained comparisons (`a < b < c`, e.g. `T34_chained_cmp`) were unsupported or miscompiled.
   - Mixed-type `(Float64, Int)` / `(Int, Float64)` floor division (`//`) and modulo (`%`), `0.0 ** neg` (`ZeroDivisionError`), `abs(INT64_MIN)` overflow, `chr()`/`ord()`, `bool()`/`str()`, and lexical scoping inside `if`/`elif` and `for` blocks had gaps.
   - Python wrapper functions (`def <name>`) collided with Mojo reserved keywords such as `fn` (`test_05_concurrent_compilation_safety`), and user variables/parameters named after Mojo hard keywords failed downstream in `mojo build`.
4. **Severe String Performance Regressions**: Unfamiliar string-scanning code such as `mask_digits` ran at `0.18x` vs Python in baseline `TRANSPILER_GENERALIZATION_AUDIT.md` due to unconditional UTF-8 `List[Codepoint]` heap allocation inside `_PyStr`, temporary `String` allocations on `out += s[i]`, and heap slicing on literal checks.
5. **Fair Benchmark Distortion in Spatial & Geospatial Examples**: `examples/ar_spatial/bench.py` and `examples/geo_distance/bench.py` originally passed Python `list`s to `@hotloop` while passing `np.ndarray` to NumPy and Numba, masking native pointer speedups behind O(N) list-unboxing overhead.
6. **Runtime Dispatcher & Packaging Weaknesses**:
   - `pyproject.toml` pulled in runtime dependency `python-dotenv`, and `hotloop/backends/mojo.py` / `cli.py` retained dead Gemini/online code paths and a hardcoded `~/mojo-hotloop/.venv/bin/mojo` path unusable by external developers.
   - `hotloop/decorator.py` lacked thread synchronization around `_LOADED_MODULES` / `_WARNED_FALLBACKS`, lacked ELF magic validation (`\x7fELF`) before `dlopen`, lacked keyword/default argument binding, mapped neither `HOTLOOP_INDEX_ERROR` to `IndexError` nor overflow fallback accurately to `_call_count_native`, and performed non-atomic artifact writes.
   - `.github/workflows/ci.yml` checked `meta['License'] == 'Apache-2.0'` (incompatible with PEP 639 `License-Expression`) and stale `requires()` filtering; documentation still referenced `--engine=gemini`, `GEMINI_API_KEY`, `python-dotenv`, and outdated benchmarks.

---

## 2. Actual Compiler, Runtime & Packaging Improvements Implemented

All improvements are general-purpose and apply uniformly to arbitrary Python AST inputs (zero benchmark-specific shortcuts or handwritten `fast.mojo` edits):

1. **Checked Indexing & Overflow/Exception Parity (`hotloop/ast_transpiler.py`, `hotloop/decorator.py`)**:
   - Added `_checked_index(idx, n)` (`UInt(idx) < UInt(n)` fast path + negative wrap + `HOTLOOP_INDEX_ERROR` -> `IndexError`) across `List[...]` and raw pointer args using Mojo 1.2.0 `unsafe_offset=`.
   - Added mixed `(Float64, Int)` / `(Int, Float64)` `_checked_floordiv`/`_checked_mod`, `0.0 ** neg -> ZeroDivisionError`, `_checked_abs(INT64_MIN)` overflow guard, `_py_bool()`, `_py_ord()`, `_py_chr()`, lexical scoping for `if`/`elif`/`for`/`AnnAssign`, parameter reassignment via `_collect_reassigned_vars`, chained comparisons (`ast.Compare`), and full `String` slicing (`_str_slice` with `step == 0 -> ValueError`).
   - Isolated wrapper export names via `_pywrap_<fn>` registered under Python name `<fn>`, and added explicit `ASTTranspileError` checks (`MOJO_RESERVED_IDENTIFIERS` & `MOJO_PARAM_KEYWORDS`) calibrated empirically against Mojo 1.2.0 (preserving common local names such as `out`).
2. **Safe Contiguous NumPy Pointer Dispatch (`hotloop/ast_transpiler.py`)**:
   - Added `_is_ptr_safe_arg()` AST analysis (restricting zero-copy pointer path to read-only `len(arg)` / `arg[i]` usage) and runtime C-ABI checks for `hasattr("ctypes"/"ndim"/"dtype"/"flags")`, `ndim == 1`, `dtype.name == "float64"|"int64"`, and `flags.c_contiguous`, plus return-list boxing fix (`ret_elem_type`) and `capacity=` list pre-allocation.
3. **General-Purpose String & LLVM Optimizations (`hotloop/ast_transpiler.py`, `hotloop/backends/mojo.py`)**:
   - Added `_PyStr` ASCII fast-path (eliminating `List[Codepoint]` heap allocation on ASCII strings and slicing directly via `self._s[byte=s_c:e_c]`).
   - Added `out.write(s.get_cp(idx))` zero-temp write lowering for `out += s[i]`, `_collect_codepoint_vars` register promotion for read-only single-character locals, and zero-allocation `_PyStr.eq_slice()` for `s[a:b] == "literal"`.
   - Enabled `-O3` optimization flag in `mojo build --emit shared-lib -O3`.
4. **Thread-Safe Offline Runtime & Portable Toolchain (`hotloop/decorator.py`, `hotloop/backends/mojo.py`, `hotloop/cli.py`, `pyproject.toml`)**:
   - Removed `python-dotenv` runtime dependency (`dependencies = []`) and Gemini online engine paths; `engine="gemini"` now returns a clean offline error.
   - Replaced hardcoded `.venv` path with `MOJO_BIN` -> `sys.executable` bin dir -> `shutil.which("mojo")` -> `~/.modular/bin/mojo`.
   - Added atomic temp-file + `os.replace` writes for `.mojo`, `.so`, `.hotloop_manifest.json` (`so_sha256`), and `__mojocache__/`; ELF `\x7fELF` validation before `dlopen`; `threading.Lock()` (`_STATE_LOCK`); keyword/default binding via `inspect.signature`; accurate `_call_count_native` accounting.

---

## 3. Evidence That Optimizations Generalize

`audit/bench_generalization.py` evaluates five previously unseen general-purpose Python functions transpiled automatically via `--engine=ast`:

| Function | Workload | Baseline (where recorded) | Final Mojo p50 | Final Python p50 | Speedup |
|----------|----------|---------------------------|----------------|------------------|---------|
| `trapezoidal_integration` | 100,000 steps | — | `1,117.5 µs` | `14,031.2 µs` | **12.56x** |
| `chebyshev_path_distance` | 10,000 waypoints | — | `112.1 µs` | `6,411.3 µs` | **57.17x** |
| `exponential_moving_average` | 50,000 values | — | `220.2 µs` | `14,616.2 µs` | **66.39x** |
| `mask_digits` | 50,000 chars | **`0.18x`** | `1,230.5 µs` | `10,532.3 µs` | **8.56x** (+47x gain) |
| `hamming_distance` | 50,000 chars | — | `490.2 µs` | `6,305.7 µs` | **12.86x** |

No example-specific branches or handwritten Mojo kernels exist in `hotloop/ast_transpiler.py`; the same `_PyStr` ASCII fast-path, `out.write(s.get_cp(i))`, and `-O3` compilation accelerated `mask_digits` (`0.18x` -> `8.56x`), `caesar_cipher` (`7.03x`), `rle_compress` (`3.28x`), and the PII/PDF/OCR text workloads simultaneously.

---

## 4. All Seven Before-and-After Benchmarks

All binaries are 100% AST-generated (`--engine=ast`). Hardware: Intel Core i5-8265U, WSL2 Ubuntu 24.04. No handwritten `fast.mojo` was used.

| Application | Baseline (`bd388058`, before) | Final (`v0.1.0-final-engineering`, after) | Strongest Competitor / Behavior |
|-------------|-------------------------------|-------------------------------------------|---------------------------------|
| **1. Quant Backtest** (100k ticks) | Pure Py `34.296 ms` p50 vs Mojo `0.406 ms` (**84.57x**) | Pure Py `43.780 ms` p50 vs Mojo `0.531 ms` (**82.39x**; mean `0.570 ms`) | **1.14x** vs warmed Numba `@njit` (`0.604 ms` p50; `1810.4 ms` JIT) |
| **2. AR Spatial 3D** (`100` / `1k` / `10k` pts) | List inputs: `1.21x` / `1.38x` / `1.39x` | `ndarray` inputs: `0.73x` (`52.38 µs`) / **7.54x** (`56.48 µs`) / **40.60x** (`105.72 µs` mean, `103.08 µs` p50) | **16.81x** vs NumPy at 10k; `0.65x` ratio vs Numba (`69.15 µs`) at 10k |
| **3. Geo Distance** (`100` / `1k` / `10k` pts) | List inputs: `2.63x` / `3.31x` / `3.42x` | `ndarray` inputs: `1.72x` (`45.21 µs`) / **6.18x** (`237.66 µs`) / **8.56x** (`1,529.59 µs`) | NumPy (`0.77x` ratio) & Numba (`0.78x` ratio) lead at 10k via SIMD libm |
| **4. PII Scrubber** (`53` / `8k` / `100k` ch) | `2.58x` / `5.58x` / `5.83x` vs Py (`2.13x` vs Regex at 100k) | **3.22x** (`9.60 µs`) / **6.63x** (`1,538.16 µs`) / **7.49x** (`14,687.96 µs`) vs Py | **1.27x / 2.37x / 2.51x** faster than compiled Python `re` |
| **5. PDF Text Cleaner** (`1k` / `10k` / `100k` ch) | `4.31x` / `4.50x` / `4.62x` vs Py (`2.09x` vs Regex at 100k) | **7.32x** (`68.62 µs`) / **6.16x** (`783.77 µs`) / **6.73x** (`7,253.67 µs`) vs Py | **3.08x / 2.98x / 2.94x** faster than compiled Python `re` |
| **6. OCR Fuzzy Matcher** (`20` / `200` / `2k` cands) | `3.20x` / `3.54x` / `1.91x` vs Py (`0.43x` vs RapidFuzz at 2k) | **5.41x** (`35.44 µs`) / **6.34x** (`301.29 µs`) / **3.62x** (`1,195.80 µs`) vs Py (forced native) | RapidFuzz C ext leads (`0.27x / 0.23x / 0.78x` ratio vs Mojo `@hotloop`) |
| **7. RAG Chunker** (`1k` / `10k` / `100k` ch) | `@hotloop` fallback `0.64x / 0.84x / 0.88x` (Direct `3.56 ms`) | `@hotloop` auto-fallback `0.39x / 1.04x / 0.78x` (Direct native `6.04 ms` at 100k) | Auto Python fallback prevents ~21x FFI `list[str]` boxing slowdown at 100k |

*Note on AR/Geo before vs after*: Updating `examples/ar_spatial/bench.py` and `examples/geo_distance/bench.py` to pass `np.ndarray` inputs (instead of forcing O(N) Python `list` unboxing) enabled `@hotloop`'s zero-copy C-pointer fast path; tiny inputs (`100` pts) incur ~35 µs C-ABI attribute validation overhead (`0.73x` on 100-vertex AR cloud), while `1k–10k` clouds scale up to `40.60x`.

---

## 5. Strongest Verified Competitive Results

- **Stateful Simulation (`quant_backtest`)**: `82.39x` vs CPython 3.12 (`0.531 ms` vs `43.780 ms` p50) and `1.14x` faster than warmed Numba `@njit` (`0.604 ms` p50, zero `1.8s` cold-JIT delay).
- **Ray-Cloud Kernel (`ar_spatial` 10k vertices)**: `40.60x` mean (`40.77x` p50) vs CPython 3.12 and `16.81x` faster than vectorized NumPy (`105.72 µs` vs `1,777.39 µs`).
- **Character State-Machine Scanners (`pdf_cleaner` & `pii_scrubber`)**: `6.16x–7.32x` vs Python (`2.94x–3.08x` vs compiled Python Regex) on PDF cleaning; `6.63x–7.49x` vs Python (`2.37x–2.51x` vs Regex) on medium/large PII scrubbing.
- **Zero-Allocation Unfamiliar Loops (`audit/bench_generalization.py`)**: `66.39x` on `exponential_moving_average` (50k) and `57.17x` on `chebyshev_path_distance` (10k).

---

## 6. Results on Unfamiliar Python Functions

`tests/test_unfamiliar_functions.py` tests **35 newly written `@hotloop` functions** compiled offline and executed natively (zero mocks), plus **6 AST rejection cases** (`test_05`):

- **Suite Result**: `Ran 6 tests in 6.378s — OK` (`0` failures, `0` crashes, `0` skipped assertions).
- **Coverage**:
  - 10 scalar numeric functions (Collatz, GCD, integer square root, Leibniz pi, LCG roll, compound decay, Horner eval, bitwise parity, power edge, clamp/abs).
  - 10 `np.ndarray` & collection functions (`dot_product`, `variance_welford`, prefix sums, argmax, negative-index pair lookup, mixed `list[float]`/`list[int]` returns & collection auto-fallback verification).
  - 10 string/Unicode & algorithmic helpers (RLE compression, Caesar cipher, UTF-8 multi-byte codepoint counting, stepped string slicing, chained character comparisons).
  - Keyword/default parameter binding, Python truthiness (`if s:`, `if not xs:`), float `NaN`/`±Inf`/`-0.0`, exception parity (`ZeroDivisionError`, `IndexError`, `ValueError` on `step==0` & `chr(-200)`).
  - Clean `ASTTranspileError` rejections on 6 unsupported constructs (list comprehension, `dict`, `try/except`, `yield`, list slice `xs[1:3]`, Mojo keyword `var` variable).
- **Measured Unfamiliar Speedups (post-final-edit)**: `dot_product(20k) = 12.12x`, `variance_welford(20k) = 18.11x`, `rle_compress(40k) = 3.28x`, `caesar_cipher(40k) = 7.03x`.

---

## 7. Full Correctness and Stability Counts

All checks below were re-executed **after** the final edit to `hotloop/` and `tests/`:

| Suite | Command | Latest Result |
|-------|---------|---------------|
| AST Provenance Builds (all 7 apps) | `.venv/bin/python audit/test_ast_provenance.py` | **7/7 Exit 0** (all compiled offline with `--engine=ast`) |
| 7-App Verification Suites | `.venv/bin/python audit/run_all_verifications.py` | **7/7 Passed — 7,220 business checks, 0 mismatches** (`1010 + 1014 + 1020 + 1020 + 1019 + 1117 + 1020`) |
| Compiler Adversarial Suite | `.venv/bin/python tests/test_compiler_adversarial.py` | **50 tests: 49 PASS, 1 EXP_FAIL (`T42_missing_annotation`), 0 UNEXPECTED FAIL** |
| Unfamiliar Function Suite | `.venv/bin/python tests/test_unfamiliar_functions.py` | **6/6 unittest methods OK** (35 compiled functions + 6 rejections) |
| Runtime Security & Stability Suite | `.venv/bin/python tests/test_runtime_security.py` | **6/6 unittest methods OK** (`RSS_DIFF < 4096 KB`) |
| Dispatch, Checked Ops, Perf & Cache Audits | `audit/test_milestone1_dispatch.py`, `test_milestones_2_3.py`, `test_performance_dispatch.py`, `test_cache_invalidation.py` | **8/8 + 13/13 + 6/6 + 6/6 OK** (`0` failures) |
| Reliability & Security Audit | `.venv/bin/python audit/test5_reliability_security.py` | **Exit 0**, child crash isolation verified (`-4`), `RSS_DIFF_KB: 0` |

---

## 8. Security and Memory-Safety Findings

- **Validated Protections**:
  - Out-of-bounds/negative indexing raises `IndexError` safely without `SIGILL` crashes (verified in subprocesses in `tests/test_runtime_security.py::test_01`).
  - Non-1D, non-C-contiguous (`arr[::2]`), wrong-dtype (`float32`/`int32`) NumPy arrays safely bypass raw C-pointer dereferencing without memory corruption (`test_02`).
  - Checked 64-bit integer overflow falls back safely to Python or raises `HotloopNativeExecutionError` in `strict=True` mode; invalid `chr()`/`step==0` raise `ValueError` (`test_03`).
  - Corrupted non-ELF `.so` files and corrupted manifests fall back cleanly to Python without calling `dlopen` on garbage bytes (`test_04`).
  - Concurrent multi-thread compilation with Mojo keyword function names (`def fn(x: int) -> int`) succeeds without symbol collision (`test_05`).
  - Repeated native array & string execution over 25,000+ iterations (`test_06`) and 100,000 iterations (`test5`) showed `RSS_DIFF_KB: 0` / `< 4096 KB`.
- **Important Security Caveat**: Passing runtime tests does **not** prove total memory safety across arbitrary C-ABI/Mojo execution. In particular, raw C pointer dispatch relies on Python ctypes buffer pointers remaining valid for the duration of a single-threaded native call (`HOTLOOP` does not spawn worker threads), and Mojo's compiler/FFI boundary runs in-process (`SIGSEGV`/`SIGILL` on an unhandled native fault still terminates the hosting Python process).

---

## 9. Clean-Install Verification

Verified completely out-of-tree in a fresh isolated virtualenv `/tmp/hotloop_ci_venv` with `--no-deps --no-index` against the final wheel `dist/mojo_hotloop-0.1.0-py3-none-any.whl`:

1. `pip install --no-deps --no-index dist/mojo_hotloop-0.1.0-py3-none-any.whl` succeeded with **zero runtime dependencies** (`Requires:` empty in `pip show`).
2. `tests/test_compiler_adversarial.py` passed (`49 PASS, 1 EXP_FAIL, 0 UNEXPECTED FAIL`).
3. Out-of-tree `/tmp/hotloop_clean_test/sample.py` ran cleanly in **pure Python fallback mode** without `.so` (`_last_backend == "python_fallback"`).
4. `MOJO_BIN=/home/gaurav/mojo-hotloop/.venv/bin/mojo /tmp/hotloop_ci_venv/bin/hotloop build ... --engine=ast --no-verify` compiled `sample.py` offline and executed `_last_backend == "native"` (`FINAL_CLEAN_FALLBACK_AND_CI_OK`, `FINAL_CLEAN_NATIVE_OK`).

---

## 10. License and Ownership Status

- **Declared License**: `Apache-2.0` in `LICENSE`, `pyproject.toml` (`License-Expression: Apache-2.0`, `License-File: LICENSE`), and wheel `METADATA`.
- **Copyright Notice Status**: `LICENSE` (line 171) and `README.md` currently carry the generic placeholder `Copyright 2026 mojo-hotloop Contributors`, and `pyproject.toml` lists `author = "mojo-hotloop Contributors"`. Legal entity/author naming and final Apache-2.0 release sign-off remain **pending owner approval**.
- **Third-Party Notices**: Updated in `docs/THIRD_PARTY_NOTICES.md` (zero base runtime dependencies; optional `numpy` BSD-3-Clause; build-time `setuptools` MIT; external `Modular Mojo 1.2.0` Community License; public-domain algorithmic provenance).

---

## 11. Remaining Known Limitations

1. **Linux / WSL2 + Mojo 1.2.0 Only**: Native Windows (outside WSL2) and macOS are unsupported; untested on Mojo versions other than `1.2.0`.
2. **Restricted Python Subset**: `dict`, `set`, `tuple`, list slicing (`xs[1:3]`), `break`, `continue`, `try`/`except`, `lambda`, list comprehensions, and `*args`/`**kwargs` raise `ASTTranspileError` and fall back to Python.
3. **NumPy Fast-Path Preconditions**: Zero-copy C-pointer dispatch triggers only on 1-D C-contiguous `float64`/`int64` `ndarray` inputs used read-only via `len(xs)`/`xs[i]`; strided, N-D, mutated, or alternate-dtype arrays take safe non-pointer paths.
4. **C-ABI & Collection Overhead**: Tiny arrays (~100 items) incur ~35 µs C-ABI wrapper check overhead; `list[str]` returns trigger auto-fallback to avoid O(N) boxing slowdowns.
5. **Mojo Reserved Identifiers**: Using Mojo hard keywords (`fn`, `var`, `struct`, `ref`, `trait`, `comptime`, `Self`) as variable/parameter names or argument-convention keywords (`mut`, `out`, `owned`, `borrowed`, `inout`, `read`) as parameter names raises `ASTTranspileError`.
6. **Cache Audit Note (`test5` 5.6)**: Legacy check 5.6 text in `audit/test5_reliability_security.py` prints a static historical note, whereas `hotloop/backends/mojo.py` & `hotloop/decorator.py` implement and enforce SHA-256 manifest verification (`audit/test_cache_invalidation.py` 6/6 OK).

---

## 12. Git Commit and Final Package Checksums

- **Immutable Baseline Commit (`master`)**: `bd388058de6cf490779f709fd0fca6231b43d04e`
- **Release Engineering Branch**: `v0.1.0-final-engineering` (committed with DCO `git commit -s` immediately following this report)
- **Baseline Artifacts (`bd388058`)**:
  - `d692b05e9e67b87a40dc17cd808adf24f91274f8a405c936443499b142b7e6b3  dist/mojo_hotloop-0.1.0-py3-none-any.whl` (27,089 bytes)
  - `42744c7ba613a65ac4feb3d2cb844563a32a45003cba520cfccd09250fcc4f05  dist/mojo_hotloop-0.1.0.tar.gz` (33,505 bytes)
- **Final Release Artifacts (`v0.1.0-final-engineering`)**:
  - `7c2aed91cd5a32f99e52fca7fae525918d385da962dda9705719df5da8693c4e  dist/mojo_hotloop-0.1.0-py3-none-any.whl` (**31,436 bytes**)
  - `d0a115575a89a108761b9b8a181faf9839e63201b5b405c118a0aa6530aad382  dist/mojo_hotloop-0.1.0.tar.gz` (**45,564 bytes**)

---

## 13. Actual GitHub CI Status

- **Workflow File**: `.github/workflows/ci.yml` (updated and validated for PEP 639 `License-Expression`, empty base runtime dependencies, offline `ASTTranspiler`, and `test_compiler_adversarial.py`).
- **Live Remote CI Execution Status**: **NOT EXECUTED ON GITHUB ACTIONS** — `git remote -v` is empty (local repository only) and `gh` CLI is not installed.
- **Local CI Simulation**: Every command in `.github/workflows/ci.yml`'s `python-tests` job was executed cleanly inside `/tmp/hotloop_ci_venv` (`CI_SIMULATION_PASS: mojo-hotloop 0.1.0 Apache-2.0 python_fallback`), and Mojo native suites ran locally against Mojo 1.2.0.

---

## 14. Exact Publication Blockers

**Technical Engineering Blockers**: **None.** All 7,220 business checks, 50 adversarial tests, 35 unfamiliar functions + 6 AST rejections, 6 runtime security/stability tests, all audit checks, benchmarks, and clean wheel installations pass on `v0.1.0-final-engineering`.

**Owner / Administrative Actions Required Before Public Release**:
1. **Legal & Ownership Sign-Off**: Confirm copyright holder identity (currently `mojo-hotloop Contributors` in `LICENSE`, `pyproject.toml`, and `README.md`) and Apache-2.0 release approval.
2. **GitHub Remote & Tagging**: Configure remote repository, push `v0.1.0-final-engineering` / merge to `main`/`master` once approved, run live GitHub Actions workflow `.github/workflows/ci.yml` on GitHub-hosted runners, and tag `v0.1.0`.
3. **PyPI Upload**: Publish `dist/mojo_hotloop-0.1.0-py3-none-any.whl` and `dist/mojo_hotloop-0.1.0.tar.gz` after owner sign-off (intentionally not uploaded).

---

## Final Verdict

**READY FOR OWNER APPROVAL — v0.1.0 DEVELOPER PREVIEW**
