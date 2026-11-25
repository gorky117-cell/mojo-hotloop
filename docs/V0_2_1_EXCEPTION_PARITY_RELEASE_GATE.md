# v0.2.1 exception-parity release gate

**B — CORRECTNESS GATE PASSES; DISCLOSED LIMITATIONS REQUIRE OWNER DECISION**

24 November 2026 IST. The requested geographic/list correction passes the complete mandatory acceptance gates. No mandatory wrong-code or safety failure remains in this run. B reflects the repeated measured geographic slowdown as well as the intentional compatibility restrictions, narrow native platform qualification, historical README/package notices and pending owner integration/release decisions described below. This is not publication approval.

## Exact source and scope

- Runtime baseline: 582afcdaa18802df48e81a3acd80a19cee899c7e.
- Preserved performance diagnosis/evidence: 42472fef4d0631d34ec7e463d8b6555fb082d2c5. No changes were made to that worktree or its evidence.
- Corrected runtime, focused test and tested artifact source: a11c9decc76dfdb7350f921d9b5f97451583e78b.
- Final local report/evidence commit: $Format:%H$ (expanded by git archive; git rev-parse HEAD gives it in the checkout).
- Isolated branch/worktree: codex/v021-exception-parity-final at /home/gaurav/mojo-hotloop-v021-exception-parity.
- Exactly one runtime file changed: hotloop/ast_transpiler.py. The decorator, ownership/argument validation, return provenance, platform/GIL qualification, security and artifact-integrity implementation are unchanged.
- Verified environment: GIL-enabled CPython 3.12.16, Linux x86-64/WSL, little endian, 64-bit pointers and 30-bit PyLong digits; Mojo 1.2.0 (2016d0cd). Tests use the provisioned local SDK; no online inference, Gemini API, Rust or cloud dependency was added.

The final evidence commit adds the regression benchmark and stale-cache probe plus this report and evidence. Its runtime and packaged source files match the tested implementation commit; the artifacts retain that original source provenance.

## Root cause and minimal correction

Before correction, a generated geographic read used lons[_checked_index(i, len(lons))]. The compiler's _checked_index normalized negative indices and checked bounds, then explicitly raised Mojo Error("HOTLOOP_INDEX_ERROR: index out of range"). That happens before native List access. The Python exception bridge recognizes the internal tag, constructs IndexError, and forwards the payload unchanged. The wrong message originated in generated code, not the bridge.

The same generic helper served proven list reads, input-element return provenance and local list stores, as well as non-list operations. The correction does not rewrite every IndexError:

1. Proven list reads use _checked_list_index: the existing bounds/negative-index guards, with "list index out of range".
2. Proven plain list stores use _checked_list_assignment_index: the same guards, with "list assignment index out of range". Augmented assignment keeps the read message because it reads the element before evaluating its RHS.
3. A directly adjacent ordering defect was reproduced: xs[bad_index] = 4 // 0 raised native IndexError before the RHS, whereas CPython raises ZeroDivisionError. The plain-store lowering now materializes the RHS exactly once into a collision-free temporary before evaluating the target. Augmented stores retain read-before-RHS order.

List proof comes from emitted native List types backed by the existing exact-list argument guards, Python list literals/local construction, or statically typed helper results already subject to native type/provenance admission. An exception's class/message is never used as proof. Unsupported helper/list-return shapes do not gain native admission.

The original generic helper and Python exception bridge remain unchanged. There is no unsafe unchecked list access, pointer borrowing, altered floating-point mode, function-name special case, exception-driven replay or new dispatch policy. An index expression is passed once to the checked helper. Effectful index/value helpers and custom __index__ cases retain correct once-only Python fallback; strict refusal executes none. These are not claimed as native side-effect support.

Explicit raises remain outside supported AST lowering. Direct and nested-helper user IndexError messages, including strings that contain the internal tag, remain unchanged in default/forced Python fallback. Strict mode refuses before running those unsupported bodies. No claim is made that this bounded list correction establishes general non-list exception-message parity.

## Original reproduction and broader evidence

Original unchanged source: examples/geo_distance/original.py.
Call: accumulate_haversine_distance([1.0, 2.0], [1.0]).

