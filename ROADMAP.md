# Roadmap

This document describes the planned milestones for mojo-hotloop.

> **Status as of v0.2.0**: Developer Preview — API and binary format may change.

---

## v0.1.0 — Developer Preview (Released 2026-11-15)

**Goal**: Establish correctness, packaging, and documentation baseline.

- [x] `@hotloop` decorator with transparent Python fallback
- [x] Deterministic AST transpiler (Mojo 1.2.0)
- [x] 7 real-world use cases verified (7,220 total tests, 0 mismatches)
- [x] Content-addressed SHA-256 manifest cache with stale-binary detection
- [x] CLI: `hotloop build <file.py> --engine=ast|auto`
- [x] 50-test adversarial compiler test suite (47 PASS, 3 expected limitations)
- [x] Apache 2.0 license, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
- [x] GitHub CI workflow (Python correctness tests, packaging checks)
- [x] Clean `pip install` with graceful fallback when Mojo is absent

---

## v0.2.0 — Optimization Passes & Generalization (Released 2026-11-17)

**Goal**: Deliver five general compiler optimization passes and expand syntax without benchmark heuristics.

- [x] Redundant bounds-check elimination & in-bounds loop hoisting
- [x] Loop-invariant expression hoisting (`_collect_and_hoist_invariants`)
- [x] String buffer pre-allocation (`reserve_bytes`)
- [x] Fast codepoint & ordinal access (`_PyStr`, `get_cp_fast`, `get_ord_fast`)
- [x] Dispatch qualifier caching & smart fallback (`_DISPATCH_QUALIFIER_CACHE`)
- [x] `break` statements inside loops with proper invariant scoping
- [x] String negative indexing (`s[-i]`)
- [x] Runtime dispatch telemetry and introspection (`inspect_dispatch`)
- [x] Zero-copy integer offset API for RAG (`chunk_document_offsets`)
- [x] Subprocess environment isolation (Mojo runtime `PYTHONEXECUTABLE` fix)
- [x] 77-function generalization testing suite (100% parity across DSP, crypto, text, geometry)
- [x] 10-test optimization safety stress suite (0 regressions, 0 crashes)
- [x] Re-verified all 7 canonical application domains (7,220 checks, 0 mismatches)

---

## v0.2.1 -- Security, Qualification & Semantic-Parity Correction (Local Candidate, Unpublished)

**Goal**: Close all safety, ABI/cache, stdlib-binding, return-ownership, math-domain/overflow, and list-exception parity defects identified after `v0.2.0`, withdraw unproven native buffer routes, and align public documentation and hosted native CI.

**Granular Status**: `Locally implemented` / `Locally verified` / `PR prepared` (local stacked branches; `PR submitted`, `Hosted CI verified`, `Merged`, and `Released` are **BLOCKED** pending contributor DCO sign-off, SDK/trademark wording review, and GitHub-hosted native CI execution).

