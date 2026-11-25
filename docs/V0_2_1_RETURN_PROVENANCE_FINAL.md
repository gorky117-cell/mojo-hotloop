# v0.2.1 return provenance: final engineering decision

22 November 2026. **B. CORRECTNESS RESTORED — PERFORMANCE REGRESSION REMAINS.**

The nine supplied constant-identity failures are fixed through native execution. PII regains its original default-native route and substantial medium/large acceleration. This is not a regression-free performance result: short/medium PII and short backtests have higher median latency than security remediation. Stop this iteration for owner review; no release action is authorized.

Runtime implementation: **5b55740bf6a3579fcdedfd9d79ba384c61c852e2**. Benchmark/verification harness freeze: **5b55740bf6a3579fcdedfd9d79ba384c61c852e2**. Final report/evidence commit: **$Format:%H$** (expanded to the exact commit by git archive; the Git source stores this export-subst marker). The final commit adds reporting tools and documentation/evidence only relative to that harness freeze; all 11 installed runtime files match the implementation commit byte for byte.

Isolated branch/worktree: codex/v021-return-provenance, /home/gaurav/mojo-hotloop-v021-return-provenance, created from 1a59efd4c2d6917fb6c1af06a15e7a403ae57e61. No protected branch, release tag or prior checkout was modified. All pre-existing refs remain identical and their commit objects recoverable; see preservation.json.

## 1. Root cause and the nine original failures

CPython's module compilation can share an actual float object among a function's default, its own code constants and a helper's code constants. The old native ABI reconstructed a Float64 as a new Python float. Its value was right, but it lost the returned object's ownership and identity. Argument-only metadata could not describe these executed constant returns.

Equal values are insufficient evidence of shared ownership. The repair maps exact AST source positions to LOAD_CONST/RETURN_CONST slots in compiled Python code, fingerprints the expected code, then resolves those slots against the **actual callable's actual code object** at first native use. The returned owner is an object from that real pool, never a numeric/text lookup. Defaults pass through ordinary signature binding; they are not substituted for same-valued code constants.

The supplied test file is byte-identical to be8c85d6's original file. Its original conservative strict-mode catch was not weakened; a separate probe requires each strict case to complete natively.

| Function | Modes | Installed 1a59 before | Proposed |
|---|---|---|---|
| literal_default | default, forced, strict | 3 identity failures | 3 native passes |
| local_constant | default, forced, strict | 3 identity failures | 3 native passes |
| helper_default | default, forced, strict | 3 identity failures | 3 native passes |
| Total | 9 cases | **9 failed** | **9 native, 0 fallback** |

Both runs use CPython 3.12.16. before-nine.log preserves all failing assertions; nine-native.json records identity, backend and counters after repair.

## 2. Compiler-wide design and safety

Five runtime files change: _provenance.py, _return_origin.py, ast_transpiler.py, decorator.py and _native_cache.py. There are no application-name conditions, replacement PII/backtest algorithms, public API additions or numerical shortcuts.

The internal result carries its value plus an origin tag and slot:

- Argument origin: return the actual bound argument.
- List-element origin: return the actual item held by the validated immutable reference snapshot.
- Code-constant origin: return the real constant held by the owning callable's code object.
- Computed value: construct the correct Python value, including explicitly fresh string allocation where required.
- Unknown origin: refuse native execution before the body, with observable fallback or strict rejection.

The owner context is built lazily so helpers defined later in the module can be resolved. A standard-library-only compiler pass compiles source to code metadata but never executes that source. Actual function/code fingerprints, actual helper bindings and intrinsic/math bindings must match. Strong references retain owners, code and constants. Root code/default identity is checked before argument binding; reachable helper/code/default and builtin/math bindings are checked before each native body. Rebinding, unsupported signatures or ambiguous layouts cannot silently reuse an earlier owner proof. Decorated helper calls are refused because their wrapper policy is not equivalent to their underlying code; plain helper calls remain supported. Equal-valued distinct code constants, imports and defaults are tested independently.

Origin reconstruction does not run the original function again. Augmented string assignment captures its RHS once before metadata inspection and builder writes; a generated-source regression test verifies one helper call site. Existing pure-arithmetic overflow fallback remains an older policy, not a new reconstruction mechanism.

This implementation intentionally qualifies **CPython 3.12.16 with 30-bit PyLong digits**. Other interpreter profiles safely refuse native entry; this is a significant release/platform limitation, not a claim of language-wide constant interning. Existing exact-type/list snapshot, range and surrogate guards remain. No new raw-pointer borrowing, writable-array access or GIL release was added; ndarray, array.array and memoryview semantics still fall back on this security-derived branch.