| Execution | Baseline class / message | Corrected class / message | Corrected backend / executions |
|---|---|---|---|
| CPython 3.12.16 | IndexError / list index out of range | Same | CPython oracle |
| Default Hotloop | IndexError / list index out of range | Same | python_fallback_slower; native 0, Python 1 |
| Forced Hotloop | IndexError / index out of range | IndexError / list index out of range | native; native 1, Python 0 |
| Strict Hotloop | IndexError / index out of range | IndexError / list index out of range | native; native 1, Python 0 |

[Exact baseline observations](evidence/exception-parity-20261124/before-final/observations.json) and [independent installed-candidate observations](evidence/exception-parity-20261124/installed-gates/lists.json) retain exception args, types, output bits, direct/input-element identities, stdout, backend and counters.

A = correct native; B = correct Python fallback; C = expected strict refusal; D = wrong execution. These observation labels are distinct from the report verdict.

| Focused list gate, 390 mode observations | A | B | C | D |
|---|---:|---:|---:|---:|
| Exact installed baseline | 128 | 125 | 29 | 108 |
| Corrected installed wheel | 236 | 125 | 29 | 0 |

Baseline D consists of 102 same-class/message mismatches and six wrong exception-order observations. The gate covers int/float/bool/string list elements, valid/negative/extreme native-sized/out-of-range indices, empty/unequal lists, list literals/locals, computed and nested-helper indices, read/RHS error order, assignment/augmented assignment, effectful helpers, custom index objects, annotation mismatches and huge Python indices, explicit user exceptions, and all three public modes. Its source hash is identical across the two installs. Counts are observations, not distinct functions or acceleration wins.

One new pytest test enforces the gate. Every pre-existing test/math gate source is unchanged. During new harness development an expected backend label was corrected to the actual existing python_fallback_slower spelling; an early stale-artifact fixture was corrected to copy its verified __mojocache__ as well as aliases. Neither correction changed runtime policy or existing test expectations.

## Full installed-artifact verification

The unchanged release acceptance driver ran from a Git archive and clean wheel installation with no source-tree runtime shadowing and no network access. The laptop/tool interruption occurred after the current pytest and adversarial results were saved. Verification resumed from the cache audit through every remaining unchanged assertion; completed results were retained.

The first resumed cache run had six fixture-build failures because the SDK rejected an existing zero-byte transform-cache file. No cache assertions or native execution were reached. [The failure log](evidence/exception-parity-20261124/cache-interrupted-sdk.log) is retained. A fresh task-local SDK cache selected by XDG_CACHE_HOME made all six tests pass. No shared cache or protected checkout was cleaned or reset. This environment recovery and the resume script are recorded in [recovery evidence](evidence/exception-parity-20261124/sdk-cache-recovery.json).

| Gate | Final result |
|---|---|
| Current installed-package pytest | 380 passed, 89 warnings, 428.21 seconds |
| Focused list gate within that suite | 390 observations; 236 A / 125 B / 29 C / 0 D |
| Original unchanged math exception gate | 15/15 correct native |
| Focused numeric/math gate | 342/342 correct native |
| Adjacent math admission gate | 111 observations; 9 A / 68 B / 34 C / 0 D |
| Existing operand/predicate gate | 1,095 observations; 396 A / 466 B / 233 C / 0 D |
| Frozen security/remediation suite | 129 passed; no failures |
| Adversarial runner | 52 total: 51 pass, 1 expected failure, 0 unexpected failures |
| Cache audit after isolated SDK recovery | 6 passed |
| Old baseline geographic artifact under corrected runtime | Default/forced stale-cache fallback; strict native error; native calls 0 in every mode |
| Original published-defect parity probes | 15/15 equal |
| Mutation/return-provenance probe | Python fallback preserves mutated input and identity; strict refuses before mutation |
| Platform/GIL, cache/ABI, ownership/buffers, pre-import bindings, provenance and frozen generalization suites | Passed within current pytest; existing admission restrictions retained |
| Clean offline wheel install, smoke and pip check | Pass |
| Offline sdist-to-wheel rebuild, clean install, smoke and pip check | Pass; rebuilt wheel byte-identical |
| Package source, RECORD, metadata, LICENSE/NOTICE | Pass: 11 runtime files, 18 wheel members, 43 sdist members |
| Unmodified frozen v0.2.0 compatibility suite | 75 passed / same 11 documented historical failures |
| Resumed acceptance driver final assertions | Pass, exit 0 |

The 129 frozen security tests overlap coverage in current pytest; these are separate suite executions, not 509 distinct current tests. The focused observation gates likewise sit inside pytest and are not added to its test count.

