# Mojo Hotloop v0.2.1 -- Consolidated Release-Readiness Report

**Date:** 2026-11-25  
**Target Release:** `v0.2.1` (Corrective local candidate; **UNPUBLISHED**)  
**Protected Baseline (`main`):** `080125ec03b68a55423d426a48c112b7415f8b48` (`gorky117-cell <gorky117@gmail.com>`)  
**Published Tags Preserved:** `v0.1.0`, `v0.2.0` (`v0.2.1` tag absent locally and remotely)  
**Verified Workstation Environment:** WSL2 Linux x86-64 (`ubuntu-24.04`), CPython `3.12.16` (64-bit, little-endian, GIL-enabled, 30-bit `PyLong`), Mojo `1.2.0 (2016d0cd)`, secondary system `/usr/bin/python3` (`3.12.3`), optional external benchmark baseline Codon `0.20.6`.

---

## 1. Executive Summary & Overall Status

| Area | Classification | Summary |
|---|---|---|
| Local compiler, runtime, security, math & list-exception verification (`PR 1`) | **PASS** | `hotloop/` and `pyproject.toml` on `codex/pr1-v021-runtime` (`ad8c8673`) match `c5661070` byte-for-byte with zero unrequested modifications; `380` pytest, `129` `c2aebd78` security, `7,220` app checks, `25` M0 reference, `15/15` math parity, corrupted `.so`/manifest rejection, and Python `3.12.3` fallback/strict gates pass offline cleanly. |
| Public documentation, disclosures, notices & roadmap alignment (`PR 2` + `PR 3`) | **PASS** | Stacked cleanly in `codex/pr2-v021-docs` (`2c7d9b5`) and `codex/pr3-v021-m0-ci` without overlapping M0 CI changes into PR 2 or keeping experimental F.2 code. |
| End-to-end public `@hotloop` performance & honest regression disclosures | **PASS** | Scalar/string loops (`quant_backtest` `55.93x`, `pii_scrubber` `6.69x`, `pdf_cleaner` `5.88x`) accelerate strongly; list/fallback workloads (`geo_distance` `+12.9%..+33.5%` forced regression over `582afcd`, `ar_spatial` forced `0.63x` slower than CPython, `rag_chunker` Python fallback, tiny calls `15.32 us`) are disclosed verbatim. |
| Contributor DCO (`Signed-off-by:`) compliance across stacked PR commits | **PASS** | All `10` commits across PR 1, PR 2, and PR 3 carry authorized `Author`, `Committer`, and `Signed-off-by: Gaurav Kumar Singh <gorky117@gmail.com>` matching `.github/workflows/contributor-assistant.yml`. |
| External Mojo/MAX SDK binary license & Modular trademark disclosures | **PASS** (policy-aligned; prebuilt `.so` redistribution prohibited) | `mojo-hotloop` wheels/sdists bundle zero SDK binaries (`Apache-2.0`). `NOTICE` and `docs/THIRD_PARTY_NOTICES.md` use factual nominative Modular trademark wording (removing unverified license claims), note `LicenseRef-MAX-Platform-Software-License` scope without bundling `.dist-info` license text, and explicitly prohibit redistributing compiled `.so` artifacts linking Modular runtime libraries (`libKGENCompilerRTShared.so`, `libMSupportGlobals.so`, `libAsyncRTRuntimeGlobals.so`). |
| GitHub-hosted CI execution (`ubuntu-24.04`, Python `3.12.16`, Mojo `1.2.0`) | **NOT VERIFIED** | Workflow `.github/workflows/ci.yml` and `reference/m0-v1` corpus are prepared locally in `PR 3` (`codex/pr3-v021-m0-ci`), but no push or hosted GitHub Actions run has occurred. |
| Remote PR creation, merge to `main`, `v0.2.1` tag, GitHub Release & PyPI publish | **BLOCKED** | Blocked pending authorized push, PR review, and live green GitHub Actions checks (Rulesets `27367642` and `27367632`); local DCO sign-offs and licensing/trademark disclosures are completed. |