The hidden owner-context ABI bumps cache schema 3 to 4. Existing source/generated-code/compiler/toolchain/settings/ABI hashes, binary digest checks, trusted paths and pinned verified-inode loading remain. Real c2 and 1a59 artifacts are rejected **before** the loader; default execution remains correct and strict mode rejects. The standalone corruption/invalidation audit passes all six tests.

## 3. String-origin proof and reusable cases

The executed string path carries ownership, rather than inferring it from equal output text:

- A normalized full step-one slice preserves its proven input/constant owner.
- Empty-string concatenation preserves the selected operand's origin on that executed branch.
- Both nonempty operands produce a new string.
- Aliases and helper results propagate the actual owner metadata.
- Builders update origin alongside writes; emptiness uses constant-time byte length.
- Extended slices and integer formatting explicitly force a fresh Python string where SDK boxing could otherwise produce a cached one-character object.
- Ambiguous selections, unsupported helpers and escaping shared containers refuse safely.

These rules follow the qualified interpreter's behavior, not arbitrary interning assumptions. Primary implementation references: [CPython Unicode slicing and concatenation](https://raw.githubusercontent.com/python/cpython/v3.12.16/Objects/unicodeobject.c), [CPython integer remainder](https://raw.githubusercontent.com/python/cpython/v3.12.16/Objects/longobject.c).

Independent tests also found that integer remainder can return the original left operand. Its reusable metadata rule follows the qualified interpreter's digit-count/leading-digit shortcut, excludes its one-digit fast path, and accounts for sign adjustment. The numerical remainder is evaluated once. Boundary tests plus 1,200 deterministic signed-64-bit identity/parity probes pass; this rule is not a function-specific exception.

A late independent check found a real policy mismatch: a helper decorated in strict mode before its native artifact existed correctly raised in Python, while a newly compiled parent inlined its body and returned a value. Three unchanged before/after probes reproduce the wrong result in default/forced/strict parent modes on 741053f. The final runtime refuses decorated-helper parents before native execution; default/forced execution preserves the actual helper exception, and strict rejects. All three regression tests require an available compiled parent entry, so ordinary missing-artifact fallback cannot manufacture a pass. Plain helper constants and PII validators remain native. Earlier measurements and all three failures are retained under pre-helper-gate.

The 111 new pytest cases cover distinct equal-valued owners, actual helper constants, folded constants/signed zero, keyword/default binding, imports and code replacement, loops/early returns, slices/builders/concatenation, list-element lifetime, remainder, mutation/sharing refusal, exception/effect order, rebinding, unsupported signatures and strict/forced behavior. These are test cases, not 108 newly supported functions.

## 4. Matched benchmark protocol

Original PII and backtest bodies and payload generators are unchanged. Five independent processes **per runtime** for each family (15 primary plus 15 companion processes) run in a network-isolated namespace, with rotating/reversed runtime order and identical Numba/manual-C++ setup. All timed PII payload hashes match across versions. Input/output types and values are checked before timing; backtests additionally compare float bits and required input identity.

Environment: Intel Core i5-8265U, WSL2 x86_64, CPU affinity 7, CPython 3.12.16, Mojo 1.2.0 (2016d0cd), NumPy 2.5.4, Numba 0.68.1. Numba uses fastmath=False. The unchanged expert C++ reference comes from 581a29ee's competitive audit and uses -O3 -fno-fast-math -ffp-contract=off. Neither C++ nor the expert regex scanner is automatic Hotloop output.

Each measurement has 15 calibrated batches. Table cells are **median of five process p50s / pooled p95 of 75 batch means, in microseconds**. They are not individual-call tail latencies. Every process and batch is retained; none was removed as an outlier. This laptop/WSL environment has substantial variability, especially at 100,000 ticks. These results establish workload-specific behavior, not universal performance guarantees.

## 5. PII recovery and competitive results

| Characters | CPython | Security native* | Return-origin fallback | Proposed native | Strict regex | CPython / proposed |
|---:|---:|---:|---:|---:|---:|---:|
| 53 | 22.086 / 43.022 | 11.189 / 11.853 | 34.580 / 42.088 | 15.640 / 25.735 | 10.502 / 16.670 | 1.41x |
| 8,192 | 4271.033 / 6629.700 | 637.430 / 746.900 | 4419.267 / 5119.967 | 767.043 / 1057.457 | 1661.987 / 2112.434 | 5.57x |
| 100,000 | 51818.798 / 136587.742 | 7686.700 / 10304.351 | 51533.001 / 60455.550 | 7970.500 / 12575.899 | 18118.100 / 32705.398 | 6.50x |

