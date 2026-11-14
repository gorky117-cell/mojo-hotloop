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
from examples.geo_distance.original import accumulate_haversine_distance

@njit
def numba_haversine(lats: np.ndarray, lons: np.ndarray) -> float:
    n = len(lats)
    if n <= 1:
        return 0.0

    total_dist = 0.0
    r = 6371.0
    rad_factor = 3.141592653589793 / 180.0

    for i in range(1, n):
        lat1 = lats[i - 1] * rad_factor
        lon1 = lons[i - 1] * rad_factor
        lat2 = lats[i] * rad_factor
        lon2 = lons[i] * rad_factor

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        half_dlat = dlat * 0.5
        half_dlon = dlon * 0.5

        sin_dlat = math.sin(half_dlat)
        sin_dlon = math.sin(half_dlon)

        a = sin_dlat * sin_dlat + math.cos(lat1) * math.cos(lat2) * sin_dlon * sin_dlon
        if a > 1.0:
            a = 1.0
        elif a < 0.0:
            a = 0.0

        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        total_dist += r * c

    return total_dist

def numpy_haversine(lat_arr: np.ndarray, lon_arr: np.ndarray) -> float:
    if len(lat_arr) <= 1:
        return 0.0
    lat_r = np.radians(lat_arr)
    lon_r = np.radians(lon_arr)
    dlat = np.diff(lat_r)
    dlon = np.diff(lon_r)
    a = np.sin(dlat * 0.5)**2 + np.cos(lat_r[:-1]) * np.cos(lat_r[1:]) * np.sin(dlon * 0.5)**2
    a = np.clip(a, 0.0, 1.0)
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(np.sum(6371.0 * c))

def generate_trail(n_points: int) -> tuple[List[float], List[float], np.ndarray, np.ndarray]:
    rng = random.Random(42)
    cur_lat = 12.9716
    cur_lon = 77.5946
    lats = [cur_lat]
    lons = [cur_lon]
    for _ in range(n_points - 1):
        cur_lat += rng.uniform(-0.01, 0.01)
        cur_lon += rng.uniform(-0.01, 0.01)
        lats.append(cur_lat)
        lons.append(cur_lon)
    return lats, lons, np.array(lats, dtype=np.float64), np.array(lons, dtype=np.float64)

def time_callable(fn: Callable, a, b, iters: int) -> float:
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(a, b)
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

def main():
    print("=" * 65)
    print("STAGE D6 BENCHMARK: GEO DISTANCE (HAVERSINE)")
    print("=" * 65)

    py_ref = accumulate_haversine_distance._original
    direct_mojo = accumulate_haversine_distance._compiled
    os.environ["HOTLOOP_FORCE_NATIVE"] = "1"
    wrapped_mojo = accumulate_haversine_distance

    workloads = [
        ("short", 100, 2000, "Short trail (100 waypoints)"),
        ("medium", 1000, 200, "Medium trail (1,000 waypoints)"),
        ("large", 10000, 20, "Long route (10,000 waypoints)"),
    ]

    # Warmup Numba JIT
    dummy_lats, dummy_lons, dummy_np_lat, dummy_np_lon = generate_trail(10)
    numba_haversine(dummy_np_lat, dummy_np_lon)

    results = {}

    for w_key, n_points, iters, desc in workloads:
        lats, lons, np_lats, np_lons = generate_trail(n_points)

        # Warmup
        for _ in range(min(iters // 5 + 2, 20)):
            py_ref(lats, lons)
            numpy_haversine(np_lats, np_lons)
            numba_haversine(np_lats, np_lons)
            direct_mojo(lats, lons)
            wrapped_mojo(lats, lons)

        trials_py = []
        trials_np = []
        trials_numba = []
        trials_direct = []
        trials_wrapped = []

        for _ in range(5):
            trials_py.append(time_callable(py_ref, lats, lons, iters))
            trials_np.append(time_callable(numpy_haversine, np_lats, np_lons, iters))
            trials_numba.append(time_callable(numba_haversine, np_lats, np_lons, iters))
            trials_direct.append(time_callable(direct_mojo, lats, lons, iters))
            trials_wrapped.append(time_callable(wrapped_mojo, lats, lons, iters))

        py_mean = sum(trials_py) / len(trials_py)
        np_mean = sum(trials_np) / len(trials_np)
        numba_mean = sum(trials_numba) / len(trials_numba)
        direct_mean = sum(trials_direct) / len(trials_direct)
        wrapped_mean = sum(trials_wrapped) / len(trials_wrapped)

        speedup_vs_py = py_mean / wrapped_mean if wrapped_mean > 0 else 0
        speedup_vs_np = np_mean / wrapped_mean if wrapped_mean > 0 else 0
        speedup_vs_numba = numba_mean / wrapped_mean if wrapped_mean > 0 else 0

        print(f"\n[{desc}] (iters={iters})")
        print(f"  Python 3.12:    {py_mean * 1000:8.2f} µs  (p50: {sorted(trials_py)[2] * 1000:8.2f} µs)")
        print(f"  NumPy Vector:   {np_mean * 1000:8.2f} µs  (p50: {sorted(trials_np)[2] * 1000:8.2f} µs) -> {np_mean / wrapped_mean:5.2f}x vs Mojo @hotloop")
        print(f"  Numba (@njit):  {numba_mean * 1000:8.2f} µs  (p50: {sorted(trials_numba)[2] * 1000:8.2f} µs) -> {numba_mean / wrapped_mean:5.2f}x vs Mojo @hotloop")
        print(f"  Mojo Direct:    {direct_mean * 1000:8.2f} µs  (p50: {sorted(trials_direct)[2] * 1000:8.2f} µs)")
        print(f"  Mojo @hotloop:  {wrapped_mean * 1000:8.2f} µs  (p50: {sorted(trials_wrapped)[2] * 1000:8.2f} µs) -> {speedup_vs_py:5.2f}x vs Python")

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

    out_file = "/home/gaurav/mojo-hotloop/examples/geo_distance/bench_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Stage D6 benchmarks saved to {out_file}")

if __name__ == "__main__":
    main()
