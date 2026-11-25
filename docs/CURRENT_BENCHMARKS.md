# Current candidate benchmark observations

Dataset: r1-v021-20261122-568faf2. Runtime: 568faf2c96ac8aa22758eccf45464fdb4c20b413. Status: UNRELEASED_OWNER_REVIEW.

Raw evidence: local review commit dc5364e7d5a58bfad6db2954ab895ab766d7c7ac, docs/evidence/r1-acceptance-20261122/measurements.json. This unpushed commit is not claimed publicly accessible.

Environment: Linux x86_64 WSL2 CPython 3.12.16 Mojo 1.2.0 (2016d0cd). Protocol: 5 processes/runtime; p50 is median of process p50; p95 is nearest-rank of 45 batch means; identical original inputs. These p95s describe batch means, not individual-call tails.

| Application / case | Backend | CPython p50 us | Public p50 / p95 us | Fastest measured strict competitor p50 us |
|---|---|---:|---:|---|
| pii_scrubber / short | native | 22.141 | 15.913 / 22.263 | expert_regex: 10.968 |
| pii_scrubber / medium | native | 4330.400 | 677.264 / 898.812 | expert_regex: 1512.820 |
| pii_scrubber / large | native | 52567.603 | 8075.100 / 8338.500 | expert_regex: 18655.900 |
| pdf_cleaner / small | native | 203.695 | 44.509 / 46.942 | cpython: 203.695 |
| pdf_cleaner / medium | native | 2016.600 | 346.123 / 363.490 | cpython: 2016.600 |
| pdf_cleaner / large | native | 19220.000 | 3173.501 / 3279.151 | cpython: 19220.000 |
| quant_backtest / 0 | native | 0.076 | 12.488 / 15.109 | cpython: 0.076 |
| quant_backtest / 100 | native | 23.104 | 12.338 / 16.159 | manual_cpp: 0.281 |
| quant_backtest / 10000 | native | 2512.067 | 43.293 / 72.911 | numba: 28.733 |
| quant_backtest / 100000 | native | 24166.300 | 398.405 / 454.018 | numba: 370.810 |
| rag_chunker / small | python_fallback_slower | 3.704 | 11.425 / 13.268 | cpython: 3.704 |
| rag_chunker / medium | python_fallback_slower | 21.563 | 30.654 / 32.145 | cpython: 21.563 |
| rag_chunker / large | python_fallback_slower | 137.762 | 145.865 / 154.016 | cpython: 137.762 |
| ocr_matcher / small | python_fallback_slower | 103.768 | 112.455 / 137.885 | rapidfuzz: 4.877 |
| ocr_matcher / medium | python_fallback_slower | 1003.275 | 1022.828 / 1256.500 | rapidfuzz: 39.632 |
| ocr_matcher / large | python_fallback_slower | 1677.625 | 1699.200 / 2180.033 | rapidfuzz: 370.600 |
| geo_distance / 100 | python_fallback_slower | 57.149 | 66.199 / 69.301 | manual_cpp: 7.150 |
| geo_distance / 1000 | python_fallback_slower | 599.292 | 631.269 / 683.908 | manual_cpp: 69.163 |
| geo_distance / 10000 | python_fallback_slower | 6366.000 | 6284.801 / 6565.100 | manual_cpp: 684.163 |
| ar_spatial / 100 | python_fallback_slower | 25.855 | 38.676 / 42.307 | manual_cpp: 2.138 |
| ar_spatial / 1000 | python_fallback_slower | 271.348 | 286.174 / 318.050 | manual_cpp: 20.485 |
| ar_spatial / 10000 | python_fallback_slower | 2799.550 | 2992.150 / 4100.700 | manual_cpp: 208.916 |

Input contracts: text/document fixtures are original strings and Python containers; spatial fixtures are Python lists. NumPy adapters include conversion and Numba list results include reflection. Equivalent ndarray-only timings cannot be substituted.

The [versioned data artifact](../benchmarks/current_public_v0_2_1_20261122.json) includes every engine, process p50 range, qualification status, Python-visible allocation peaks, AOT/cache/import/first-call/JIT costs and losing cases. No incorrect result enters the strict ranking. Tolerance-only NumPy and the disqualified PDF regex remain visible in data. Public fallback is not native acceleration; forced paths and private entries are separate. Private entry timing includes conversion/validation.

tracemalloc excludes Mojo/native allocation and total RSS. After-build import/first call and fresh-process startup are different scopes. Source/inputs and raw trial hashes are in the owner R1 evidence package. This workstation study makes no shared-runner performance guarantee.

[Historical claims and provenance](PRE_M0_CREDIBILITY_REVIEW.md) are separate. No v0.2.1 publication or universal speedup is implied.