*The security runtime is correct on these timed payloads, but fails the separate unredacted-number owner probe. It is not globally strict-compatible. Proposed passes both that probe and the original fixtures.

All 1,019 original PII fixtures execute natively and pass. An additional qualification reuses their original verifier/generators and adds 19 Unicode, surrogate, NUL, boundary and owner cases: **1,037 native + 1 safe surrogate fallback**, all value/type/owner checks correct. The manually adapted scanner passes the same 1,038 cases. The old regex.sub reference is not used for strict ranking.

Proposed is about **5.57x / 6.50x** faster than CPython at 8,192 / 100,000 characters using table medians, and about **2.17x / 2.27x** faster than this strict scanner. At 53 characters the scanner wins. Relative to security, proposed medians are 39.8% slower at 53 characters, 20.3% slower at 8,192 and 3.7% slower at 100,000. The short-input regression exceeds 10% in all five paired trials; medium exceeds it in three. Substantial native acceleration is restored, with these losses explicitly retained.

## 6. Backtest correctness, competitors and overhead

| Ticks | CPython | Security* | Return-origin | Proposed | Warm Numba* | Manual C++* |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0.077 / 0.082 | 10.353 / 31.079 | 10.553 / 11.496 | 11.541 / 12.195 | 0.207 / 0.246 | 0.081 / 0.087 |
| 100 | 23.004 / 23.853 | 10.476 / 30.481 | 10.981 / 11.427 | 12.021 / 13.564 | 0.421 / 0.451 | 0.285 / 0.306 |
| 10,000 | 2357.550 / 2671.060 | 41.444 / 54.561 | 41.648 / 47.347 | 41.917 / 54.103 | 28.558 / 30.660 | 32.347 / 34.610 |
| 100,000 | 23540.749 / 31075.750 | 385.258 / 504.500 | 387.547 / 421.353 | 395.830 / 424.026 | 369.019 / 482.794 | 378.300 / 452.842 |

*At zero ticks, security, Numba and manual C++ return a new float: their timing is **value-only and disqualified from the strict identity ranking**. Proposed and return-origin return the exact price object. At positive ticks the measured results have matching Python float type and bits; no fast-math relaxation was used. Original exception/boundary fixtures also pass.

CPython remains the clear winner at zero ticks. Proposed public execution is about 1.91x / 56.24x / 59.47x faster than CPython at 100 / 10,000 / 100,000 ticks using table medians. It loses to warmed Numba and manual C++ at every positive measured size by the median. At 100,000 ticks it loses to Numba in 4/5 paired processes and C++ in 4/5. These are comparisons on the measured contracts, not proof that competitors preserve every untested Python exception or alias.

Proposed call layers, same units/protocol:

| Ticks | Public | Verified private entry | Prepared raw entry diagnostic |
|---:|---:|---:|---:|
| 0 | 11.541 / 12.195 | 3.228 / 3.393 | 2.584 / 2.718 |
| 100 | 12.021 / 13.564 | 3.513 / 3.568 | 2.855 / 3.902 |
| 10,000 | 41.917 / 54.103 | 31.492 / 38.244 | 30.915 / 35.239 |
| 100,000 | 395.830 / 424.026 | 373.756 / 402.071 | 372.230 / 554.203 |

The verified private entry still includes Python owner checks, numerical/input conversion, native computation and reconstruction. The prepared raw diagnostic uses the already-proven context with stationary callable bindings; it is not an ordinary public path or a proposed safety bypass. At zero ticks, public minus verified-private medians is 8.31 us, and verified-private minus prepared medians is 0.64 us. At 100 ticks the latter is 0.66 us. These differences locate overhead but are not additive cycle accounting. Large-size batch/process variability prevents precise additive decomposition.

The ordinary generated numerical Mojo body is byte-identical across the three revisions. The actually called tagged kernel does add bookkeeping: optimized native kernel size/instruction count grows from **443 bytes/105 instructions** (security), through **484/112** (return-origin), to **536/120** (proposed). Floating arithmetic/comparison/conversion instruction counts match, with one additional register move. New constant-state return metadata introduces additional state/control work around cash updates. This is not zero-cost metadata and is retained in generated patches/disassembly.

## 7. Regressions, causes and stop decision

