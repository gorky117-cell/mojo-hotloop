import os
import sys
import time
import numpy as np

repo_root = "/home/gaurav/mojo-hotloop"

mojo_code = """
from std.memory import OpaquePointer
from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

# 1. Running Max
def mojo_running_max_np(py_arr: PythonObject) raises -> PythonObject:
    var np = Python.import_module("numpy")
    var ptr_int = Int(py=py_arr.ctypes.data)
    var size = Int(py=py_arr.size)
    var in_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=ptr_int)
    var in_ptr = in_op.unsafe_bitcast[Float64]()
    
    var out_arr = np.empty(size, dtype=np.float64)
    var out_ptr_int = Int(py=out_arr.ctypes.data)
    var out_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=out_ptr_int)
    var out_ptr = out_op.unsafe_bitcast[Float64]()
    
    if size == 0:
        return out_arr
        
    var cur_max = in_ptr[0]
    out_ptr[0] = cur_max
    for i in range(1, size):
        var v = in_ptr[i]
        if v > cur_max:
            cur_max = v
        out_ptr[i] = cur_max
        
    return out_arr

# 2. Count Greater
def mojo_count_greater_np(py_arr: PythonObject, py_thresh: PythonObject) raises -> PythonObject:
    var ptr_int = Int(py=py_arr.ctypes.data)
    var size = Int(py=py_arr.size)
    var threshold = Float64(py=py_thresh)
    var in_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=ptr_int)
    var in_ptr = in_op.unsafe_bitcast[Float64]()
    
    var count: Int = 0
    for i in range(size):
        if in_ptr[i] > threshold:
            count += 1
            
    return PythonObject(count)

# 3. Simple Moving Average
def mojo_sma_np(py_arr: PythonObject, py_window: PythonObject) raises -> PythonObject:
    var np = Python.import_module("numpy")
    var ptr_int = Int(py=py_arr.ctypes.data)
    var size = Int(py=py_arr.size)
    var window = Int(py=py_window)
    
    if size < window or window <= 0:
        return np.empty(0, dtype=np.float64)
        
    var in_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=ptr_int)
    var in_ptr = in_op.unsafe_bitcast[Float64]()
    
    var out_len = size - window + 1
    var out_arr = np.empty(out_len, dtype=np.float64)
    var out_ptr_int = Int(py=out_arr.ctypes.data)
    var out_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=out_ptr_int)
    var out_ptr = out_op.unsafe_bitcast[Float64]()
    
    var w_sum: Float64 = 0.0
    for i in range(window):
        w_sum += in_ptr[i]
    out_ptr[0] = w_sum / Float64(window)
    
    var idx: Int = 1
    for i in range(window, size):
        w_sum += in_ptr[i] - in_ptr[i - window]
        out_ptr[idx] = w_sum / Float64(window)
        idx += 1
        
    return out_arr

# 4. 1M element sum reduction
def mojo_sum_np(py_arr: PythonObject) raises -> PythonObject:
    var ptr_int = Int(py=py_arr.ctypes.data)
    var size = Int(py=py_arr.size)
    var in_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=ptr_int)
    var in_ptr = in_op.unsafe_bitcast[Float64]()
    
    var total: Float64 = 0.0
    for i in range(size):
        total += in_ptr[i]
        
    return PythonObject(total)

@export
def PyInit_test_numpy_all() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("test_numpy_all")
        m.def_function[mojo_running_max_np]("running_max")
        m.def_function[mojo_count_greater_np]("count_greater")
        m.def_function[mojo_sma_np]("simple_moving_average")
        m.def_function[mojo_sum_np]("sum_array")
        return m.finalize()
    except e:
        abort(String("error: ", e))
"""

with open("/home/gaurav/mojo-hotloop/audit/test_numpy_all.mojo", "w") as f:
    f.write(mojo_code)