**Overall Release Go/No-Go:** **BLOCKED** (`Local technical, DCO, and notice readiness: PASS` / `Public release & push: BLOCKED` pending explicit push/PR authorization and live GitHub-hosted CI verification).

---

## 2. Repository & Commit Verification

* **Protected baseline:** `main` is untouched at `080125ec03b68a55423d426a48c112b7415f8b48` (tree inspected, `v0.1.0` and `v0.2.0` tags preserved).
* **Prior single-branch integration preserved untouched:** `codex/v021-local-release-integration` at `/home/gaurav/mojo-hotloop-v021-local-integration` (`c56610705daf7664463c2d09110072af368e6222` / `ca46849bcf78ab33e0265ee8bc04110f8e49c8f6`).
* **Primary Phase F workspace preserved untouched:** `/home/gaurav/mojo-hotloop` on `feat/phase-f-v0.3.0` (`99178a5`).
* **Experimental Phase F.2 preserved separately:** `/home/gaurav/mojo-hotloop-f2-security-repair` on `codex/phase-f2-security-repair` (`61b0c363` / `aa8a21e8`, clean working tree, **zero** F.2 files or NumPy zero-copy/SIMD code present in `v0.2.1`).
* **Stacked 3-PR local branches verified:**
  1. `codex/pr1-v021-runtime` (`ad8c86739f3488d9a89bd8cc8474d4a4923036b5`): `080125e -> 62135d8 -> febe2c5 -> 69fa0bb -> 0a6dacf -> aceec46 -> 582afcd -> a11c9de -> ad8c8673`.
  2. `codex/pr2-v021-docs` (`2c7d9b52ba97d9c81953111b483909f4b2a62953`): Pre-M0 credibility docs, `THIRD_PARTY_NOTICES`, `CURRENT_BENCHMARKS`, `CHANGELOG`, `SUPPORTED_SYNTAX`, and reconciled `ROADMAP.md` (`0` runtime edits, `0` M0 CI files).
  3. `codex/pr3-v021-m0-ci` (`HEAD` of `/home/gaurav/mojo-hotloop-pr3-ci`): `.github/workflows/ci.yml`, `reference/m0-v1/*`, `tools/*`, `docs/M0_NATIVE_CI_AND_REFERENCE.md`, [`ROADMAP_EXECUTION_STATUS_2026-11-25.md`](ROADMAP_EXECUTION_STATUS_2026-11-25.md), and this report. `git diff ad8c8673..HEAD -- hotloop pyproject.toml` is empty.

**Classification:** **PASS** (local Git ancestry & isolation).

---

## 3. Environment & Toolchain Matrix

| Component | Tested Version / Identity | Role in `v0.2.1` | Native Qualification Status |
|---|---|---|---|
| Host / OS | WSL2 Ubuntu `24.04` (`Linux x86_64`, little-endian) | Primary local build & test host | **PASS** (qualified) |
| Primary Python | CPython `3.12.16` (64-bit, GIL-enabled, 30-bit `PyLong`) | Qualified native runtime | **PASS** (qualified) |
| Mojo Toolchain | `Mojo 1.2.0 (2016d0cd)` | Offline AST-to-Mojo `.so` compiler (`XDG_CACHE_HOME` isolated cleanly from corrupted shared transform cache entry) | **PASS** (qualified) |
| Secondary Python | `/usr/bin/python3` (`3.12.3`, GCC `13.3.0`) | Compatibility & non-qualified fallback/strict verification (`compatibility.py` with and without `mojo` on `PATH`) | **PASS** (correctly routes to Python fallback; `strict=True` raises `HotloopNativeExecutionError`) |
| External Comparison Compiler | Codon `0.20.6` (`/home/gaurav/codon-bench`) | Optional same-machine benchmark baseline (`benchmarks/run_codon_jit_suite.py`) | **PASS** (benchmark baseline only; no runtime dependency) |
| GitHub Hosted Runners | `ubuntu-24.04`, Python `3.12.16`, Mojo `1.2.0` (configured in `.github/workflows/ci.yml`) | Remote CI target | **NOT VERIFIED** (no remote push/dispatch executed) |
| Windows / macOS / Other CPython patches / Free-threaded | Not qualified in `v0.2.1` | Fallback only (`strict=True` rejects) | **NOT VERIFIED** as native targets (intentionally excluded) |

