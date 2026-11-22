# v0.2.1 release acceptance

22 November 2026. **B — READY WITH DISCLOSED LIMITATIONS REQUIRING OWNER APPROVAL**, for proposed runtime **568faf2c96ac8aa22758eccf45464fdb4c20b413**. No publication is authorized.

The unchanged 52bc429 candidate was independently rebuilt and its 296-test result reproduced. Its runtime bytes match 5b55740 across all 11 package files. A policy gap remained: Python patch/digit checks did not explicitly exclude unsupported OS/architecture/word-size/GIL profiles. An isolated correction adds those gates and a descriptive profile identity; it changes no numerical algorithm, dispatch threshold, pointer access or public API.

The added tests first expose 18 failures/10 passes against the old admission policy, using injected profile flags and a forbidden-user-kernel spy. These are policy tests, not actual ARM/macOS/free-threaded runs. The proposed runtime passes all 28 checks and the full installed suite.

## Source and artifact integrity

Source base: 52bc42965637b802ff652b9334d4c3ecd45da7d3. Runtime fix: 568faf2c96ac8aa22758eccf45464fdb4c20b413. This report branch adds audit tools/evidence only.

Exact git-archive source was built into wheel/sdist with network disabled. Runtime bytes, LICENSE/NOTICE, METADATA, RECORD and no bundled native binaries were checked; sdist rebuilt the identical wheel at fixed SOURCE_DATE_EPOCH. Both clean installs pass fallback/native smoke and pip check without mandatory NumPy/google dependencies.

~~~text
2bfd942a27228d93070cd8c6ab800ce2758618802e71ddc1772b3be23e14a71e mojo_hotloop-0.2.1-py3-none-any.whl
5c22be5c1b685e42d91851294e971a05d35a3d17a9c60375b8f58201af5910b6 mojo_hotloop-0.2.1.tar.gz
Verified 11 package files, 18 wheel members, 35 sdist members.
~~~

The package's Apache-2.0 declaration is preserved. No SDK is redistributed. Installed external mojo/compiler/lldb 1.2.0 metadata says LicenseRef-MAX-Platform-Software-License; current upstream source licensing differs by component. The documentation review records this external-terms applicability question without granting a license or claiming legal certification. Source ownership remains the maintainer's declaration/DCO responsibility.

## Supported environment matrix

| Environment | Actual verification | Public behavior |
|---|---|---|
| Linux x86-64 little endian 64-bit GIL CPython 3.12.16, Mojo 1.2.0 (2016d0cd) | Installed artifact and complete suites | Qualified native for supported inputs; explicit fallback elsewhere |
| Installed Ubuntu CPython 3.12.3 | Actual source-from-Git subprocess, real artifact compiled/loaded | Default/forced return original owner through semantic fallback; strict rejects; native user-body spy never entered |
| Other Python patch/minor versions, PyPy | UNVERIFIED actual environments; version/implementation injection tested | Policy rejects unqualified native entry |
| ARM/macOS/native Windows/32-bit/big-endian | UNVERIFIED actual environments; admission injection tested | Proposed policy rejects user kernel |
| Free-threaded/GIL-disabled builds | UNVERIFIED actual environments; admission injection tested | Proposed policy rejects user kernel |
| GitHub-hosted Ubuntu 24.04 exact interpreter | New workflow not run | UNVERIFIED; local passes do not establish hosted success |

Exact patch qualification protects CPython bytecode/constant mapping and PyLong shortcut assumptions. It is deliberately not relaxed. Cache identity includes implementation bytes, source/generated code, host ABI, SDK launcher and underlying compiler/linker/runtime/std.mojoc content, settings and environment selection. Full binary digest, directory ownership and pinned-inode loading remain. New implementation/profile identity invalidates older builds; no cache/ABI checks were weakened.

## Correctness and route accounting

- Unchanged original candidate: **296 current tests passed** independently.
- Proposed installed artifact: **324 tests passed**, including 28 admission checks; the original 296 remain.
- Original c2 security suite: **129 passed**, independent rerun.
- Original nine constant-identity tests remain unchanged; argument/list-element, code/default/helper ownership, string slices/concatenation/freshness, zero-tick price identity and decorated-helper strict behavior are included.
- Overflow, division/modulo, float bits/types, Unicode/surrogates, mutation, unsupported NumPy/buffers, exceptions, warnings, cache corruption and SDK/ABI mismatch are exercised.
- Seven application suites: **7,220 scenarios passed**. Actual wrapper counters: **6,220 native / 3,071 fallback**, plus the RAG strict refusal. Additional calls and forced paths mean scenario totals are not native-call totals.
- Standalone cache audit: **6 passed**; adversarial: **49 passed + 1 expected rejection**; original defect reproductions: **15/15 equal**.
- Frozen v0.2.0 suite remains **75 passed / 11 failed**. Passing current tests does not make that historical suite green.

All application implementations and benchmark generators are unchanged. Native list interoperability uses validated private copies; arbitrary Python lists are not zero-copy. No borrowed mutable buffer/GIL-release optimization was introduced.

