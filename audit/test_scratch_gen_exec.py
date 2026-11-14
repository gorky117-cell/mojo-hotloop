import math
import random
import ctypes
import numpy as np
import importlib

# Load compiled module
import sys
sys.path.insert(0, '/home/gaurav/mojo-hotloop/audit')
import scratch_gen

# Pure Python references
def py_trapezoidal_integration(a: float, b: float, n_steps: int) -> float:
    if n_steps <= 0:
        return 0.0
    h = (b - a) / float(n_steps)
    inv_sqrt_2pi = 0.3989422804014327
    total = 0.5 * (math.exp(-a * a * 0.5) + math.exp(-b * b * 0.5))
    x = a
    for _ in range(1, n_steps):
        x += h
        total += math.exp(-x * x * 0.5)
    return total * h * inv_sqrt_2pi

def py_chebyshev_path_distance(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n <= 1:
        return 0.0
    total = 0.0
    for i in range(1, n):
        dx = abs(xs[i] - xs[i - 1])
        dy = abs(ys[i] - ys[i - 1])
        if dx > dy:
            total += dx
        else:
            total += dy
    return total

def py_exponential_moving_average(values: list[float], alpha: float) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    ema = values[0]
    one_minus_alpha = 1.0 - alpha
    for i in range(1, n):
        ema = alpha * values[i] + one_minus_alpha * ema
    return ema

def py_mask_digits(text: str) -> str:
    n = len(text)
    res = ""
    for i in range(n):
        if text[i] >= "0" and text[i] <= "9":
            res += "*"
        else:
            res += text[i]
    return res

def py_hamming_distance(s1: str, s2: str) -> int:
    n1 = len(s1)
    n2 = len(s2)
    min_len = min(n1, n2)
    dist = abs(n1 - n2)
    for i in range(min_len):
        if s1[i] != s2[i]:
            dist += 1
    return dist

print("--- Testing Function 1: trapezoidal_integration ---")
for a, b, n in [(-2.0, 2.0, 1000), (0.0, 5.0, 50000), (-1.0, 1.0, 10), (0.0, 0.0, 100)]:
    py_res = py_trapezoidal_integration(a, b, n)
    mojo_res = scratch_gen.trapezoidal_integration(a, b, n)
    diff = abs(py_res - mojo_res)
    assert diff < 1e-9, f"Mismatch: py={py_res}, mojo={mojo_res}"
print("PASSED Function 1!")

print("--- Testing Function 2: chebyshev_path_distance ---")
rng = random.Random(42)
for size in [0, 1, 10, 500]:
    xs = [rng.uniform(-100, 100) for _ in range(size)]
    ys = [rng.uniform(-100, 100) for _ in range(size)]
    py_res = py_chebyshev_path_distance(xs, ys)
    # Test with standard list
    mojo_res_list = scratch_gen.chebyshev_path_distance(xs, ys)
    assert abs(py_res - mojo_res_list) < 1e-9, f"List Mismatch: py={py_res}, mojo={mojo_res_list}"
    # Test with numpy array (.ctypes path)
    if size > 0:
        np_xs = np.array(xs, dtype=np.float64)
        np_ys = np.array(ys, dtype=np.float64)
        mojo_res_np = scratch_gen.chebyshev_path_distance(np_xs, np_ys)
        assert abs(py_res - mojo_res_np) < 1e-9, f"NP Mismatch: py={py_res}, mojo={mojo_res_np}"
print("PASSED Function 2!")

print("--- Testing Function 3: exponential_moving_average ---")
for size in [0, 1, 5, 200]:
    vals = [rng.uniform(10, 50) for _ in range(size)]
    alpha = 0.15
    py_res = py_exponential_moving_average(vals, alpha)
    mojo_res = scratch_gen.exponential_moving_average(vals, alpha)
    assert abs(py_res - mojo_res) < 1e-9, f"Mismatch: py={py_res}, mojo={mojo_res}"
    if size > 0:
        np_vals = np.array(vals, dtype=np.float64)
        mojo_res_np = scratch_gen.exponential_moving_average(np_vals, alpha)
        assert abs(py_res - mojo_res_np) < 1e-9, f"NP Mismatch: py={py_res}, mojo={mojo_res_np}"
print("PASSED Function 3!")

print("--- Testing Function 4: mask_digits ---")
test_texts = [
    "",
    "Hello World!",
    "Order #12345 placed on 2026-11-15 for $99.95",
    "No digits here at all",
    "0123456789",
    "Mixed: A1B2C3D4E5F6G7H8I9J0",
]
for text in test_texts:
    py_res = py_mask_digits(text)
    mojo_res = scratch_gen.mask_digits(text)
    assert py_res == mojo_res, f"Mismatch: py={repr(py_res)}, mojo={repr(mojo_res)}"
print("PASSED Function 4!")

print("--- Testing Function 5: hamming_distance ---")
pairs = [
    ("", ""),
    ("apple", "apply"),
    ("karolin", "kathrin"),
    ("1011101", "1001001"),
    ("short", "longer_string"),
    ("identical", "identical"),
]
for s1, s2 in pairs:
    py_res = py_hamming_distance(s1, s2)
    mojo_res = scratch_gen.hamming_distance(s1, s2)
    assert py_res == mojo_res, f"Mismatch: s1={s1}, s2={s2}, py={py_res}, mojo={mojo_res}"
print("PASSED Function 5!")

print("ALL 5 GENERALIZATION FUNCTIONS VERIFIED CORRECTLY!")