| Original application suite | Verified scenarios | Observed route qualification |
|---|---:|---|
| PII Scrubber | 1,019 | Native |
| RAG Document Chunker | 1,020 | Original string chunks use semantic fallback; separate integer-offset controls remain native |
| PDF Text Cleaner | 1,020 | Native |
| OCR Fuzzy Matcher | 1,020 | Forced boxed-list native plus default list fallback |
| Quantitative Backtesting | 1,117 | Native |
| Geographic Distance | 1,014 | Forced boxed-list native plus ndarray fallback |
| AR Spatial 3D | 1,010 | Forced boxed-list native plus ndarray fallback |
| Total | 7,220 passed | Scenario success is not all-default-native coverage |

[Full current pytest log](evidence/exception-parity-20261124/full-a11c9de/pytest.log), [frozen security log](evidence/exception-parity-20261124/full-a11c9de/remediation-tests/result.log), application verification logs/counters, parity/mutation observations and resumed driver exit are retained in the evidence directory.

### Eleven historical failures, separate and unchanged

| Frozen v0.2.0 test | Unchanged first-failure classification |
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

The same eleven IDs and first failed source assertions are independently checked against the previous classification. Nine are intentional semantic-safety restrictions with historical mandatory-native expectations; one expects ValueError for valid Python 2 ** -1 == 0.5; one demands >5x speed. Later assertions after each first failure are not claimed as executed. No frozen test was deleted, xfailed or edited. [Classification](evidence/exception-parity-20261124/historical-classification.json).

## Performance preservation

No optimization was implemented. Five independent processes per runtime ran in alternating order on CPU 7, with fresh per-process application builds, installed import-path assertions, identical original source/input hashes, and strict value/type/float-bit/alias qualification before timing. Both sides use CPython 3.12.16 and the same local toolchain/environment.

All figures below are microseconds. p50 is the median of 45 batch means (nine per process); p95 is linearly interpolated across those batch means, not individual-call tail latency. Calls include public validation, copies, dispatch and result conversion. GC stays enabled; tracemalloc allocation measurements occur separately. WSL/host scheduling/frequency are uncontrolled beyond affinity. This bounded regression test does not establish a speedup over optimized competitors.

| Application / size | Mode / actual backend | CPython after p50 | Before public p50 / p95 | After public p50 / p95 | Change |
|---|---|---:|---:|---:|---:|
| geo_distance / 100 | default / python_fallback_slower | 78.040 | 97.509 / 202.778 | 93.208 / 180.305 | -4.4% |
| geo_distance / 100 | forced / native | 78.040 | 59.949 / 105.390 | 61.608 / 91.281 | +2.8% |
| geo_distance / 100 | strict / native | 78.040 | 58.645 / 94.972 | 59.270 / 72.717 | +1.1% |
| geo_distance / 1000 | default / python_fallback_slower | 842.280 | 914.075 / 1457.134 | 828.217 / 1095.733 | -9.4% |
| geo_distance / 1000 | forced / native | 842.280 | 551.857 / 954.349 | 490.112 / 683.507 | -11.2% |
| geo_distance / 1000 | strict / native | 842.280 | 539.233 / 885.368 | 481.190 / 622.373 | -10.8% |
| geo_distance / 10000 | default / python_fallback_slower | 8403.300 | 8783.600 / 10831.510 | 8887.000 / 11719.640 | +1.2% |
| geo_distance / 10000 | forced / native | 8403.300 | 4912.299 / 7458.653 | 6557.199 / 11545.539 | +33.5% |
| geo_distance / 10000 | strict / native | 8403.300 | 5330.000 / 7562.699 | 6351.701 / 11914.260 | +19.2% |
| pdf_cleaner / large | default / native | 33477.195 | 4645.100 / 19405.759 | 4988.803 / 9312.880 | +7.4% |
| pdf_cleaner / medium | default / native | 2964.300 | 474.550 / 673.418 | 608.200 / 1309.808 | +28.2% |
| pdf_cleaner / small | default / native | 289.947 | 68.024 / 102.805 | 65.209 / 122.928 | -4.1% |
| pii_scrubber / large | default / native | 87340.000 | 12981.379 / 23126.860 | 14546.500 / 16594.898 | +12.1% |
| pii_scrubber / medium | default / native | 6285.500 | 965.160 / 1603.550 | 1011.650 / 2033.987 | +4.8% |
| pii_scrubber / short | default / native | 32.048 | 22.124 / 42.479 | 23.552 / 44.810 | +6.5% |
| quant_backtest / 0 | default / native | 0.104 | 18.652 / 47.221 | 17.806 / 32.678 | -4.5% |
| quant_backtest / 100 | default / native | 33.514 | 19.371 / 56.814 | 18.979 / 30.024 | -2.0% |
| quant_backtest / 10000 | default / native | 3499.400 | 68.167 / 164.359 | 63.500 / 94.031 | -6.8% |
| quant_backtest / 100000 | default / native | 34123.700 | 748.217 / 1289.586 | 576.956 / 801.029 | -22.9% |

