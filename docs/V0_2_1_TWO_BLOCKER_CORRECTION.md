# v0.2.1 two-blocker correction

**A — BOTH BLOCKERS FIXED; ALL MANDATORY GATES PASS**

Technical gate result, finalized 23 November 2026 IST. This is local corrective engineering and owner-review material, not permission to release.

## Exact baseline and implementation

- Original R1: 69fa0bbfcfa772e3ceb35464286eea89f0a6398a.
- Frozen math implementation and direct parent: 0a6dacf668810443d5c4f825c7829f02be699a0d.
- Previous final math report: 649e9be53d3d67d5cbe2c6082a63148e44baa3e0, preserved on its original branch and in the earlier Windows review bundle.
- Corrected runtime and independently installed/tested source: aceec467cd846289568927a2783e7f50bfe1e21b.
- Final evidence/report commit: $Format:%H$ (expanded by git archive; use git rev-parse HEAD in the checkout).
- New branch/worktree: codex/v021-two-blocker-final at /home/gaurav/mojo-hotloop-v021-two-blocker.
- Only two runtime files changed: hotloop/ast_transpiler.py and hotloop/_return_origin.py, 26 insertions and 2 deletions. Existing decorator, argument validation, ownership, buffer and artifact-security implementation are unchanged.
- Tested environment: GIL-enabled CPython 3.12.16, Linux x86-64/WSL, Mojo 1.2.0 (2016d0cd).

No architecture, public API, dispatch threshold or general compiler optimization was introduced.

## The two causes and corrections

| Cause | Exact frozen behavior | Corrective rule | Corrected behavior |
|---|---|---|---|
| Generic explicit Float64 conversion at math calls admits String parsing | math.log on a str-annotated argument "2.0" returns 0.6931471805599453 natively in default, forced and strict modes; Python raises TypeError | Emit a numeric-only overloaded helper instead of the generic constructor | String operand has no matching native overload. Default/forced call Python once and raise TypeError; strict refuses before application execution |
| Qualified math-operation table omitted isnan/isinf | Valid float predicates use semantic fallback in default/forced mode; strict refuses; current and frozen-security native-route assertions fail | Restore exactly these two unary operations with Bool-returning checked helpers | Supported int/float/bool predicate entries return Python bool natively; the unchanged route assertion passes |

Before/after reproductions are retained in [frozen adjacent observations](evidence/two-blocker-20261123/before-exact-adjacent/observations.json), [corrected adjacent observations](evidence/two-blocker-20261123/after-exact-adjacent/observations.json) and [frozen predicate routes](evidence/two-blocker-20261123/before-predicates.json).

## Numeric admission proof

The generated _math_operand helper has exactly three overloads:

~~~text
Float64 → unchanged Float64
Int → Float64
Bool → Int → Float64
~~~

There is deliberately no String, PythonObject, complex or generic conversion-protocol overload. Mojo overload resolution must prove a supported native numeric representation at every emitted math call, including temporary values and helper results. Rejected source is not turned into a cached executable. The generated rejection and accepted code are preserved as string-log-rejected.mojo and numeric-and-predicates.mojo.

This type proof is paired with the **existing actual-runtime checks**, not trusted annotations alone. Every generated entry calls hotloop._arguments.checked_argument before unboxing or the native body: exact builtin type must match the declared representation, and native Int is range checked. The public wrapper also rejects foreign object kinds before entry. A str arriving at a float-annotated parameter cannot be parsed by Float64: it fails the actual-type guard. A str correctly matching a str annotation cannot be passed to _math_operand: the native source is rejected.

Float/int/bool annotation mismatches, complex values, NumPy scalars, numeric subclasses, custom __float__/__index__ objects and huge integers use correct Python fallback or expected strict refusal. Their successful fallback is not counted as native correctness. Objects with conversion side effects run their Python conversion once in fallback; strict refusal runs none. Keyword/default binding, pre-import trust, helper ownership and math-binding provenance retain their existing guards.