| Workload | Proposed process-p50 range (us) | Change vs security median | Trials >10% slower |
|---|---:|---:|---:|
| pii, 53 | 14.713–25.252 | +39.8% | 5/5 |
| pii, 8,192 | 652.300–1004.671 | +20.3% | 3/5 |
| pii, 100,000 | 7723.800–12182.499 | +3.7% | 1/5 |
| backtest, 0 | 11.457–11.962 | +11.5% | 3/5 |
| backtest, 100 | 11.779–12.192 | +14.7% | 3/5 |
| backtest, 10,000 | 40.919–52.832 | +1.1% | 2/5 |
| backtest, 100,000 | 385.279–420.177 | +2.7% | 1/5 |

In this final cohort, aggregate security-baseline regressions above 10% are zero ticks (+11.5%), 100 ticks (+14.7%), short PII (+39.8%) and medium PII (+20.3%). Short PII exceeds +10% in all five paired processes; the other three do so in three processes. Relative to return-origin, no backtest aggregate exceeds +10% (the zero/100-tick medians are +9.4%/+9.5%). The earlier pre-helper-gate cohort had a +15.9% 10,000-tick regression; the final cohort is +1.1%. The late helper restriction is not exercised by these plain-helper workloads, so that difference must not be presented as a demonstrated loop optimization. Both complete cohorts and all variability remain in evidence.

The established causes are extra actual-owner validation/Python Entry dispatch and generated return metadata; the disassembly proves additional integer/control work, not altered floating computation. Exact attribution of the entire latency delta to individual operations was not established. CPython and competitors also vary between runs, so attributing every percentage point to metadata would be unjustified. Tiny Python work remains much cheaper than any wrapper. No new size threshold, double execution or runtime profiling was introduced.

PII medium/large native acceleration is recovered, so this is not blanket fallback. However, the repeatable short-PII regression and other disclosed latency/cold-cost increases preclude outcome A. Stop with **B** rather than launch a general optimization cycle or discard safety/owner checks.

## 7a. Other five applications: original payload regression checks

These supplementary measurements retain all three original text/candidate payload sizes, and the original trail/cloud generators at 100 / 1,000 / 10,000 points. PDF/RAG sizes are 1,024 / 10,240 / 100,000 characters; OCR sizes are 20 / 200 / 2,000 candidates. Inputs remain Python lists for the spatial/collection comparisons, without undocumented buffer conversion.

Five independent processes per runtime use nine batches per case. Cells are process-median p50 / pooled p95 of 45 batch means (us). Default and forced routes are separate. This is a regression check against the earlier runtimes and CPython, not a new all-competitor ranking.

