# v0.2.1 private security remediation review

**READY FOR PRIVATE OWNER SECURITY REVIEW**

The candidate corrects all six observed value, type or control-flow mismatches in v0.2.0’s 15-case differential probe. A separate probe confirms that Python callers see their list mutate exactly once and receive that same list back. The patch retires native borrowed buffers, removes unchecked indexed access from the generated collection paths, and makes a verified private cache entry a prerequisite for native dispatch. Existing applications that relied on native NumPy inputs will see a significant performance and strict-mode compatibility change.

## Provenance and scope

| Reference | Exact revision |
|---|---|
| Upstream v0.2.0 commit | `b1ea08d0c0a3cbf9a946ace2b3c5b1360ac0b704` |
| Upstream source tree | `a86ad315688cf44bb9ab5a2d639a3dd396e69d63` |
| First corrective commit | `569c846d2b1f1a9352dc26994dac9f5fddb6feec` |
| Exact source of the tested wheel and sdist, including strict telemetry | `5bf4b224c2c685324cbbabd3f48bd03409263d37` |
| Standalone audit fixture repairs | `821a9821395de3d47cd23cc95396d4ed08a333b2` |
| Final local review commit in Git exports | `$Format:%H$` |

In a checkout, `git log -1 --format=%H -- docs/V0_2_1_SECURITY_REMEDIATION.md` resolves the last row. Git expands the identifier in the exported owner copy. The local branch is `security/v0.2.1-remediation`. It descends directly from the published commit. The annotated tag objects remain `a2d31656223d3efb8e3281f376e4c7128e1dd4c4` (v0.1.0) and `dfcb776a962125cbaeffa6b853732a0382067a83` (v0.2.0). The v0.1.0 tag peels to `b7d587e3ac2b9201e56253a5f7ecdd267da7301d`. The protected local main reference was `080125ec03b68a55423d426a48c112b7415f8b48` at verification.

The private published-release audit supplied the findings and original probes. Only the widened multiply from `95c90f2`, the compiler FP setting from `618571d`, and selected cache identity and verification logic from `061e383` were adapted. The package contains no pipeline or experimental raw-buffer implementation.

## Findings, reproductions and remedies

| Finding and classification | Published evidence | Candidate result and route |
|---|---|---|
| Signed multiplication, correctness, both versions | Minimum signed 64-bit integer × −1 returned −9223372036854775808 in normal and strict native execution. | Compute in Int128, check, then narrow. Normal dispatch returns the Python integer 9223372036854775808 through overflow fallback. Strict raises. Minimum × 1 remains native. |
| Zero-trip loop, correctness, v0.2.0 | A loop containing division by zero raised even with zero iterations. v0.1.0 returned 0.0. | Retired speculative invariant hoisting. Zero trips return 0.0 natively. The one-iteration control raises Python’s ZeroDivisionError. Nested, skipped and early-exit paths are covered. Loop-else and callers that depend on it use Python. |
| List mutation and identity, correctness, both versions | The tags’ own swap function returned an equal copy under force and strict. The caller’s list stayed [1, 2, 3, 4]. | Disqualify functions that mutate, retain, alias or return a borrowed list unless its use meets the read-only rules. Propagate exclusions through helper calls. Default and force return the caller’s [4, 2, 3, 1] by identity. Strict raises before mutation and records native_error with zero executed calls. |
| NumPy return types, correctness, both versions | Contiguous float64, a valid strided input and float32 produced builtins.float where Python returned the NumPy scalar type. | Array and NumPy scalar arguments take observable semantic fallback. Values, types and Python exceptions are preserved by CPython. Strict rejects the call. |
| Floating-point contraction, correctness, both versions | The two-sample recurrence returned binary64 bits `3fec517ef8e18fc1`. Separate Python operations yield `3fec517ef8e18fc2`. | Compile with `--fp-mode contract=off`. The forced, read-only boxed-list recurrence returned `3fec517ef8e18fc2` natively. Tested signed zero, infinities, NaN and a multiply/add cancellation control. |
| Borrowed buffer admission, native-memory security and numerical integrity, both versions | Generated code read address attributes without a pinned, fully validated export. Safe descriptor inspection showed unaligned and foreign-endian arrays satisfying the old superficial tests. | Remove that entry from generated code. Reject all buffer exporters before native unboxing. The defensive child-process tests exercise legitimate exporters and compare Python behavior. |
| Unproven bounds elimination, native-memory security and correctness, v0.2.0 | Inspection found function-wide length aliases driving unchecked access. The generated numeric probe included the old unchecked-index helper. | Retain per-access checks for generated list and codepoint indexing. The same probe contains no old unchecked-index helper, fast codepoint getter or raw-address conversion. Out-of-range supported inputs retain IndexError. |
| Unverified extension loads, native-code integrity, both versions | Tagged loaders could reach the extension loader before validating a binary checksum or build identity. The old source-key cache also skipped a manifest check. | Require a trusted directory, qualified build manifest, matching runtime/compiler context and actual binary digest before load. Ordinary dispatch falls back and strict rejects unusable artifacts. |