---

## 4. Runtime Behavior & Verification Coverage

All 10 runtime behavior categories were executed directly against installed wheel builds of `v0.2.1` (`ad8c8673` / `PR 3` runtime):

| Scenario | Verified Observation | Classification |
|---|---|---|
| 1. Native execution on supported syntax | `ok_kernel(100, 0.5)` returns `2475.0` with `last_backend="native"`, `backend_available=True`, `call_count_native=1`; `quant_backtest`, `pii_scrubber`, `pdf_cleaner`, and `25/25` M0 corpus checks dispatch as specified. | **PASS** |
| 2. Unsupported Python syntax (`try/except`) | `hotloop build mod_bad.py` exits `1` cleanly (`Unsupported statement type: Try`); runtime call falls back to Python returning `6` (`HotloopFallbackWarning`); `@hotloop(strict=True)` raises `HotloopNativeExecutionError`. | **PASS** |
| 3. Controlled Python fallback | `rag_chunker`, `ocr_matcher`, `geo_distance`, `ar_spatial`, NumPy/buffer inputs, bounded/keyword string prefix/suffix, and variadic calls fall back to Python with `HotloopFallbackWarning` and exact CPython outputs. | **PASS** |
| 4. Strict mode failures | `strict=True` raises `HotloopNativeExecutionError` on unqualified Python (`3.12.3`), missing binaries, corrupted `.so` cache artifacts, unsupported syntax, non-list buffers (`numpy.ndarray`, `array.array`, `memoryview`), and non-numeric `math` operands. | **PASS** |
| 5. Missing native build (`--no-build` / unbuilt module) | Pre-build call executes Python fallback (`fallback_reason: No native binary found...`); `tools/run_m0_reference.py --no-build --samples 1` produces expected `46` strict/forced refusal failures without false native passes. | **PASS** |
| 6. Cold compile vs warm cache reuse | Fresh `hotloop.cli build mod_ok.py --no-verify` completes in `6.705 s` (7-app cold builds: `2.572 s - 4.288 s`); first call `0.809 ms`, second call `0.085 ms`; 7-app warm cache-hit checks range `0.016 s - 0.070 s`. | **PASS** |
| 7. Cache invalidation across edits / builds | `audit/test_cache_invalidation.py` passes (`6/6`) verifying compiler, SDK, build-setting, source, and runtime-ABI cache keying. | **PASS** |
| 8. Invalid cache artifacts (corrupted `.so` & manifest) | Overwriting cached `.so` with `"CORRUPT_NOT_ELF"` rejects native loading cleanly (`Native binary is missing or failed SHA256 verification`), falling back safely in default mode and raising `HotloopNativeExecutionError` under `HOTLOOP_STRICT=1`. Corrupting manifest JSON falls back safely (`Expecting property name enclosed in double quotes...`). Shared `~/.cache/modular` also contained a pre-existing 0-byte transform file from prior work, confirming the value of clean cache isolation. | **PASS** |
| 9. Unsupported Python patch version (`3.12.3`) | `audit/release_acceptance/compatibility.py` on `/usr/bin/python3` (`3.12.3`) BOTH without Mojo (`build_ok=false`, `python_fallback`) and with Mojo `1.2.0` on `PATH` (`build_ok=true`, `python_fallback_semantics` with `native_calls=0`, `strict` -> `HotloopNativeExecutionError`) prevents unsafe ABI execution. | **PASS** |
| 10. Return value & exception parity vs CPython | `ok_kernel(-1, -2.0)` raises `ValueError: math domain error`; `15/15` `parity_probe.py`, `15/15` `tools/check_math_semantics.py`, `129/129` `c2aebd78` security suite, `390` list-exception checks, and `1,095` operand/predicate checks pass. | **PASS** |

---

## 5. Benchmarks & Performance Methodology