- geo_distance/10000/forced_public: aggregate +33.5%; paired process changes +71.6%, +70.8%, +7.3%, -12.5%, +26.9%; >10% in 3/5 pairs.
- geo_distance/10000/strict_public: aggregate +19.2%; paired process changes +112.7%, +20.0%, +8.9%, -12.9%, +47.8%; >10% in 3/5 pairs.
- pdf_cleaner/medium/default_public: aggregate +28.2%; paired process changes +14.0%, -7.3%, +91.8%, -13.4%, +159.8%; >10% in 3/5 pairs.
- pii_scrubber/large/default_public: aggregate +12.1%; paired process changes -17.6%, +14.0%, -18.5%, +18.3%, +12.8%; >10% in 3/5 pairs.

These initial flags receive a separate confirmation below. The raw JSON also retains its descriptive four-of-five screen; that screen must not be interpreted as absence of a regression when three pairs are slower.

Variability is retained below and in all ten raw worker JSON files. [Complete results](evidence/exception-parity-20261124/performance/results.json) include per-process medians, paired changes, Python-visible peak allocations, source/input hashes, actual dispatch/counters and compilation/cache timings.

| Application / size / mode | Before process-median range | After process-median range | Pairs slower >10% |
|---|---:|---:|---:|
| geo_distance / 100 / default | 79.504-185.241 | 75.802-160.092 | 1/5 |
| geo_distance / 100 / forced | 53.793-88.146 | 50.889-66.363 | 0/5 |
| geo_distance / 100 / strict | 50.575-73.546 | 49.124-66.119 | 0/5 |
| geo_distance / 1000 / default | 793.400-1056.574 | 720.750-955.825 | 1/5 |
| geo_distance / 1000 / forced | 490.357-674.680 | 422.700-525.825 | 0/5 |
| geo_distance / 1000 / strict | 458.125-821.757 | 418.964-521.328 | 0/5 |
| geo_distance / 10000 / default | 8537.899-9646.791 | 7264.501-11422.299 | 1/5 |
| geo_distance / 10000 / forced | 4340.500-6923.793 | 4656.700-10119.800 | 3/5 |
| geo_distance / 10000 / strict | 4545.300-5648.794 | 4921.500-11564.799 | 3/5 |
| pdf_cleaner / large / default | 3942.100-18510.699 | 4365.101-7868.200 | 3/5 |
| pdf_cleaner / medium / default | 415.555-533.400 | 417.091-1231.440 | 3/5 |
| pdf_cleaner / small / default | 55.476-90.085 | 54.737-110.839 | 1/5 |
| pii_scrubber / large / default | 11172.699-19473.501 | 10579.503-16037.397 | 3/5 |
| pii_scrubber / medium / default | 880.950-1398.875 | 803.133-1831.033 | 2/5 |
| pii_scrubber / short / default | 18.566-26.192 | 19.075-25.938 | 3/5 |
| quant_backtest / 0 / default | 16.516-44.019 | 16.426-20.900 | 1/5 |
| quant_backtest / 100 / default | 15.905-41.202 | 17.067-22.371 | 2/5 |
| quant_backtest / 10000 / default | 56.184-125.049 | 56.850-64.940 | 1/5 |
| quant_backtest / 100000 / default | 582.878-1227.467 | 513.678-722.867 | 0/5 |