Both old wheels were retested against CPython. v0.1.0 matched 10/15, v0.2.0 matched 9/15, and the candidate matched 15/15. The candidate’s 15 outcomes comprised **10 native** (including the expected division exception), **2 Python overflow fallbacks** and **3 Python semantic fallbacks**. The separate list-identity probe used fresh inputs in each mode. The security findings on the published versions are based on source and generated code inspection. No unsafe memory read or execution of a modified binary was needed to establish the missing controls. [Per-case results, values, types, exceptions and routes](evidence/v0_2_1_remediation.json)

Related numeric restrictions include checked shift boundaries, Python handling for negative integer exponents, large-integer true division that may double round, floating floor division/remainder, and selected power/domain cases. Tests cover the distinction between a returned value, a Python exception, and a strict native rejection.

## Native boundary and cache guarantees

The extension accepts exact supported scalar types. For qualified read-only list inputs it makes a tuple snapshot while Python owns the GIL, checks exact element types and integer range, then unboxes that snapshot into native-owned storage. The generated entry repeats argument qualification for callers that directly reach the entry. There is no pointer borrowed from an external mutable buffer. An ndarray, array.array, memoryview, buffer-like subclass or NumPy scalar goes through Python or strict rejection. The subprocess checks cover writable and read-only views, wrong dtype, rank, noncontiguous layout, foreign byte order, unaligned storage, empty arrays, released views, resize and a concurrent Python writer. These tests establish the route on the tested inputs. They do not establish a general thread-safety guarantee for user code.

Build identity covers source bytes, generated code conventions and hash, compiler package implementation bytes, the selected local Mojo version and toolchain fingerprint, flags and relevant environment, CPython ABI, optimizer mode and host characteristics. Build outputs use temporary files and atomic replacement. The builder rechecks source and context before advertising the artifact. Loader validation independently discovers the compiler, checks directory ownership and write permissions, verifies metadata and SHA-256, then opens and verifies the ELF bytes on a file descriptor retained for the loaded module. An adjacent legacy fast.so alone gives no native dispatch. Rebuild each source module when upgrading. Keep the source, its verified cache and the corresponding trusted local Mojo installation available.

Changing the implementation, ABI, toolchain, version, settings, manifest, generated digest or binary caused rejection in the dedicated cache tests. A tripwire replaced the native loader in rejection tests. Valid cache reuse still executed native code. Additional tests covered source edits with restored mtime, a source change during compilation, optimizer-mode changes and shared-writable files/directories. Native module initialization also altered two libc environment variables without updating Python’s mapping on this host. Restoring both at loader exit fixed false cache misses and incorrect interpreter selection in child processes.

## Independent validation

