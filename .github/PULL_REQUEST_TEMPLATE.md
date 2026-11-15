## Pull Request

### Description

<!-- Clear 1–3 sentence description of what this PR does and why -->

### Type of Change

- [ ] Bug fix (compiler correctness, fallback behavior, stale cache)
- [ ] New transpiler feature (new Python syntax or stdlib support)
- [ ] Performance improvement (measured, with evidence below)
- [ ] Documentation update
- [ ] Test addition / coverage improvement
- [ ] Build / CI / packaging change
- [ ] Other: _______________

### Related Issue

Fixes #<!-- issue number -->

---

### Checklist

**Tests**
- [ ] `tests/test_compiler_adversarial.py` runs with 0 unexpected failures
- [ ] New tests added for the changed/added behavior
- [ ] `audit/run_all_verifications.py` passes 7/7 (if Mojo is available)

**Benchmark Evidence** (required for performance claims)

> Include p50 median timings before and after, measured with at least 100 trials.
> State the hardware, Python version, and Mojo version.

```
Before: X ms (p50), backend: native
After:  Y ms (p50), backend: native
Speedup: Z%
Hardware: ...
```

**Documentation**
- [ ] `docs/SUPPORTED_SYNTAX.md` updated (if new syntax supported)
- [ ] `CHANGELOG.md` entry added under `[Unreleased]`

**DCO Sign-off**
- [ ] Every commit in this PR has a `Signed-off-by:` line
  (`git commit -s` adds this automatically)

---

### How to Test This PR

```bash
# Commands a reviewer can run to verify this PR
git checkout <branch>
.venv/bin/python tests/test_compiler_adversarial.py
```