NaN, infinity, signed zero, domain errors, overflow and underflow are not globally rejected. The previous operation-specific libm and exception rules remain unchanged; the 15 original and 342 focused numerical checks still execute natively. isnan/isinf return Bool, which boxes as Python bool. Ninety direct predicate observations cover supported float, int and bool inputs in all three modes, including special values.

Valid float helper/temporary expressions remain native. String-valued helper/local expressions are refused. A separate mismatched helper-parameter probe is rejected by the native type checker, with correct default/forced fallback and pre-execution strict refusal; see helper-contract.json. Imported math aliases remain conservative fallback/refusal paths; this repair does not add alias syntax support.

Evaluation order and Python exceptions are compared to the installed CPython oracle. Side-effecting helpers retain existing pre-execution restrictions. No user function is executed twice to profile it or to choose a backend. The test harness separately executes the Python oracle for verification.

## Correctness scorecard and accounting

A = correct native; B = correct Python fallback; C = expected strict refusal; D = wrong execution. These observation classes are separate from the final engineering decision.

| Gate | Frozen result | Corrected installed-package result |
|---|---|---|
| Original unchanged 15 math checks | 15 correct native, from preserved prior verification | **15 A**, no fallback |
| Existing 342 focused numeric observations | 342 correct native | **342 A**, no fallback |
| Existing 111 adjacent observations | 9 A / 66 B / 33 C / 3 D | **9 A / 68 B / 34 C / 0 D** |
| New bounded operand/predicate gate, 1,095 observations | Not claimed as a complete baseline run | **396 A / 466 B / 233 C / 0 D** |
| Current pytest | 376 passed / 2 failed, 378 tests | **379 passed / 0 failed**, 89 warnings, 304.21 s |
| Frozen 129 security checks | 128 passed / 1 failed | **129 passed**, 65 warnings, 51.15 s |

The four math gates contain 1,563 mode observations in total: 762 A, 534 B, 267 C and zero D. They are not 1,563 distinct functions. Raw installed-package observations and their verification context are under installed-gates/. The original gate SHA-256 remains 23d1a795a11dc26ca4ae170b64aaf4d940c256e855ad0518bc983e08d9f7067b.

All 18 pre-existing test source files, including the original15/342/111 pytest gates, remain byte-identical to 0a6dacf. The only added pytest check runs the new focused gate. Tests were not deleted, xfailed, assigned different routes or given looser tolerances.

## Complete regression and safety checks

The full acceptance driver ran from a clean wheel installation with networking disabled using a separate network namespace. The suite receives tests/audit/examples from the exact Git archive, without a hotloop source tree shadowing the installed package. All mandatory driver assertions passed and the driver exited zero.

| Check | Result |
|---|---|
| Current pytest, including all previous 375 R1 checks | 379 passed |
| Frozen security suite | 129 passed |
| Compiler adversarial runner | 51 pass, 1 expected failure, 0 unexpected failures, 52 total |
| Cache audit | 6 passed |
| Original 15 published-defect parity probes | 15/15 equal; native/fallback routes retained individually |
| Mutation/return identity probe | Default/forced preserve mutated input identity through Python; strict refuses before mutation |
| Platform/GIL, provenance, Unicode/helper binding, variadic fallback, pre-import trust and buffer bounds/ownership | Existing tests passed in the complete suite |
| Artifact source, RECORD, LICENSE/NOTICE and metadata checks | Pass: 11 runtime files, 18 wheel members, 42 sdist members; no SDK/native binaries bundled |
| Clean offline wheel installation/smoke and pip check | Pass |
| Offline sdist-to-wheel rebuild/install/smoke | Pass; wheel rebuilt from sdist is byte-identical |
| Old frozen-math binary under the corrected compiler identity | Default/forced stale-cache fallback; strict native error; zero native executions |

No buffer borrowing, ownership contract, raw-pointer access or GIL behavior changed. The implementation/generated-source cache identity changes automatically cover the new helper and operation table; no structural ABI or manifest-schema change was needed. The stale-binary test independently confirms refusal before native body execution.