**Methodology:** Public `@hotloop` end-to-end latency measured using [`audit/release_acceptance/measure_applications.py`](../audit/release_acceptance/measure_applications.py) across 5 isolated worker processes per runtime (`9` batch means each, pinned CPU affinity, `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=1`, original Python inputs/outputs, contrasting `PR 3` (`v0.2.1`) vs published `080125e` (`v0.2.0`)). Codon `0.20.6` was measured separately on the same workstation using `/home/gaurav/mojo-hotloop/benchmarks/run_codon_jit_suite.py` (single-process `@codon.jit` trials, disclosed separately). Private entry timings are excluded from public claims.

| Application / Scale | Default `@hotloop` Route (`v0.2.1`) | CPython `p50` (us) | `@hotloop` Default `p50 / p95` (us) | `@hotloop` Forced `p50` (us) | Strict Competitors `p50` (us) (`manual_cpp` / `numba` / `rapidfuzz` / `expert_regex` / Codon `0.20.6`*) | Speedup vs CPython & Honest Assessment |
|---|---|---:|---:|---:|---|---:|
| `quant_backtest / 100k` | `native` | `29,187.200` | `521.873 / 695.193` | -- | `numba`: `453.424`, `manual_cpp`: `474.938`, Codon*: `713.990` | **`55.93x`** native win (competitive with `numba`/`manual_cpp`, beats Codon*; `0`-tick tiny call slows to `15.319 us` vs CPython `0.093 us`) |
| `pii_scrubber / large` | `native` | `66,290.401` | `9,901.800 / 13,408.800` | -- | `expert_regex`: `22,926.899`, Codon*: `13,147,529.449` | **`6.69x`** native win (`2.32x` faster than `expert_regex`; `short` is `1.39x` vs `expert_regex` `1.95x`) |
| `pdf_cleaner / large` | `native` | `23,888.100` | `4,059.700 / 4,901.300` | -- | `compiled_regex`: disqualified (`strict_correct=False`), Codon*: `10,859,839.326` | **`5.88x`** strict-correct win (`small`: `4.55x`, `medium`: `5.74x`) |
| `ocr_matcher / large` | `python_fallback_slower` | `2,107.467` | `2,311.867 / 2,644.900` | `921.700` | `rapidfuzz`: `511.217`, Codon*: `404.962` | **Default fallback (`0.91x`)**; forced copies yield `2.29x` (`medium`: `5.28x`) behind `rapidfuzz` & Codon* |
| `geo_distance / 10k` | `python_fallback_slower` | `7,330.000` | `7,757.301 / 8,520.399` | `4,534.100` | `manual_cpp`: `828.767`, `numpy` (`strict_correct=False`): `1,616.380`, `numba`: `18,518.800`, Codon* list: `2,003.255` | **Default fallback (`0.94x`)**; forced `1.62x` (**regressed** vs unsafe `080125e` `2,408.667 us` and `+12.9%..+33.5%` vs `582afcd` due to validated list copy + bounds/index parity) |
| `ar_spatial / 10k` | `python_fallback_slower` | `3,433.950` | `3,499.700 / 9,875.700` | `5,419.500` | `manual_cpp`: `238.081`, `numpy`: `2,417.600`, `numba`: `26,187.311`, Codon* list: `1,887.885` | **Default fallback (`0.98x`)**; forced **`0.63x` slower than CPython** due to 3 validated list copies |
| `rag_chunker / large` | `python_fallback_slower` | `169.572` | `185.014 / 260.062` | `--` | Codon*: `1,310.105` | **Default fallback (`0.92x`)**; `private_entry` native route intentionally withdrawn (`None`) |

\* *Codon `0.20.6` methodology (`run_codon_jit_suite.py`, peak RSS `1,228,084 KB`, JIT compile `5.52 s - 17.87 s`): compilation overhead and `2-10` warmup calls are excluded from warm timings, and all `7` kernels (`quant`, `ar_spatial`, `geo`, `pdf`, `pii`, `ocr`, `rag`) were verified output-equivalent (`7/7`) against CPython `original.py`. However, `cj_pdf` (`10.86 s`) and `cj_pii` (`13.15 s`) reproduce the unoptimized Python character-loop `result += ch` idiom verbatim; under Codon's immutable `str` representation this causes `O(N^2)` reallocation/copying, whereas CPython uses amortized in-place `_PyUnicodeWriter` resizing and Mojo Hotloop lowers `+=` onto a mutable `String` (`reserve_bytes`). Equivalent output is therefore not an optimized Codon string implementation, and this single-process harness is not directly substitutable for 5-process public `@hotloop` timings.*

