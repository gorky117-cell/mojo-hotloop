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
def py_quant_backtest(ticks: int, initial_price: float, trailing_pct: float, stop_pct: float) -> float:
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

@numba.njit(cache=True)
def numba_quant_backtest(ticks: int, initial_price: float, trailing_pct: float, stop_pct: float) -> float:
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
def py_sum_powers(n: int, p: int) -> int:
    total: int = 0
    for i in range(1, n + 1):
        total += i ** p
    return total

@numba.njit(cache=True)
def numba_sum_powers(n: int, p: int) -> int:
    total: int = 0
    for i in range(1, n + 1):
        total += i ** p
    return total

# 3. Collatz Steps
from audit.bench_collatz.original import collatz_steps as mojo_collatz
def py_collatz_steps(n: int) -> int:
    steps: int = 0
    curr: int = n
    while curr > 1:
        if curr % 2 == 0:
            curr = curr // 2
        else:
            curr = 3 * curr + 1
        steps += 1
    return steps

@numba.njit(cache=True)
def numba_collatz_steps(n: int) -> int:
    steps: int = 0
    curr: int = n
    while curr > 1:
        if curr % 2 == 0:
            curr = curr // 2
        else:
            curr = 3 * curr + 1
        steps += 1
    return steps

# 4. Running Max
from audit.unseen_cases.running_max.original import running_max as mojo_running_max
def py_running_max(values: list[float]) -> list[float]:
    if len(values) == 0:
        return []
    current_max: float = values[0]
    result: list[float] = []
    for v in values:
        if v > current_max:
            current_max = v
        result.append(current_max)
    return result

@numba.njit(cache=True)
def numba_running_max(values: np.ndarray) -> np.ndarray:
    n = len(values)
    if n == 0:
        return np.empty(0, dtype=np.float64)
    res = np.empty(n, dtype=np.float64)
    cur = values[0]
    for i in range(n):
        v = values[i]
        if v > cur:
            cur = v
        res[i] = cur
    return res

# 5. Count Greater
from audit.unseen_cases.count_greater.original import count_greater as mojo_count_greater
def py_count_greater(values: list[float], threshold: float) -> int:
    count: int = 0
    for v in values:
        if v > threshold:
            count += 1
    return count

@numba.njit(cache=True)
def numba_count_greater(values: np.ndarray, threshold: float) -> int:
    count = 0
    for i in range(len(values)):
        if values[i] > threshold:
            count += 1
    return count

# 6. Simple Moving Average
from audit.unseen_cases.simple_moving_average.original import simple_moving_average as mojo_sma
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

@numba.njit(cache=True)
def numba_sma(values: np.ndarray, window: int) -> np.ndarray:
    n = len(values)
    if n < window or window <= 0:
        return np.empty(0, dtype=np.float64)
    out_len = n - window + 1
    res = np.empty(out_len, dtype=np.float64)
    w_sum = 0.0
    for i in range(window):
        w_sum += values[i]
    res[0] = w_sum / window
    idx = 1
    for i in range(window, n):
        w_sum += values[i] - values[i - window]
        res[idx] = w_sum / window
        idx += 1
    return res

