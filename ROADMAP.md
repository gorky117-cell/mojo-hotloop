# Roadmap

This document describes the planned milestones for mojo-hotloop.

> **Status as of v0.1.0**: Developer Preview — API and binary format may change.

---

## v0.1.0 — Developer Preview (Released 2026-11-15)

**Goal**: Establish correctness, packaging, and documentation baseline.

- [x] `@hotloop` decorator with transparent Python fallback
- [x] Deterministic AST transpiler (Mojo 1.2.0)
- [x] 7 real-world use cases verified (7,220 total tests, 0 mismatches)
- [x] Content-addressed SHA-256 manifest cache with stale-binary detection
- [x] CLI: `hotloop build <file.py> --engine=ast|gemini|auto`
- [x] 50-test adversarial compiler test suite (47 PASS, 3 expected limitations)
- [x] Apache 2.0 license, CHANGELOG, CONTRIBUTING, CODE_OF_CONDUCT, SECURITY
- [x] GitHub CI workflow (Python correctness tests, packaging checks)
- [x] Clean `pip install` with graceful fallback when Mojo is absent

---

## v0.2.0 — Syntax Expansion (Target: Q1 2027)

**Goal**: Expand the set of Python programs the AST transpiler can handle.

- [ ] Chained comparisons (`a < b < c` → expand to `a < b and b < c`)
- [ ] Negative list indexing (`xs[-1]` → `xs[len(xs)-1]`)
- [ ] `break` and `continue` statements in loops
- [ ] Tuple return type (`-> tuple[int, float]`)
- [ ] `dict[str, float]` read-only access
- [ ] String slice (`s[i:j]`)
- [ ] `enumerate()` and `zip()` in for loops
- [ ] `assert` statement (compiled as runtime check)
- [ ] Support `# noqa: hotloop-skip` annotation to exclude functions

---

## v0.3.0 — NumPy Fast Path (Target: Q2 2027)

**Goal**: Zero-copy NumPy 1-D array acceleration via raw pointer interop.

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