**Classification:** **PASS** (matched empirical evidence and explicit regression disclosures).

---

## 6. Legal, Licensing & DCO Governance

| Governance Check | Observed State | Classification |
|---|---|---|
| Developer Certificate of Origin (`.github/workflows/contributor-assistant.yml`) | Enforces `^Signed-off-by:\s+([^\n<]+)\s+<([^@>\n\s]+@[^@>\n\s]+)>/mi` on every PR commit. All `10` commits across `PR 1` (`ad8c8673`), `PR 2` (`2c7d9b5`), and `PR 3` carry authorized `Author`, `Committer`, and `Signed-off-by: Gaurav Kumar Singh <gorky117@gmail.com>`. | **PASS** |
| `mojo-hotloop` package license | `pyproject.toml` and `LICENSE` declare `Apache-2.0`; no SDK binaries are bundled inside `mojo-hotloop` wheels or sdists. | **PASS** |
| External Mojo/MAX SDK & compiled `.so` artifacts | `mojo`/`mojo-compiler`/`mojo-lldb-libs` (`1.2.0`) & `modular` (`26.7.0`) declare `LicenseRef-MAX-Platform-Software-License` without shipping `.dist-info` license text; compiled `.so` files dynamically link `libKGENCompilerRTShared.so`, `libMSupportGlobals.so`, and `libAsyncRTRuntimeGlobals.so`. `docs/THIRD_PARTY_NOTICES.md` separates local SDK usage and explicitly prohibits redistributing precompiled `.so` artifacts without claiming unverified rights. | **PASS** (accurately disclosed) |
| Modular trademark notice | `NOTICE` and `docs/THIRD_PARTY_NOTICES.md` remove unverified `"used under license"` phrasing, retain independence/no-endorsement disclaimers, and use nominative attribution aligned with `modular.com/legal/trademark`. | **PASS** |

---

## 7. Packaging & Artifact Integrity

* Wheel/sdist generation in `verify.sh` uses clean `git archive <commit>` sources, `SOURCE_DATE_EPOCH=$(git show -s --format=%ct <commit>)`, offline `setuptools.build_meta`, `audit/verify_patch_artifacts.py`, byte-for-byte `cmp` identity of `sdist -> wheel` rebuilds, and clean venv installation verified by `offline_probe.py` and `pip check`.
* Prior verified single-branch integration commit `c5661070` produced `mojo_hotloop-0.2.1-py3-none-any.whl` (`56,940` bytes, `sha256: d0329ebfb...`) and `mojo_hotloop-0.2.1.tar.gz` (`99,392` bytes, `sha256: a4f9cff28...`). Rebuilt artifacts and exact SHA-256 digests from the final `codex/pr3-v021-m0-ci` `HEAD` commit are verified **after** this commit lands so no stale digest is cited for newly built packages.

**Classification:** **PASS** (verified offline build reproducibility; final post-commit digests recorded in release handoff log).

---

## 8. Documentation & Claims Integrity

* `README.md`, `CHANGELOG.md`, `ROADMAP.md`, `docs/SUPPORTED_SYNTAX.md`, `docs/CURRENT_BENCHMARKS.md`, `docs/PRE_M0_CREDIBILITY_REVIEW.md`, `docs/M0_NATIVE_CI_AND_REFERENCE.md`, `docs/THIRD_PARTY_NOTICES.md`, and `examples/numpy_vector/README.md` accurately state:
  * 100% offline AST compilation & `mojo build` execution (zero Gemini/OpenAI/AI runtime or Rust dependency).
  * Narrow qualified native scope (`Linux x86-64`, CPython `3.12.16`, Mojo `1.2.0`).
  * Complete withdrawal of unsafe native zero-copy `ndarray`/`array.array`/`memoryview`/shared-container paths in `v0.2.1`.
  * Preservation of `v0.1.0` / `v0.2.0` historical reports alongside `11` documented frozen `v0.2.0` compatibility failures (`75 passed / 11 failed`).
