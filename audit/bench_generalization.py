import gc
import math
import random
import time
import statistics
import numpy as np
import sys
sys.path.insert(0, '/home/gaurav/mojo-hotloop/audit')
import scratch_gen

# Pure Python functions
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

def bench_fn(fn, args, runs=50, iters_per_run=10):
    # Warmup
    for _ in range(5):
        fn(*args)
    times = []
    gc.disable()
    try:
        for _ in range(runs):
            t0 = time.perf_counter_ns()
            for _ in range(iters_per_run):
                fn(*args)
            t1 = time.perf_counter_ns()
            times.append((t1 - t0) / (iters_per_run * 1000.0)) # microseconds
    finally:
        gc.enable()
    times.sort()
    p50 = statistics.median(times)
    mean = statistics.mean(times)
    return p50, mean

results = []

print("========================================================================")
print("MOJO-HOTLOOP — TRANSPILER GENERALIZATION BENCHMARK AUDIT")
print("Hardware: Intel Core i5-8265U | Ubuntu 24.04 (WSL2) | Python 3.12.16 | Mojo 1.2.0")
print("Provenance: 100% AST-Generated via hotloop.ast_transpiler (ZERO HANDWRITTEN KERNELS)")
print("========================================================================")

# 1. Numerical Loop: Trapezoidal Integration (100,000 steps)
n_steps = 100_000
p50_py, mean_py = bench_fn(py_trapezoidal_integration, (-5.0, 5.0, n_steps), runs=50, iters_per_run=5)
p50_mojo, mean_mojo = bench_fn(scratch_gen.trapezoidal_integration, (-5.0, 5.0, n_steps), runs=50, iters_per_run=10)
speedup = p50_py / p50_mojo
results.append(("1. Numerical Loop (trapezoidal_integration)", f"{n_steps:,} steps", p50_py, p50_mojo, speedup))
print(f"[1/5] Numerical Loop (100k steps):")
print(f"      Python: {p50_py:8.2f} µs | Mojo: {p50_mojo:8.2f} µs | Speedup: {speedup:6.2f}x")

# 2. Coordinate Distance: Chebyshev Path Distance (10,000 points)
rng = random.Random(42)
n_pts = 10_000
xs_arr = np.array([rng.uniform(-100, 100) for _ in range(n_pts)], dtype=np.float64)
ys_arr = np.array([rng.uniform(-100, 100) for _ in range(n_pts)], dtype=np.float64)
xs_list = list(xs_arr)
ys_list = list(ys_arr)

# Bench Python with list
p50_py, mean_py = bench_fn(py_chebyshev_path_distance, (xs_list, ys_list), runs=50, iters_per_run=10)
# Bench Mojo with contiguous pointer (.ctypes)
p50_mojo, mean_mojo = bench_fn(scratch_gen.chebyshev_path_distance, (xs_arr, ys_arr), runs=50, iters_per_run=20)
speedup = p50_py / p50_mojo
results.append(("2. Coordinate Distance (chebyshev_path_distance)", f"{n_pts:,} waypoints", p50_py, p50_mojo, speedup))
print(f"[2/5] Coordinate Distance (10k waypoints):")
print(f"      Python: {p50_py:8.2f} µs | Mojo: {p50_mojo:8.2f} µs | Speedup: {speedup:6.2f}x")

# 3. Stateful Reduction: Exponential Moving Average (50,000 items)
n_vals = 50_000
vals_arr = np.array([rng.uniform(10, 100) for _ in range(n_vals)], dtype=np.float64)
vals_list = list(vals_arr)
p50_py, mean_py = bench_fn(py_exponential_moving_average, (vals_list, 0.05), runs=50, iters_per_run=10)
p50_mojo, mean_mojo = bench_fn(scratch_gen.exponential_moving_average, (vals_arr, 0.05), runs=50, iters_per_run=20)
speedup = p50_py / p50_mojo
results.append(("3. Stateful Reduction (exponential_moving_average)", f"{n_vals:,} values", p50_py, p50_mojo, speedup))
print(f"[3/5] Stateful Reduction (50k values):")
print(f"      Python: {p50_py:8.2f} µs | Mojo: {p50_mojo:8.2f} µs | Speedup: {speedup:6.2f}x")

# 4. Text Scanning & Masking: Digit Masking (50,000 characters)
chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_.,;:!? "
text_sample = "".join(rng.choice(chars) for _ in range(50_000))
p50_py, mean_py = bench_fn(py_mask_digits, (text_sample,), runs=30, iters_per_run=5)
p50_mojo, mean_mojo = bench_fn(scratch_gen.mask_digits, (text_sample,), runs=30, iters_per_run=5)
speedup = p50_py / p50_mojo
results.append(("4. Text Scanning & Masking (mask_digits)", f"{len(text_sample):,} chars", p50_py, p50_mojo, speedup))
print(f"[4/5] Text Scanning & Masking (50k chars):")
print(f"      Python: {p50_py:8.2f} µs | Mojo: {p50_mojo:8.2f} µs | Speedup: {speedup:6.2f}x")

# 5. String Similarity: Hamming Distance (50,000 characters)
s1 = "".join(rng.choice(chars) for _ in range(50_000))
s2 = "".join(rng.choice(chars) for _ in range(50_000))
p50_py, mean_py = bench_fn(py_hamming_distance, (s1, s2), runs=30, iters_per_run=5)
p50_mojo, mean_mojo = bench_fn(scratch_gen.hamming_distance, (s1, s2), runs=30, iters_per_run=5)
speedup = p50_py / p50_mojo
results.append(("5. String Similarity (hamming_distance)", f"{len(s1):,} chars", p50_py, p50_mojo, speedup))
print(f"[5/5] String Similarity (50k chars):")
print(f"      Python: {p50_py:8.2f} µs | Mojo: {p50_mojo:8.2f} µs | Speedup: {speedup:6.2f}x")

print("\n========================================================================")
print("GENERALIZATION SCORECARD SUMMARY")
print("========================================================================")
print(f"{'Category / Workload':<45} | {'Size':<16} | {'Python (p50)':<12} | {'Mojo (p50)':<12} | {'Speedup':<8}")
print("-" * 105)
for cat, sz, py_t, mojo_t, spd in results:
    py_str = f"{py_t:,.1f} µs"
    mojo_str = f"{mojo_t:,.1f} µs"
    print(f"{cat:<45} | {sz:<16} | {py_str:<12} | {mojo_str:<12} | {spd:6.2f}x")
print("========================================================================")
