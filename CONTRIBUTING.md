# Contributing to mojo-hotloop

Thank you for your interest in contributing! mojo-hotloop is an open-source
project and welcomes contributions from everyone.

---

## Code of Conduct & Engineering Ethics

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md) and voluntarily aligns with the [Engineering Ethics & Professional Practice Guidelines](docs/ENGINEERING_ETHICS.md) (adapted from the ACM Code of Ethics and ACM/IEEE-CS Software Engineering Code of Ethics).

By participating, you agree to uphold these standards, conduct constructive code reviews, report benchmarks honestly, and respect fellow contributors.

---

## Developer Certificate of Origin (DCO)

All contributions **must** include a DCO sign-off. We use the
[Developer Certificate of Origin version 1.1](https://developercertificate.org/).

Add a sign-off line to every commit:

```
Signed-off-by: Your Name <your@email.com>
```

The easiest way is to use `git commit -s`. This certifies that you wrote or
have the right to contribute the code under the Apache 2.0 license.

There is **no CLA** to sign. The DCO sign-off is sufficient.

---

## How to Contribute

### 1. Reporting Bugs

Use the GitHub issue templates:
- **Compiler Bug** — wrong transpiler output or incorrect Mojo code generated
- **Native Crash** — SIGSEGV or abort in native execution
- **Performance Regression** — a function that was faster before
- **Installation Failure** — `pip install` or Mojo build fails

### 2. Proposing Features

Open a GitHub Discussion or issue describing:
- The Python syntax or pattern you want supported
- A minimal example (input Python → expected Mojo output)
- Why existing workarounds are insufficient

### 3. Submitting Code

#### Setup

```bash
# Requires WSL2 Ubuntu 24.04 or native Linux
# Requires Mojo 1.2.0 (via `modular install mojo`)
git clone https://github.com/gorky117-cell/mojo-hotloop
cd mojo-hotloop
python3 -m venv .venv
.venv/bin/pip install -e .
```

#### Running Tests

```bash
# AST transpiler unit tests (no Mojo required)
.venv/bin/python tests/test_compiler_adversarial.py

# Full use-case verification (requires Mojo)
.venv/bin/python audit/run_all_verifications.py

# AST provenance build test (requires Mojo)
.venv/bin/python audit/test_ast_provenance.py
```

#### Making Changes to the AST Transpiler

The transpiler lives in `hotloop/ast_transpiler.py`. When adding support for
a new Python construct:

1. Add a test case in `tests/test_compiler_adversarial.py`
2. Add the transpilation logic in `MojoASTTranspiler.visit_*`
3. Verify the generated Mojo compiles cleanly with `mojo build`
4. Update `docs/SUPPORTED_SYNTAX.md`

#### Pull Request Requirements

- **Correctness First**: All existing tests must pass with 0 unexpected failures; performance optimizations must demonstrate zero numerical regressions.
- **Test Coverage**: New compiler features or transformations must include unit tests in `tests/test_compiler_adversarial.py`.
- **Reproducible Benchmark Evidence**: Required for any performance claim. Submit p50 medians across $\ge 100$ trials, stating exact hardware, Python version, and Mojo version (see `docs/BENCHMARKS.md`).
- **Intellectual Property & DCO**: Every commit must carry a `Signed-off-by:` line (`git commit -s`). Contributors retain copyright in their submissions under Apache-2.0. No plagiarized code or uncredited third-party inclusions are permitted.
- **PR Template**: Use the standard pull request template and link any relevant GitHub issue.

### 4. Documentation

Documentation improvements are especially welcome. The key files are:
- `README.md` — getting started
- `docs/SUPPORTED_SYNTAX.md` — transpiler capability reference
- `docs/BENCHMARKS.md` — honest benchmark methodology

---

## Code Style

- Python: follow PEP 8, use type annotations throughout
- Mojo: follow the patterns in `hotloop/ast_transpiler.py`'s output
- No line length limit enforced, but keep lines readable (soft limit ~100)
- Comments explaining *why*, not *what*

---

## Questions?

Open a GitHub Discussion or file an issue. The maintainers aim to respond
within 7 days.
