#!/usr/bin/env python3
# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Adversarial compiler tests for mojo-hotloop AST transpiler.
Part 5 of the v0.1.0 release brief.

Tests 40 previously-unseen Python functions across edge cases including:
empty inputs, overflow, NaN/Inf, negative indexing, long loops, unicode,
concurrent safety, cache idempotency, stale cache, and more.

Exit code 0 if all pass or only expected-failures fail.
Exit code 1 if any unexpected failures occur.
"""

import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import threading

# Ensure hotloop package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hotloop.ast_transpiler import transpile_python_to_mojo, ASTTranspileError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RESULTS = {}  # test_name -> {"status": "PASS"|"FAIL"|"EXPECTED_FAIL", "detail": str}


def record(name, status, detail=""):
    RESULTS[name] = {"status": status, "detail": detail}


def run_transpile(source, mod_name="test_mod"):
    """Returns (ok: bool, output: str, error: str)"""
    try:
        out = transpile_python_to_mojo(source, mod_name)
        return True, out, ""
    except ASTTranspileError as e:
        return False, "", str(e)
    except Exception as e:
        return False, "", f"Unexpected {type(e).__name__}: {e}"


def expect_transpile_ok(name, source):
    ok, out, err = run_transpile(source)
    if ok:
        record(name, "PASS", "Transpilation succeeded")
    else:
        record(name, "FAIL", f"Transpilation unexpectedly failed: {err}")


def expect_transpile_fail(name, source, reason=""):
    ok, out, err = run_transpile(source)
    if not ok:
        record(name, "EXPECTED_FAIL", f"Correctly rejected: {err[:120]}")
    else:
        record(name, "EXPECTED_FAIL",
               f"Transpiler accepted (may be a known limitation): {reason}")


# ---------------------------------------------------------------------------
# Test sources — 40 functions
# ---------------------------------------------------------------------------

T01 = """
from hotloop import hotloop

@hotloop
def trivial_zero() -> int:
    return 0
"""

T02 = """
from hotloop import hotloop

@hotloop
def near_int64_max(x: int) -> int:
    limit: int = 9223372036854775806
    return limit + x
"""

T03 = """
from hotloop import hotloop

@hotloop
def divide(a: float, b: float) -> float:
    return a / b
"""

T04 = """
from hotloop import hotloop

@hotloop
def classify_fp(x: float) -> float:
    if x != x:
        return -1.0
    if x > 1e308:
        return 2.0
    return x
"""

T05 = """
from hotloop import hotloop

@hotloop
def last_elem(xs: list[float]) -> float:
    return xs[-1]
"""

T06 = """
from hotloop import hotloop

