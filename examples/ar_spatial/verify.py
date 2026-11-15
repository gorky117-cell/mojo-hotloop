import math
import os
import random
import sys

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

import numpy as np
from examples.ar_spatial.original import find_closest_point_to_ray

def numpy_closest_point_to_ray(
    xs: list[float],
    ys: list[float],
    zs: list[float],
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
    d = np.array([ray_dx * inv_len, ray_dy * inv_len, ray_dz * inv_len], dtype=np.float64)
    o = np.array([ray_ox, ray_oy, ray_oz], dtype=np.float64)
    p = np.stack([xs, ys, zs], axis=-1).astype(np.float64)

    v = p - o
    t = np.clip(np.sum(v * d, axis=-1), 0.0, None)
    w = v - t[:, None] * d
    dist_sq = np.sum(w * w, axis=-1)
    return int(np.argmin(dist_sq))

def run_tests():
    print("[*] Starting Stage D7: AR Spatial 3D Verification Suite...")

    # 1. Deterministic cases
    deterministic_cases = [
        ([], [], [], 0.0, 0.0, 0.0, 0.0, 0.0, 1.0), # Empty cloud
        ([1.0], [0.0], [5.0], 0.0, 0.0, 0.0, 0.0, 0.0, 1.0), # Single point
        ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [1.0, 2.0, 3.0], 0.0, 0.0, 0.0, 0.0, 0.0, 1.0), # Collinear points on ray
        ([5.0, -1.0, 2.0], [0.0, 0.0, 0.0], [10.0, 10.0, 10.0], 0.0, 0.0, 0.0, 0.0, 0.0, 1.0), # Off-axis points
        ([0.0, 0.0], [0.0, 0.0], [-5.0, 5.0], 0.0, 0.0, 0.0, 0.0, 0.0, 1.0), # Behind vs ahead
        ([1.0, 2.0], [1.0, 2.0], [1.0, 2.0], 0.0, 0.0, 0.0, 0.0, 0.0, 0.0), # Degenerate ray
        ([10.0, 20.0, 30.0], [10.0, 20.0, 30.0], [10.0, 20.0, 30.0], 5.0, 5.0, 5.0, 1.0, 1.0, 1.0), # Ray along diagonal
        ([100.0, 0.0], [0.0, 100.0], [0.0, 0.0], 0.0, 0.0, 0.0, 1.0, 0.0, 0.0), # Ray along X axis
        ([0.0, 0.0], [100.0, 0.0], [0.0, 100.0], 0.0, 0.0, 0.0, 0.0, 1.0, 0.0), # Ray along Y axis
        ([1.5, -2.5, 3.5], [4.5, -5.5, 6.5], [7.5, -8.5, 9.5], 1.0, 2.0, 3.0, 0.577, 0.577, 0.577),
    ]

    deterministic_passed = 0
    for xs, ys, zs, ox, oy, oz, dx, dy, dz in deterministic_cases:
        py_res = find_closest_point_to_ray._original(xs, ys, zs, ox, oy, oz, dx, dy, dz)
        np_res = numpy_closest_point_to_ray(xs, ys, zs, ox, oy, oz, dx, dy, dz)
        np_xs = np.array(xs, dtype=np.float64)
        np_ys = np.array(ys, dtype=np.float64)
        np_zs = np.array(zs, dtype=np.float64)
        mojo_res = find_closest_point_to_ray(np_xs, np_ys, np_zs, ox, oy, oz, dx, dy, dz)

        if find_closest_point_to_ray._last_backend != "native":
            print(f"[FAIL] Expected native backend for NumPy array, got {find_closest_point_to_ray._last_backend}")
            sys.exit(1)

        # Also check Python list auto-fallback safety
        fb_res = find_closest_point_to_ray(xs, ys, zs, ox, oy, oz, dx, dy, dz)
        if fb_res != py_res or find_closest_point_to_ray._last_backend != "python_fallback_slower":
            print(f"[FAIL] List fallback parity/backend check failed: {find_closest_point_to_ray._last_backend}")
            sys.exit(1)

        if py_res != mojo_res:
            print(f"[FAIL] Deterministic mismatch: py={py_res}, mojo={mojo_res}")
            sys.exit(1)

        if py_res != np_res:
            print(f"[FAIL] Deterministic NumPy mismatch: py={py_res}, np={np_res}")
            sys.exit(1)

        deterministic_passed += 1

    print(f"  [✓] Deterministic cases passed ({deterministic_passed} tests)")

    # 2. Randomized 3D point cloud stress testing (1,000 cases via public @hotloop + NumPy ndarray)
    rng = random.Random(42)
    random_passed = 0
    total_3d_points = 0
    native_before = find_closest_point_to_ray._call_count_native

    for test_idx in range(1000):
        n_points = rng.randint(2, 200)
        xs = [rng.uniform(-50.0, 50.0) for _ in range(n_points)]
        ys = [rng.uniform(-50.0, 50.0) for _ in range(n_points)]
        zs = [rng.uniform(-50.0, 50.0) for _ in range(n_points)]
        np_xs = np.array(xs, dtype=np.float64)
        np_ys = np.array(ys, dtype=np.float64)
        np_zs = np.array(zs, dtype=np.float64)

        ox = rng.uniform(-10.0, 10.0)
        oy = rng.uniform(-10.0, 10.0)
        oz = rng.uniform(-10.0, 10.0)

        dx = rng.uniform(-1.0, 1.0)
        dy = rng.uniform(-1.0, 1.0)
        dz = rng.uniform(-1.0, 1.0)

        py_res = find_closest_point_to_ray._original(xs, ys, zs, ox, oy, oz, dx, dy, dz)
        np_res = numpy_closest_point_to_ray(xs, ys, zs, ox, oy, oz, dx, dy, dz)
        mojo_res = find_closest_point_to_ray(np_xs, np_ys, np_zs, ox, oy, oz, dx, dy, dz)

        if find_closest_point_to_ray._last_backend != "native":
            print(f"[FAIL] Expected native backend at #{test_idx}, got {find_closest_point_to_ray._last_backend}")
            sys.exit(1)

        if py_res != mojo_res:
            print(f"[FAIL] Random 3D test #{test_idx} mismatch:")
            print(f"  Points: {n_points}")
            print(f"  Py:   {py_res}")
            print(f"  Mojo: {mojo_res}")
            print(f"  NP:   {np_res}")
            sys.exit(1)

        if py_res != np_res:
            print(f"[FAIL] Random NumPy mismatch at #{test_idx}: py={py_res}, np={np_res}")
            sys.exit(1)

        random_passed += 1
        total_3d_points += n_points

    total_tests = deterministic_passed + random_passed
    native_runs = find_closest_point_to_ray._call_count_native
    print(f"[✓] Stage D7: AR Spatial 3D PASSED: {total_tests} tests verified ({total_3d_points} 3D vertices, 100% matched against NumPy & Py, {native_runs} native @hotloop ndarray executions, 0 mismatches). Zero errors.")

if __name__ == "__main__":
    run_tests()