Tests ran as an unprivileged user in a loopback-only Linux network namespace, using installed wheels and a separately provisioned local toolchain. Environment: Ubuntu 24.04.3 LTS, x86-64 WSL2, CPython 3.12.16, Mojo 1.2.0 (2016d0cd), NumPy 2.5.4, pytest 9.2.0, RapidFuzz 3.14.6 and setuptools 84.2.1.

| Test | Actual outcome |
|---|---|
| Published v0.1.0 tests on their original wheel | 62 passed |
| Published v0.2.0 tests on their original wheel | 86 passed |
| Unchanged v0.1.0 tests on candidate | 56 passed, 6 failed |
| Unchanged v0.2.0 tests on candidate | 75 passed, 11 failed |
| Complete candidate pytest suite | **129 passed**, 65 expected fallback warnings. Includes 27 new semantic/boundary cases and 16 new cache cases. |
| Standalone adversarial compiler suite | 49 passed, 1 expected rejection, 0 unexpected failures |
| Standalone cache lifecycle | 6 passed |
| Application verification | **7,220 of 7,220** matched. Quant 1,117, AR 1,010, geo 1,014, OCR 1,020, PII 1,019, PDF 1,020, RAG 1,020. |
| Supplemental diagnostics | 6 dispatch, 6 Unicode and 2 text-boundary checks passed. Peak RSS grew by 0 KiB across 15,000 text calls and 640 KiB across 60,000 measured strict-native collection calls. |

AR and geo each check both routes on every case, giving 2,024 strict native boxed-list calls and 2,024 ndarray fallbacks across those applications. OCR and RAG check a forced native route and default list fallback. Quant, PII and PDF verify native execution. The 7,220 figure counts application cases once. The standalone Unicode fixture is an independently built local test extension. The collection RSS check now asserts actual native counters. Bounded peak-RSS observations on these workloads cannot establish absence of leaks.

The unchanged v0.2.0 suite failed nine tests that asserted retired native routing or counters (including mixed floating divmod), one that expected ValueError for Python’s valid `2 ** -1 == 0.5`, and one that required a greater-than-5× win across mismatched representations. The six v0.1.0 failures cover the same categories. The candidate tests assert Python values, types, exceptions and actual routes separately. The standalone dispatch audit previously imported an absent fixture. It now uses the repository’s quant application, with its original Python function as oracle. Individual unchanged test names and timings are recorded in the evidence. [Raw comparisons and suite results](evidence/v0_2_1_remediation.json)

## Performance cost

End-to-end decorated call times in microseconds, median of three independent Python processes per wheel. Entries in parentheses are the minimum and maximum of the three process medians. Each process alternated five timed Python and decorated batches on the same input object after warmup. Measurements ran separately from compilation and regression jobs. The last column gives the equivalent undecorated Python median on the candidate runs.

| Workload | Published 0.2.0 µs | Candidate 0.2.1 µs | CPython µs | Candidate route |
|---|---:|---:|---:|---|
| Sum of squares, 1 iteration | 2.75 (2.72–2.77) | 5.64 (5.60–5.87) | 0.14 | Native |
| Sum of squares, 8,192 | 16.13 (15.97–16.62) | 20.49 (20.35–23.09) | 471.16 | Native |
| Sum of 8,192 ndarray values | 21.68 (21.40–25.08) | 954.40 (952.72–965.11) | 953.99 | Python, preserves NumPy scalar |
| Sum of 8,192 list values, default | 258.66 (255.81–268.38) | 263.25 (255.00–263.33) | 250.80 | Python |
| Same list, explicitly forced | 444.22 (432.13–447.71) | 982.38 (977.03–992.93) | 256.86 | Native, validated snapshot |

