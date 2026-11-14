import json
import math
import os
import random
import sys
import time
import numba
import numpy as np

repo_root = "/home/gaurav/mojo-hotloop"
sys.path.insert(0, repo_root)

# 1. Quant Backtest
from examples.quant_backtest.original import stateful_trailing_backtest as mojo_quant
from examples.quant_backtest.original import stateful_trailing_backtest as _quant_wrapped
py_quant = _quant_wrapped._original

@numba.njit(cache=True)
def numba_quant(ticks: int, initial_price: float, trailing_pct: float, stop_pct: float) -> float:
    price = initial_price
    peak_price = initial_price
    position = 1
    cash = 0.0
    cooldown = 0
    rng_state = 123456789
    for i in range(ticks):
        rng_state = (rng_state * 1664525 + 1013904223) % 2147483648
        ret = (rng_state / 2147483648.0 - 0.5) * 0.02
        price = price * (1.0 + ret)
        if cooldown > 0:
            cooldown -= 1
            continue
        if position == 1:
            if price > peak_price:
                peak_price = price
            drop = (peak_price - price) / peak_price
            if drop >= trailing_pct or price <= initial_price * (1.0 - stop_pct):
                cash = price * 0.999
                position = 0
                cooldown = 10
        else:
            if price < peak_price * 0.95:
                position = 1
                peak_price = price
                cash = 0.0
                cooldown = 5
    if position == 1:
        return price
    return cash

# 2. Sum Powers
from audit.bench_sum_powers.original import sum_powers as mojo_sum_powers
py_sum_powers = mojo_sum_powers._original

@numba.njit(cache=True)
def numba_sum_powers(n: int, p: int) -> int:
    total = 0
    for i in range(1, n + 1):
        total += i ** p
    return total

# 3. Collatz Steps
from audit.bench_collatz.original import collatz_steps as mojo_collatz
py_collatz = mojo_collatz._original

@numba.njit(cache=True)
def numba_collatz(n: int) -> int:
    steps = 0
    val = n
    while val > 1:
        if val % 2 == 0:
            val = val // 2
        else:
            val = (3 * val) + 1
        steps += 1
    return steps

# 4. Collections Category A (Python List in/out)
from audit.unseen_cases.running_max.original import running_max as rm_wrapped
from audit.unseen_cases.count_greater.original import count_greater as cg_wrapped
from audit.unseen_cases.simple_moving_average.original import simple_moving_average as sma_wrapped

py_rm = rm_wrapped._original
py_cg = cg_wrapped._original
py_sma = sma_wrapped._original

# 5. Collections Category B (NumPy zero-copy contiguous array)
from hotloop.decorator import _load_native_module
mod_np, _ = _load_native_module(os.path.join(repo_root, "audit/test_numpy_all.so"))
assert mod_np is not None, "Failed to load test_numpy_all.so"
np_mojo_rm = getattr(mod_np, "running_max")
np_mojo_cg = getattr(mod_np, "count_greater")
np_mojo_sma = getattr(mod_np, "simple_moving_average")
np_mojo_sum = getattr(mod_np, "sum_array")

@numba.njit(cache=True)
def nb_running_max(arr):
    n = len(arr)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    cur = arr[0]
    out[0] = cur
    for i in range(1, n):
        v = arr[i]
        if v > cur:
            cur = v
        out[i] = cur
    return out

@numba.njit(cache=True)
def nb_count_greater(arr, thresh):
    c = 0
    for i in range(len(arr)):
        if arr[i] > thresh:
            c += 1
    return c

@numba.njit(cache=True)
def nb_sma(arr, window):
    n = len(arr)
    if n < window or window <= 0:
        return np.empty(0, dtype=np.float64)
    out = np.empty(n - window + 1, dtype=np.float64)
    s = 0.0
    for i in range(window):
        s += arr[i]
    out[0] = s / window
    idx = 1
    for i in range(window, n):
        s += arr[i] - arr[i - window]
        out[idx] = s / window
        idx += 1
    return out

@numba.njit(cache=True)
def nb_sum(arr):
    s = 0.0
    for i in range(len(arr)):
        s += arr[i]
    return s