## Seven-application matched performance

All times below are microseconds, p50 / p95 of batch means. Five independent processes per runtime, nine batches per case; no trial was discarded. The p95 is not individual-call tail latency. Original inputs and output contracts match across runtimes. Default routes are shown; forced/public/private records remain in the full JSON.

| Application / case | CPython us | Public us | Backend | Best measured strict competitor / us | Public vs security |
|---|---:|---:|---|---|---:|
| pii_scrubber / short | 22.141 / 37.122 | 15.913 / 22.263 | native | expert_regex: 10.968 / 18.738 | +37.9% |
| pii_scrubber / medium | 4330.400 / 9987.700 | 677.264 / 898.812 | native | expert_regex: 1512.820 / 1854.975 | +0.1% |
| pii_scrubber / large | 52567.603 / 60547.500 | 8075.100 / 8338.500 | native | expert_regex: 18655.900 / 28676.802 | +3.1% |
| pdf_cleaner / small | 203.695 / 213.483 | 44.509 / 46.942 | native | cpython: 203.695 / 213.483 | +6.9% |
| pdf_cleaner / medium | 2016.600 / 2115.167 | 346.123 / 363.490 | native | cpython: 2016.600 / 2115.167 | -5.5% |
| pdf_cleaner / large | 19220.000 / 20581.801 | 3173.501 / 3279.151 | native | cpython: 19220.000 / 20581.801 | +1.6% |
| quant_backtest / 0 | 0.076 / 0.098 | 12.488 / 15.109 | native | cpython: 0.076 / 0.098 | +9.7% |
| quant_backtest / 100 | 23.104 / 29.688 | 12.338 / 16.159 | native | manual_cpp: 0.281 / 0.382 | +5.9% |
| quant_backtest / 10000 | 2512.067 / 3271.450 | 43.293 / 72.911 | native | numba: 28.733 / 38.274 | +2.5% |
| quant_backtest / 100000 | 24166.300 / 29147.101 | 398.405 / 454.018 | native | numba: 370.810 / 395.830 | -2.9% |
| rag_chunker / small | 3.704 / 3.859 | 11.425 / 13.268 | python_fallback_slower | cpython: 3.704 / 3.859 | +2.6% |
| rag_chunker / medium | 21.563 / 22.196 | 30.654 / 32.145 | python_fallback_slower | cpython: 21.563 / 22.196 | -5.1% |
| rag_chunker / large | 137.762 / 147.162 | 145.865 / 154.016 | python_fallback_slower | cpython: 137.762 / 147.162 | -14.5% |
| ocr_matcher / small | 103.768 / 125.980 | 112.455 / 137.885 | python_fallback_slower | rapidfuzz: 4.877 / 6.055 | +1.5% |
| ocr_matcher / medium | 1003.275 / 1663.767 | 1022.828 / 1256.500 | python_fallback_slower | rapidfuzz: 39.632 / 85.357 | +0.3% |
| ocr_matcher / large | 1677.625 / 2152.533 | 1699.200 / 2180.033 | python_fallback_slower | rapidfuzz: 370.600 / 501.233 | +0.4% |
| geo_distance / 100 | 57.149 / 60.658 | 66.199 / 69.301 | python_fallback_slower | manual_cpp: 7.150 / 7.316 | +1.5% |
| geo_distance / 1000 | 599.292 / 624.255 | 631.269 / 683.908 | python_fallback_slower | manual_cpp: 69.163 / 84.623 | -9.0% |
| geo_distance / 10000 | 6366.000 / 6942.199 | 6284.801 / 6565.100 | python_fallback_slower | manual_cpp: 684.163 / 751.010 | -0.5% |
| ar_spatial / 100 | 25.855 / 28.323 | 38.676 / 42.307 | python_fallback_slower | manual_cpp: 2.138 / 2.304 | +1.1% |
| ar_spatial / 1000 | 271.348 / 290.246 | 286.174 / 318.050 | python_fallback_slower | manual_cpp: 20.485 / 31.054 | -6.3% |
| ar_spatial / 10000 | 2799.550 / 3497.200 | 2992.150 / 4100.700 | python_fallback_slower | manual_cpp: 208.916 / 228.633 | +3.9% |

Numba compiles unchanged original numerical source with fastmath=False; reflected Python-list conversion is included. NumPy adapters include list-to-array conversion and output conversion. The C++ references and regex/library adapters are explicitly expert implementations, never presented as automatic Hotloop output. RAG's original efficient CPython string operations remain the reference. Cython/Pythran/Codon were not installed in this independent review environment, and no new performance was invented for them.

The original PDF regex fails the strict output contract and is excluded from ranking. NumPy Haversine can satisfy the original tolerance but differ in float bits; tolerance-only rows are disclosed separately. Zero-tick security/Numba/C++ boxing fails required input identity and is not a strict win. Comparator qualification is scoped to measured fixtures, not universal Python compatibility.