| Application / original size | Public mode | CPython | Security public | Return-origin public | Proposed public | Actual proposed route | Change vs security |
|---|---|---:|---:|---:|---:|---|---:|
| pdf_cleaner / small | default | 195.938 / 200.891 | 42.157 / 56.279 | 43.025 / 51.189 | 42.689 / 46.310 | native | +1.3% (0/5 >10%) |
| pdf_cleaner / medium | default | 1952.900 / 1992.800 | 321.673 / 395.434 | 343.714 / 385.450 | 334.600 / 351.471 | native | +4.0% (0/5 >10%) |
| pdf_cleaner / large | default | 18837.400 / 19264.999 | 3137.003 / 3479.699 | 3111.100 / 3603.102 | 3173.300 / 3624.900 | native | +1.2% (0/5 >10%) |
| rag_chunker / small | default | 3.621 / 4.028 | 10.971 / 12.791 | 10.827 / 11.429 | 11.227 / 14.020 | python_fallback_slower | +2.3% (1/5 >10%) |
| rag_chunker / medium | default | 22.263 / 26.599 | 29.917 / 34.711 | 30.098 / 30.978 | 31.165 / 37.294 | python_fallback_slower | +4.2% (1/5 >10%) |
| rag_chunker / large | default | 135.558 / 160.841 | 140.788 / 164.433 | 145.463 / 149.269 | 145.785 / 170.600 | python_fallback_slower | +3.5% (1/5 >10%) |
| ocr_matcher / small | default | 100.558 / 103.928 | 106.440 / 113.217 | 110.760 / 126.695 | 109.505 / 158.964 | python_fallback_slower | +2.9% (1/5 >10%) |
| ocr_matcher / small | forced | 100.558 / 103.928 | 26.583 / 27.910 | 27.631 / 31.018 | 30.221 / 42.801 | native | +13.7% (4/5 >10%) |
| ocr_matcher / medium | default | 1019.225 / 2126.567 | 1004.850 / 1157.000 | 1108.524 / 1249.700 | 1033.800 / 1388.000 | python_fallback_slower | +2.9% (1/5 >10%) |
| ocr_matcher / medium | forced | 1019.225 / 2126.567 | 185.004 / 193.650 | 203.512 / 236.757 | 196.188 / 265.611 | native | +6.0% (1/5 >10%) |
| ocr_matcher / large | default | 1674.400 / 2217.100 | 1689.249 / 1746.850 | 1846.299 / 2062.951 | 1734.800 / 2258.800 | python_fallback_slower | +2.7% (1/5 >10%) |
| ocr_matcher / large | forced | 1674.400 / 2217.100 | 656.514 / 708.943 | 717.917 / 829.460 | 702.033 / 870.680 | native | +6.9% (2/5 >10%) |
| geo_distance / 100 | default | 56.962 / 61.416 | 64.218 / 69.128 | 63.866 / 67.905 | 65.369 / 71.560 | python_fallback_slower | +1.8% (2/5 >10%) |
| geo_distance / 100 | forced | 56.962 / 61.416 | 42.417 / 43.608 | 41.378 / 44.712 | 44.316 / 48.468 | native | +4.5% (2/5 >10%) |
| geo_distance / 1000 | default | 610.150 / 650.229 | 619.572 / 632.050 | 616.229 / 647.443 | 625.975 / 752.288 | python_fallback_slower | +1.0% (1/5 >10%) |
| geo_distance / 1000 | forced | 610.150 / 650.229 | 372.777 / 383.008 | 365.000 / 388.817 | 382.500 / 452.700 | native | +2.6% (2/5 >10%) |
| geo_distance / 10000 | default | 6233.100 / 10047.000 | 6083.102 / 6418.801 | 6287.099 / 6405.700 | 6270.100 / 9092.800 | python_fallback_slower | +3.1% (2/5 >10%) |
| geo_distance / 10000 | forced | 6233.100 / 10047.000 | 3621.902 / 3844.701 | 3606.200 / 3793.000 | 3738.300 / 4737.300 | native | +3.2% (2/5 >10%) |
| ar_spatial / 100 | default | 24.572 / 38.504 | 36.943 / 39.167 | 38.227 / 42.522 | 37.306 / 43.951 | python_fallback_slower | +1.0% (1/5 >10%) |
| ar_spatial / 100 | forced | 24.572 / 38.504 | 57.185 / 61.474 | 58.951 / 60.688 | 59.979 / 82.253 | native | +4.9% (2/5 >10%) |
| ar_spatial / 1000 | default | 276.356 / 318.823 | 281.759 / 291.347 | 288.871 / 300.627 | 289.582 / 339.500 | python_fallback_slower | +2.8% (2/5 >10%) |
| ar_spatial / 1000 | forced | 276.356 / 318.823 | 446.273 / 466.191 | 454.044 / 461.673 | 462.010 / 517.167 | native | +3.5% (2/5 >10%) |
| ar_spatial / 10000 | default | 2818.700 / 3126.799 | 2731.900 / 2892.700 | 2814.400 / 2911.600 | 2852.900 / 3281.300 | python_fallback_slower | +4.4% (2/5 >10%) |
| ar_spatial / 10000 | forced | 2818.700 / 3126.799 | 4323.300 / 4629.600 | 4298.700 / 4525.200 | 4479.000 / 5009.800 | native | +3.6% (2/5 >10%) |

Repeatable >10% median regressions (at least four paired trials above 10%): ocr_matcher/small/forced (+13.7%, 4/5 trials >10%). All other positive/negative changes remain in the table and raw evidence. Owner checks and origin state add overhead on native routes; Python fallback timings also vary, so the percentages are not exact per-instruction causal attribution.

Proposed supplementary measurement counters: **17,814 native / 25,635 fallback**. Timed values/types passed; scalar float bits matched in all recorded supplementary cases: **True**. Geographic/AR qualification still uses the original tolerance contract and makes no universal transcendental-bitwise guarantee. Forced AR native calls lose to Python at these sizes; default fallback is appropriate. Some forced OCR/geographic payloads benefit from native execution, but this limited corpus does not justify a broad dispatch-policy change.

## 8. Compilation, caching and memory costs