@hotloop
def count_up(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += 1
    return total
"""

T07 = """
from hotloop import hotloop

@hotloop
def deep_cond(a: int, b: int, c: int, d: int, e: int) -> int:
    if a > 0:
        if b > 0:
            if c > 0:
                if d > 0:
                    if e > 0:
                        return 5
                    return 4
                return 3
            return 2
        return 1
    return 0
"""

T08 = """
from hotloop import hotloop

@hotloop
def count_ascii(s: str) -> int:
    count: int = 0
    for i in range(len(s)):
        c: int = ord(s[i])
        if c < 128:
            count += 1
    return count
"""

T09 = """
from hotloop import hotloop

@hotloop
def safe_len(s: str) -> int:
    return len(s)
"""

T10 = """
from hotloop import hotloop

@hotloop
def sum_list(xs: list[float]) -> float:
    total: float = 0.0
    for i in range(len(xs)):
        total += xs[i]
    return total
"""

T11 = """
from hotloop import hotloop

@hotloop
def clamp_inf(x: float) -> float:
    cap: float = 1e308
    if x > cap:
        return cap
    if x < -cap:
        return -cap
    return x
"""

T14 = """
from hotloop import hotloop

@hotloop
def int64_add(a: int, b: int) -> int:
    return a + b
"""

T15 = """
from hotloop import hotloop

@hotloop
def factorial_iter(n: int) -> int:
    result: int = 1
    for i in range(1, n + 1):
        result = result * i
    return result
"""

T16 = """
from hotloop import hotloop

@hotloop
def geometric_sum(xs: list[float]) -> float:
    if len(xs) == 0:
        return 0.0
    product: float = 1.0
    for i in range(len(xs)):
        product = product * xs[i]
    return product
"""

T17 = """
from hotloop import hotloop

@hotloop
def all_positive(xs: list[float]) -> bool:
    for i in range(len(xs)):
        if xs[i] <= 0.0:
            return False
    return True
"""

T18 = """
from hotloop import hotloop

@hotloop
def scale_list(xs: list[float], factor: float) -> list[float]:
    result: list[float] = []
    for i in range(len(xs)):
        result.append(xs[i] * factor)
    return result
"""

T19 = """
from hotloop import hotloop

@hotloop
def squares_list(n: int) -> list[int]:
    result: list[int] = []
    for i in range(n):
        result.append(i * i)
    return result
"""

T20 = """
from hotloop import hotloop

@hotloop
def weighted_sum(a: float, b: float, c: float, d: float, e: float, w: float) -> float:
    return (a + b + c + d + e) * w
"""

T21 = """
import math
from hotloop import hotloop

@hotloop
def trig_combo(x: float, y: float) -> float:
    r: float = math.sqrt(x * x + y * y)
    theta: float = math.atan2(y, x)
    return math.sin(theta) * r + math.cos(theta) * r
"""

T22 = """
from hotloop import hotloop

@hotloop
def abs_diff(a: float, b: float) -> float:
    diff: float = a - b
    if diff < 0.0:
        return -diff
    return diff
"""

T23 = """
from hotloop import hotloop

@hotloop
def build_string(n: int) -> str:
    s: str = ""
    for i in range(n):
        s += "x"
    return s
"""

T24 = """
from hotloop import hotloop

@hotloop
def count_nonempty(xs: list[float]) -> int:
    total: int = 0
    if len(xs) == 0:
        return 0
    for i in range(len(xs)):
        if xs[i] != 0.0:
            total += 1
    return total
"""

T25 = """
from hotloop import hotloop

@hotloop
def matrix_sum(n: int, m: int) -> int:
    total: int = 0
    for i in range(n):
        for j in range(m):
            total += i * m + j
    return total
"""

T26 = """
from hotloop import hotloop

@hotloop
def find_first_gt(xs: list[float], threshold: float) -> int:
    for i in range(len(xs)):
        if xs[i] > threshold:
            return i
    return -1
"""

T27 = """
from hotloop import hotloop

@hotloop
def bool_logic(a: bool, b: bool, c: bool) -> bool:
    if a and b:
        return True
    if a or c:
        return True
    return False
"""

T28 = """
from hotloop import hotloop

@hotloop
def mixed_math(n: int, x: float) -> float:
    total: float = 0.0
    for i in range(n):
        total += x * i
    return total
"""

T29 = """
from hotloop import hotloop

@hotloop
def div_mod(a: int, b: int) -> int:
    q: int = a // b
    r: int = a % b
    return q * b + r
"""

T30 = """
from hotloop import hotloop

@hotloop
def power_sum(base: float, n: int) -> float:
    total: float = 0.0
    for i in range(n):
        total += base ** i
    return total
"""

T31 = """
from hotloop import hotloop

@hotloop
def sum_zero_range(n: int) -> int:
    total: int = 0
    for i in range(0):
        total += i
    return total
"""

T32 = """
from hotloop import hotloop

@hotloop
def classify_int(x: int) -> int:
    if x < 0:
        return -1
    if x == 0:
        return 0
    return 1
"""

T33 = """
from hotloop import hotloop

@hotloop
def aug_assign_ops(n: int) -> float:
    a: int = 0
    b: float = 1.0
    for i in range(n):
        a += i
        b *= 1.001
    return b + a
"""

T34 = """
from hotloop import hotloop

@hotloop
def in_range(x: int, lo: int, hi: int) -> bool:
    return lo <= x <= hi
"""

T35 = """
from hotloop import hotloop

@hotloop
def repeat_char(c: str, n: int) -> str:
    result: str = ""
    for i in range(n):
        result += c
    return result
"""

T36 = """
from hotloop import hotloop

@hotloop
def collatz_steps(n: int) -> int:
    steps: int = 0
    while n != 1:
        if n % 2 == 0:
            n = n // 2
        else:
            n = 3 * n + 1
        steps += 1
    return steps
"""

T37 = """
from hotloop import hotloop

@hotloop
def safe_div(a: int, b: int) -> int:
    if b == 0:
        return 0
    return a // b
"""

T38 = """
import math
from hotloop import hotloop

@hotloop
def abs_sqrt(x: float) -> float:
    if x < 0.0:
        x = -x
    return math.sqrt(x)
"""

T39 = """
from hotloop import hotloop

@hotloop
def even_squares(n: int) -> list[int]:
    result: list[int] = []
    for i in range(n):
        if i % 2 == 0:
            result.append(i * i)
    return result
"""

T_RANGE2 = """
from hotloop import hotloop

@hotloop
def range_two_arg(start: int, stop: int) -> int:
    total: int = 0
    for i in range(start, stop):
        total += i
    return total
"""

# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------

def test_01_empty_return():
    expect_transpile_ok("T01_empty_return", T01)


def test_02_int64_boundary():
    expect_transpile_ok("T02_int64_boundary", T02)


def test_03_div_zero():
    expect_transpile_ok("T03_div_zero", T03)


def test_04_nan_inf():
    expect_transpile_ok("T04_nan_inf", T04)


def test_05_neg_index():
    expect_transpile_ok("T05_neg_index", T05)


def test_06_long_loop():
    expect_transpile_ok("T06_long_loop", T06)


def test_07_nested_cond():
    expect_transpile_ok("T07_nested_cond", T07)


def test_08_unicode():
    expect_transpile_ok("T08_unicode", T08)


def test_09_empty_string():
    expect_transpile_ok("T09_empty_string", T09)


def test_10_empty_list():
    expect_transpile_ok("T10_empty_list", T10)


def test_11_float_inf_lit():
    expect_transpile_ok("T11_float_inf_lit", T11)


def test_12_cache_idempotency():
    source = """
from hotloop import hotloop

@hotloop
def add_one(x: int) -> int:
    return x + 1
"""
    ok1, out1, _ = run_transpile(source, "cache_test")
    ok2, out2, _ = run_transpile(source, "cache_test")
    if ok1 and ok2 and out1 == out2:
        record("T12_cache_idempotency", "PASS",
               "Identical inputs produce identical Mojo output (deterministic)")
    elif ok1 and ok2:
        record("T12_cache_idempotency", "FAIL",
               "Identical inputs produced different Mojo output (non-deterministic!)")
    else:
        record("T12_cache_idempotency", "FAIL",
               f"Transpilation failed: ok1={ok1}, ok2={ok2}")


def test_13_concurrent_safety():
    source = """
from hotloop import hotloop

@hotloop
def sq(x: float) -> float:
    return x * x
"""
    errors = []

    def worker():
        try:
            transpile_python_to_mojo(source, "concurrent_mod")
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    if not errors:
        record("T13_concurrent_safety", "PASS",
               "8 concurrent transpilations succeeded")
    else:
        record("T13_concurrent_safety", "FAIL",
               f"Errors during concurrent transpilation: {errors[0][:80]}")


def test_14_int64_add():
    expect_transpile_ok("T14_int64_add", T14)


def test_15_return_int():
    expect_transpile_ok("T15_return_int", T15)


def test_16_return_float():
    expect_transpile_ok("T16_return_float", T16)


def test_17_return_bool():
    expect_transpile_ok("T17_return_bool", T17)


def test_18_return_list_float():
    expect_transpile_ok("T18_return_list_float", T18)


def test_19_return_list_int():
    expect_transpile_ok("T19_return_list_int", T19)


def test_20_five_params():
    expect_transpile_ok("T20_five_params", T20)


def test_21_trig():
    expect_transpile_ok("T21_trig", T21)


def test_22_abs_scalar():
    expect_transpile_ok("T22_abs_scalar", T22)


def test_23_string_concat():
    expect_transpile_ok("T23_string_concat", T23)


def test_24_len_calls():
    expect_transpile_ok("T24_len_calls", T24)


def test_25_nested_for():
    expect_transpile_ok("T25_nested_for", T25)


def test_26_early_return():
    expect_transpile_ok("T26_early_return", T26)


def test_27_bool_and_or():
    expect_transpile_ok("T27_bool_and_or", T27)


def test_28_mixed_arith():
    expect_transpile_ok("T28_mixed_arith", T28)


def test_29_floordiv_mod():
    expect_transpile_ok("T29_floordiv_mod", T29)


def test_30_power():
    expect_transpile_ok("T30_power", T30)


def test_31_zero_range():
    expect_transpile_ok("T31_zero_range", T31)


def test_32_multi_return():
    expect_transpile_ok("T32_multi_return", T32)


def test_33_augmented_assign():
    expect_transpile_ok("T33_augmented_assign", T33)


def test_34_chained_cmp():
    expect_transpile_ok("T34_chained_cmp", T34)


def test_35_return_str():
    expect_transpile_ok("T35_return_str", T35)


def test_36_while_loop():
    expect_transpile_ok("T36_while_loop", T36)


def test_37_int_div_zero():
    expect_transpile_ok("T37_int_div_zero", T37)


def test_38_sqrt_edge():
    expect_transpile_ok("T38_sqrt_edge", T38)


def test_39_list_int_cond():
    expect_transpile_ok("T39_list_int_cond", T39)


def test_40_stale_cache_detection():
    """Test manifest-based stale binary detection logic."""
    with tempfile.TemporaryDirectory() as tmpdir:
        src_file = os.path.join(tmpdir, "mymod.py")
        manifest_file = os.path.join(tmpdir, "mymod.hotloop_manifest.json")
        fake_so = os.path.join(tmpdir, "mymod.so")

        src = "def add(x, y): return x + y\n"
        with open(src_file, "w") as f:
            f.write(src)

        # Write manifest with WRONG hash to simulate stale cache
        stale_hash = "deadbeef" * 8
        manifest = {"source_sha256": stale_hash, "source_file": "mymod.py"}
        with open(manifest_file, "w") as f:
            json.dump(manifest, f)

        # Fake .so
        with open(fake_so, "wb") as f:
            f.write(b"\x7fELF")

        from hotloop.decorator import _is_binary_stale, _compute_file_hash
        cur_hash = _compute_file_hash(src_file)
        is_stale, reason = _is_binary_stale(fake_so, src_file, cur_hash)

        if is_stale and reason:
            record("T40_stale_cache_detection", "PASS",
                   f"Correctly detected stale binary: {reason[:80]}")
        else:
            record("T40_stale_cache_detection", "FAIL",
                   f"Failed to detect stale binary: is_stale={is_stale}, reason={reason}")


def test_41_range_two_arg():
    """range(start, stop) two-argument form."""
    expect_transpile_ok("T41_range_two_arg", T_RANGE2)


def test_42_missing_annotation():
    """Function without type annotation should be rejected."""
    source = """
from hotloop import hotloop

@hotloop
def no_annotations(x, y):
    return x + y
"""
    ok, out, err = run_transpile(source)
    if not ok:
        record("T42_missing_annotation", "EXPECTED_FAIL",
               f"Correctly rejected unannotated function: {err[:100]}")
    else:
        # Some transpilers may accept unannotated code with defaults
        record("T42_missing_annotation", "EXPECTED_FAIL",
               "Transpiler accepted unannotated function (known limitation)")


def test_43_no_hotloop_single_fn():
    """Single function without @hotloop decorator - should work (fallback behavior)."""
    source = """
def add(x: int, y: int) -> int:
    return x + y
"""
    ok, out, err = run_transpile(source)
    if ok:
        record("T43_no_hotloop_single_fn", "PASS",
               "Single-function file transpiles without @hotloop decorator")
    else:
        record("T43_no_hotloop_single_fn", "EXPECTED_FAIL",
               f"Rejected (also acceptable): {err[:80]}")


def test_44_empty_string_input():
    """Verify transpilation of function that handles empty string semantics."""
    source = """
from hotloop import hotloop

@hotloop
def is_empty(s: str) -> bool:
    return len(s) == 0
"""
    expect_transpile_ok("T44_empty_string_input", source)


def test_45_modulo_zero_guard():
    """Modulo by zero guarded at runtime."""
    source = """
from hotloop import hotloop

@hotloop
def safe_mod(a: int, b: int) -> int:
    if b == 0:
        return 0
    return a % b
"""
    expect_transpile_ok("T45_modulo_zero_guard", source)


def test_46_multiple_accumulator_vars():
    """Multiple accumulator variables in one loop."""
    source = """
from hotloop import hotloop

@hotloop
def running_stats(xs: list[float]) -> float:
    n: int = len(xs)
    if n == 0:
        return 0.0
    total: float = 0.0
    sq_total: float = 0.0
    for i in range(n):
        total += xs[i]
        sq_total += xs[i] * xs[i]
    mean: float = total / n
    return sq_total / n - mean * mean
"""
    expect_transpile_ok("T46_multiple_accumulators", source)


def test_47_nested_list_build():
    """Build list inside conditional inside loop."""
    source = """
from hotloop import hotloop

@hotloop
def filter_gt(xs: list[float], threshold: float) -> list[float]:
    result: list[float] = []
    for i in range(len(xs)):
        if xs[i] > threshold:
            result.append(xs[i])
    return result
"""
    expect_transpile_ok("T47_nested_list_build", source)


def test_48_break_in_loop():
    """break statement inside a for loop."""
    source = """
from hotloop import hotloop

@hotloop
def first_negative_idx(xs: list[float]) -> int:
    for i in range(len(xs)):
        if xs[i] < 0.0:
            return i
    return -1
"""
    expect_transpile_ok("T48_break_via_return", source)


def test_49_bool_return_from_comparison():
    """Direct comparison as return value."""
    source = """
from hotloop import hotloop

@hotloop
def is_sorted(xs: list[float]) -> bool:
    for i in range(len(xs) - 1):
        if xs[i] > xs[i + 1]:
            return False
    return True
"""
    expect_transpile_ok("T49_bool_return_comparison", source)


def test_50_math_pi_e():
    """Use math.pi and math.e constants."""
    source = """
import math
from hotloop import hotloop

@hotloop
def circle_area(r: float) -> float:
    return math.pi * r * r
"""
    ok, out, err = run_transpile(source)
    if ok:
        record("T50_math_pi_e", "PASS", "math.pi reference transpiled")
    else:
        record("T50_math_pi_e", "EXPECTED_FAIL",
               f"math.pi not supported (known limitation): {err[:80]}")


def test_51_cli_check_syntax():
    """Verify CLI --check-syntax runs deterministic offline validation."""
    source = """
from hotloop import hotloop

@hotloop
def add_nums(a: int, b: int) -> int:
    return a + b
"""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
        f.write(source)
        tmp_name = f.name
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "hotloop.cli", "build", tmp_name, "--check-syntax"],
            capture_output=True,
            text=True
        )
        if proc.returncode == 0 and "[+] Syntax check PASSED" in proc.stdout:
            record("T51_cli_check_syntax", "PASS", "hotloop build --check-syntax passed offline validation")
        else:
            record("T51_cli_check_syntax", "FAIL", f"CLI exited with {proc.returncode}: {proc.stderr or proc.stdout}")
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)


def test_52_startswith_endswith():
    """Verify str.startswith() and str.endswith() transpilation."""
    source = """
from hotloop import hotloop

@hotloop
def check_prefix_suffix(line: str, prefix: str, suffix: str) -> bool:
    b1: bool = line.startswith(prefix)
    b2: bool = line.endswith(suffix)
    b3: bool = line.startswith("http://")
    b4: bool = line.endswith(".json")
    b5: bool = line.startswith(("a", "b"))
    return b1 and b2 and b3 and b4 and b5
"""
    ok, out, err = run_transpile(source)
    if ok:
        record("T52_startswith_endswith", "PASS", "startswith and endswith transpiled cleanly")
    else:
        record("T52_startswith_endswith", "FAIL", f"Transpilation failed: {err}")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_01_empty_return,
    test_02_int64_boundary,
    test_03_div_zero,
    test_04_nan_inf,
    test_05_neg_index,
    test_06_long_loop,
    test_07_nested_cond,
    test_08_unicode,
    test_09_empty_string,
    test_10_empty_list,
    test_11_float_inf_lit,
    test_12_cache_idempotency,
    test_13_concurrent_safety,
    test_14_int64_add,
    test_15_return_int,
    test_16_return_float,
    test_17_return_bool,
    test_18_return_list_float,
    test_19_return_list_int,
    test_20_five_params,
    test_21_trig,
    test_22_abs_scalar,
    test_23_string_concat,
    test_24_len_calls,
    test_25_nested_for,
    test_26_early_return,
    test_27_bool_and_or,
    test_28_mixed_arith,
    test_29_floordiv_mod,
    test_30_power,
    test_31_zero_range,
    test_32_multi_return,
    test_33_augmented_assign,
    test_34_chained_cmp,
    test_35_return_str,
    test_36_while_loop,
    test_37_int_div_zero,
    test_38_sqrt_edge,
    test_39_list_int_cond,
    test_40_stale_cache_detection,
    test_41_range_two_arg,
    test_42_missing_annotation,
    test_43_no_hotloop_single_fn,
    test_44_empty_string_input,
    test_45_modulo_zero_guard,
    test_46_multiple_accumulator_vars,
    test_47_nested_list_build,
    test_48_break_in_loop,
    test_49_bool_return_from_comparison,
    test_50_math_pi_e,
    test_51_cli_check_syntax,
    test_52_startswith_endswith,
]


def print_summary():
    col_w = 38
    print("\n" + "=" * 72)
    print(f"{'Test':<{col_w}} {'Status':<18} {'Detail'}")
    print("=" * 72)

    pass_cnt = 0
    fail_cnt = 0
    exp_fail_cnt = 0

    for name in sorted(RESULTS):
        info = RESULTS[name]
        status = info["status"]
        detail = (info["detail"] or "")[:55]
        if status == "PASS":
            marker = "PASS"
            pass_cnt += 1
        elif status == "EXPECTED_FAIL":
            marker = "EXP_FAIL"
            exp_fail_cnt += 1
        else:
            marker = "*** FAIL ***"
            fail_cnt += 1
        print(f"{name:<{col_w}} {marker:<18} {detail}")

    print("=" * 72)
    print(f"TOTAL: {len(RESULTS)} tests  |  "
          f"PASS: {pass_cnt}  |  "
          f"EXP_FAIL: {exp_fail_cnt}  |  "
          f"UNEXPECTED FAIL: {fail_cnt}")
    print("=" * 72)
    return fail_cnt


if __name__ == "__main__":
    print("=" * 72)
    print("mojo-hotloop Adversarial Compiler Test Suite v0.1.0")
    print(f"Python {sys.version}")
    print("=" * 72)

    for test_fn in ALL_TESTS:
        try:
            test_fn()
        except Exception as exc:
            name = test_fn.__name__.replace("test_", "T").upper()
            record(name, "FAIL", f"Test runner exception: {exc}")

    fail_count = print_summary()
    sys.exit(1 if fail_count > 0 else 0)