| Application | Scenarios | Actual verified routes |
|---|---:|---|
| PII Scrubber | 1,019 | Native |
| RAG Document Chunker | 1,020 | Semantic fallback, including forced calls |
| PDF Text Cleaner | 1,020 | Native |
| OCR Fuzzy Matcher | 1,020 | Forced boxed-list native plus default list fallback |
| Quantitative Backtesting | 1,117 | Native |
| Geographic Distance | 1,014 | Forced boxed-list native plus ndarray fallback |
| AR Spatial 3D | 1,010 | Forced boxed-list native plus ndarray fallback |
| Total | **7,220 passed; zero mismatches** | Scenario success is not all-default-native coverage |

### Eleven historical compatibility failures retained

The frozen published v0.2.0 suite still reports **75 passed, 11 failed**, 23 warnings, 53.44 s. The same eleven failure IDs are enforced by the acceptance driver. They are separately documented exceptions to old expectations, not hidden current-suite failures.

| Frozen historical test | Classification of first failed assertion |
|---|---|
| test_generalization_e6.py::TestGeneralizationE6::test_02_distance_geometry_10_functions | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_generalization_e6.py::TestGeneralizationE6::test_03_array_transforms_10_functions | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_generalization_e6.py::TestGeneralizationE6::test_05_validation_search_bitwise_12_functions | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_optimization_safety_e8.py::TestOptimizationSafetyE8::test_10_dispatch_qualifier_cache_drift_safety | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_runtime_security.py::TestRuntimeSecurityAndStability::test_02_numpy_wrong_dtype_shape_and_non_contiguous_safety | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_runtime_security.py::TestRuntimeSecurityAndStability::test_07_inspect_dispatch_runtime_introspection | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_unfamiliar_functions.py::TestUnfamiliarFunctions::test_01_scalar_numerical_10_functions | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_unfamiliar_functions.py::TestUnfamiliarFunctions::test_02_numpy_and_collection_10_functions | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_unfamiliar_functions.py::TestUnfamiliarFunctions::test_03_strings_unicode_and_helpers_10_functions | Intentional semantic-safety restriction; obsolete historical mandatory-native assertion |
| test_unfamiliar_functions.py::TestUnfamiliarFunctions::test_04_kwargs_truthiness_exceptions_and_edges | Obsolete ValueError expectation: CPython 2 ** -1 returns 0.5 |
| test_unfamiliar_functions.py::TestUnfamiliarFunctions::test_06_unfamiliar_speedups_summary | Obsolete mandatory >5x boxed-array speed assertion; not a correctness condition |

The complete first failed source assertion and message for each test are in historical-classification.json. Nine are old mandatory-native expectations now restricted for semantic safety; one expects ValueError for Python's valid 2 ** -1 == 0.5; one demands a >5x speedup. Later assertions after the first failure in a historical test are not claimed as executed.

## Matched performance regression

All numbers below are microseconds, measured end to end through public @hotloop. Every timed result passes matching type/value/float-bit/alias or exception qualification before timing. The frozen baseline is the separately installed 0a6dacf package, not the pre-math R1 package. Candidate is the separately installed aceec46 package. Each worker asserts its installed import path and records the compiler implementation digest.

Five independent processes per runtime run in alternating order, pinned to CPU 7. Each case has nine batch means per process. p50 is the median of the five process medians. p95 is nearest-rank p95 of 45 batch means, **not individual-call tail latency**. CPU scheduling/frequency and WSL/host activity are not controlled beyond affinity. Warm calls include validation, ownership/dispatch and output/exception construction. No competitor rewrite, threshold change or general optimization was made.

Matched inputs: PII 53/8,192/100,000 characters; PDF 1,024/10,240/100,000 characters; quant 0/100/10,000/100,000 ticks. Eight valid math operation kernels plus the five original invalid-input cases are included. Raw source/input hashes must agree across all ten workers. CPython p50 below is from candidate-side processes; baseline-side CPython measurements are also retained.