* `python3 benchmarks/generate_benchmark_reports.py --check` and `python3 tools/check_review_docs.py` validate zero table drift and zero broken local links across both `PR 2` and `PR 3`.

**Classification:** **PASS**.

---

## 9. Roadmap Reconciliation

* [`ROADMAP.md`](../ROADMAP.md) (updated cleanly in `PR 2`) adds the unpublished `v0.2.1` corrective milestone and explicitly defers NumPy/SIMD Phase F.2 work (`codex/phase-f2-security-repair` at `61b0c36` / `aa8a21e`) to `v0.3.0`.
* [`ROADMAP_EXECUTION_STATUS_2026-11-25.md`](ROADMAP_EXECUTION_STATUS_2026-11-25.md) (added in `PR 3`) reconciles `R1`, `Pre-M0`, `M0`, and `M1`-`M6` using granular statuses (`Locally implemented`, `Locally verified`, `PR prepared`, `PR submitted`, `Hosted CI verified`, `Merged`, `Released`, `Blocked`).

**Classification:** **PASS**.

---

## 10. Stacked PR Plan & Exact Proposed GitHub Actions

Local branches are cleanly separated with zero cross-contamination:

1. **PR 1 (`codex/pr1-v021-runtime` -> `main`):** `ad8c86739f3488d9a89bd8cc8474d4a4923036b5` -- Corrective `v0.2.1` runtime, security/ABI/cache/binding/return-ownership/math/list-exception parity, `pyproject.toml` (`0.2.1`), `.github/workflows/ci.yml` version check (`0.2.1`), and R1 evidence gates. (`8` commits.)
2. **PR 2 (`codex/pr2-v021-docs` -> `codex/pr1-v021-runtime`):** `2c7d9b52ba97d9c81953111b483909f4b2a62953` -- Pre-M0 public documentation, benchmark disclosures, notices, and reconciled `ROADMAP.md`. (`1` commit.)
3. **PR 3 (`codex/pr3-v021-m0-ci` -> `codex/pr2-v021-docs`):** `HEAD` of `/home/gaurav/mojo-hotloop-pr3-ci` -- M0 GitHub-hosted native CI (`.github/workflows/ci.yml`), frozen 25-function `reference/m0-v1` corpus, `tools/*`, `README.md` M0 CI link alignment, [`ROADMAP_EXECUTION_STATUS_2026-11-25.md`](ROADMAP_EXECUTION_STATUS_2026-11-25.md), and this report. (`1` commit.)

**GitHub Rulesets Observed (`080125e` / `origin`):**
* Ruleset `27367642` (`main`): requires PR review, conversation thread resolution, extra approval for unattributed changes, and status check `"Python Tests (Python 3.12)"`.
* Ruleset `27367632` (`refs/tags/v*`): protects release tags.

**Classification:** **PASS** (local PR preparation) / **BLOCKED** (remote submission, CI execution, merge, tagging).

---

## 11. Complete Gate & Test Ledger (Summary)

*Full post-final-commit run results on `codex/pr3-v021-m0-ci` HEAD are executed and reported directly upon completing this commit, including:*
* `audit/release_acceptance/verify.sh` (`HOTLOOP_EXPECTED_PYTEST_COUNT=380`): `380` current pytest tests, `129` frozen `c2aebd78` remediation checks, `86` frozen `v0.2.0` checks (`75 passed / 11 documented expected failures`: `9` intentional native-route safety withdrawals + `1` obsolete `2 ** -1` `ValueError` + `1` obsolete `>5x` speed assertion), `51+1/52` adversarial compiler tests, `7,220/7,220` application checks, `6/6` cache invalidation tests, `15/15` `parity_probe.py`, `identity_probe.py`.
* M0 & semantic gates: `tools/native_ci_preflight.py`, `tools/native_ci_smoke.py`, `tools/run_m0_reference.py` (`25/25`), `tools/run_m0_reference.py --no-build --samples 1` (`46` failures), `tools/check_math_semantics.py` (`15/15`).
* Standalone gates: `audit/exception_parity/gate.py` (`390` checks), `audit/math_correctness/original_gate.py` (`15` checks), `run_adjacent.py` (`342` checks), `run_focused.py` (`111` checks), `audit/two_blocker/gate.py` (`1,095` checks).
* Documentation & packaging gates: `benchmarks/generate_benchmark_reports.py --check`, `tools/check_review_docs.py`, `audit/verify_patch_artifacts.py`, byte-for-byte `sdist -> wheel` rebuild (`cmp`), `offline_probe.py`, `pip check`, `compatibility.py` (`3.12.16` and `3.12.3`).

