import array
import os
import sys
import time
import numpy as np

repo_root = "/home/gaurav/mojo-hotloop"
sys.path.insert(0, repo_root)

# 1. Load native modules directly from audit/unseen_cases
from hotloop.decorator import _load_native_module

so_rm = os.path.join(repo_root, "audit/unseen_cases/running_max/fast.so")
mod_rm, err_rm = _load_native_module(so_rm)
assert mod_rm is not None, f"Failed to load {so_rm}: {err_rm}"
mojo_rm = getattr(mod_rm, "running_max")

so_cg = os.path.join(repo_root, "audit/unseen_cases/count_greater/fast.so")
mod_cg, err_cg = _load_native_module(so_cg)
assert mod_cg is not None, f"Failed to load {so_cg}: {err_cg}"
mojo_cg = getattr(mod_cg, "count_greater")

so_sma = os.path.join(repo_root, "audit/unseen_cases/simple_moving_average/fast.so")
mod_sma, err_sma = _load_native_module(so_sma)
assert mod_sma is not None, f"Failed to load {so_sma}: {err_sma}"
mojo_sma = getattr(mod_sma, "simple_moving_average")

# Python implementations
def py_running_max(values: list[float]) -> list[float]:
    if not values:
        return []
    result: list[float] = []
    current_max: float = values[0]
    for v in values:
        if v > current_max:
            current_max = v
        result.append(current_max)
    return result

def py_count_greater(values: list[float], threshold: float) -> int:
    count: int = 0
    for v in values:
        if v > threshold:
            count += 1
    return count

def py_sma(values: list[float], window: int) -> list[float]:
    if len(values) < window or window <= 0:
        return []
    result: list[float] = []
    window_sum: float = 0.0
    for i in range(window):
        window_sum += values[i]
    result.append(window_sum / window)
    for i in range(window, len(values)):
        window_sum += values[i] - values[i - window]
        result.append(window_sum / window)
    return result

# Synthetic data: 50,000 floats
import random
rng = random.Random(42)
py_list_50k = [rng.uniform(-1000.0, 1000.0) for _ in range(50000)]
np_arr_50k = np.array(py_list_50k, dtype=np.float64)

def bench_fn(fn, *args, iters=20):
    for _ in range(2):
        fn(*args)
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(*args)
    t1 = time.perf_counter_ns()
    return (t1 - t0) / iters / 1e6  # ms

print("=== COMPONENT-BY-COMPONENT BREAKDOWN (50,000 FLOATS) ===")

# Running Max
t_py_rm = bench_fn(py_running_max, py_list_50k)
t_mj_rm = bench_fn(mojo_rm, py_list_50k)
print(f"1. Running Max:")
print(f"   - Pure Python               : {t_py_rm:.3f} ms")
print(f"   - Current Mojo (via FFI)    : {t_mj_rm:.3f} ms")

# Count Greater
t_py_cg = bench_fn(py_count_greater, py_list_50k, 0.0)
t_mj_cg = bench_fn(mojo_cg, py_list_50k, 0.0)
print(f"2. Count Greater:")
print(f"   - Pure Python               : {t_py_cg:.3f} ms")
print(f"   - Current Mojo (via FFI)    : {t_mj_cg:.3f} ms")

# SMA
t_py_sma = bench_fn(py_sma, py_list_50k, 50)
t_mj_sma = bench_fn(mojo_sma, py_list_50k, 50)
print(f"3. Simple Moving Average:")
print(f"   - Pure Python               : {t_py_sma:.3f} ms")
print(f"   - Current Mojo (via FFI)    : {t_mj_sma:.3f} ms")

# Now isolate buffer conversions
t_in = bench_fn(lambda l: array.array('d', l), py_list_50k)
arr_tmp = array.array('d', py_list_50k)
t_out = bench_fn(lambda a: a.tolist(), arr_tmp)
print(f"\nBuffer conversion breakdown:")
print(f"   - list -> array.array('d')  : {t_in:.3f} ms")
print(f"   - array.array('d') -> list  : {t_out:.3f} ms")
print(f"   - Total conversion cost     : {t_in + t_out:.3f} ms")
