# External Testing Guide — mojo-hotloop v0.1.0

This guide explains how to independently verify the mojo-hotloop project
from scratch on your own machine.

---

## Prerequisites

### Required

- **Linux** (Ubuntu 20.04+ or Debian 12+) or **WSL2** on Windows 11
- **Python 3.12** (`python3 --version`)
- **git**

### For Native Mojo Acceleration (Optional but Recommended)

- **Mojo 1.2.0** via Modular toolchain:
  ```bash
  pip install modular
  modular install mojo
  # Verify:
  mojo --version  # Should print: mojo 1.2.0 (2016d0cd ...)
  ```

> [!NOTE]
> Without Mojo installed, all functions will execute via the Python fallback
> path. All correctness tests will still pass. Only the benchmark numbers
> will not be reproducible.

---

## Step 1 — Clone and Install

```bash
git clone https://github.com/mojo-hotloop/mojo-hotloop
cd mojo-hotloop

# Verify git HEAD
git log --oneline -1
# Should show: 47a2c41 or the v0.1.0 release commit

# Create venv and install
python3 -m venv .venv
.venv/bin/pip install -e .

# Verify install
.venv/bin/python -c "from hotloop import hotloop; print('Import OK')"
```

---

## Step 2 — Smoke Test (No Mojo Required)

```bash
cat > /tmp/test_hotloop.py << 'EOF'
import warnings
warnings.simplefilter("always")
from hotloop import hotloop

@hotloop
def sum_squares(xs: list[float]) -> float:
    total: float = 0.0
    for i in range(len(xs)):
        total += xs[i] * xs[i]
    return total

data = [1.0, 2.0, 3.0, 4.0, 5.0]
result = sum_squares(data)
print(f"Result: {result}")
print(f"Backend: {sum_squares._last_backend}")
expected = sum(x*x for x in data)
assert abs(result - expected) < 1e-9, f"Mismatch: {result} != {expected}"
print("SMOKE TEST: PASS")
EOF

.venv/bin/python /tmp/test_hotloop.py
```

**Expected output** (without Mojo installed):
```
/tmp/test_hotloop.py:14: HotloopFallbackWarning: [mojo-hotloop] Falling back to Python implementation ...
Result: 55.0
Backend: python_fallback
SMOKE TEST: PASS
```

**Expected output** (with Mojo installed and `.so` pre-built):
```
Result: 55.0
Backend: native
SMOKE TEST: PASS
```

---

## Step 3 — Adversarial Compiler Tests (No Mojo Required)

```bash
.venv/bin/python tests/test_compiler_adversarial.py
```

**Expected output** (last 5 lines):
```
...
========================================================================
TOTAL: 50 tests  |  PASS: 47  |  EXP_FAIL: 3  |  UNEXPECTED FAIL: 0
========================================================================
```

Exit code should be `0`.

---

## Step 4 — Build All 7 Use Cases (Requires Mojo)

```bash
.venv/bin/python audit/test_ast_provenance.py
```

Each use case should report:
```
Return code: 0
STDOUT:
[*] mojo-hotloop building '...' using engine='ast', backend='mojo'
[+] Build SUCCESS: Successfully transpiled and built .../fast.so via AST engine.
```

All 7 must return code 0.

---

## Step 5 — Run All Verification Suites (Requires Mojo + pre-built .so)

```bash
cd /home/<user>/mojo-hotloop    # adjust path
.venv/bin/python audit/run_all_verifications.py
```

**Expected output**:
```
Discovered 7 verification suites.
--- Running examples/ar_spatial/verify.py ---
PASSED: ...1010 tests verified... 0 mismatches...
--- Running examples/geo_distance/verify.py ---
PASSED: ...1014 tests verified... 0 mismatches...
--- Running examples/ocr_matcher/verify.py ---
PASSED: ...1020 tests verified...
--- Running examples/pdf_cleaner/verify.py ---
PASSED: ...1020 tests verified...
--- Running examples/pii_scrubber/verify.py ---
PASSED: ...1019 tests verified...
--- Running examples/quant_backtest/verify.py ---
PASSED: ...1117 tests...
--- Running examples/rag_chunker/verify.py ---
PASSED: ...1020 tests verified...
=======================================================
Verification Suites Summary: 7/7 Passed
ALL VERIFICATION SUITES PASSED!
```

---

## Step 6 — Verify Clean pip Install

```bash
python3 -m venv /tmp/hl_external_test
/tmp/hl_external_test/bin/pip install /path/to/mojo-hotloop  # or pip install mojo-hotloop

/tmp/hl_external_test/bin/python /tmp/test_hotloop.py
# Should print: SMOKE TEST: PASS
```

---

## Step 7 — Verify Stale Cache Detection

```bash
cat > /tmp/stale_test.py << 'EOF'
import hashlib, json, os, tempfile
from hotloop.decorator import _is_binary_stale, _compute_file_hash

with tempfile.TemporaryDirectory() as d:
    src = os.path.join(d, "mod.py")
    so  = os.path.join(d, "mod.so")
    mf  = os.path.join(d, "mod.hotloop_manifest.json")

    with open(src, "w") as f: f.write("x = 1\n")
    with open(so, "wb") as f: f.write(b"\x7fELF")
    # Write a stale (wrong) hash in the manifest
    with open(mf, "w") as f:
        json.dump({"source_sha256": "deadbeef" * 8}, f)

    cur = _compute_file_hash(src)
    is_stale, reason = _is_binary_stale(so, src, cur)
    assert is_stale, f"Expected stale, got: {is_stale}, {reason}"
    print(f"STALE DETECTION: PASS ({reason})")
EOF

.venv/bin/python /tmp/stale_test.py
```

---

## Reporting Issues

If any step produces unexpected results:

1. Note the exact command you ran
2. Copy the full output (stdout + stderr)
3. Note your OS, Python version, and Mojo version (`mojo --version`)
4. Open a GitHub issue using the appropriate template:
   - `Installation Failure` — pip install fails
   - `Compiler Bug` — wrong transpiler output
   - `Native Crash` — SIGSEGV or abort

---

## What Cannot Be Independently Verified Without Mojo

- Native backend activation (`_last_backend == "native"`)
- Benchmark speedup numbers
- Correct Mojo compilation of generated `.mojo` source
- The 7,220-test verification suite results

All **correctness** properties (Python fallback behavior, stale cache
detection, adversarial transpiler tests) can be verified without Mojo.
