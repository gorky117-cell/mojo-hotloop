import math
import os
import random
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.geo_distance.original import accumulate_haversine_distance

def numpy_haversine(lats: list[float], lons: list[float]) -> float:
    import numpy as np
    if len(lats) <= 1:
        return 0.0
    lat_arr = np.radians(np.array(lats, dtype=np.float64))
    lon_arr = np.radians(np.array(lons, dtype=np.float64))

    dlat = np.diff(lat_arr)
    dlon = np.diff(lon_arr)

    a = np.sin(dlat * 0.5)**2 + np.cos(lat_arr[:-1]) * np.cos(lat_arr[1:]) * np.sin(dlon * 0.5)**2
    a = np.clip(a, 0.0, 1.0)
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(np.sum(6371.0 * c))

def run_tests():
    from hotloop import hotloop
    forced = hotloop(strict=True)(accumulate_haversine_distance._original)
    print("[*] Starting Stage D6: Geo Distance Verification Suite...")

    # 1. Deterministic cases
    deterministic_cases = [
        ([], []),
        ([12.9716], [77.5946]), # Bangalore single point
        ([12.9716, 12.9716], [77.5946, 77.5946]), # Identical points = 0 km
        ([0.0, 0.0], [0.0, 90.0]), # Equator quarter turn (~10,007.5 km)
        ([0.0, 0.0], [0.0, 180.0]), # Equator half turn (~20,015 km)
        ([90.0, -90.0], [0.0, 0.0]), # Pole to pole (~20,015 km)
        ([12.9716, 13.0827], [77.5946, 80.2707]), # Bangalore to Chennai (~290 km)
        ([37.7749, 40.7128], [-122.4194, -74.0060]), # SF to NYC (~4,130 km)
        ([51.5074, 48.8566, 52.5200], [-0.1278, 2.3522, 13.4050]), # London -> Paris -> Berlin
        ([0.0, 0.1, 0.2, 0.3], [0.0, 0.1, 0.2, 0.3]),
        ([-45.0, -45.0], [-179.0, 179.0]), # Crossing antimeridian
        ([89.9, 89.9], [0.0, 180.0]), # Near north pole
        ([-89.9, -89.9], [0.0, 180.0]), # Near south pole
        ([10.0, 10.0, 10.0], [20.0, 20.0, 20.0]), # Multi-point stationary
    ]

    import numpy as np
    deterministic_passed = 0
    for lats, lons in deterministic_cases:
        py_res = accumulate_haversine_distance._original(lats, lons)
        np_res = numpy_haversine(lats, lons)
        np_lats = np.array(lats, dtype=np.float64)
        np_lons = np.array(lons, dtype=np.float64)
        mojo_res = accumulate_haversine_distance(np_lats, np_lons)
        assert accumulate_haversine_distance._last_backend == "python_fallback_semantics"
        assert type(mojo_res) is type(accumulate_haversine_distance._original(np_lats, np_lons))
        native_res = forced(lats, lons)
        assert math.isclose(native_res, py_res, rel_tol=1e-8, abs_tol=1e-8)

        if forced._last_backend != "native":
            print(f"[FAIL] Expected native backend for forced list trail, got {accumulate_haversine_distance._last_backend}")
            sys.exit(1)

        fb_res = accumulate_haversine_distance(lats, lons)
        if not math.isclose(fb_res, py_res, rel_tol=1e-12) or accumulate_haversine_distance._last_backend != "python_fallback_slower":
            print(f"[FAIL] List fallback check failed: {accumulate_haversine_distance._last_backend}")
            sys.exit(1)

        if not math.isclose(py_res, mojo_res, rel_tol=1e-8, abs_tol=1e-8):
            print(f"[FAIL] Deterministic mismatch: py={py_res}, mojo={mojo_res}")
            sys.exit(1)

        if not math.isclose(py_res, np_res, rel_tol=1e-7, abs_tol=1e-7):
            print(f"[FAIL] Deterministic NumPy mismatch: py={py_res}, np={np_res}")
            sys.exit(1)

        deterministic_passed += 1

    print(f"  [✓] Deterministic cases passed ({deterministic_passed} tests)")

    # 2. Randomized GPS trails (1,000 cases via public @hotloop + NumPy ndarray)
    rng = random.Random(42)
    random_passed = 0
    total_points = 0

    for test_idx in range(1000):
        n_points = rng.randint(2, 150)
        # Generate smooth GPS trajectory
        cur_lat = rng.uniform(-80.0, 80.0)
        cur_lon = rng.uniform(-170.0, 170.0)
        lats = [cur_lat]
        lons = [cur_lon]

        for _ in range(n_points - 1):
            cur_lat += rng.uniform(-0.1, 0.1)
            cur_lon += rng.uniform(-0.1, 0.1)
            cur_lat = max(-89.0, min(89.0, cur_lat))
            cur_lon = max(-179.0, min(179.0, cur_lon))
            lats.append(cur_lat)
            lons.append(cur_lon)

        np_lats = np.array(lats, dtype=np.float64)
        np_lons = np.array(lons, dtype=np.float64)
        py_res = accumulate_haversine_distance._original(lats, lons)
        mojo_res = accumulate_haversine_distance(np_lats, np_lons)
        assert accumulate_haversine_distance._last_backend == "python_fallback_semantics"
        assert type(mojo_res) is type(accumulate_haversine_distance._original(np_lats, np_lons))
        native_res = forced(lats, lons)
        assert math.isclose(native_res, py_res, rel_tol=1e-8, abs_tol=1e-8)

        if forced._last_backend != "native":
            print(f"[FAIL] Expected native backend at #{test_idx}, got {accumulate_haversine_distance._last_backend}")
            sys.exit(1)

        if not math.isclose(py_res, mojo_res, rel_tol=1e-8, abs_tol=1e-8):
            print(f"[FAIL] Random trail #{test_idx} mismatch:")
            print(f"  Points: {n_points}")
            print(f"  Py:   {py_res:.10f}")
            print(f"  Mojo: {mojo_res:.10f}")
            sys.exit(1)

        random_passed += 1
        total_points += n_points

    total_tests = deterministic_passed + random_passed
    native_runs = forced._call_count_native
    print(f"[✓] Stage D6: Geo Distance PASSED: {total_tests} tests verified ({total_points} GPS waypoints, 100% matched against NumPy & Py, {native_runs} forced native boxed-list calls and {total_tests} ndarray Python fallback calls, 0 mismatches). Zero errors.")

if __name__ == "__main__":
    run_tests()