def measure_benchmark(name, py_fn, py_args, nb_fn, nb_args, mj_fn, mj_args, iters=10, warmup=2):
    print(f"\n>>> Benchmarking Workload: {name} (trials=5, iters={iters})")

    # Warmup
    for _ in range(warmup):
        py_fn(*py_args)
        nb_fn(*nb_args)
        mj_fn(*mj_args)

    assert getattr(mj_fn, "_last_backend", "") == "native", f"Mojo function {name} did not execute natively!"

    def run_trials(fn, args, count):
        trials = []
        for _ in range(5):
            t0 = time.perf_counter_ns()
            for _ in range(count):
                fn(*args)
            t1 = time.perf_counter_ns()
            ms = (t1 - t0) / count / 1_000_000.0
            trials.append(ms)
        return trials

    py_iters = max(1, iters // 5) if "Quant" in name or "Running" in name or "Average" in name else iters
    py_trials = run_trials(py_fn, py_args, py_iters)
    nb_trials = run_trials(nb_fn, nb_args, iters)
    mj_trials = run_trials(mj_fn, mj_args, iters)

    def stats(ts):
        avg = sum(ts) / len(ts)
        return {"avg_ms": avg, "min_ms": min(ts), "max_ms": max(ts), "trials_ms": ts}

    py_stat = stats(py_trials)
    nb_stat = stats(nb_trials)
    mj_stat = stats(mj_trials)

    speedup_vs_py = py_stat["avg_ms"] / mj_stat["avg_ms"] if mj_stat["avg_ms"] > 0 else 0
    speedup_vs_nb = nb_stat["avg_ms"] / mj_stat["avg_ms"] if mj_stat["avg_ms"] > 0 else 0

    print(f"  Pure Python     : avg = {py_stat['avg_ms']:.4f} ms | min = {py_stat['min_ms']:.4f} ms")
    print(f"  Numba (warmed)  : avg = {nb_stat['avg_ms']:.4f} ms | min = {nb_stat['min_ms']:.4f} ms")
    print(f"  Mojo @hotloop   : avg = {mj_stat['avg_ms']:.4f} ms | min = {mj_stat['min_ms']:.4f} ms")
    print(f"  Speedup vs Py   : {speedup_vs_py:.2f}x")
    print(f"  Speedup vs Numba: {speedup_vs_nb:.2f}x")

    return {
        "name": name,
        "python": py_stat,
        "numba": nb_stat,
        "mojo_hotloop": mj_stat,
        "speedup_vs_python": speedup_vs_py,
        "speedup_vs_numba": speedup_vs_nb,
    }

def main():
    rng = random.Random(42)
    results = []

    # 1. Quant Backtest (100k ticks)
    res_1 = measure_benchmark(
        "Quant Backtest (100k ticks)",
        py_quant_backtest, (100000, 100.0, 0.05, 0.001),
        numba_quant_backtest, (100000, 100.0, 0.05, 0.001),
        mojo_quant, (100000, 100.0, 0.05, 0.001),
        iters=20, warmup=3
    )
    results.append(res_1)

    # 2. Sum Powers (n=10k, p=2)
    res_2 = measure_benchmark(
        "Sum Powers (n=10k, p=2)",
        py_sum_powers, (10000, 2),
        numba_sum_powers, (10000, 2),
        mojo_sum_powers, (10000, 2),
        iters=200, warmup=10
    )
    results.append(res_2)

    # 3. Collatz Steps (n=989,345,275)
    res_3 = measure_benchmark(
        "Collatz Steps (n=989,345,275)",
        py_collatz_steps, (989345275,),
        numba_collatz_steps, (989345275,),
        mojo_collatz, (989345275,),
        iters=200, warmup=10
    )
    results.append(res_3)

    # Prepare shared data for collections
    data_50k_py = [rng.uniform(-1000.0, 1000.0) for _ in range(50000)]
    data_50k_np = np.array(data_50k_py, dtype=np.float64)

    data_100k_py = [rng.uniform(-1000.0, 1000.0) for _ in range(100000)]
    data_100k_np = np.array(data_100k_py, dtype=np.float64)

    # 4. Running Max (50k floats)
    res_4 = measure_benchmark(
        "Running Max (50k floats)",
        py_running_max, (data_50k_py,),
        numba_running_max, (data_50k_np,),
        mojo_running_max, (data_50k_py,),
        iters=15, warmup=2
    )
    results.append(res_4)

    # 5. Count Greater (100k floats)
    res_5 = measure_benchmark(
        "Count Greater (100k floats)",
        py_count_greater, (data_100k_py, 0.0),
        numba_count_greater, (data_100k_np, 0.0),
        mojo_count_greater, (data_100k_py, 0.0),
        iters=20, warmup=2
    )
    results.append(res_5)

    # 6. Simple Moving Average (50k floats, win=100)
    res_6 = measure_benchmark(
        "Simple Moving Average (50k floats, win=100)",
        py_sma, (data_50k_py, 100),
        numba_sma, (data_50k_np, 100),
        mojo_sma, (data_50k_py, 100),
        iters=15, warmup=2
    )
    results.append(res_6)

    # Save to JSON
    out_path = os.path.join(repo_root, "audit", "phase_b_benchmark_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[+] Full benchmark results saved to {out_path}")

if __name__ == "__main__":
    main()
