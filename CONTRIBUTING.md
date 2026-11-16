# Contributing to mojo-hotloop

Thank you for your interest in contributing! mojo-hotloop is an open-source
project and welcomes contributions from everyone.

---

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).
By participating you agree to abide by its terms.

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
git clone https://github.com/gauravatwork117/mojo-hotloop
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

- All existing tests must pass
- New features must include at least one test
- Benchmark evidence required for performance claims (see `docs/BENCHMARKS.md`)
- DCO sign-off on every commit (`git commit -s`)
- Use the PR template

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
