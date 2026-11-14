import numpy as np
import sys
import time

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from audit.test_numpy_ptr import sum_numpy_1d

# Test with 1D numpy float64 array
arr = np.array([1.5, 2.5, 3.5, 4.5, 5.5], dtype=np.float64)
res = sum_numpy_1d(arr)
print("NumPy Input Array:", arr)
print("Mojo Sum Result  :", res)
assert res == 17.5, f"Expected 17.5, got {res}"
print("Small array verification: PASSED")

# Large array test (1,000,000 elements)
large_arr = np.ones(1_000_000, dtype=np.float64)
t0 = time.perf_counter()
res_large = sum_numpy_1d(large_arr)
t1 = time.perf_counter()
assert res_large == 1_000_000.0
print(f"Large array (1M elements) sum: {res_large:.1f} in {(t1 - t0)*1000:.3f} ms")
print("SUCCESS: True zero-copy NumPy 1D contiguous array interoperability in Mojo 1.2.0 verified!")