def compute_stats(trials_ms):
    sorted_ts = sorted(trials_ms)
    mean_val = sum(trials_ms) / len(trials_ms)
    p50_val = sorted_ts[len(sorted_ts) // 2]
    p95_val = sorted_ts[int(math.ceil(0.95 * len(sorted_ts))) - 1]
    variance = sum((x - mean_val) ** 2 for x in trials_ms) / len(trials_ms)
    std_val = math.sqrt(variance)
    cv_pct = (std_val / mean_val * 100.0) if mean_val > 0 else 0.0
    return {
        "trials_ms": trials_ms,
        "mean_ms": mean_val,
        "p50_ms": p50_val,
        "p95_ms": p95_val,
        "min_ms": sorted_ts[0],
        "max_ms": sorted_ts[-1],
        "std_ms": std_val,
        "cv_pct": cv_pct,
    }

def run_5_trials(fn, args, iters):
    trials = []
    for _ in range(5):
        t0 = time.perf_counter_ns()
        for _ in range(iters):
            fn(*args)
        t1 = time.perf_counter_ns()
        ms = (t1 - t0) / iters / 1e6
        trials.append(ms)
    return compute_stats(trials)

def benchmark_workload(name, py_fn, py_args, py_iters, nb_fn, nb_args, nb_iters, mj_fn, mj_args, mj_iters, baseline_name="Python"):
    print(f"\n=================================================================")
    print(f"Benchmarking: {name}")
    print(f"=================================================================")

    # Warmup
    for _ in range(3):
        if py_fn: py_fn(*py_args)
        if nb_fn: nb_fn(*nb_args)
        if mj_fn: mj_fn(*mj_args)

    backend = getattr(mj_fn, "_last_backend", "direct_native")

    py_stats = run_5_trials(py_fn, py_args, py_iters) if py_fn else None
    nb_stats = run_5_trials(nb_fn, nb_args, nb_iters) if nb_fn else None
    mj_stats = run_5_trials(mj_fn, mj_args, mj_iters)

    speedup_py = (py_stats["mean_ms"] / mj_stats["mean_ms"]) if py_stats and mj_stats["mean_ms"] > 0 else 0.0
    speedup_nb = (nb_stats["mean_ms"] / mj_stats["mean_ms"]) if nb_stats and mj_stats["mean_ms"] > 0 else 0.0

    if speedup_py > 1.05:
        verdict = "FASTER"
    elif speedup_py >= 0.95:
        verdict = "APPROXIMATELY EQUAL"
    else:
        verdict = "SLOWER"

    print(f"Default Backend       : {backend}")
    if py_stats:
        print(f"Python ({baseline_name}) : mean = {py_stats['mean_ms']:.4f} ms | p50 = {py_stats['p50_ms']:.4f} ms | p95 = {py_stats['p95_ms']:.4f} ms | CV = {py_stats['cv_pct']:.1f}%")
    if nb_stats:
        print(f"Numba (warmed)        : mean = {nb_stats['mean_ms']:.4f} ms | p50 = {nb_stats['p50_ms']:.4f} ms | p95 = {nb_stats['p95_ms']:.4f} ms | CV = {nb_stats['cv_pct']:.1f}%")
    print(f"Mojo Hotloop          : mean = {mj_stats['mean_ms']:.4f} ms | p50 = {mj_stats['p50_ms']:.4f} ms | p95 = {mj_stats['p95_ms']:.4f} ms | CV = {mj_stats['cv_pct']:.1f}%")
    print(f"Speedup vs Python     : {speedup_py:.2f}x [{verdict}]")
    if nb_stats:
        print(f"Speedup vs Numba      : {speedup_nb:.2f}x")

    return {
        "name": name,
        "default_backend": backend,
        "python": py_stats,
        "numba": nb_stats,
        "mojo": mj_stats,
        "speedup_vs_python": speedup_py,
        "speedup_vs_numba": speedup_nb,
        "verdict": verdict,
    }

def main():
    results = []

    # 1. Quant Backtest (100k ticks)
    results.append(benchmark_workload(
        "Quant Backtest (100,000 ticks)",
        py_quant, (100000, 100.0, 0.05, 0.001), 3,
        numba_quant, (100000, 100.0, 0.05, 0.001), 20,
        mojo_quant, (100000, 100.0, 0.05, 0.001), 20
    ))

    # 2. Sum Powers (n=10k, p=2)
    results.append(benchmark_workload(
        "Sum Powers (n=10,000, p=2)",
        py_sum_powers, (10000, 2), 50,
        numba_sum_powers, (10000, 2), 200,
        mojo_sum_powers, (10000, 2), 200
    ))

    # 3. Collatz Steps (n=989,345,275)
    results.append(benchmark_workload(
        "Collatz Steps (n=989,345,275)",
        py_collatz, (989345275,), 200,
        numba_collatz, (989345275,), 1000,
        mojo_collatz, (989345275,), 1000
    ))

    # Prepare data for collections
    rng = random.Random(42)
    data_50k_py = [rng.uniform(-1000.0, 1000.0) for _ in range(50000)]
    data_50k_np = np.array(data_50k_py, dtype=np.float64)

    # 4. Running Max — Category A: Python List (Default Dispatch)
    results.append(benchmark_workload(
        "Running Max (50k floats) [Category A: Python list, Default Dispatch]",
        py_rm, (data_50k_py,), 15,
        None, (), 0,
        rm_wrapped, (data_50k_py,), 15
    ))

    # 5. Running Max — Category A: Python List (Forced Native)
    from hotloop import hotloop
    forced_rm = hotloop(py_rm, force_native=True)
    results.append(benchmark_workload(
        "Running Max (50k floats) [Category A: Python list, Forced Native]",
        py_rm, (data_50k_py,), 15,
        None, (), 0,
        forced_rm, (data_50k_py,), 10
    ))

    # 6. Running Max — Category B: NumPy Array (Zero-Copy)
    results.append(benchmark_workload(
        "Running Max (50k floats) [Category B: NumPy Array Zero-Copy]",
        np.maximum.accumulate, (data_50k_np,), 50,
        nb_running_max, (data_50k_np,), 50,
        np_mojo_rm, (data_50k_np,), 50,
        baseline_name="NumPy accumulate"
    ))

    # 7. Count Greater — Category A: Python List (Default Dispatch)
    results.append(benchmark_workload(
        "Count Greater (50k floats) [Category A: Python list, Default Dispatch]",
        py_cg, (data_50k_py, 0.0), 30,
        None, (), 0,
        cg_wrapped, (data_50k_py, 0.0), 30
    ))

    # 8. Count Greater — Category A: Python List (Forced Native)
    forced_cg = hotloop(py_cg, force_native=True)
    results.append(benchmark_workload(
        "Count Greater (50k floats) [Category A: Python list, Forced Native]",
        py_cg, (data_50k_py, 0.0), 30,
        None, (), 0,
        forced_cg, (data_50k_py, 0.0), 20
    ))

    # 9. Count Greater — Category B: NumPy Array (Zero-Copy)
    results.append(benchmark_workload(
        "Count Greater (50k floats) [Category B: NumPy Array Zero-Copy]",
        lambda arr, t: np.count_nonzero(arr > t), (data_50k_np, 0.0), 50,
        nb_count_greater, (data_50k_np, 0.0), 50,
        np_mojo_cg, (data_50k_np, 0.0), 50,
        baseline_name="NumPy count_nonzero"
    ))

    # 10. Simple Moving Average — Category A: Python List (Default Dispatch)
    results.append(benchmark_workload(
        "Simple Moving Average (50k floats, w=50) [Category A: Python list, Default Dispatch]",
        py_sma, (data_50k_py, 50), 10,
        None, (), 0,
        sma_wrapped, (data_50k_py, 50), 10
    ))

    # 11. Simple Moving Average — Category A: Python List (Forced Native)
    forced_sma = hotloop(py_sma, force_native=True)
    results.append(benchmark_workload(
        "Simple Moving Average (50k floats, w=50) [Category A: Python list, Forced Native]",
        py_sma, (data_50k_py, 50), 10,
        None, (), 0,
        forced_sma, (data_50k_py, 50), 10
    ))

    # 12. Simple Moving Average — Category B: NumPy Array (Zero-Copy)
    def np_sma_conv(arr, w):
        return np.convolve(arr, np.ones(w)/w, mode='valid')
    results.append(benchmark_workload(
        "Simple Moving Average (50k floats, w=50) [Category B: NumPy Array Zero-Copy]",
        np_sma_conv, (data_50k_np, 50), 15,
        nb_sma, (data_50k_np, 50), 50,
        np_mojo_sma, (data_50k_np, 50), 50,
        baseline_name="NumPy convolve"
    ))

    # 13. Sum Reduction (1,000,000 floats)
    data_1m_np = np.ones(1000000, dtype=np.float64)
    results.append(benchmark_workload(
        "Sum Reduction (1,000,000 floats) [Category B: NumPy Zero-Copy]",
        np.sum, (data_1m_np,), 20,
        nb_sum, (data_1m_np,), 20,
        np_mojo_sum, (data_1m_np,), 20,
        baseline_name="NumPy sum"
    ))

    out_file = os.path.join(repo_root, "audit/phase_b1_benchmark_results.json")
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[+] Complete benchmark results saved to {out_file}")

if __name__ == "__main__":
    main()
