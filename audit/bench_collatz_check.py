import os
import sys
import time
import numba

repo_root = "/home/gaurav/mojo-hotloop"
sys.path.insert(0, repo_root)

from audit.bench_collatz.original import collatz_steps as mojo_collatz

def py_collatz_steps(n: int) -> int:
    steps = 0
    val = n
    while val > 1:
        if val % 2 == 0:
            val = val // 2
        else:
            val = (3 * val) + 1
        steps += 1
    return steps

@numba.njit(cache=True)
def numba_collatz_steps(n: int) -> int:
    steps = 0
    val = n
    while val > 1:
        if val % 2 == 0:
            val = val // 2
        else:
            val = (3 * val) + 1
        steps += 1
    return steps

# Warmup
for _ in range(10):
    py_collatz_steps(989345275)
    numba_collatz_steps(989345275)
    mojo_collatz(989345275)

print("Backend:", mojo_collatz._last_backend)

def run_bench(fn, iters=1000):
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(989345275)
    t1 = time.perf_counter_ns()
    return (t1 - t0) / iters / 1000.0  # microseconds

print("--- Collatz steps latency ---")
py_us = run_bench(py_collatz_steps)
nb_us = run_bench(numba_collatz_steps)
mj_us = run_bench(mojo_collatz)

print(f"Python:       {py_us:.3f} µs")
print(f"Numba warm:   {nb_us:.3f} µs")
print(f"Mojo @hotloop:{mj_us:.3f} µs")
print(f"Speedup vs Py: {py_us / mj_us:.2f}x")
