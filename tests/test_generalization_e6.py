import math
import os
import shutil
import sys
import tempfile
import time
import unittest
import numpy as np

from hotloop.backends.mojo import MojoBackend

MODULE_SOURCE = '''
import math
from hotloop import hotloop

# --- Category 1: Numerical Loops (10 functions) ---
@hotloop
def fib_loop(n: int) -> int:
    if n <= 1:
        return n
    a: int = 0
    b: int = 1
    for _ in range(2, n + 1):
        c: int = a + b
        a = b
        b = c
    return b

@hotloop
def collatz_steps(n: int) -> int:
    steps: int = 0
    val: int = n
    while val > 1:
        if val % 2 == 0:
            val = val // 2
        else:
            val = 3 * val + 1
        steps += 1
    return steps

@hotloop
def leibniz_pi_est(terms: int) -> float:
    acc: float = 0.0
    sign: float = 1.0
    for i in range(terms):
        acc += sign / (2.0 * float(i) + 1.0)
        sign = -sign
    return acc * 4.0

@hotloop
def newton_sqrt_est(val: float, iters: int) -> float:
    if val <= 0.0:
        return 0.0
    x: float = val
    for _ in range(iters):
        x = 0.5 * (x + val / x)
    return x

@hotloop
def geo_series_sum(a: float, r: float, n: int) -> float:
    total: float = 0.0
    term: float = a
    for _ in range(n):
        total += term
        term *= r
    return total

@hotloop
def harmonic_mean_loop(n: int) -> float:
    if n <= 0:
        return 0.0
    sum_inv: float = 0.0
    for i in range(1, n + 1):
        sum_inv += 1.0 / float(i)
    return float(n) / sum_inv

@hotloop
def chebyshev_t_eval(n: int, x: float) -> float:
    if n == 0:
        return 1.0
    if n == 1:
        return x
    t0: float = 1.0
    t1: float = x
    for _ in range(2, n + 1):
        t2: float = 2.0 * x * t1 - t0
        t0 = t1
        t1 = t2
    return t1

@hotloop
def lucas_number(n: int) -> int:
    if n == 0:
        return 2
    if n == 1:
        return 1
    a: int = 2
    b: int = 1
    for _ in range(2, n + 1):
        c: int = a + b
        a = b
        b = c
    return b

@hotloop
def bessel_j0_approx(x: float, terms: int) -> float:
    ans: float = 1.0
    term: float = 1.0
    x_half_sq: float = (x * 0.5) * (x * 0.5)
    for m in range(1, terms + 1):
        term = -term * x_half_sq / float(m * m)
        ans += term
    return ans

@hotloop
def logistic_map_orbit(r: float, x0: float, steps: int) -> float:
    x: float = x0
    for _ in range(steps):
        x = r * x * (1.0 - x)
    return x

# --- Category 2: Distance & Geometry (10 functions) ---
@hotloop
def euclidean_dist_3d(x1: float, y1: float, z1: float, x2: float, y2: float, z2: float) -> float:
    dx: float = x1 - x2
    dy: float = y1 - y2
    dz: float = z1 - z2
    return math.sqrt(dx * dx + dy * dy + dz * dz)

@hotloop
def manhattan_dist_arr(xs: list[float], ys: list[float]) -> float:
    n: int = min(len(xs), len(ys))
    total: float = 0.0
    for i in range(n):
        diff: float = xs[i] - ys[i]
        if diff < 0.0:
            diff = -diff
        total += diff
    return total

@hotloop
def chebyshev_dist_arr(xs: list[float], ys: list[float]) -> float:
    n: int = min(len(xs), len(ys))
    max_d: float = 0.0
    for i in range(n):
        diff: float = xs[i] - ys[i]
        if diff < 0.0:
            diff = -diff
        if diff > max_d:
            max_d = diff
    return max_d

@hotloop
def canberra_dist_arr(xs: list[float], ys: list[float]) -> float:
    n: int = min(len(xs), len(ys))
    total: float = 0.0
    for i in range(n):
        num: float = abs(xs[i] - ys[i])
        denom: float = abs(xs[i]) + abs(ys[i])
        if denom > 0.0:
            total += num / denom
    return total

@hotloop
def minkowski_dist_p3(xs: list[float], ys: list[float]) -> float:
    n: int = min(len(xs), len(ys))
    sum_cubes: float = 0.0
    for i in range(n):
        diff: float = abs(xs[i] - ys[i])
        sum_cubes += diff * diff * diff
    return sum_cubes ** (1.0 / 3.0)

@hotloop
def point_seg_dist_sq(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    abx: float = bx - ax
    aby: float = by - ay
    apx: float = px - ax
    apy: float = py - ay
    ab_len_sq: float = abx * abx + aby * aby
    if ab_len_sq == 0.0:
        return apx * apx + apy * apy
    t: float = (apx * abx + apy * aby) / ab_len_sq
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    proj_x: float = ax + t * abx
    proj_y: float = ay + t * aby
    dx: float = px - proj_x
    dy: float = py - proj_y
    return dx * dx + dy * dy

@hotloop
def shoelace_polygon_area(xs: list[float], ys: list[float]) -> float:
    n: int = min(len(xs), len(ys))
    if n < 3:
        return 0.0
    area: float = 0.0
    for i in range(n):
        j: int = (i + 1) % n
        area += xs[i] * ys[j] - xs[j] * ys[i]
    return abs(area) * 0.5

@hotloop
def triangle_circumradius(a: float, b: float, c: float) -> float:
    s: float = (a + b + c) * 0.5
    prod: float = s * (s - a) * (s - b) * (s - c)
    if prod <= 0.0:
        return 0.0
    area: float = math.sqrt(prod)
    return (a * b * c) / (4.0 * area)

@hotloop
def cosine_sim_arr(xs: list[float], ys: list[float]) -> float:
    n: int = min(len(xs), len(ys))
    dot: float = 0.0
    norm_x: float = 0.0
    norm_y: float = 0.0
    for i in range(n):
        dot += xs[i] * ys[i]
        norm_x += xs[i] * xs[i]
        norm_y += ys[i] * ys[i]
    denom: float = math.sqrt(norm_x * norm_y)
    if denom == 0.0:
        return 0.0
    return dot / denom

@hotloop
def haversine_single_pair(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rad: float = math.pi / 180.0
    dlat: float = (lat2 - lat1) * rad
    dlon: float = (lon2 - lon1) * rad
    a: float = math.sin(dlat * 0.5) ** 2 + math.cos(lat1 * rad) * math.cos(lat2 * rad) * math.sin(dlon * 0.5) ** 2
    c: float = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return 6371.0 * c

# --- Category 3: Array Transforms & Reductions (10 functions) ---
@hotloop
def running_prod_mod(xs: list[int], m: int) -> int:
    acc: int = 1
    for i in range(len(xs)):
        acc = (acc * (xs[i] % m)) % m
    return acc

@hotloop
def exp_weighted_average(xs: list[float], alpha: float) -> float:
    n: int = len(xs)
    if n == 0:
        return 0.0
    ema: float = xs[0]
    one_minus_alpha: float = 1.0 - alpha
    for i in range(1, n):
        ema = alpha * xs[i] + one_minus_alpha * ema
    return ema

@hotloop
def dot_prod_fast(xs: list[float], ys: list[float]) -> float:
    n: int = min(len(xs), len(ys))
    total: float = 0.0
    for i in range(n):
        total += xs[i] * ys[i]
    return total

@hotloop
def l2_norm_scaled(xs: list[float], scale: float) -> float:
    sum_sq: float = 0.0
    for i in range(len(xs)):
        sum_sq += xs[i] * xs[i]
    return math.sqrt(sum_sq) * scale

@hotloop
def count_above_threshold(xs: list[float], thresh: float) -> int:
    cnt: int = 0
    for i in range(len(xs)):
        if xs[i] > thresh:
            cnt += 1
    return cnt

@hotloop
def find_local_min_idx(xs: list[float]) -> int:
    n: int = len(xs)
    if n < 3:
        return -1
    for i in range(1, n - 1):
        if xs[i] < xs[i - 1] and xs[i] < xs[i + 1]:
            return i
    return -1

@hotloop
def kurtosis_excess_eval(xs: list[float], mean: float, std: float) -> float:
    n: int = len(xs)
    if n < 4 or std <= 0.0:
        return 0.0
    m4: float = 0.0
    for i in range(n):
        dev: float = (xs[i] - mean) / std
        m4 += dev * dev * dev * dev
    return (m4 / float(n)) - 3.0

@hotloop
def sparse_dot_gather(xs: list[float], indices: list[int], ys: list[float]) -> float:
    k: int = min(len(indices), len(ys))
    n_xs: int = len(xs)
    dot: float = 0.0
    for i in range(k):
        idx: int = indices[i]
        if 0 <= idx < n_xs:
            dot += xs[idx] * ys[i]
    return dot

@hotloop
def matrix_diagonal_trace(matrix_flat: list[float], n: int) -> float:
    trace: float = 0.0
    for i in range(n):
        trace += matrix_flat[i * n + i]
    return trace

@hotloop
def spread_min_max(xs: list[float]) -> float:
    n: int = len(xs)
    if n == 0:
        return 0.0
    min_v: float = xs[0]
    max_v: float = xs[0]
    for i in range(1, n):
        v: float = xs[i]
        if v < min_v:
            min_v = v
        if v > max_v:
            max_v = v
    return max_v - min_v

# --- Category 4: String Scanning & Text Processing (10 functions) ---
@hotloop
def count_digits_in_str(s: str) -> int:
    cnt: int = 0
    for i in range(len(s)):
        ch: str = s[i]
        if "0" <= ch <= "9":
            cnt += 1
    return cnt

@hotloop
def count_tokens_by_space(s: str) -> int:
    n: int = len(s)
    words: int = 0
    in_word: bool = False
    for i in range(n):
        ch: str = s[i]
        if ch == " " or ch == "\\t" or ch == "\\n":
            in_word = False
        else:
            if not in_word:
                words += 1
                in_word = True
    return words

@hotloop
def first_adjacent_pair_idx(s: str) -> int:
    n: int = len(s)
    for i in range(n - 1):
        if s[i] == s[i + 1]:
            return i
    return -1

@hotloop
def sum_ord_codepoints(s: str) -> int:
    total: int = 0
    for i in range(len(s)):
        total += ord(s[i])
    return total

@hotloop
def check_brackets_depth(s: str) -> bool:
    depth: int = 0
    for i in range(len(s)):
        ch: str = s[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0

@hotloop
def longest_char_streak(s: str) -> int:
    n: int = len(s)
    if n == 0:
        return 0
    max_streak: int = 1
    curr_streak: int = 1
    for i in range(1, n):
        if s[i] == s[i - 1]:
            curr_streak += 1
            if curr_streak > max_streak:
                max_streak = curr_streak
        else:
            curr_streak = 1
    return max_streak

@hotloop
def djb2_str_hash(s: str) -> int:
    h: int = 5381
    for i in range(len(s)):
        h = ((h * 33) + ord(s[i])) & 4294967295
    return h

@hotloop
def fnv1a_str_hash(s: str) -> int:
    h: int = 2166136261
    for i in range(len(s)):
        h = ((h ^ ord(s[i])) * 16777619) & 4294967295
    return h

@hotloop
def count_uppercase_chars(s: str) -> int:
    cnt: int = 0
    for i in range(len(s)):
        ch: str = s[i]
        if "A" <= ch <= "Z":
            cnt += 1
    return cnt

@hotloop
def is_hex_color_literal(s: str) -> bool:
    n: int = len(s)
    if n != 7:
        return False
    if s[0] != "#":
        return False
    for i in range(1, 7):
        ch: str = s[i]
        if not (("0" <= ch <= "9") or ("a" <= ch <= "f") or ("A" <= ch <= "F")):
            return False
    return True

# --- Category 5: Validation, Search & Bitwise (12 functions) ---
@hotloop
def binary_search_arr(arr: list[int], target: int) -> int:
    low: int = 0
    high: int = len(arr) - 1
    while low <= high:
        mid: int = (low + high) // 2
        val: int = arr[mid]
        if val == target:
            return mid
        elif val < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1

@hotloop
def popcount_64(val: int) -> int:
    cnt: int = 0
    v: int = val
    while v > 0:
        cnt += v & 1
        v = v >> 1
    return cnt

@hotloop
def parity_of_int(val: int) -> int:
    p: int = 0
    v: int = val
    while v > 0:
        p = p ^ (v & 1)
        v = v >> 1
    return p

@hotloop
def is_prime_check(n: int) -> bool:
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i: int = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

@hotloop
def gcd_scalar(a: int, b: int) -> int:
    x: int = a
    if x < 0:
        x = -x
    y: int = b
    if y < 0:
        y = -y
    while y != 0:
        t: int = y
        y = x % y
        x = t
    return x

@hotloop
def lcm_scalar(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    x: int = a
    if x < 0:
        x = -x
    y: int = b
    if y < 0:
        y = -y
    g_x: int = x
    g_y: int = y
    while g_y != 0:
        t: int = g_y
        g_y = g_x % g_y
        g_x = t
    return (x // g_x) * y

@hotloop
def lcg_next_n(seed: int, steps: int) -> int:
    val: int = seed
    for _ in range(steps):
        val = (val * 1664525 + 1013904223) & 4294967295
    return val

@hotloop
def gray_code_encode(n: int) -> int:
    return n ^ (n >> 1)

@hotloop
def count_trailing_zeros_64(val: int) -> int:
    if val == 0:
        return 64
    cnt: int = 0
    v: int = val
    while (v & 1) == 0:
        cnt += 1
        v = v >> 1
    return cnt

@hotloop
def mod_exp_scalar(base: int, exp: int, mod: int) -> int:
    if mod == 1:
        return 0
    res: int = 1
    b: int = base % mod
    e: int = exp
    while e > 0:
        if e % 2 == 1:
            res = (res * b) % mod
        e = e // 2
        b = (b * b) % mod
    return res

@hotloop
def integer_sqrt_binsearch(n: int) -> int:
    if n < 0:
        return -1
    if n <= 1:
        return n
    low: int = 1
    high: int = n
    ans: int = 1
    while low <= high:
        mid: int = (low + high) // 2
        if mid * mid <= n:
            ans = mid
            low = mid + 1
        else:
            high = mid - 1
    return ans

@hotloop
def catalan_num_iter(n: int) -> int:
    if n <= 1:
        return 1
    c: int = 1
    for i in range(1, n + 1):
        c = (c * (4 * i - 2)) // (i + 1)
    return c
'''