| Workload / size | CPython p50 | Frozen public p50 / p95 | Corrected public p50 / p95 | p50 change | Actual frozen → corrected route |
|---|---:|---:|---:|---:|---|
| pii_scrubber/short | 24.224 | 15.643 / 17.688 | 16.870 / 18.500 | +7.8% | native → native |
| pii_scrubber/medium | 4661.014 | 691.885 / 740.736 | 716.369 / 772.286 | +3.5% | native → native |
| pii_scrubber/large | 54548.557 | 7985.524 / 8789.528 | 8618.724 / 9275.328 | +7.9% | native → native |
| pdf_cleaner/small | 210.351 | 45.955 / 53.496 | 45.500 / 61.991 | -1.0% | native → native |
| pdf_cleaner/medium | 2066.006 | 385.263 / 471.424 | 355.009 / 435.781 | -7.9% | native → native |
| pdf_cleaner/large | 19735.959 | 3491.311 / 3661.011 | 3244.609 / 4236.513 | -7.1% | native → native |
| quant_backtest/0 | 0.080 | 13.262 / 17.222 | 13.113 / 13.898 | -1.1% | native → native |
| quant_backtest/100 | 25.121 | 13.832 / 15.784 | 13.216 / 15.304 | -4.5% | native → native |
| quant_backtest/10000 | 2597.408 | 47.683 / 55.316 | 46.074 / 49.190 | -3.4% | native → native |
| quant_backtest/100000 | 26463.783 | 452.751 / 489.579 | 423.047 / 484.279 | -6.6% | native → native |
| math_sine/valid | 0.107 | 8.767 / 10.954 | 8.190 / 9.276 | -6.6% | native → native |
| math_cosine/valid | 0.102 | 8.705 / 9.558 | 8.173 / 9.905 | -6.1% | native → native |
| math_logarithm/valid | 0.103 | 8.722 / 9.640 | 8.104 / 10.597 | -7.1% | native → native |
| math_exponential/valid | 0.097 | 8.604 / 9.348 | 8.225 / 13.031 | -4.4% | native → native |
| math_sine/inf | 0.350 | 12.332 / 13.383 | 11.542 / 16.550 | -6.4% | native → native |
| math_cosine/inf | 0.352 | 12.166 / 13.405 | 11.478 / 24.620 | -5.7% | native → native |
| math_logarithm/zero | 0.347 | 11.893 / 14.653 | 11.414 / 12.936 | -4.0% | native → native |
| math_logarithm/negative | 0.347 | 11.897 / 13.359 | 11.311 / 20.681 | -4.9% | native → native |
| math_exponential/overflow | 0.357 | 11.829 / 12.810 | 11.612 / 18.013 | -1.8% | native → native |
| math_square_root/valid | 0.095 | 8.530 / 9.624 | 7.942 / 11.966 | -6.9% | native → native |
| math_angle/valid | 0.133 | 8.449 / 9.973 | 8.244 / 14.391 | -2.4% | native → native |
| math_is_nan/valid | 0.079 | 10.976 / 11.985 | 7.991 / 12.015 | -27.2% | python_fallback_semantics → native |
| math_is_inf/valid | 0.077 | 11.113 / 12.005 | 7.946 / 10.094 | -28.5% | python_fallback_semantics → native |

All 23 timed cases have correct results or exceptions in both packages. The corrected public route is native in all 23; the frozen package uses semantic fallback for the two predicate kernels. No comparable aggregate p50 regression exceeds 10%. PII changes range from +3.5% to +7.9%; PDF from -1.0% to -7.9%; quant from -1.1% to -6.6%; six valid native math kernels from -2.4% to -7.1%. These small changes overlap process variability and are not advertised as compiler speedups. The two restored predicates improve public p50 by 27.2% and 28.5% compared with their previous fallback routes.