| Scope, median (process range) | Security | Return-origin | Proposed |
|---|---:|---:|---:|
| Backtest cold AOT build | 2.737 s (2.549–3.429) | 2.550 s (2.447–2.609) | 2.642 s (2.566–2.721) |
| Backtest verified build-cache hit | 6.756 ms (6.284–7.404) | 10.272 ms (9.892–10.423) | 12.808 ms (12.193–13.728) |
| Backtest import after building | 45.363 ms (44.003–50.290) | 43.750 ms (42.729–43.926) | 44.839 ms (43.837–47.696) |
| Backtest first public call after import | 248.500 us (224.100–926.200) | 288.500 us (243.700–1185.800) | 420.800 us (335.800–903.600) |
| PII cold AOT build | 2.106 s (1.978–3.057) | 2.011 s (1.926–2.155) | 2.431 s (2.246–6.613) |
| PII verified build-cache hit | 15.906 ms (14.476–18.327) | 34.058 ms (30.511–37.839) | 52.615 ms (50.139–112.145) |
| PII first public call after import | 52.500 us (46.900–56.900) | 316.100 us (217.500–635.900) | 509.200 us (426.500–1521.901) |
| Numba JIT after importing Numba | 0.622 s (0.438–1.758) | 0.454 s (0.436–0.531) | 0.461 s (0.458–0.525) |

Fresh interpreter + load + first zero-tick call, warm OS caches: baseline **0.783 s (0.765–0.932)**; origin **0.783 s (0.780–0.862)**; candidate **0.784 s (0.768–0.865)**. These are separate from imports performed in an already-running builder process.

A cold AOT build means a new Hotloop artifact/directory; SDK/OS caches were not flushed. Backend import precedes AOT timing. Numba import precedes its JIT timer. Repeated build-cache hits still transpile/fingerprint source before validating/reusing the binary; heavier provenance analysis especially raises PII cache-hit cost. These are real costs, not native execution time.

Approximate proposed AOT amortization, using median AOT build cost and CPython/public warm savings only: pii: 377,034 / 694 / 56 calls at 53 / 8,192 / 100,000; backtest: 240,584 / 1,142 / 115 calls at 100 / 10,000 / 100,000. Zero ticks never amortizes. Startup adds cost; these estimates are not dispatch rules.

Python-visible tracemalloc public peak medians: backtest 1,910/1,910/1,853/1,853 bytes in size order; pii 1,790/62,868/749,502 bytes in size order. These peaks exclude Mojo/native allocator storage and do not measure total allocations or prove absence of leaks. Per-engine/process observations and ranges are retained.

## 9. Exact dispatch and full validation

Original application verifiers report **7,220 passing scenarios**, with extra dispatch checks/calls. Actual wrapper counters are:

| Application (original scenarios) | Native counter | Fallback counter | Route details |
|---|---:|---:|---|
| quant_backtest (1,117) | 1,117 | 0 | Scalar native, including zero-tick identity and expected exception |
| pii_scrubber (1,019) | 1,019 | 0 | Default native |
| pdf_cleaner (1,020) | 1,020 | 0 | Default native |
| ocr_matcher (1,020) | 1,020 | 1 | 1,020 forced native; one default list fallback |
| geo_distance (1,014) | 1,014 | 1,028 | 1,014 forced list calls; ndarray/default-list fallbacks |
| ar_spatial (1,010) | 1,010 | 1,020 | 1,010 forced list calls; ndarray/default-list fallbacks |
| rag_chunker (1,020) | 20 | 1,022 | String outputs fall back; 20 integer-offset calls native; one strict refusal |

Totals: **6,220 native calls, 3,071 Python fallback calls**, plus the separate RAG strict refusal. Scenario counts are not native-call counts. Forced boxed-list calls are disclosed; ndarray fallbacks are never counted as native. Geographic/AR verification uses the original tolerances, not a universal bitwise transcendental claim. The observer captures wrapper factory returns without replacing compiler/runtime functions; the quantitative verifier's unchanged worker runs inside the already-isolated probe process.

Other explicit qualification results: nine constant cases **9 native/0 fallback**; argument-origin probe **41 native/0 fallback** (the default list case is explicitly excluded); PII qualification **1,037 native/1 fallback**. These overlap application cases and must not be added as unique-function coverage.

Benchmark measurement routines' public counter deltas, including calibration/correctness/allocation calls but excluding initial import probes and private calls:

| Measured runtime | Public native calls | Public fallback calls |
|---|---:|---:|
| baseline | 191,755 | 0 |
| origin | 163,600 | 25,110 |
| candidate | 183,865 | 0 |