| Application | Before build seconds median (range) | After build seconds median (range) | Before / after cache-check seconds median |
|---|---:|---:|---:|
| geo_distance | 4.736 (4.153-16.749) | 5.084 (4.187-7.676) | 0.0220 / 0.0258 |
| pii_scrubber | 5.303 (4.261-24.125) | 4.568 (3.635-6.863) | 0.0943 / 0.0852 |
| pdf_cleaner | 3.693 (3.282-21.755) | 4.147 (3.554-5.792) | 0.0449 / 0.0383 |
| quant_backtest | 4.224 (3.001-21.379) | 3.678 (3.573-4.378) | 0.0263 / 0.0191 |

Build times mean fresh application artifact generation, not a cold OS or fresh SDK installation. The initial preparation workers inherited CPU-7-only affinity; subsequent workers allowed all eight CPUs for SDK compilation and restored CPU 7 before warm-call timing. Raw build_cpus records distinguish these preparations. Build-time ranges therefore include this setup difference and are descriptive, not an accepted compiler speedup. Cache timings are build-time verification/reuse, not per-call cost. The immutable compiler/generated-source identity changes invalidate old binaries; the ABI layout and manifest schema remain unchanged. The [old-cache rejection probe](evidence/exception-parity-20261124/stale-cache-rejection.json) confirms exclusion before native entry.

### Independent confirmation with no compilation in timing workers

A second complete five-process-per-runtime matrix reused each runtime's first-trial binaries. The public loader still verifies source, manifest, implementation/ABI identity, binary integrity and ownership; native-route assertions disqualify fallback. No application compilation runs in these workers. Timing stays on CPU 7, with the same original inputs, output contracts and batch protocol. All 320 result qualifications pass again.

| Initially flagged case | Replay before p50 / p95 | Replay after p50 / p95 | Change | Pairs >10% | Paired changes |
|---|---:|---:|---:|---:|---|
| geo_distance/10000/forced_public | 5237.400 / 7943.119 | 5915.200 / 9651.381 | +12.9% | 3/5 | +13.0%, -25.2%, +19.0%, -6.0%, +56.1% |
| geo_distance/10000/strict_public | 4941.200 / 7712.240 | 6125.801 / 30252.180 | +24.0% | 4/5 | +38.4%, -18.9%, +35.0%, +378.1%, +22.0% |
| pdf_cleaner/medium/default_public | 543.362 / 898.215 | 449.000 / 760.477 | -17.4% | 1/5 | -31.6%, -2.5%, -15.0%, -30.3%, +10.8% |
| pii_scrubber/large/default_public | 12665.500 / 16714.100 | 11698.200 / 20085.140 | -7.6% | 1/5 | -17.0%, -8.8%, -5.7%, -3.6%, +20.1% |

The 10,000-point geographic native slowdown repeats in both independent experiments: forced +33.5% initially and +12.9% in confirmation; strict +19.2% initially and +24.0% in confirmation. Strict is >10% slower in four of five confirmatory pairs. These are disclosed measured regressions, not dismissed by the first matrix's screen. At that size, candidate forced/strict p50 remains below matched CPython, while default dispatch remains Python.

Variability is material. In confirmation, strict geographic process medians range from 4,471-6,175 us before and 4,832-22,996 us after; its p95 batch mean rises from 7,712 to 30,252 us. Forced ranges overlap (4,806-7,031 us before; 4,585-7,948 us after). The PII-large and PDF-medium slowdowns do not persist. Native-call source changes and noisy host measurements do not by themselves establish the cause; no compiler or wrapper optimization was attempted to conceal this result.

The full confirmatory matrix, including every other case, is retained in [confirmation results](evidence/exception-parity-20261124/performance-confirmation/results.json). This performance uncertainty and repeated geographic regression are explicit owner-review limitations.


## Exact candidate packages and provenance

- mojo_hotloop-0.2.1-py3-none-any.whl — 59614 bytes; SHA-256 7fe26c9bf170d5f763b593ef92b49e4aa62c0932e547f1109df084e08fbc8031
- mojo_hotloop-0.2.1.tar.gz — 104845 bytes; SHA-256 fabfb679db4dc10f90f676e1c01c8fcacc834b71f7ed3dee23d4e9b1c8da18ab

Implementation Git archive SHA-256: 1974eeee0b8988a16c68c716b5ad4431e6df55477129e9b42e18f70d8d16c938.

The wheel has no mandatory third-party runtime dependencies. NumPy is an optional extra; Mojo is an external prerequisite and is not bundled. No native .so or SDK components are shipped. Package checks verify source bytes, RECORD and notices. The tested source revision is a11c9decc76dfdb7350f921d9b5f97451583e78b; later report/evidence work does not silently alter those files. An sdist rebuild produces the exact same wheel. Byte-for-byte reproducible gzip/sdist output across separate builds is not asserted.

