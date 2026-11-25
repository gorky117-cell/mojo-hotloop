# M0 native CI and reference baseline

Status: LOCAL INTEGRATION VERIFIED; AWAITING OWNER AUTHORIZATION FOR HOSTED RUN. The original proposal `b111070` was based on runtime `568faf2`. This integrated candidate combines the tested `v0.2.1` corrective runtime (`a11c9decc76dfdb7350f921d9b5f97451583e78b`), Pre-M0 documentation/notices, and M0 CI/reference corpus (`ef3706930f6502f0f6d9ac88190cdd476e6d0fbf`). No push, new hosted run, or new badge is authorized.

Existing public CI run 44120208039 on main commit 080125ec03b68a55423d426a48c112b7415f8b48 succeeded, including native compilation/backend assertion. This is historical evidence, not validation of the new candidate or exact qualification gate.

## Proposed job

Ubuntu label ubuntu-24.04, x64, CPython exactly 3.12.16 and Mojo 1.2.0 (2016d0cd). The official actions/python-versions manifest currently lists a 3.12.16 Ubuntu 24.04 x64 release. Setup must fail rather than substitute another patch version. The preflight checks actual Python/GIL/word size, SDK version, installed package location and complete native-cache toolchain fingerprint.

The current-main Python job (with the 0.2.1 metadata assertion) and repaired DCO workflow are preserved. Mojo, mojo-compiler and mojo-lldb-libs are all pinned to 1.2.0 and checked in preflight. The native job installs the package, asserts a real public-call native smoke, runs the 25-function corpus, proves that no-build fallback fails required-native cases, runs current tests/security/cache and all seven application suites. Test copies omit hotloop source so installed code is exercised. Artifacts contain observations/versions, not SDK binaries or reusable untrusted native caches.

CI uses the package network for dependency installation. Installed compilation/runtime remain offline. Hosted timings are diagnostic observations, never stable speedup acceptance thresholds. Actual runner ImageVersion, workflow URL and run ID remain UNVERIFIED until authorized hosted execution.

## Frozen reference

reference/m0-v1/manifest.json defines 25 functions and immutable source hashes. Each retains inputs, expected CPython values/types/bits or exception, route requirements and explicit unsupported cases. Raw observations preserve cold build/cache, warm public and Python timings, ownership, mutation, stdout, exceptions, modes and environment.

Original b111070 local result (fresh integration results are recorded separately): 24 successful module builds, 14 correct default-native fixtures, 16 correct forced-native fixtures, zero unexplained mode mismatches. Build success can include refusal stubs and is not native execution coverage. A no-build run retains all 25 rows, reports zero native fixtures and fails 46 required-native mode checks.

The reference set includes intentionally unsupported ternary syntax, mutable list identity, shared container output, NumPy/array/memoryview fallback, surrogate fallback, code/default/helper constants, scalar/list-element identity, overflow, zero division and string allocation/ownership.

## Reproduce locally

Use the installed candidate interpreter, unset PYTHONPATH, and fresh output directories:

~~~bash
python tools/native_ci_preflight.py --output /tmp/NEW_ENV.json
python tools/native_ci_smoke.py --directory /tmp/NEW_SMOKE
python tools/run_m0_reference.py --output /tmp/NEW_REFERENCE
python tools/run_m0_reference.py --no-build --samples 1 --output /tmp/NEW_NEGATIVE
~~~

The last command must exit nonzero and write observations with 25 rows, zero native successes and nonempty route failures. No function is removed from the denominator.

## Owner gate

Approve the R1 runtime dependency first, review this separate stacked diff and genuine DCO attribution, then authorize the branch push/PR and hosted execution. Record the actual run URL, ID, commit and uploaded environment. Only then consider a native status badge or adding its exact job context to required branch checks. Neither a local result nor an older green job completes current M0.


## Math semantic parity gate

The previously reproduced math domain/overflow defects (`sin(inf)`, `cos(inf)`, `log(0)`, `log(-1)`, `exp(1000)`) and numeric-only operand admission (`isnan`/`isinf` plus exact `int`/`float`/`bool` gating) were repaired in the integrated `v0.2.1` runtime (`a11c9dec`). `tools/check_math_semantics.py` (`15/15`) and the broader pytest math/exception suites (`380` tests) remain enabled and mandatory in `.github/workflows/ci.yml` without expected-failure waivers. The required-native smoke and frozen 25-function corpus prevent fallback-only green passes and fail when native artifacts are withheld.