The old ndarray result had the wrong scalar type. Its time documents the cost of retiring that path. The large scalar workload still gained about 23× against its own Python implementation on this host. Tiny scalar calls and forced list traversal lost to Python. The validated binding, snapshot and per-element checks add work, and removing unsafe compiler shortcuts affects generated kernels. These aggregate timings do not isolate the contribution of each change. [Benchmark driver](../audit/bench_patch_dispatch.py) · [Per-process measurements](evidence/v0_2_1_remediation.json)

## Distribution and offline contract

| Local artifact | Bytes | SHA-256 |
|---|---:|---|
| mojo_hotloop-0.2.1-py3-none-any.whl | 42,695 | `6ce78be25db5c8e19f8899b9e5014a535fdc6f93e32f4856e2637a136df6836f` |
| mojo_hotloop-0.2.1.tar.gz | 71,965 | `cbd747a2f1a090907fde333947d2de2831d21cf26d2525b48a42d4faa8a85f84` |

All nine shipped package source files matched the artifact commit in both formats. All 16 wheel members were accounted for in RECORD and its hash and size records validated. The sdist had 29 files. Both distributions carry the matching Apache-2.0 LICENSE and NOTICE, distribution version 0.2.1, Python >=3.12, zero mandatory third-party Python packages, optional NumPy extras and no native binary. A separate offline build from this sdist produced a **byte-identical wheel** with a fixed SOURCE_DATE_EPOCH. The sdist checksum identifies this exact archive. Independent sdist builds can carry different tar timestamps. Both installed independently in fresh environments. The smoke tests ran before exposing test dependencies, with only pip and mojo-hotloop installed. They covered missing binary, fallback, strict rejection, local native execution, rejection of unsupported source and deterministic generated Mojo across default, ast and auto engines. There is no remote compilation, AI SDK, external API dependency or Rust component in the shipped runtime. A locally provisioned Mojo compiler remains necessary for the verified native path.

## Reproduction

In an isolated Linux user-owned scratch directory, set V to a local CPython/Mojo/test environment and P to the review checkout. Run inside a network namespace with only loopback available. The following builds from the exact artifact revision.

```bash
set -eu
export MOJO_BIN="$V/bin/mojo" PATH="$V/bin:$PATH" PIP_NO_INDEX=1
unset PYTHONPATH HOTLOOP_STRICT HOTLOOP_FORCE_NATIVE HOTLOOP_STRICT_PERF
C=5bf4b224c2c685324cbbabd3f48bd03409263d37
D=$(mktemp -d)
mkdir -p "$D/src" "$D/dist" "$D/quick" "$D/suite/benchmarks" "$D/rebuilt"
git -C "$P" archive "$C" | tar -x -C "$D/src"
export SOURCE_DATE_EPOCH=$(git -C "$P" show -s --format=%ct "$C")
(cd "$D/src" && "$V/bin/python" -c 'import sys,setuptools.build_meta as b; out=sys.argv[1]; b.build_sdist(out); b.build_wheel(out)' "$D/dist")
(cd "$P" && "$V/bin/python" audit/verify_patch_artifacts.py "$D/dist" "$C")
"$V/bin/python" -m venv "$D/venv"
py="$D/venv/bin/python"
"$py" -m pip install --no-index "$D/dist/"*.whl
(cd "$D/quick" && "$py" "$P/audit/remediation/offline_probe.py")
"$V/bin/python" -m pip wheel --no-deps --no-index --no-build-isolation "$D/dist/"*.tar.gz -w "$D/rebuilt"
cmp "$D/dist/"*.whl "$D/rebuilt/"*.whl
```

For the full tests, first provision pytest, NumPy, RapidFuzz and the other local test libraries in the test interpreter. This run exposed the preprovisioned V site-packages to the test venv only after completing the bare-wheel smoke test. Copy tests, examples and audit into scratch so source-checkout imports cannot shadow the installed package. Confirm hotloop.__file__ is under the candidate venv. Then run the following.