No general performance optimization was attempted. PII/PDF/positive-tick backtesting retain native acceleration over CPython on qualifying sizes. Tiny calls can lose badly; safe fallback workloads remain visible. All process p50 ranges, winning/losing alternatives and security-baseline changes are in measurement-summary.json. More conservative list policy is unchanged.

## Cold costs, memory and startup

Per-application AOT build, verified cache hit, import-after-build, first public call and Numba JIT costs are preserved for every process in measurement-summary.json. Fresh-interpreter startup has five candidate processes per application; its wall scope includes launch/import/input setup/first call and an oracle check, with warm OS caches. It is separate from warmed latency.

Python-visible tracemalloc peaks are recorded per engine/process. They exclude Mojo/native allocator storage, total allocation counts and RSS; they do not prove leak absence. The private generated entry includes ownership/input validation and conversion, not just the numerical kernel. It is never substituted for public latency.

| Application | Cold AOT s | Verified cache ms | First public us | Fresh startup wall s | Large public Python-visible peak bytes |
|---|---:|---:|---:|---:|---:|
| pii_scrubber | 3.108 | 53.122 | 746.000 | 0.769 | 749,310 |
| pdf_cleaner | 2.076 | 24.231 | 332.600 | 0.780 | 499,518 |
| quant_backtest | 1.941 | 13.221 | 133.700 | 0.768 | 1,853 |
| rag_chunker | 1.959 | 25.705 | 299.900 | 0.753 | 510,020 |
| ocr_matcher | 1.941 | 20.052 | 203.800 | 0.759 | 1,824 |
| geo_distance | 2.034 | 15.016 | 165.200 | 0.763 | 1,707 |
| ar_spatial | 2.148 | 19.546 | 155.800 | 0.764 | 1,847 |

Fresh startup uses each original smallest case; cold AOT means a fresh artifact directory, not flushed SDK/OS caches. Exact ranges, import costs and all memory samples remain in the JSON.

## Eleven historical compatibility failures

Each full test ID, first assertion and original trace is preserved in historical-assertions.json and published-tests.log:

| Test | First discrepancy / classification |
|---|---|
| E6 distance geometry | manhattan_dist_arr expected native; ndarray semantic fallback is an intentional restriction |
| E6 array transforms | running_prod_mod expected native; same representation restriction |
| E6 validation/search | binary_search_arr expected native; same restriction |
| E8 dispatch qualifier/cache drift | obsolete native admission expectation for restricted arrays |
| Runtime security wrong dtype/shape/strides | old unsafe conversion/native expectation; corrected refusal |
| Runtime introspection | obsolete ndarray-native counter expectation |
| Unfamiliar scalar numerical | mixed_arith_calc floor/mod path deliberately falls back |
| Unfamiliar collection | dot_product ndarray native expectation withdrawn |
| Unfamiliar strings/helpers | helper_composition ndarray expectation; restored string slices pass earlier cases |
| Unfamiliar kwargs/edges | incorrect ValueError expectation for 2 ** -1 (Python returns 0.5) |
| Unfamiliar speed summary | invalid mandatory historical >5x threshold |

These are nine restricted-native/obsolete-route assertions and two invalid assertions, not unexplained current value mismatches. Coverage withdrawals still belong in release notes.

## Draft release notes and risks

Proposed v0.2.1 repairs Python object provenance and cache/native semantic boundaries, restores qualified native string paths, preserves observable fallback/strict behavior, and explicitly bounds interpreter/platform admission. Rebuild older artifacts.

This developer preview supports a defined typed subset. NumPy/typed-buffer objects and caller-visible mutation/shared object graphs may require Python. Decorated helper policies are not inlined. Compilation, cache hits, wrapper overhead and short-input regressions remain. Strict mode is not a speed guarantee. Unsupported actual platforms remain unverified; admission tests are not portability certification.

Owner must approve the minimal fix, package hashes, release notes and external SDK notice wording. Existing public assets/tags remain unchanged. No merge, push, tag, settings change or publication occurred. Source/package verification does not grant approval to release.

## Reproduce

Run the audit scripts from this separate checkout using a locally provisioned toolchain, fresh directories and network isolation:

~~~bash
bash audit/release_acceptance/verify.sh /tmp/NEW_GATE 568faf2c96ac8aa22758eccf45464fdb4c20b413
python audit/release_acceptance/compatibility.py /usr/bin/python3 py3123 /tmp/NEW_COMPAT 568faf2c96ac8aa22758eccf45464fdb4c20b413
python audit/release_acceptance/measure_applications.py /tmp/NEW_BENCH SECURITY_PY PROPOSED_PY
python audit/release_acceptance/summarize.py /tmp/NEW_BENCH/results.json /tmp/NEW_SUMMARY.json
python audit/release_acceptance/startup_applications.py /tmp/NEW_BENCH PROPOSED_PY /tmp/NEW_STARTUP.json
~~~

See evidence/r1-acceptance-20261122 for exact packages, logs, all input/source digests, modes, per-process data, environment and GitHub read-only observations. Benchmark setup initially had a forced-counter instrumentation error; that exploratory run was stopped and all accepted trials rerun after correction. No results from the stopped cohort enter current tables.
