## Pull Request

### Description
<!-- Clear 1–3 sentence description of what this PR does and why -->

### Type of Change
- [ ] Compiler correctness fix (AST visitor, type deduction, boundary handling)
- [ ] New Python AST syntax feature (new syntax or stdlib construct)
- [ ] Performance improvement (measured and reproduced, with evidence below)
- [ ] Memory safety / hardening / security improvement
- [ ] Test addition / verification suite expansion
- [ ] Documentation improvement
- [ ] Build / packaging / CI improvement

### Related Issue
Fixes #<!-- issue number -->

---

### Contributor Checklist

#### 1. Developer Certificate of Origin (DCO)
- [ ] Every commit in this PR includes a valid DCO sign-off (`Signed-off-by: Full Name <email@domain.com>`) via `git commit -s`.
- [ ] I certify that this code is an original work or correctly attributed under the Apache License 2.0.

#### 2. Tests & Compiler Correctness
- [ ] Offline adversarial test suite passes with 0 failures:
  ```bash
  python tests/test_compiler_adversarial.py
  ```
- [ ] New unit tests covering the change have been added to `tests/`.
- [ ] Full use-case verifications pass 7/7 (if Mojo 1.2.0 is available locally):
  ```bash
  python audit/run_all_verifications.py
  ```
- [ ] Strict Python 3.12 semantics are preserved (no silent numerical divergences).

#### 3. Memory Safety & Security Safeguards
- [ ] Bounds checks are enforced on pointer and slice accesses.
- [ ] Zero unvetted raw memory allocations or memory leaks across the C-ABI.
- [ ] Subprocess executions (e.g. `mojo build`) use sanitized arguments and safe file paths.

#### 4. Benchmark Reproducibility (Required for performance claims)
- [ ] Benchmark methodology follows `docs/BENCHMARKS.md` ($\ge 100$ trials, median $p_{50}$).
- [ ] Environment details included below (CPU, OS, Python version, Mojo version).
- [ ] No cherry-picked runs or synthetic microbenchmarks.

| Workload | Input Scale | Baseline $p_{50}$ | Proposed $p_{50}$ | Speedup |
| :--- | :--- | :--- | :--- | :--- |
| | | | | |

#### 5. Ethics & Licensing
- [ ] Complies with the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).
- [ ] Complies with [Engineering Ethics & Professional Practice](docs/ENGINEERING_ETHICS.md).
- [ ] Licensed under Apache License 2.0 (contributors retain their own copyright).
