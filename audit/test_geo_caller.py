import sys, time
import numpy as np

sys.path.insert(0, '/home/gaurav/mojo-hotloop/audit')
sys.path.insert(0, '/home/gaurav/mojo-hotloop')

import fast_geo
from examples.geo_distance.original import accumulate_haversine_distance
from examples.geo_distance.bench import numpy_haversine, numba_haversine

n = 10000
lats_np = np.random.uniform(-90.0, 90.0, n).astype(np.float64)
lons_np = np.random.uniform(-180.0, 180.0, n).astype(np.float64)

lats_list = lats_np.tolist()
lons_list = lons_np.tolist()

# Warmup Numba
numba_haversine(lats_np[:10], lons_np[:10])

# Correctness check
res_py = accumulate_haversine_distance(lats_list, lons_list)
res_mojo_np = fast_geo.accumulate_haversine_distance(lats_np, lons_np)
res_mojo_list = fast_geo.accumulate_haversine_distance(lats_list, lons_list)
res_numpy = numpy_haversine(lats_np, lons_np)
res_numba = numba_haversine(lats_np, lons_np)

print(f"Diff Mojo(NP) vs Py: {abs(res_mojo_np - res_py):.6e}")
print(f"Diff Mojo(List) vs Py: {abs(res_mojo_list - res_py):.6e}")
print(f"Diff NumPy vs Py: {abs(res_numpy - res_py):.6e}")
print(f"Diff Numba vs Py: {abs(res_numba - res_py):.6e}")
assert abs(res_mojo_np - res_py) < 1e-4

# Benchmarks
iters = 50

# 1. Pure Python (list)
t0 = time.perf_counter_ns()
for _ in range(iters):
    accumulate_haversine_distance(lats_list, lons_list)
t1 = time.perf_counter_ns()
print(f"Pure Python (list):   {(t1 - t0) / (iters * 1e6):.4f} ms")

# 2. NumPy vectorized
t0 = time.perf_counter_ns()
for _ in range(iters):
    numpy_haversine(lats_np, lons_np)
t1 = time.perf_counter_ns()
print(f"NumPy vectorized:     {(t1 - t0) / (iters * 1e6):.4f} ms")

# 3. Numba (@njit)
t0 = time.perf_counter_ns()
for _ in range(iters):
    numba_haversine(lats_np, lons_np)
t1 = time.perf_counter_ns()
print(f"Numba (@njit):        {(t1 - t0) / (iters * 1e6):.4f} ms")

# 4. Fast Mojo (NumPy pointer)
t0 = time.perf_counter_ns()
for _ in range(iters):
    fast_geo.accumulate_haversine_distance(lats_np, lons_np)
t1 = time.perf_counter_ns()
print(f"Mojo (NumPy pointer): {(t1 - t0) / (iters * 1e6):.4f} ms")

# 5. Mojo (Python list conversion)
t0 = time.perf_counter_ns()
for _ in range(iters):
    fast_geo.accumulate_haversine_distance(lats_list, lons_list)
t1 = time.perf_counter_ns()
print(f"Mojo (List convert):  {(t1 - t0) / (iters * 1e6):.4f} ms")