The differing totals reflect calibrated iteration counts, not different payload sets.

| Verification | Actual result |
|---|---|
| Entire installed current pytest | **296 passed**, 81 warnings |
| New independent provenance tests | **111 passed**, included above |
| Original supplied nine tests | **9 passed**, unchanged; separate all-native probe |
| Original c2 security suite, unchanged | **129 passed**, 65 warnings |
| Seven original applications | **7,220 passing scenarios**, actual routes above |
| Adversarial compiler audit | **49 passes + 1 expected rejection**, zero unexpected failures |
| Standalone invalidation/corruption audit | **6 passed**; additional cache/security cases in pytest |
| Original published-defect probe | **15/15 equal**, including NumPy fallback, exceptions and float ordering |
| Mutation/list identity probe | Correct default/forced Python effects; strict refusal before mutation |
| Old c2 and 1a59 artifacts | Both refused before native loader; safe default and strict behavior |
| Offline wheel and sdist | Bare no-NumPy/no-google smoke and pip check pass; rebuilt wheel byte-identical |
| Artifact contents | 11 runtime files match Git, RECORD/licenses/metadata checked; no bundled native binary |
| Frozen v0.2.0 compatibility suite | **75 passed, 11 failed**, all original failing IDs retained |

Unfamiliar/E6 embedded workloads and the holdout file are unchanged; source-integrity.json records hashes. The current suite only updates route expectations where proven string/helper native execution is restored and retains value/identity assertions. No frozen workload was rewritten and no test was deleted or marked xfail. Raw logs and unified diffs retain their original whitespace; source/report formatting checks pass, while evidence integrity is checked by byte hashes.

All eleven historical failures remain visible individually:

| Historical test | Classification / observed failure |
|---|---|
| E6 test_02_distance_geometry_10_functions | Intentional representation restriction; manhattan_dist_arr ndarray falls back instead of old native expectation |
| E6 test_03_array_transforms_10_functions | Intentional representation restriction; running_prod_mod ndarray falls back |
| E6 test_05_validation_search_bitwise_12_functions | Intentional representation restriction; binary_search_arr ndarray falls back |
| E8 optimization test_10_dispatch_qualifier_cache_drift_safety | Obsolete native-qualification expectation for restricted ndarray inputs |
| Runtime security test_02_numpy_wrong_dtype_shape_and_non_contiguous_safety | Corrected unsafe coercion/intentional ndarray refusal conflicts with old native expectation |
| Runtime security test_07_inspect_dispatch_runtime_introspection | Obsolete native-counter/ndarray expectation |
| Unfamiliar test_01_scalar_numerical_10_functions | Intentional numerical-semantic restriction; mixed_arith_calc floor/mod path falls back |
| Unfamiliar test_02_numpy_and_collection_10_functions | Intentional representation restriction; dot_product ndarray falls back |
| Unfamiliar test_03_strings_unicode_and_helpers_10_functions | helper_composition ndarray falls back; reverse/stride strings now pass earlier cases |
| Unfamiliar test_04_kwargs_truthiness_exceptions_and_edges | Incorrect historical ValueError expectation for 2 ** -1 (Python returns 0.5) |
| Unfamiliar test_06_unfamiliar_speedups_summary | Invalid mandatory >5x historical benchmark threshold |

These eleven are nine withdrawn-native/obsolete-route expectations plus two invalid assertions, rather than new value/identity failures in the maintained subset. They remain compatibility/coverage limitations and are not silently waived as universal Python support.

During this run a counter-collector assumption about the quantitative verifier's subprocess caused a harness KeyError after its 1,117 scenarios passed. The collector was fixed and all seven suites rerun. An installed-byte inspector initially imported the source checkout because of its working directory; it was corrected to run outside the source tree before accepting all three exact package hashes. Neither failed harness attempt is used as benchmark or correctness evidence.

## 10. Remaining limits and release recommendation

Arbitrary Python object graphs, shared noncanonical objects inside newly constructed containers, indirect local-container escapes, unknown origin or decorated helpers, selected min/max aliases, nested definitions/unsupported signatures, source stream I/O, some mixed numerical semantics and arbitrary buffer exporters remain Python-only or rejected. Mutation/identity restrictions are intentional; strict and forced modes do not bypass semantic safety. Unsupported origin decisions precede the native body; no general Python sandbox guarantee is claimed.

Native qualification is tied to the tested CPython patch version/ABI. First-call owner preparation, compilation/cache costs, short-call overhead, source-size analysis costs and long-input variability must be documented before a release decision. Public typed-buffer binary interoperability from other branches is not silently included in this security-derived candidate.

