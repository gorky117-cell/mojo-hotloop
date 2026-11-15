import gc
import json
import math
import os
import random
import sys
import time
from typing import Callable, Dict, List

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

import numpy as np
from numba import njit
from examples.ar_spatial.original import find_closest_point_to_ray
from examples.ar_spatial.verify import numpy_closest_point_to_ray

@njit
def numba_closest_point_to_ray(
    xs: np.ndarray,
    ys: np.ndarray,
    zs: np.ndarray,
    ray_ox: float,
    ray_oy: float,
    ray_oz: float,
    ray_dx: float,
    ray_dy: float,
    ray_dz: float,
) -> int:
    n = len(xs)
    if n == 0 or len(ys) != n or len(zs) != n:
        return -1

    dir_len_sq = ray_dx * ray_dx + ray_dy * ray_dy + ray_dz * ray_dz
    if dir_len_sq <= 0.0:
        return -1

    inv_len = 1.0 / math.sqrt(dir_len_sq)
    dx = ray_dx * inv_len
    dy = ray_dy * inv_len
    dz = ray_dz * inv_len

    best_idx = -1
    min_dist_sq = 1e30

    for i in range(n):
        vx = xs[i] - ray_ox
        vy = ys[i] - ray_oy
        vz = zs[i] - ray_oz

        t = vx * dx + vy * dy + vz * dz
        if t < 0.0:
            t = 0.0

        wx = vx - t * dx
        wy = vy - t * dy
        wz = vz - t * dz

        dist_sq = wx * wx + wy * wy + wz * wz
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_idx = i

    return best_idx

def generate_cloud(n_points: int):
    rng = random.Random(42)
    xs = [rng.uniform(-20.0, 20.0) for _ in range(n_points)]
    ys = [rng.uniform(-20.0, 20.0) for _ in range(n_points)]
    zs = [rng.uniform(1.0, 50.0) for _ in range(n_points)]
    np_xs = np.array(xs, dtype=np.float64)
    np_ys = np.array(ys, dtype=np.float64)
    np_zs = np.array(zs, dtype=np.float64)
    ray = (0.0, 0.0, 0.0, 0.1, 0.2, 1.0)
    return xs, ys, zs, np_xs, np_ys, np_zs, ray

def time_callable(fn: Callable, args: tuple, iters: int) -> float:
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(*args)
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

def main():
    print("=" * 65)
    print("STAGE D7 BENCHMARK: AR SPATIAL 3D (RAY POINT CLOUD INTERSECTION)")
    print("=" * 65)

    py_ref = find_closest_point_to_ray._original
    direct_mojo = find_closest_point_to_ray._compiled
    wrapped_mojo = find_closest_point_to_ray

    workloads = [
        ("small", 100, 2000, "Small cloud (100 vertices)"),
        ("medium", 1000, 200, "Medium cloud (1,000 vertices)"),
        ("large", 10000, 20, "Large cloud (10,000 vertices)"),
    ]

    # Warmup Numba JIT
    d_xs, d_ys, d_zs, d_npx, d_npy, d_npz, d_ray = generate_cloud(10)
    numba_closest_point_to_ray(d_npx, d_npy, d_npz, *d_ray)

    results = {}

    for w_key, n_points, iters, desc in workloads:
        xs, ys, zs, np_xs, np_ys, np_zs, ray = generate_cloud(n_points)
        py_args = (xs, ys, zs, *ray)
        np_args = (np_xs, np_ys, np_zs, *ray)
        numba_args = (np_xs, np_ys, np_zs, *ray)

        # Warmup
        for _ in range(min(iters // 5 + 2, 20)):
            py_ref(*py_args)
            numpy_closest_point_to_ray(*np_args)
            numba_closest_point_to_ray(*numba_args)
            direct_mojo(*np_args)
            wrapped_mojo(*np_args)

        trials_py = []
        trials_np = []
        trials_numba = []
        trials_direct = []
        trials_wrapped = []

        for _ in range(5):
            trials_py.append(time_callable(py_ref, py_args, iters))
            trials_np.append(time_callable(numpy_closest_point_to_ray, np_args, iters))
            trials_numba.append(time_callable(numba_closest_point_to_ray, numba_args, iters))
            trials_direct.append(time_callable(direct_mojo, np_args, iters))
            trials_wrapped.append(time_callable(wrapped_mojo, np_args, iters))

        py_mean = sum(trials_py) / len(trials_py)
        np_mean = sum(trials_np) / len(trials_np)
        numba_mean = sum(trials_numba) / len(trials_numba)
        direct_mean = sum(trials_direct) / len(trials_direct)
        wrapped_mean = sum(trials_wrapped) / len(trials_wrapped)

        speedup_vs_py = py_mean / wrapped_mean if wrapped_mean > 0 else 0
        speedup_vs_np = np_mean / wrapped_mean if wrapped_mean > 0 else 0
        speedup_vs_numba = numba_mean / wrapped_mean if wrapped_mean > 0 else 0

        print(f"\n[{desc}] (iters={iters})")
        print(f"  Python 3.12:           {py_mean * 1000:8.2f} µs  (p50: {sorted(trials_py)[2] * 1000:8.2f} µs)")
        print(f"  NumPy Vector:          {np_mean * 1000:8.2f} µs  (p50: {sorted(trials_np)[2] * 1000:8.2f} µs) -> {np_mean / wrapped_mean:5.2f}x vs Mojo @hotloop")
        print(f"  Numba (@njit):         {numba_mean * 1000:8.2f} µs  (p50: {sorted(trials_numba)[2] * 1000:8.2f} µs) -> {numba_mean / wrapped_mean:5.2f}x vs Mojo @hotloop")
        print(f"  Mojo Direct (ndarray): {direct_mean * 1000:8.2f} µs  (p50: {sorted(trials_direct)[2] * 1000:8.2f} µs)")
        print(f"  Mojo @hotloop(ndarray):{wrapped_mean * 1000:8.2f} µs  (p50: {sorted(trials_wrapped)[2] * 1000:8.2f} µs) -> {speedup_vs_py:5.2f}x vs Python")

        results[w_key] = {
            "desc": desc,
            "points": n_points,
            "py_ms": py_mean,
            "numpy_ms": np_mean,
            "numba_ms": numba_mean,
            "mojo_direct_ms": direct_mean,
            "mojo_wrapped_ms": wrapped_mean,
            "speedup_vs_py": speedup_vs_py,
            "speedup_vs_np": speedup_vs_np,
            "speedup_vs_numba": speedup_vs_numba,
        }

    out_file = "/home/gaurav/mojo-hotloop/examples/ar_spatial/bench_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Stage D7 benchmarks saved to {out_file}")

if __name__ == "__main__":
    main()
