# mojo-hotloop

> **Corrective v0.2.1 release candidate — unreleased; awaiting owner review, DCO attestation, and legal clarification.** Earlier math domain/overflow (`sin`, `cos`, `log`, `exp`, operand-type admission, `isnan`/`isinf`) and list-bounds/assignment-order defects are repaired and verified locally against a clean offline wheel (`380` pytest checks, `129` frozen security checks, `7,220` application scenarios, `15` math parity checks, `390` list-exception checks, `1,095` operand/predicate checks). Disclosed performance regressions, narrow native platform scope, and `11` separately tracked historical `v0.2.0` compatibility failures remain documented below. No release tag, PyPI package, or hosted CI promotion is authorized.

An offline deterministic Python-to-Mojo transpiler for a documented typed Python subset, with observable native execution and Python fallback.

The published releases are `v0.1.0` and [v0.2.0 Developer Preview](https://github.com/gorky117-cell/mojo-hotloop/releases/tag/v0.2.0) on GitHub. The `v0.2.1` corrective candidate described here is **local and unreleased**, awaiting owner approval; no PyPI release is claimed. Historical native-array and maximum-speedup claims from `v0.1.0`/`v0.2.0` are not promises for `v0.2.1` (experimental Phase F.2 buffer work is kept separate and is not part of `v0.2.1`).

## Supported environment and semantics

The corrective `v0.2.1` candidate qualifies native execution only on **Linux x86-64, little endian, 64-bit GIL-enabled CPython 3.12.16 with 30-bit PyLong digits and Mojo 1.2.0 (`2016d0cd`)**. WSL2 on Ubuntu 24.04 is the verified local environment. Other CPython patch versions, architectures, free-threaded builds, and native Windows/macOS are not qualified for native execution and fall back to Python safely (or raise `HotloopNativeExecutionError` under `strict=True`).

Supported native inputs are exact built-in Python scalars (`int`, `float`, `bool`, `str`) and validated private copies of qualified `list[int|float|bool|str]` inputs on read-only/proven kernels. In `v0.2.1`, NumPy arrays and scalars (`numpy.ndarray`, `numpy.float64`, `numpy.int64`, `numpy.bool_`), `array.array`, `memoryview`, and arbitrary buffer exporters execute via Python fallback in both default and `force_native=True` modes (and raise `HotloopNativeExecutionError` in `strict=True`); no zero-copy pointer borrowing or SIMD vectorization is enabled in `v0.2.1`. Bounded/keyword `startswith`/`endswith` calls, variadic signatures, replaced stdlib bindings, unproven mutable/aliased containers, `math.floor`/`math.ceil`, and unsupported syntax also use Python fallback.

See [syntax and qualification](docs/SUPPORTED_SYNTAX.md). Language lowering support does not guarantee native admission for every value or a speedup.

## Install a reviewed candidate

Obtain an owner-approved wheel and its SHA-256. No v0.2.1 publication is implied. Dependency installation may use the network; installed transpilation and execution are offline.

~~~bash
python3.12 --version  # Must report 3.12.16 for native qualification
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install mojo==1.2.0
mojo --version       # Mojo 1.2.0 (2016d0cd)
python -m pip install --no-index --no-deps /path/to/approved/mojo_hotloop-0.2.1-py3-none-any.whl
~~~

The SDK is an external prerequisite, not part of the Hotloop wheel. Review its own applicable terms; the project's Apache-2.0 license does not relicense external SDK components.

## Build and observe the public call

Save this as example.py:

~~~python
from hotloop import hotloop

@hotloop
def sum_squares(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i*i
    return total
~~~

~~~bash
hotloop build example.py --engine=ast
python -c 'import example; from hotloop import inspect_dispatch; print(example.sum_squares(5000)); print(inspect_dispatch(example.sum_squares))'
~~~

Inspect the actual backend. Missing/stale/unqualified artifacts or unsupported calls fall back with observable warnings and counters. Build in a directory you control and retain the verified cache. Rebuild artifacts from older versions. The compiler does not run a CPython differential benchmark on ordinary calls.

Use @hotloop(strict=True) to reject unsupported native execution. force_native=True bypasses performance qualification only; it does not bypass ownership, representation, range, cache or platform checks. Strict mode is not a performance guarantee.

## Current candidate benchmark observations

These are matched-input public-call measurements on one recorded workstation, not hosted-runner guarantees or universal acceleration. Native and fallback are distinct; strict compatibility is scoped to the listed fixtures.

<!-- CURRENT_BENCHMARKS_START -->
| Application / case | Backend | CPython p50 us | Public p50 / p95 us | Fastest measured strict competitor p50 us |
|---|---|---:|---:|---|
| pii_scrubber / large | native | 52567.603 | 8075.100 / 8338.500 | expert_regex: 18655.900 |
| pdf_cleaner / large | native | 19220.000 | 3173.501 / 3279.151 | cpython: 19220.000 |
| quant_backtest / 100000 | native | 24166.300 | 398.405 / 454.018 | numba: 370.810 |
| rag_chunker / large | python_fallback_slower | 137.762 | 145.865 / 154.016 | cpython: 137.762 |
| ocr_matcher / large | python_fallback_slower | 1677.625 | 1699.200 / 2180.033 | rapidfuzz: 370.600 |
| geo_distance / 10000 | python_fallback_slower | 6366.000 | 6284.801 / 6565.100 | manual_cpp: 684.163 |
| ar_spatial / 10000 | python_fallback_slower | 2799.550 | 2992.150 / 4100.700 | manual_cpp: 208.916 |
<!-- CURRENT_BENCHMARKS_END -->

[Complete current tables and protocol](docs/CURRENT_BENCHMARKS.md) include small/medium/large cases, forced routes, p95, cold costs, variance, memory limitations and losing competitors. The versioned data file and its exact measured runtime revision (`568faf2`) are linked there. **Known performance regressions:** subsequent `v0.2.1` exception-parity verification ([exception-parity report](docs/V0_2_1_EXCEPTION_PARITY_RELEASE_GATE.md)) reproduced a slowdown on 10,000-waypoint `geo_distance` boxed-list native paths (`+12.9%` to `+33.5%` forced and `+19.2%` to `+24.0%` strict across 5-process paired trials vs pre-repair baseline), alongside tiny-call FFI validation/conversion overhead on small inputs (`quant_backtest / 0`: `12.488 us` native vs `0.076 us` CPython) and default fallback on boxed-list/string workloads (`rag_chunker`, `ocr_matcher`, `geo_distance`, `ar_spatial`). Private entry timing includes validation/conversion and is never substituted for public latency.

The [v0.1.0 historical dataset](benchmarks/canonical_benchmarks_v0.1.0.json) and [historical report](BENCHMARK_REPORT.md) remain unchanged. Their 69.34x backtest, 4.96x PII and ndarray figures are historical measurements under different contracts. They are not current corrective-release claims. Conflicting figures from other runs are indexed in [claim reconciliation](docs/PRE_M0_CREDIBILITY_REVIEW.md).

## CI, offline compilation, and verification

All transpilation, `mojo build` native compilation, SHA-256 manifest/cache verification, and runtime execution run **100% offline** with zero AI/cloud APIs or Rust dependencies (network access is only needed if installing packages via `pip`).

Existing hosted CI on public main predates this candidate. Its [recorded run](https://github.com/gorky117-cell/mojo-hotloop/actions/runs/44120208039) includes a successful native smoke step. The updated `v0.2.1` CI workflow and 25-function frozen corpus are prepared locally in `.github/workflows/ci.yml` and [M0 CI specification](docs/M0_NATIVE_CI_AND_REFERENCE.md); no new green hosted badge is installed before an authorized hosted pass.

~~~bash
python tests/test_compiler_adversarial.py
python benchmarks/generate_benchmark_reports.py --check
~~~

The full native/security release gate runs from a clean wheel installation with `380` collected pytest cases (including `129` frozen security checks, math parity gates, list exception-parity checks, and all `7,220` original application scenarios). The unmodified frozen `v0.2.0` compatibility suite retains **75 passed / 11 separately documented failures** (`9` intentional semantic-safety withdrawals vs obsolete mandatory-native assertions, `1` obsolete `2 ** -1` `ValueError` assertion, and `1` obsolete `>5x` speed assertion); the preserved `v0.2.0` NumPy example carries an explicit historical notice. Local passes do not substitute for a GitHub-hosted CI run.

## Contributing and reporting

Read [CONTRIBUTING.md](CONTRIBUTING.md), [the code of conduct](CODE_OF_CONDUCT.md) and [SECURITY.md](SECURITY.md). DCO attestation and maintainer review remain required. Report vulnerabilities privately through the repository Security tab, not public issues.

History: [existing engineering index](docs/history/README.md) and [release/claim history](docs/history/REVIEW_HISTORY_2026.md).

## License and independence

Mojo Hotloop's own code is Apache-2.0; [LICENSE](LICENSE) and [NOTICE](NOTICE) are preserved. Copyright 2026 Gaurav Kumar Singh and contributors.

This independent project is not affiliated with, sponsored by or endorsed by Modular, Inc. MAX® and Mojo® are trademarks of Modular, Inc. used under license. The attribution follows the [published policy](https://www.modular.com/legal/trademark); it does not assert an exclusive trademark grant. [Third-party notices](docs/THIRD_PARTY_NOTICES.md) distinguish external SDK terms from the project's license.