import subprocess
subprocess.run([
    "/home/gaurav/mojo-hotloop/.venv/bin/mojo", "build",
    "/home/gaurav/mojo-hotloop/audit/test_numpy_all.mojo",
    "--emit", "shared-lib",
    "-o", "/home/gaurav/mojo-hotloop/audit/test_numpy_all.so"
], check=True)

from hotloop.decorator import _load_native_module
mod, err = _load_native_module("/home/gaurav/mojo-hotloop/audit/test_numpy_all.so")
assert mod is not None, f"Failed to load: {err}"

mj_rm = getattr(mod, "running_max")
mj_cg = getattr(mod, "count_greater")
mj_sma = getattr(mod, "simple_moving_average")
mj_sum = getattr(mod, "sum_array")

import numba

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

# Correctness verification
np.random.seed(42)
test_50k = np.random.randn(50000).astype(np.float64)
test_1m = np.random.randn(1000000).astype(np.float64)

# 1. Running Max
assert np.allclose(mj_rm(test_50k), np.maximum.accumulate(test_50k)), "RM mismatch!"
# 2. Count Greater
assert mj_cg(test_50k, 0.0) == np.count_nonzero(test_50k > 0.0), "CG mismatch!"
# 3. SMA
res_mj_sma = mj_sma(test_50k, 50)
res_nb_sma = nb_sma(test_50k, 50)
assert np.allclose(res_mj_sma, res_nb_sma), "SMA mismatch!"
# 4. 1M Sum
assert np.isclose(mj_sum(test_1m), np.sum(test_1m)), "Sum mismatch!"

print("=== ALL 4 NUMPY CORRECTNESS CHECKS PASSED ===")

def bench(fn, *args, iters=100):
    for _ in range(5):
        fn(*args)
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(*args)
    t1 = time.perf_counter_ns()
    return (t1 - t0) / iters / 1e6

print("\n--- 1. Running Maximum (50k floats) ---")
t_np = bench(np.maximum.accumulate, test_50k)
t_nb = bench(nb_running_max, test_50k)
t_mj = bench(mj_rm, test_50k)
print(f"NumPy accumulate:      {t_np:.4f} ms")
print(f"Numba (warmed):        {t_nb:.4f} ms")
print(f"Mojo zero-copy:        {t_mj:.4f} ms")
print(f"Speedup vs NumPy:      {t_np / t_mj:.2f}x")

print("\n--- 2. Count Greater (50k floats) ---")
t_np = bench(lambda: np.count_nonzero(test_50k > 0.0))
t_nb = bench(nb_count_greater, test_50k, 0.0)
t_mj = bench(mj_cg, test_50k, 0.0)
print(f"NumPy count_nonzero:   {t_np:.4f} ms")
print(f"Numba (warmed):        {t_nb:.4f} ms")
print(f"Mojo zero-copy:        {t_mj:.4f} ms")
print(f"Speedup vs NumPy:      {t_np / t_mj:.2f}x")

print("\n--- 3. Simple Moving Average (50k floats, w=50) ---")
def np_sma(arr, w):
    return np.convolve(arr, np.ones(w)/w, mode='valid')
t_np = bench(np_sma, test_50k, 50, iters=20)
t_nb = bench(nb_sma, test_50k, 50)
t_mj = bench(mj_sma, test_50k, 50)
print(f"NumPy convolve:        {t_np:.4f} ms")
print(f"Numba (warmed):        {t_nb:.4f} ms")
print(f"Mojo zero-copy:        {t_mj:.4f} ms")
print(f"Speedup vs NumPy:      {t_np / t_mj:.2f}x")

print("\n--- 4. Sum Reduction (1,000,000 floats) ---")
t_np = bench(np.sum, test_1m, iters=20)
t_nb = bench(nb_sum, test_1m, iters=20)
t_mj = bench(mj_sum, test_1m, iters=20)
print(f"NumPy sum:             {t_np:.4f} ms")
print(f"Numba (warmed):        {t_nb:.4f} ms")
print(f"Mojo zero-copy:        {t_mj:.4f} ms")
print(f"Speedup vs NumPy:      {t_np / t_mj:.2f}x")