```bash
cp -r "$P/tests" "$P/examples" "$P/audit" "$D/suite/"
cd "$D/suite"
export PYTHONPATH="$PWD:$PWD/audit" OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
"$py" -m pytest -q tests
"$py" tests/test_compiler_adversarial.py
"$py" audit/test_cache_invalidation.py
for a in quant_backtest ar_spatial geo_distance ocr_matcher pii_scrubber pdf_cleaner rag_chunker; do
  "$py" -m hotloop.cli build "examples/$a/original.py" --no-verify
  "$py" "examples/$a/verify.py"
done
for a in running_max count_greater simple_moving_average; do
  "$py" -m hotloop.cli build "audit/unseen_cases/$a/original.py" --no-verify
done
"$py" audit/test_performance_dispatch.py
"$py" audit/test_collections_memory.py
"$MOJO_BIN" build -O3 audit/unicode_primitives.mojo --emit shared-lib -o audit/unicode_primitives.so
"$py" audit/test_unicode_semantics.py
"$py" audit/test_text_boundary_memory.py
```

For exact historical comparisons, extract each tag’s tests with `git archive v0.1.0 tests` or `git archive v0.2.0 tests` into its own scratch directory, create its benchmarks directory, and run pytest there once per installed wheel. Run `audit/remediation/parity_probe.py` and `identity_probe.py /absolute/path/to/tests/test_unfamiliar_functions.py` in separate empty directories per interpreter. For timings, run `audit/bench_patch_dispatch.py --directory DIR --build` once per interpreter, then rerun without --build three times in alternating release order.

## Proposed private GitHub Security Advisory

**Title** — Insufficient validation of native buffer access and cached extensions in Mojo Hotloop Developer Preview.

**Affected releases** — Verified source findings in mojo-hotloop v0.1.0 and v0.2.0 for buffer admission and extension integrity. Unsafe bounds elimination additionally affects v0.2.0. The proposed patched version is v0.2.1, pending owner review.

**Impact and prerequisites** — An application that admits an unsuitable Python buffer to affected native code can produce incorrect data or risk an invalid memory access. The v0.2.0 compiler can remove collection bounds checks without sufficient proof. An installation that loads a stale, corrupted or untrusted local native artifact risks incorrect execution or execution with the host Python process’s privileges. Cache integrity impact depends on who can write the artifact directory and which local builds are reused. The review did not establish exploitation, a compromised release asset, remote reachability or a specific severity score.

**Temporary mitigation and proposed resolution** — Use the original Python functions for affected kernels and keep shared or untrusted build outputs outside the application’s import/load paths. Avoid forced native array/list use with the affected releases. For the proposed update, rebuild from trusted sources under a private directory using the trusted local toolchain. NumPy and other exporters use Python. Existing raw native modules require replacement. Signed multiplication, mutation, control-flow and numerical parity corrections also belong in the release notes.

**Owner decision** — Review the memory and loader changes independently, determine deployment exposure, advisory severity and disclosure timing, and coordinate user guidance privately. Upstream contributor/DCO authorization, rights and trademark questions identified by the published-release audit remain owner matters. The local engineering commits use an agent identity and carry no owner sign-off.

## Residual limits

The tests cover one Linux x86-64 CPython/Mojo combination. They do not prove universal Python equivalence, cross-platform native loading, bitwise portability of all libm operations or absence of memory errors in Mojo. Linux descriptor pinning relies on /proc/self/fd. Hashes detect damage and mismatches within a trusted installation. An attacker controlling the user account, toolchain, source or both cache and metadata is outside that trust boundary. An explicit manual extension import bypasses decorator validation. Long-lived processes retain a descriptor per loaded native module. Formally verifying every native helper, immutable Python scalar identity and concurrent changes to the application’s own Python objects remains outside this evidence. Historical performance scripts that reach into the old private loader or hand-build raw-pointer examples are research artifacts and cannot validate the new public path.

The candidate is available for a **private owner decision**. Public disclosure, tagging, a merge and distribution each require separate owner authorization.