This preserves the measured application behavior; it does not make tiny calls profitable. Zero-tick quant remains about 165× slower than CPython. The corrected scalar predicate wrappers take about 8 microseconds versus 0.077–0.079 microseconds for CPython, roughly 101–104× slower. Valid scalar numerical wrappers are about 62–85× slower than CPython; native exception paths about 32–33× slower. Nine of the ten required application-size cases beat their original CPython functions; the zero-tick case loses. No threshold was adjusted to hide this existing loss, and no general performance gain or universal acceleration is claimed. Raw paired process data supports inspection of all variation; no extra replay or outlier deletion was used. No >10% regression required an additional optimization or explanatory replay.

Process variability is retained rather than hidden by an extra benchmark replay:

| Workload / size | Frozen process-median range | Corrected process-median range |
|---|---:|---:|
| pii_scrubber/short | 13.647–16.836 | 14.994–17.197 |
| pii_scrubber/medium | 610.402–715.152 | 669.282–767.419 |
| pii_scrubber/large | 7661.323–8650.727 | 8007.925–9118.227 |
| pdf_cleaner/small | 39.094–51.088 | 44.089–56.005 |
| pdf_cleaner/medium | 314.128–402.901 | 344.624–430.881 |
| pdf_cleaner/large | 3100.509–3611.611 | 3173.309–3917.311 |
| quant_backtest/0 | 10.622–15.437 | 11.916–13.361 |
| quant_backtest/100 | 12.206–14.743 | 12.148–13.377 |
| quant_backtest/10000 | 38.741–53.641 | 42.661–47.779 |
| quant_backtest/100000 | 368.346–485.201 | 407.410–482.457 |
| math_sine/valid | 8.329–9.203 | 7.772–8.900 |
| math_cosine/valid | 8.292–9.003 | 7.544–9.141 |
| math_logarithm/valid | 8.382–9.040 | 7.482–9.273 |
| math_exponential/valid | 8.319–9.068 | 7.579–11.544 |
| math_sine/inf | 11.865–12.922 | 11.325–15.726 |
| math_cosine/inf | 11.698–12.800 | 11.219–14.262 |
| math_logarithm/zero | 11.652–12.878 | 11.376–12.377 |
| math_logarithm/negative | 11.634–12.526 | 11.276–14.751 |
| math_exponential/overflow | 11.528–12.595 | 11.227–13.244 |
| math_square_root/valid | 8.259–8.765 | 7.789–10.005 |
| math_angle/valid | 8.176–8.892 | 7.865–10.057 |
| math_is_nan/valid | 10.952–11.372 | 7.682–9.702 |
| math_is_inf/valid | 10.882–11.439 | 7.850–9.454 |

Build figures are fresh artifact-generation wall time per process, not toolchain installation or fully cold machine startup. The full acceptance driver separately verifies cache integrity and installation behavior.

| Application | Frozen build seconds median (range) | Corrected build seconds median (range) |
|---|---:|---:|
| pii_scrubber | 3.381 (3.089–3.430) | 3.470 (3.123–3.605) |
| pdf_cleaner | 2.240 (2.033–2.351) | 2.283 (2.094–2.364) |
| quant_backtest | 2.112 (1.914–2.416) | 2.025 (1.940–2.199) |

## Package hashes and reproducibility

Source snapshot aceec467cd846289568927a2783e7f50bfe1e21b git-archive SHA-256:
fd3f05c45e849beb990a3ed1a8703c9afc1aeea80a7c22d56a3bb217d3344436.

| Fully tested review artifact | SHA-256 |
|---|---|
| mojo_hotloop-0.2.1-py3-none-any.whl | 3496110eca75fd0f9afb6dd66c9360d4886c8462f00c1831680a3e84e9b12f46 |
| mojo_hotloop-0.2.1.tar.gz | 141e7ce6df01cec64b36f804760a2674486fa6e56caa61d4f871324c8ca79e0a |

These packages were built from and installed for the exact runtime commit above. The final report/evidence-only commit has the same packaged source payload; final-source verification and the full final Git-archive hash are in the Windows review bundle. A version string of 0.2.1 is not a published release.

