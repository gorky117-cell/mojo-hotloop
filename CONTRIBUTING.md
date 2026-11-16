# Contributing to Mojo Hotloop

Thank you for your interest in contributing to **Mojo Hotloop**!

Mojo Hotloop is an independent open-source project created by **Gaurav Kumar Singh** that provides transparent ahead-of-time (AOT) acceleration of Python hot loops using Mojo shared libraries.

We welcome outside developers and researchers worldwide to help us improve compiler correctness, expand supported Python syntax, optimize native C-ABI execution, enhance documentation, and verify or challenge benchmarks.

---

## 1. Open Contribution Model

We believe in open, transparent, and reproducible software engineering:

- **Forking and Branching**: You can freely fork the repository, experiment with compiler enhancements, and submit pull requests. Contributors do not need direct write access to the official repository.
- **Participating in Discussions**: Ask questions, suggest ideas, or share experience in [GitHub Discussions](https://github.com/gorky117-cell/mojo-hotloop/discussions).
- **Reporting Issues**: Report compiler bugs, native crashes, installation issues, or performance regressions using our structured issue templates.
- **Reproducing Benchmarks**: We encourage independent verification of our published performance claims. All benchmark harnesses are reproducible and open.
- **Apache-2.0 Rights**: These contribution guidelines apply to official upstream merges into `gorky117-cell/mojo-hotloop`. They do **not** override, restrict, or modify your statutory rights under the Apache License 2.0 to use, modify, distribute, or fork the software.

---

## 2. Automated Contributor Assistance & Developer FAQ

To help developers contribute smoothly, the project provides automated checks and guidance:

### System & Environment Requirements
- **OS**: Linux x86-64 (Ubuntu 24.04 LTS recommended, native or WSL2).
- **Python**: CPython 3.12+ (tested with 3.12.16).
- **Mojo Compiler**: Mojo 1.2.0 CLI (`modular install mojo`) required for building native libraries. (The AST transpiler and adversarial test suite run 100% offline without Mojo installed).

### Supported Python Syntax
Mojo Hotloop currently transpiles a deterministic subset of Python 3.12 into idiomatic Mojo:
- Scalar numeric arithmetic (`int`, `float`, `bool`).
- Stateful loops (`for`, `while`, `break`, `continue`).
- 1-D C-contiguous `numpy.ndarray` (`float64`, `int64`) zero-copy pointer paths.
- String operations and character loops.
- Consult [`docs/SUPPORTED_SYNTAX.md`](docs/SUPPORTED_SYNTAX.md) for the comprehensive type and operator matrix.

### Native Execution vs. Transparent Fallback
- When compilation succeeds and hardware supports it, `@hotloop` executes native C-ABI libraries.
- If native compilation fails or is unavailable, `@hotloop` emits a `HotloopFallbackWarning` and transparently executes the original Python function.
- If native FFI boxing overhead exceeds compute savings (e.g., returning thousands of boxed strings as in the RAG chunker), `@hotloop` prefers Python fallback to avoid performance degradation.
- **Environment Overrides**:
  - `HOTLOOP_STRICT_NATIVE=1`: Raises `HotloopNativeExecutionError` instead of falling back.
  - `HOTLOOP_FORCE_FALLBACK=1`: Forces pure Python execution for debugging.

### Running Tests Locally
```bash
# Set up development virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 1. Run offline compiler adversarial tests (No Mojo required, 50 tests)
python tests/test_compiler_adversarial.py

# 2. Run unfamiliar-function tests (Requires Mojo 1.2.0, 35 functions across 6 tiers)
python tests/test_unfamiliar_functions.py

# 3. Run runtime security & memory stability tests (Requires Mojo 1.2.0, 10,000 iterations)
python tests/test_runtime_security.py

# 4. Run full real-world business verification suites (Requires Mojo 1.2.0, 7,220 assertions)
python audit/run_all_verifications.py
```

### Reproducing Benchmarks
- We measure end-to-end wall-clock time including FFI boundary overhead.
- Every reported speedup is based on the median ($p_{50}$) across $\ge 100$ trials.
- Never benchmark cold compiles or JIT warmup. Always report the exact CPU model, OS, Python version, and Mojo version (see [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md)).

---

## 3. Contribution Boundaries & Engineering Standards

Every contribution to the official repository must adhere to rigorous engineering standards:

### Compiler Correctness First
- Semantic correctness always takes precedence over speedups.
- The transpiled Mojo kernel must produce outputs numerically identical to the Python reference implementation within standard IEEE-754 precision limits.
- Zero silent regressions: all existing tests must continue to pass.

### Native Memory Safety
- All pointer and array indexing must include bounds checks or enforce strict buffer invariants.
- No raw memory leaks or unmanaged buffer allocations across the C-ABI.
- Use explicit lifetimes and safe wrappers when passing data between Python and Mojo.

### Secure Subprocess & Library Loading
- Compiler subprocesses (`mojo build`) must use sanitized arguments and validated paths.
- Dynamic shared library loading (`ctypes.CDLL`) must verify manifest hashes and prevent arbitrary code execution from untrusted temporary directories.

### Honest & Reproducible Benchmarks
- Benchmark manipulation, artificial loop modifications, or selective trial reporting are strictly prohibited.
- If a benchmark competitor (e.g. Codon, Numba) fails or encounters a pathological edge case, report the failure or timeout transparently rather than claiming an artificial speedup.

### Intellectual Property, Provenance & Attribution
- All contributed code must be original work or correctly licensed under Apache-2.0.
- Algorithmic sources must cite published academic literature or open specifications (see [`docs/THIRD_PARTY_NOTICES.md`](docs/THIRD_PARTY_NOTICES.md)).
- Plagiarism, copied proprietary code, or unlicensed third-party code are strictly prohibited.

### Professional Ethics & Code of Conduct
- We enforce the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
- We voluntarily adhere to the [Engineering Ethics & Professional Practice Guidelines](docs/ENGINEERING_ETHICS.md), aligned with ACM/IEEE software engineering ethics.

### Responsible Vulnerability Disclosure
- Security vulnerabilities or native memory bugs must be reported privately via [GitHub Security Advisories](https://github.com/gorky117-cell/mojo-hotloop/security/advisories/new) rather than public issues. See [`SECURITY.md`](SECURITY.md).

---

## 4. Ownership, Copyright & Contributor Rights

### Founder Attribution
The original architecture, compiler design, and codebase are:
```
Copyright 2026 Gaurav Kumar Singh and mojo-hotloop contributors
```

### Contributor Copyright Retention
- **No Copyright Assignment**: Mojo Hotloop does **not** require contributors to assign their copyright to the founder or project.
- Contributors retain legitimate copyright in their own contributions.
- All contributions are licensed to the project and community under the **Apache License 2.0**.
- Accepted contributors are acknowledged in commit history, release notes, and contributor listings.

### Developer Certificate of Origin (DCO)
All commits must include a Developer Certificate of Origin (DCO) sign-off line:
```
Signed-off-by: Full Name <your.email@example.com>
```
Use `git commit -s` to automatically append this line. This certifies that you have the legal right to submit the work under the Apache-2.0 license (see [developercertificate.org](https://developercertificate.org/)).

---

## 5. Step-by-Step Contribution Workflow

1. **Fork the Repository**: Create a fork of `https://github.com/gorky117-cell/mojo-hotloop` under your own GitHub account.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feat/your-feature-name
   ```
3. **Make Surgical Changes**: Focus on a single bug fix, syntax addition, or optimization. Keep diffs readable and well-commented.
4. **Add Tests**:
   - For AST transpiler changes: add unit tests to `tests/test_compiler_adversarial.py`.
   - For new language features: add sample functions to `tests/test_unfamiliar_functions.py`.
5. **Run Verification**:
   ```bash
   python tests/test_compiler_adversarial.py
   ```
6. **Commit with DCO Sign-off**:
   ```bash
   git commit -s -m "feat(compiler): add support for python built-in abs()"
   ```
7. **Push to Your Fork**:
   ```bash
   git push origin feat/your-feature-name
   ```
8. **Open a Pull Request**:
   - Fill out the pull request template completely.
   - Link any related issues (`Fixes #12`).
   - The Automated Contributor Assistant will verify your DCO sign-off and provide guidance.
   - Review will automatically be requested from `@gorky117-cell` via CODEOWNERS.

---

## Need Help?
- General questions: [GitHub Discussions](https://github.com/gorky117-cell/mojo-hotloop/discussions)
- Bug reports: [GitHub Issues](https://github.com/gorky117-cell/mojo-hotloop/issues)