GENERALIZATION_RESULTS = {}

class TestGeneralizationE6(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="hotloop_gen_e6_")
        cls.mod_path = os.path.join(cls.tmpdir, "gen_e6_mod.py")
        with open(cls.mod_path, "w", encoding="utf-8") as f:
            f.write(MODULE_SOURCE)

        backend = MojoBackend()
        ok, msg, so_path = backend.build_ast(cls.mod_path, mod_name="fast")
        assert ok, f"Generalization challenge suite failed to build:\n{msg}"

        sys.path.insert(0, cls.tmpdir)
        import gen_e6_mod  # type: ignore
        cls.mod = gen_e6_mod

    @classmethod
    def tearDownClass(cls):
        if cls.tmpdir in sys.path:
            sys.path.remove(cls.tmpdir)
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _check(self, category: str, fn_name: str, *args, approx=False, **kwargs):
        fn = getattr(self.mod, fn_name)
        expected = fn._original(*args, **kwargs)
        actual = fn(*args, **kwargs)
        self.assertEqual(fn._last_backend, "native", f"{fn_name} expected native, got {fn._last_backend}")
        if approx:
            self.assertTrue(math.isclose(actual, expected, rel_tol=1e-7, abs_tol=1e-7), f"{fn_name}: {actual} != {expected}")
        else:
            self.assertEqual(actual, expected, f"{fn_name}: {actual} != {expected}")

        # Benchmark speedup
        # 1. Python
        py_times = []
        for _ in range(25):
            t0 = time.perf_counter()
            fn._original(*args, **kwargs)
            py_times.append(time.perf_counter() - t0)
        p50_py = float(np.median(py_times))

        # 2. Native
        native_times = []
        for _ in range(25):
            t0 = time.perf_counter()
            fn(*args, **kwargs)
            native_times.append(time.perf_counter() - t0)
        p50_native = float(np.median(native_times))

        speedup = p50_py / p50_native if p50_native > 0 else 1.0
        GENERALIZATION_RESULTS[fn_name] = {
            "category": category,
            "py_ms": p50_py * 1000.0,
            "native_ms": p50_native * 1000.0,
            "speedup": speedup,
            "verified": True,
        }
        return actual

    def test_01_numerical_loops_10_functions(self):
        c = "Numerical Loops"
        self._check(c, "fib_loop", 50)
        self._check(c, "collatz_steps", 670617279)
        self._check(c, "leibniz_pi_est", 10000, approx=True)
        self._check(c, "newton_sqrt_est", 1234567.89, 20, approx=True)
        self._check(c, "geo_series_sum", 1.0, 0.99, 1000, approx=True)
        self._check(c, "harmonic_mean_loop", 5000, approx=True)
        self._check(c, "chebyshev_t_eval", 20, 0.75, approx=True)
        self._check(c, "lucas_number", 45)
        self._check(c, "bessel_j0_approx", 2.5, 25, approx=True)
        self._check(c, "logistic_map_orbit", 3.99, 0.4, 5000, approx=True)

    def test_02_distance_geometry_10_functions(self):
        c = "Distance & Geometry"
        self._check(c, "euclidean_dist_3d", 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, approx=True)
        xs = np.linspace(-10.0, 10.0, 2048, dtype=np.float64)
        ys = np.linspace(5.0, 25.0, 2048, dtype=np.float64)
        self._check(c, "manhattan_dist_arr", xs, ys, approx=True)
        self._check(c, "chebyshev_dist_arr", xs, ys, approx=True)
        self._check(c, "canberra_dist_arr", xs, ys, approx=True)
        self._check(c, "minkowski_dist_p3", xs, ys, approx=True)
        self._check(c, "point_seg_dist_sq", 2.0, 3.0, 0.0, 0.0, 5.0, 5.0, approx=True)
        poly_x = np.array([0.0, 4.0, 4.0, 0.0], dtype=np.float64)
        poly_y = np.array([0.0, 0.0, 3.0, 3.0], dtype=np.float64)
        self._check(c, "shoelace_polygon_area", poly_x, poly_y, approx=True)
        self._check(c, "triangle_circumradius", 7.0, 8.0, 9.0, approx=True)
        self._check(c, "cosine_sim_arr", xs, ys, approx=True)
        self._check(c, "haversine_single_pair", 37.7749, -122.4194, 40.7128, -74.0060, approx=True)

    def test_03_array_transforms_10_functions(self):
        c = "Array Transforms & Reductions"
        arr_i = np.arange(1, 1001, dtype=np.int64)
        arr_f = np.linspace(0.5, 500.0, 2048, dtype=np.float64)
        arr_f2 = np.linspace(-250.0, 250.0, 2048, dtype=np.float64)
        self._check(c, "running_prod_mod", arr_i, 1000000007)
        self._check(c, "exp_weighted_average", arr_f, 0.05, approx=True)
        self._check(c, "dot_prod_fast", arr_f, arr_f2, approx=True)
        self._check(c, "l2_norm_scaled", arr_f, 1.5, approx=True)
        self._check(c, "count_above_threshold", arr_f, 250.0)
        sine_curve = np.array([math.sin(i * 0.1) for i in range(100)], dtype=np.float64)
        self._check(c, "find_local_min_idx", sine_curve)
        self._check(c, "kurtosis_excess_eval", arr_f, 250.0, 144.0, approx=True)
        indices = np.array([10, 25, 50, 100, 200], dtype=np.int64)
        ys = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        self._check(c, "sparse_dot_gather", arr_f, indices, ys, approx=True)
        mat_flat = np.linspace(1.0, 64.0, 64, dtype=np.float64)
        self._check(c, "matrix_diagonal_trace", mat_flat, 8, approx=True)
        self._check(c, "spread_min_max", arr_f2, approx=True)

    def test_04_string_scanning_10_functions(self):
        c = "String Scanning & Text"
        doc = "Total invoice #9481 on 2026-11-15: $492.50 USD for vendor ACME Corp. (Status: PAID) " * 50
        self._check(c, "count_digits_in_str", doc)
        self._check(c, "count_tokens_by_space", doc)
        self._check(c, "first_adjacent_pair_idx", "The quick brown fox jumps over the lazy dogg.")
        self._check(c, "sum_ord_codepoints", doc)
        brackets = "(((())))(()())(())" * 100
        self._check(c, "check_brackets_depth", brackets)
        self._check(c, "longest_char_streak", "aaabbbcccccdddddddeeeee")
        self._check(c, "djb2_str_hash", doc)
        self._check(c, "fnv1a_str_hash", doc)
        self._check(c, "count_uppercase_chars", doc)
        self._check(c, "is_hex_color_literal", "#1a2B3c")

    def test_05_validation_search_bitwise_12_functions(self):
        c = "Validation, Search & Bitwise"
        sorted_arr = np.arange(10, 20000, 2, dtype=np.int64)
        self._check(c, "binary_search_arr", sorted_arr, 12344)
        self._check(c, "popcount_64", 0x5555555555555555)
        self._check(c, "parity_of_int", 0x123456789ABCDEF)
        self._check(c, "is_prime_check", 2147483647)
        self._check(c, "gcd_scalar", 1071, 462)
        self._check(c, "lcm_scalar", 1071, 462)
        self._check(c, "lcg_next_n", 42, 50000)
        self._check(c, "gray_code_encode", 12345)
        self._check(c, "count_trailing_zeros_64", 0x80000000)
        self._check(c, "mod_exp_scalar", 7, 560, 561)
        self._check(c, "integer_sqrt_binsearch", 987654321)
        self._check(c, "catalan_num_iter", 15)

    def test_06_print_summary(self):
        print(f"\\n{'='*75}")
        print(f"{'UNSEEN FUNCTION':<28} | {'CATEGORY':<24} | {'SPEEDUP':>8} | {'STATUS'}")
        print(f"{'='*75}")
        for fn_name, data in GENERALIZATION_RESULTS.items():
            print(f"{fn_name:<28} | {data['category']:<24} | {data['speedup']:>7.2f}x | VERIFIED")
        print(f"{'='*75}")
        print(f"Total Unseen Functions Evaluated: {len(GENERALIZATION_RESULTS)} / 50 target (100% Correctness Parity)")
        import json
        with open("benchmarks/generalization_results.json", "w") as f:
            json.dump(GENERALIZATION_RESULTS, f, indent=2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