- [x] Narrow native ABI/runtime qualification to Linux x86-64 little-endian 64-bit GIL-enabled CPython `3.12.16` with Mojo `1.2.0` (`2016d0cd`), with safe Python fallback and `strict=True` refusal elsewhere *(locally verified)*
- [x] Full cache identity verification (compiler, SDK files, build settings, source, runtime ABI) and binary inode pinning (`rebuilt`/invalid cache detection) *(locally verified)*
- [x] Pre-import stdlib/intrinsic binding verification and verified scalar/constant/list-element return ownership *(locally verified)*
- [x] Explicit withdrawal of `v0.2.0` native `ndarray`/buffer/shared-container borrowing paths (`v0.2.1` copies qualified exact lists of builtin elements; buffer exporters fall back to Python or fail in `strict=True`) *(locally verified)*
- [x] Bounded/keyword `startswith`/`endswith` and variadic signature fallback preservation *(locally verified)*
- [x] CPython `ValueError`/`OverflowError` parity for unary `math.sin`, `math.cos`, `math.sqrt`, `math.log`, `math.exp`, binary `math.atan2`, and `math.isnan`/`math.isinf` (`int`/`float`/`bool` operands only) *(locally verified)*
- [x] CPython exact `IndexError` messages and RHS-before-index evaluation order on proven list reads/stores (`a11c9de`, `2789bdf`) *(locally verified; disclosed `geo_distance` 10k boxed-list slowdown)*
- [x] Pre-M0 public documentation, `NOTICE`/`THIRD_PARTY_NOTICES` updates, and matched-contract benchmark credibility tables *(PR 2 prepared; legal wording review pending)*
- [ ] M0 hosted GitHub Actions CI (`ubuntu-24.04`, Python `3.12.16`, Mojo `1.2.0`) and 25-function corpus verification *(PR 3 prepared locally; hosted CI UNVERIFIED until authorized push)*
- [ ] Remote PR review, hosted CI execution, tag, and release publication *(local DCO sign-off completed across PRs 1-3; remote push/CI/release BLOCKED pending authorization)*

> **Separate Phase F.2 track (`v0.3.0` candidate):** Safe NumPy zero-copy & SIMD optimization work is preserved independently on branch `codex/phase-f2-security-repair` (`61b0c36` / `aa8a21e`) and is explicitly **excluded** from `v0.2.1`.

---

## v0.3.0 — Syntax & Vectorization Expansion (Target: Q1 2027)

**Goal**: Expand Python syntax and SIMD vectorization paths.

- [ ] `continue` statements in loop bodies
- [ ] Chained comparisons (`a < b < c` → `a < b and b < c`)
- [ ] Negative list indexing (`xs[-1]` → `xs[len(xs)-1]`)
- [ ] Tuple return type (`-> tuple[int, float]`)
- [ ] Explicit SIMD vectorization pragmas for math loops
- [ ] Multi-dimensional array access patterns


---

## v0.3.0 — NumPy Fast Path (Target: Q2 2027)

**Goal**: Zero-copy NumPy 1-D array acceleration via raw pointer interop *(experimental security-repaired prototype preserved off-branch on `codex/phase-f2-security-repair` at `61b0c36`/`aa8a21e`; deferred until after `v0.2.1` release)*.

- [ ] `numpy.ndarray` (1-D, contiguous, float64/int64) as parameter type
- [ ] Direct C pointer dispatch: bypass per-element Python FFI
- [ ] Non-contiguous array detection with automatic copy + warning
- [ ] Benchmarks: target >10x over NumPy for simple reduction kernels

---

## v0.4.0 — Watch Mode & Incremental Rebuild (Target: Q3 2027)

**Goal**: Developer experience improvements.

- [ ] `hotloop watch <file.py>` — rebuild on source change
- [ ] Incremental transpilation (function-level invalidation)
- [ ] `hotloop check <file.py>` — lint without compiling
- [ ] VS Code extension: inline backend indicator, fallback warning highlights

---

## v0.5.0 — Multi-Function Modules (Target: Q4 2027)

**Goal**: Support files with multiple `@hotloop`-decorated functions.

- [ ] Multiple exports in a single `.so` module
- [ ] Helper function inlining across annotated functions
- [ ] Module-level constant folding
- [ ] Shared `__mojocache__` directory with per-function manifests

---

## v1.0.0 — Stable Release (Target: 2028)

**Goal**: API stability, broad compatibility, production quality.

- [ ] Stable decorator API (no breaking changes after 1.0.0)
- [ ] Stable CLI interface
- [ ] Windows (native) support
- [ ] macOS (Apple Silicon) support
- [ ] PyPI package (`pip install mojo-hotloop`)
- [ ] Comprehensive test suite (500+ tests, CI on GitHub Actions)
- [ ] Full documentation site (ReadTheDocs or similar)
- [ ] Security audit by independent third party