**Byte-for-byte sdist reproducibility is not achieved.** A second build from the same commit with the same SOURCE_DATE_EPOCH has SHA-256 5140f446ccdfc99cecfa8fa2b8773bf00145cc76d19d9e130695b116442d2820. All 42 file payloads match; the gzip header records a different wall-clock timestamp. This inherited packaging limitation is documented in sdist-reproducibility.json and was not patched in a two-correctness-blocker assignment. The wheel rebuilt from the sdist is nevertheless byte-identical to the fully tested wheel. Runtime file digests are in source-identity.json.

## Integration and preservation

Actual ancestry was checked: corrected source descends from R1, Pre-M0 a094b6dc0bfb20a2e8ca1feee98827908805f63b depends on R1, and M0 ef3706930f6502f0f6d9ac88190cdd476e6d0fbf depends on Pre-M0. Temporary-index application found one README-only Pre-M0 conflict and no M0 conflict. A temporary documentation-only resolution leaves all runtime/test bytes unchanged relative to aceec46. This is mechanical integration feasibility, not a merge/rebase, hosted-CI result or an updated proposal branch. Existing proposals were not altered.

All 50 existing refs and 35 existing worktree mappings remain unchanged; there are now 36 worktrees, including this sole new one. Original dirty-checkout status is unchanged. All 18 previous test source files remain identical.

The original release candidates, all previous reports/evidence, tags and dirty worktrees remain recoverable. No new external dependencies, Gemini/AI API, Rust backend, cloud requirement or public API was introduced. There was no push, merge, PR publication, tag/release creation or developer outreach.

## Reproduction and owner decisions

Use the supported CPython/Mojo environment. Set V to the provisioned SDK venv. For source-only gates set PYTHONPATH to this isolated checkout; for installed acceptance the driver clears it and constructs the exact artifact environment.

~~~sh
export PATH="$V/bin:$PATH" MOJO_BIN="$V/bin/mojo" PIP_NO_INDEX=1
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
PYTHONPATH="$PWD" python audit/math_correctness/original_gate.py --output /tmp/original-NEW
PYTHONPATH="$PWD" python audit/math_correctness/run_focused.py --output /tmp/numeric-NEW
PYTHONPATH="$PWD" python audit/math_correctness/run_adjacent.py --output /tmp/adjacent-NEW
PYTHONPATH="$PWD" python audit/two_blocker/gate.py --output /tmp/operands-NEW
HOTLOOP_EXPECTED_PYTEST_COUNT=379 bash audit/release_acceptance/verify.sh /tmp/full-NEW aceec467cd846289568927a2783e7f50bfe1e21b
python audit/math_correctness/benchmark.py /tmp/performance-NEW FROZEN_INSTALLED_PYTHON CORRECTED_INSTALLED_PYTHON
python audit/math_correctness/summarize_performance.py /tmp/performance-NEW/results.json /tmp/performance-NEW/summary.json
~~~

[Raw performance](evidence/two-blocker-20261123/performance/results.json), [installed numeric/operand gates](evidence/two-blocker-20261123/installed-gates/operands.json), [current pytest](evidence/two-blocker-20261123/full-aceec46/pytest.log), [security pytest](evidence/two-blocker-20261123/full-aceec46/remediation-tests/result.log), [cache rejection](evidence/two-blocker-20261123/stale-cache-rejection.json) and [mechanical integration proof](evidence/two-blocker-20261123/integration-check.json) are retained with a SHA256.json evidence manifest. Setup-notes records discarded source-shadowed probes and the correction to a new fixture's unsupported conditional syntax; neither changed an existing test or entered the accepted scorecard.

Native platform restrictions, conservative unsupported-object/alias fallback, expensive tiny public calls and unreproducible sdist container timestamps remain disclosed limitations. No broad speed guarantee follows from this repair. Genuine contributor DCO attestation, SDK licensing/attribution decisions, remote integration/hosted-CI permission and exact artifact release approval remain owner gates. This technical decision does not waive them.

Stop at local owner review. Do not publish these artifacts or update protected proposals automatically.