**Do not label this branch performance-regression-free or automatically release it.** The nine active semantic blockers are repaired and native PII restored on the qualified subset; outcome B requires owner acceptance of the disclosed regressions and restrictions. Releasing c2 alone would retain the demonstrated object-identity defects, including zero-tick backtest and constant ownership; it cannot be recommended as a fully correct substitute.

For a later reviewed version, prioritize reducing repeated proven-owner/call overhead and reducing unnecessary origin state with evidence across the corpus, then expand escaping-container provenance. These are recommendations, not work authorized or started in this closeout. No new feature cycle, merge, push, tag or publication is performed.

## 11. Reproduction and evidence

Provision Mojo/Numba/test dependencies locally first. No downloads or AI inference are required. Run from this isolated checkout with fresh output directories and recorded installed baseline environments:

~~~bash
export V=/home/gaurav/mojo-hotloop/.venv
export MOJO_BIN="$V/bin/mojo" PATH="$V/bin:$PATH"
export PIP_NO_INDEX=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
unset PYTHONPATH HOTLOOP_STRICT HOTLOOP_FORCE_NATIVE HOTLOOP_STRICT_PERF
# Execute under unshare --net (as the workstation's local user).
bash audit/return_provenance/verify.sh /tmp/NEW_PROVENANCE_GATE 5b55740bf6a3579fcdedfd9d79ba384c61c852e2
PROPOSED_PY=/tmp/NEW_PROVENANCE_GATE/venv/bin/python
"$PROPOSED_PY" audit/return_provenance/nine_probe.py tests/test_return_origin_constants.py /tmp/NEW_NINE
"$PROPOSED_PY" audit/return_provenance/argument_probe.py /tmp/NEW_ARGUMENTS --expect-fixed
"$PROPOSED_PY" audit/return_provenance/qualify_scanner.py "$PWD" /tmp/NEW_SCANNER
python audit/return_provenance/benchmark.py /tmp/NEW_BENCH SECURITY_PY ORIGIN_PY "$PROPOSED_PY"
python audit/return_provenance/summarize.py /tmp/NEW_BENCH/results.json /tmp/NEW_SUMMARY.json
python audit/return_provenance/inspect_artifacts.py /tmp/NEW_BENCH SECURITY_PY ORIGIN_PY "$PROPOSED_PY" /tmp/NEW_ENV.json
python audit/return_provenance/startup.py /tmp/NEW_BENCH SECURITY_PY ORIGIN_PY "$PROPOSED_PY" /tmp/NEW_STARTUP.json
python audit/return_provenance/other_applications.py /tmp/NEW_OTHER SECURITY_PY ORIGIN_PY "$PROPOSED_PY"
python audit/return_provenance/summarize_other.py /tmp/NEW_OTHER/results.json /tmp/NEW_OTHER_SUMMARY.json
~~~

The nine/argument/scanner probes must use PROPOSED_PY, not a different system interpreter. SECURITY_PY is an offline wheel installation of c2aebd78; ORIGIN_PY is 1a59efd4; PROPOSED_PY is the installed verified runtime. Their complete runtime hashes and paths are in environment.json. inspect_artifacts.py checks runtime bytes against HEAD, or HOTLOOP_AUDIT_CANDIDATE_REV when set. This review sets it to the exact implementation commit. Package construction and dependency setup commands are in verify.sh; unset PYTHONPATH before probing; the inspector runs its Python -c checks outside the source checkout to prevent package shadowing.

[Other-application raw results](evidence/v0_2_1_return_provenance/other-applications.json), [other-application summary](evidence/v0_2_1_return_provenance/other-summary.json), [Raw performance](evidence/v0_2_1_return_provenance/performance.json), [summary and regressions](evidence/v0_2_1_return_provenance/performance-summary.json), [verification summary](evidence/v0_2_1_return_provenance/verification-summary.json), [all current pytest output](evidence/v0_2_1_return_provenance/verification/pytest.log), [original nine failures](evidence/v0_2_1_return_provenance/before-nine.log), [native nine results](evidence/v0_2_1_return_provenance/nine-native.json), [scanner qualification](evidence/v0_2_1_return_provenance/scanner-qualification.json), [installed environment and generated-code checks](evidence/v0_2_1_return_provenance/environment.json), [preserved refs](evidence/v0_2_1_return_provenance/preservation.json).

**Stopped for owner review. No automatic release approval.**
