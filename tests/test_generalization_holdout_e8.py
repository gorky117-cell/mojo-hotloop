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
Phase E.8 Fresh Holdout Generalization Verification Suite.

Tests 25 previously unseen holdout functions across DSP, finance, cryptography,
numerical analysis, text parsing, and geometry WITHOUT any compiler modifications.
Verifies functional correctness, records native/fallback execution, and measures speedups.
"""

import math
import os
import shutil
import sys
import tempfile
import time
import unittest
import numpy as np

from hotloop.backends.mojo import MojoBackend

HOLDOUT_SOURCE = '''
import math
from hotloop import hotloop

# 1. Numerical & Finance: Polynomial Horner Evaluation
@hotloop
def horner_eval(coeffs: list[float], x: float) -> float:
    res: float = 0.0
    for i in range(len(coeffs)):
        res = res * x + coeffs[i]
    return res

# 2. Numerical & Math: Simpson's Rule Quadrature (f(x) = x^3 - 2x + 1)
@hotloop
def simpson_integral_cubic(a: float, b: float, n: int) -> float:
    if n % 2 != 0:
        n = n + 1
    h: float = (b - a) / float(n)
    s: float = (a * a * a - 2.0 * a + 1.0) + (b * b * b - 2.0 * b + 1.0)
    for i in range(1, n):
        x: float = a + float(i) * h
        fx: float = x * x * x - 2.0 * x + 1.0
        if i % 2 == 0:
            s += 2.0 * fx
        else:
            s += 4.0 * fx
    return s * (h / 3.0)

# 3. DSP & Statistics: Moving Variance Accumulator
@hotloop
def moving_variance_sum(xs: list[float], mean: float) -> float:
    var_sum: float = 0.0
    for i in range(len(xs)):
        diff: float = xs[i] - mean
        var_sum += diff * diff
    return var_sum

# 4. Time Series: Exponential Smoothing
@hotloop
def exp_smoothing_series(xs: list[float], alpha: float) -> float:
    s: float = 0.0
    if len(xs) > 0:
        s = xs[0]
    for i in range(1, len(xs)):
        s = alpha * xs[i] + (1.0 - alpha) * s
    return s

# 5. Cryptography & Hash: Adler-32 Checksum
@hotloop
def adler32_checksum(s: str) -> int:
    a: int = 1
    b: int = 0
    mod: int = 65521
    for i in range(len(s)):
        a = (a + ord(s[i])) % mod
        b = (b + a) % mod
    return (b * 65536) + a

# 6. Cryptography & Bitwise: Stein's Binary GCD
@hotloop
def binary_gcd_stein(u: int, v: int) -> int:
    if u == 0:
        return v
    if v == 0:
        return u
    shift: int = 0
    while ((u | v) & 1) == 0:
        u = u // 2
        v = v // 2
        shift += 1
    while (u & 1) == 0:
        u = u // 2
    while v != 0:
        while (v & 1) == 0:
            v = v // 2
        if u > v:
            t: int = v
            v = u
            u = t
        v = v - u
    return u * (1 << shift)

# 7. Text Analysis: Vowel-to-Consonant Counter
@hotloop
def count_vowels_strict(s: str) -> int:
    cnt: int = 0
    for i in range(len(s)):
        c: int = ord(s[i])
        if c == 65 or c == 69 or c == 73 or c == 79 or c == 85 or c == 97 or c == 101 or c == 105 or c == 111 or c == 117:
            cnt += 1
    return cnt

# 8. Text Parsing: Custom ASCII String-to-Int Parser
@hotloop
def parse_int_ascii(s: str) -> int:
    val: int = 0
    sign: int = 1
    start: int = 0
    if len(s) > 0 and ord(s[0]) == 45:
        sign = -1
        start = 1
    for i in range(start, len(s)):
        c: int = ord(s[i])
        if c >= 48 and c <= 57:
            val = val * 10 + (c - 48)
        else:
            break
    return val * sign

# 9. Text Parsing: Sanitize Identifier (replace non-alnum with underscore)
@hotloop
def sanitize_ident_str(s: str) -> str:
    out: str = ""
    for i in range(len(s)):
        c: int = ord(s[i])
        if (c >= 65 and c <= 90) or (c >= 97 and c <= 122) or (c >= 48 and c <= 57):
            out += s[i]
        else:
            out += "_"
    return out

# 10. Geometry: Polygon Perimeter Accumulator
@hotloop
def polygon_perimeter_2d(xs: list[float], ys: list[float]) -> float:
    n: int = len(xs)
    if n < 2 or n != len(ys):
        return 0.0
    perim: float = 0.0
    for i in range(n):
        nxt: int = (i + 1) % n
        dx: float = xs[nxt] - xs[i]
        dy: float = ys[nxt] - ys[i]
        perim += math.sqrt(dx * dx + dy * dy)
    return perim

# 11. Linear Algebra: Matrix Frobenius Norm (Flattened N x N)
@hotloop
def frobenius_norm_flat(mat: list[float]) -> float:
    sq_sum: float = 0.0
    for i in range(len(mat)):
        sq_sum += mat[i] * mat[i]
    return math.sqrt(sq_sum)

# 12. Linear Algebra: Vector Clamp Between Min and Max Bounds
@hotloop
def sum_clamped_values(xs: list[float], lower: float, upper: float) -> float:
    tot: float = 0.0
    for i in range(len(xs)):
        v: float = xs[i]
        if v < lower:
            v = lower
        elif v > upper:
            v = upper
        tot += v
    return tot

# 13. Dynamic Programming / DSP: Maximum Subarray Kadane Loop
@hotloop
def kadane_max_subarray(xs: list[float]) -> float:
    if len(xs) == 0:
        return 0.0
    max_so_far: float = xs[0]
    curr_max: float = xs[0]
    for i in range(1, len(xs)):
        curr_max = max(xs[i], curr_max + xs[i])
        if curr_max > max_so_far:
            max_so_far = curr_max
    return max_so_far

# 14. Information Theory: Binary Entropy Evaluation
@hotloop
def binary_entropy_loop(p: float, terms: int) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    q: float = 1.0 - p
    return -(p * math.log(p) + q * math.log(q))

# 15. Bitwise & Cryptography: Count Consecutive Set Bits
@hotloop
def max_consecutive_ones(n: int) -> int:
    cnt: int = 0
    while n > 0:
        n = n & (n << 1)
        cnt += 1
    return cnt

# 16. Statistics: Pearson Correlation Numerator
@hotloop
def correlation_covar_sum(xs: list[float], ys: list[float], mx: float, my: float) -> float:
    n: int = len(xs)
    if n != len(ys):
        return 0.0
    cov: float = 0.0
    for i in range(n):
        cov += (xs[i] - mx) * (ys[i] - my)
    return cov

# 17. DSP: Peak Count Above Neighbor Threshold
@hotloop
def count_signal_peaks(signal: list[float], threshold: float) -> int:
    peaks: int = 0
    n: int = len(signal)
    for i in range(1, n - 1):
        if signal[i] > signal[i - 1] and signal[i] > signal[i + 1] and signal[i] >= threshold:
            peaks += 1
    return peaks

# 18. Geometry: 3D Ray-Sphere Intersection Distance
@hotloop
def ray_sphere_intersect_t(ox: float, oy: float, oz: float, dx: float, dy: float, dz: float, radius: float) -> float:
    b: float = 2.0 * (ox * dx + oy * dy + oz * dz)
    c: float = (ox * ox + oy * oy + oz * oz) - radius * radius
    disc: float = b * b - 4.0 * c
    if disc < 0.0:
        return -1.0
    return (-b - math.sqrt(disc)) / 2.0

# 19. Text Parsing: Count Delimited Substrings
@hotloop
def count_delimiter_occurrences(s: str, delim: str) -> int:
    d_ord: int = ord(delim)
    cnt: int = 0
    for i in range(len(s)):
        if ord(s[i]) == d_ord:
            cnt += 1
    return cnt

# 20. Numerical Analysis: Newton-Raphson Reciprocal (1 / val)
@hotloop
def newton_reciprocal(d: float, iters: int) -> float:
    x: float = 0.1
    for _ in range(iters):
        x = x * (2.0 - d * x)
    return x

# 21. Statistics: L1 Mean Absolute Deviation
@hotloop
def mean_absolute_dev(xs: list[float], mean: float) -> float:
    s: float = 0.0
    for i in range(len(xs)):
        s += abs(xs[i] - mean)
    if len(xs) > 0:
        return s / float(len(xs))
    return 0.0

# 22. Numerical Analysis: Chebyshev Polynomial First Kind Degree 5
@hotloop
def chebyshev_t5(x: float) -> float:
    # T5(x) = 16x^5 - 20x^3 + 5x
    x2: float = x * x
    return x * (16.0 * x2 * x2 - 20.0 * x2 + 5.0)

# 23. Text Processing: Caesar Cipher Shift ASCII
@hotloop
def caesar_cipher_ascii(s: str, shift: int) -> str:
    res: str = ""
    for i in range(len(s)):
        c: int = ord(s[i])
        if c >= 65 and c <= 90:
            shifted: int = 65 + ((c - 65 + shift) % 26)
            res += chr(shifted)
        elif c >= 97 and c <= 122:
            shifted: int = 97 + ((c - 97 + shift) % 26)
            res += chr(shifted)
        else:
            res += s[i]
    return res

# 24. Bitwise: Bit Reversal 16-bit
@hotloop
def bit_reverse_16(x: int) -> int:
    rev: int = 0
    for i in range(16):
        rev = (rev << 1) | (x & 1)
        x = x >> 1
    return rev

# 25. Finance: Trailing High Watermark Drawdown Loop
@hotloop
def max_drawdown_percent(prices: list[float]) -> float:
    if len(prices) == 0:
        return 0.0
    peak: float = prices[0]
    max_dd: float = 0.0
    for i in range(1, len(prices)):
        p: float = prices[i]
        if p > peak:
            peak = p
        elif peak > 0.0:
            dd: float = (peak - p) / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd * 100.0
'''


HOLDOUT_BENCH_RESULTS = {}


class TestGeneralizationHoldoutE8(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="hotloop_holdout_e8_")
        cls.mod_path = os.path.join(cls.tmpdir, "holdout_e8_mod.py")
        with open(cls.mod_path, "w", encoding="utf-8") as f:
            f.write(HOLDOUT_SOURCE)

        backend = MojoBackend()
        ok, msg, so_path = backend.build_ast(cls.mod_path, mod_name="fast")
        assert ok, f"Holdout suite failed to build:\n{msg}"

        sys.path.insert(0, cls.tmpdir)
        import holdout_e8_mod  # type: ignore
        cls.mod = holdout_e8_mod

    @classmethod
    def tearDownClass(cls):
        if cls.tmpdir in sys.path:
            sys.path.remove(cls.tmpdir)
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _check(self, name: str, category: str, *args, approx=False, **kwargs):
        fn = getattr(self.mod, name)
        expected = fn._original(*args, **kwargs)
        actual = fn(*args, **kwargs)
        if approx:
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-6), f"{name}: {actual} != {expected}")
        else:
            self.assertEqual(actual, expected, f"{name}: {actual} != {expected}")

        # Benchmark 20 iterations
        py_times = []
        for _ in range(20):
            t0 = time.perf_counter()
            fn._original(*args, **kwargs)
            py_times.append(time.perf_counter() - t0)
        p50_py = float(np.median(py_times))

        mj_times = []
        for _ in range(20):
            t0 = time.perf_counter()
            fn(*args, **kwargs)
            mj_times.append(time.perf_counter() - t0)
        p50_mj = float(np.median(mj_times))

        speedup = p50_py / p50_mj if p50_mj > 0 else 1.0
        HOLDOUT_BENCH_RESULTS[name] = {
            "category": category,
            "py_ms": p50_py * 1000.0,
            "mj_ms": p50_mj * 1000.0,
            "speedup": speedup,
            "backend": fn._last_backend,
            "verified": True,
        }

    def test_01_numerical_and_quadrature(self):
        # 1. Horner evaluation
        coeffs = np.array([1.2, -3.4, 5.6, -7.8, 9.0, -1.1, 2.2, -3.3, 4.4, 5.5], dtype=np.float64)
        self._check("horner_eval", "Numerical & Quadrature", coeffs, 1.05, approx=True)

        # 2. Simpson cubic integral
        self._check("simpson_integral_cubic", "Numerical & Quadrature", 0.0, 5.0, 1000, approx=True)

        # 3. Newton reciprocal
        self._check("newton_reciprocal", "Numerical & Quadrature", 2.5, 50, approx=True)

        # 4. Chebyshev T5
        self._check("chebyshev_t5", "Numerical & Quadrature", 0.75, approx=True)

    def test_02_dsp_and_statistics(self):
        rng = np.random.RandomState(42)
        xs = np.array(rng.randn(2000), dtype=np.float64)
        ys = np.array(rng.randn(2000), dtype=np.float64)

        # 5. Moving variance sum
        self._check("moving_variance_sum", "DSP & Statistics", xs, float(np.mean(xs)), approx=True)

        # 6. Exponential smoothing
        self._check("exp_smoothing_series", "DSP & Statistics", xs, 0.2, approx=True)

        # 7. Pearson correlation covariance sum
        self._check("correlation_covar_sum", "DSP & Statistics", xs, ys, float(np.mean(xs)), float(np.mean(ys)), approx=True)

        # 8. Mean absolute deviation
        self._check("mean_absolute_dev", "DSP & Statistics", xs, float(np.mean(xs)), approx=True)

        # 9. Signal peaks
        sig = np.sin(np.linspace(0, 100, 2000))
        self._check("count_signal_peaks", "DSP & Statistics", sig, 0.5)

    def test_03_cryptography_and_bitwise(self):
        # 10. Adler-32
        text = "The quick brown fox jumps over the lazy dog! 1234567890" * 40
        self._check("adler32_checksum", "Cryptography & Bitwise", text)

        # 11. Stein binary GCD
        self._check("binary_gcd_stein", "Cryptography & Bitwise", 12345678901234, 987654321098)

        # 12. Max consecutive ones
        self._check("max_consecutive_ones", "Cryptography & Bitwise", 0b111110111111101111)

        # 13. Bit reverse 16
        self._check("bit_reverse_16", "Cryptography & Bitwise", 0b1011001110001101)

    def test_04_text_parsing_and_string(self):
        text = "Mojo Hotloop: Automatic Python-to-Mojo Compiler v0.2.0 Hardening!" * 30

        # 14. Count vowels
        self._check("count_vowels_strict", "Text Parsing & Strings", text)

        # 15. Parse integer
        self._check("parse_int_ascii", "Text Parsing & Strings", "-9876543210")

        # 16. Sanitize identifier
        self._check("sanitize_ident_str", "Text Parsing & Strings", text)

        # 17. Count delimiter
        self._check("count_delimiter_occurrences", "Text Parsing & Strings", text, "o")

        # 18. Caesar cipher
        self._check("caesar_cipher_ascii", "Text Parsing & Strings", text, 13)

    def test_05_geometry_finance_and_dp(self):
        # 19. Polygon perimeter
        pxs = np.array([0.0, 4.0, 4.0, 0.0, -2.0], dtype=np.float64)
        pys = np.array([0.0, 0.0, 3.0, 3.0, 1.5], dtype=np.float64)
        self._check("polygon_perimeter_2d", "Geometry & Finance", pxs, pys, approx=True)

        # 20. Frobenius norm flat
        mat = np.array(np.random.RandomState(99).randn(100), dtype=np.float64)
        self._check("frobenius_norm_flat", "Geometry & Finance", mat, approx=True)

        # 21. Sum clamped values
        self._check("sum_clamped_values", "Geometry & Finance", mat, -0.5, 0.5, approx=True)

        # 22. Kadane max subarray
        self._check("kadane_max_subarray", "Geometry & Finance", mat, approx=True)

        # 23. Binary entropy
        self._check("binary_entropy_loop", "Geometry & Finance", 0.35, 100, approx=True)

        # 24. Ray sphere intersection
        self._check("ray_sphere_intersect_t", "Geometry & Finance", 0.0, 0.0, -5.0, 0.0, 0.0, 1.0, 2.0, approx=True)

        # 25. Max drawdown percent
        prices = np.array([100.0, 105.0, 102.0, 110.0, 95.0, 98.0, 115.0, 90.0, 120.0], dtype=np.float64)
        self._check("max_drawdown_percent", "Geometry & Finance", prices, approx=True)

    def test_06_print_holdout_summary(self):
        print("\n" + "=" * 80)
        print("PHASE E.8 FRESH HOLDOUT GENERALIZATION SCORECARD (25 UNSEEN FUNCTIONS)")
        print("=" * 80)
        print(f"{'FUNCTION':<28} | {'CATEGORY':<24} | {'SPEEDUP':>8} | {'BACKEND':<10} | {'STATUS'}")
        print("-" * 80)
        for name, r in HOLDOUT_BENCH_RESULTS.items():
            print(f"{name:<28} | {r['category']:<24} | {r['speedup']:>7.2f}x | {r['backend']:<10} | VERIFIED")
        print("=" * 80)
        self.assertEqual(len(HOLDOUT_BENCH_RESULTS), 25)


if __name__ == "__main__":
    unittest.main(verbosity=2)