**Classification:** **PASS** (local execution post-final commit) / **NOT VERIFIED** (hosted GitHub CI).

---

## 12. Remaining Known Defects, Withdrawals & Regressions

1. **Withdrawn `v0.2.0` capabilities (`11` frozen `v0.2.0` failures):** NumPy `ndarray` zero-copy pointer borrowing, arbitrary buffer exporters (`array.array`, `memoryview`), mutating/aliased container native execution (`rag_chunker`), and obsolete `2 ** -1` / `>5x` micro-assertions.
2. **Performance regressions & overhead:** `geo_distance` 10k forced (`+12.9%..+33.5%` vs `582afcd`, `4,534.1 us` vs `2,408.667 us` unsafe `080125e`); `ar_spatial` 10k forced (`5,419.5 us`, `0.63x` slower than CPython); tiny-call FFI overhead (`quant_backtest / 0`: `15.319 us` vs `0.093 us`); default safe Python fallback on collection/string workloads (`rag_chunker`, `ocr_matcher`, `geo_distance`, `ar_spatial`).
3. **Excluded math/string forms (intentional safe fallback / `strict` refusal):** `math.floor`, `math.ceil`, `math.pow`, 2-arg `math.log`, NumPy scalars, custom `__float__`/`__index__` objects, aliased stdlib imports, bounded/keyword `startswith`/`endswith`, and variadic keywords.
4. **Shared host cache note:** `/home/gaurav/.cache/modular/.mojo_cache/...` contained a pre-existing 0-byte file on this workstation; isolated `XDG_CACHE_HOME` builds cleanly without touching shared host state.

**Classification:** **PASS** (honestly disclosed; non-blocking to corrective `v0.2.1` scope).

---

## 13. Owner Authorization & Release Gate Checklist

Before any remote push, PR creation, or `v0.2.1` release:

- [x] **DCO Attestation:** Authorized and applied `Gaurav Kumar Singh <gorky117@gmail.com>` across `Author`, `Committer`, and `Signed-off-by:` trailers on all `10` commits in PR 1, PR 2, and PR 3.
- [x] **Legal / Trademark Disclosures:** Removed unverified license phrasing and prohibited precompiled `.so` redistribution in `NOTICE` and `docs/THIRD_PARTY_NOTICES.md`.
- [ ] **Push & Open Stacked PRs:** Push `codex/pr1-v021-runtime` -> open PR 1 against `main`, then PR 2, then PR 3.
- [ ] **Hosted CI Pass:** Verify green `Python Tests (Python 3.12)`, `Native Verification`, and `DCO` checks on GitHub Actions (`ubuntu-24.04`).
- [ ] **Final Release Mechanics (Post-Merge):** Merge PR 1 -> PR 2 -> PR 3 sequentially, tag `v0.2.1` from clean `main`, create GitHub Release with final SHA-256 wheel/sdist digests, and update PyPI / CI badge links only after live pass.

**Classification:** **BLOCKED** pending owner execution.

---

## 14. Post-`v0.2.1` Phase F.2 / `v0.3.0` Handoff

Experimental safe NumPy zero-copy & SIMD optimization work remains cleanly isolated on `/home/gaurav/mojo-hotloop-f2-security-repair` (`codex/phase-f2-security-repair` at `61b0c36` / `aa8a21e`). It resolves PEP 3118 buffer safety, return provenance, and dispatch blockers for future `v0.3.0` evaluation, and must **only** be rebased/reviewed against `main` after `v0.2.1` merges and ships.
