import sys, time
import numpy as np

sys.path.insert(0, '/home/gaurav/mojo-hotloop/audit')
sys.path.insert(0, '/home/gaurav/mojo-hotloop')

import fast_ar
from examples.ar_spatial.original import find_closest_point_to_ray
from examples.ar_spatial.bench import numba_closest_point_to_ray
from examples.ar_spatial.verify import numpy_closest_point_to_ray

n = 10000
xs_np = np.random.uniform(-10.0, 10.0, n).astype(np.float64)
ys_np = np.random.uniform(-10.0, 10.0, n).astype(np.float64)
zs_np = np.random.uniform(-10.0, 10.0, n).astype(np.float64)

xs_list = xs_np.tolist()
ys_list = ys_np.tolist()
zs_list = zs_np.tolist()

ray = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)

# Warmup numba
numba_closest_point_to_ray(xs_np[:10], ys_np[:10], zs_np[:10], *ray)

# Correctness check
idx_py = find_closest_point_to_ray(xs_list, ys_list, zs_list, *ray)
idx_mojo_np = fast_ar.find_closest_point_to_ray(xs_np, ys_np, zs_np, *ray)
idx_numpy = numpy_closest_point_to_ray(xs_np, ys_np, zs_np, *ray)
idx_numba = numba_closest_point_to_ray(xs_np, ys_np, zs_np, *ray)

print(f"Indices: Py={idx_py}, Mojo={idx_mojo_np}, NumPy={idx_numpy}, Numba={idx_numba}")
assert idx_py == idx_mojo_np == idx_numpy == idx_numba, "Mismatch in nearest point index!"

# Benchmarks
iters = 50

# 1. Pure Python (list)
t0 = time.perf_counter_ns()
for _ in range(iters):
    find_closest_point_to_ray(xs_list, ys_list, zs_list, *ray)
t1 = time.perf_counter_ns()
print(f"Pure Python (list):    {(t1 - t0) / (iters * 1e6):.4f} ms")

# 2. NumPy vectorized
t0 = time.perf_counter_ns()
for _ in range(iters):
    numpy_closest_point_to_ray(xs_np, ys_np, zs_np, *ray)
t1 = time.perf_counter_ns()
print(f"NumPy vectorized:      {(t1 - t0) / (iters * 1e6):.4f} ms")

# 3. Numba (@njit)
t0 = time.perf_counter_ns()
for _ in range(iters):
    numba_closest_point_to_ray(xs_np, ys_np, zs_np, *ray)
t1 = time.perf_counter_ns()
print(f"Numba (@njit):         {(t1 - t0) / (iters * 1e6):.4f} ms")

# 4. Fast Mojo (NumPy pointer)
t0 = time.perf_counter_ns()
for _ in range(iters):
    fast_ar.find_closest_point_to_ray(xs_np, ys_np, zs_np, *ray)
t1 = time.perf_counter_ns()
print(f"Mojo (NumPy pointer):  {(t1 - t0) / (iters * 1e6):.4f} ms")