These are locally verified corrective candidate artifacts, not an approved release. They preserve historical README notices/claims under an explicit corrective-prototype disclaimer. The owner should approve the truthful Pre-M0 documentation and exact resulting artifact hashes before any publication; integration would require a new reviewed release build.

## Limitations, integration and release decision

The corrective branch qualifies only the exact supported CPython/GIL/platform layout. The Python >=3.12 packaging marker is broader than native qualification: other environments must use safe Python fallback or strict refusal. Writable/arbitrary buffer borrowing is not enabled. NumPy arrays/scalars, array.array and memoryview retain Python fallback; lists are validated and copied, never treated as zero-copy.

Default list dispatch remains conservative Python execution. Forced/strict list calls can be native without being faster. Unproven output provenance/helper shapes, explicit raises, effectful helpers, mutation/identity-sensitive behavior and unsupported AST remain fallback or pre-execution strict refusal. General non-list exception parity, new syntax and new performance policies are outside this bounded correction. Passing this gate is not a universal Python-semantics or acceleration claim.

R1 must promote the corrected descendant rather than the previous runtime baseline. Actual ancestry confirms R1 69fa0bbfcfa772e3ceb35464286eea89f0a6398a is an ancestor of this implementation; Pre-M0 a094b6dc0bfb20a2e8ca1feee98827908805f63b depends on R1, and M0 ef3706930f6502f0f6d9ac88190cdd476e6d0fbf depends on Pre-M0. A temporary-index-only integration dry run found one README conflict for Pre-M0 and no M0 conflict. Virtual resolution preserves the corrected runtime/tests and uses the truthful documentation layout with a current review notice. [Exact integration check](evidence/exception-parity-20261124/integration-check.json).

Promotion order remains corrected R1 → Pre-M0 → dependent M0. M0 must run the full current suite including the new list gate, exact CPython 3.12.16 preflight, required-native reference cases and the negative no-build/fallback gate. No generic CI redesign or hosted CI run occurred; no remote action is authorized here. Genuine contributor attestations and any outstanding SDK/licensing decisions remain owner matters; no sign-off or legal approval is manufactured.

The owner decision is whether to accept the explicitly restricted corrective compatibility scope and proceed with the separate documentation/integration/release review. This work closes the reproduced list defect and its adjacent assignment-order error. All mandatory current correctness/safety gates pass after environment recovery; the eleven historical incompatibilities remain disclosed.

All 52 pre-existing refs and 37 pre-existing worktrees remain unchanged; the new worktree is the 38th. The original dirty checkout and all original tests/math gates/generalization fixtures are preserved. The final engineering branch is committed and clean. No merge, rebase, reset, push, PR, tag, release or publication was performed.

## Reproduction

Use a clean installed source candidate with the qualified provisioned toolchain, keep networking disabled for artifact checks, and select a fresh task-local SDK cache if the shared SDK cache is damaged. No SDK cache clearing is needed.

~~~bash
export V=/home/gaurav/mojo-hotloop/.venv
export PATH="$V/bin:$PATH" MOJO_BIN="$V/bin/mojo" PIP_NO_INDEX=1
export XDG_CACHE_HOME=/tmp/hotloop-exception-parity-replay-sdk
HOTLOOP_EXPECTED_PYTEST_COUNT=380 bash audit/release_acceptance/verify.sh /tmp/hotloop-exception-parity-replay a11c9decc76dfdb7350f921d9b5f97451583e78b
python audit/exception_parity/performance.py /tmp/hotloop-exception-performance-replay BASELINE_INSTALLED_PYTHON CANDIDATE_INSTALLED_PYTHON
python audit/exception_parity/performance.py /tmp/hotloop-exception-performance-confirm BASELINE_INSTALLED_PYTHON CANDIDATE_INSTALLED_PYTHON /tmp/hotloop-exception-performance-replay
~~~

The source-tree focused gate needs PYTHONPATH pointed at the intended source runtime; installed-package gates must not let the source tree shadow the wheel. The performance workers assert their installed paths. The baseline install used here was independently checked byte-for-byte against all eleven baseline runtime files.

This report is a stop for owner review, not authorization for further optimization or remote integration.
