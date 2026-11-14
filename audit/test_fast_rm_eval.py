import array
import os
import sys
import time

repo_root = "/home/gaurav/mojo-hotloop"

mojo_code = """
from std.memory import OpaquePointer
from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

def fast_rm_buffer(py_in_arr: PythonObject, py_out_arr: PythonObject) raises -> PythonObject:
    var in_binfo = py_in_arr.buffer_info()
    var in_addr = Int(py=in_binfo[0])
    var size = Int(py=in_binfo[1])
    
    var out_binfo = py_out_arr.buffer_info()
    var out_addr = Int(py=out_binfo[0])
    
    var in_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=in_addr)
    var in_ptr = in_op.unsafe_bitcast[Float64]()
    
    var out_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=out_addr)
    var out_ptr = out_op.unsafe_bitcast[Float64]()
    
    if size == 0:
        return PythonObject(0)
        
    var cur = in_ptr[0]
    out_ptr[0] = cur
    for i in range(1, size):
        var v = in_ptr[i]
        if v > cur:
            cur = v
        out_ptr[i] = cur
        
    return PythonObject(size)

@export
def PyInit_test_fast_rm() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("test_fast_rm")
        m.def_function[fast_rm_buffer]("fast_rm_buffer")
        return m.finalize()
    except e:
        abort(String("error: ", e))
"""

with open("/home/gaurav/mojo-hotloop/audit/test_fast_rm.mojo", "w") as f:
    f.write(mojo_code)

import subprocess
subprocess.run([
    "/home/gaurav/mojo-hotloop/.venv/bin/mojo", "build",
    "/home/gaurav/mojo-hotloop/audit/test_fast_rm.mojo",
    "--emit", "shared-lib",
    "-o", "/home/gaurav/mojo-hotloop/audit/test_fast_rm.so"
], check=True)

from hotloop.decorator import _load_native_module
mod, _ = _load_native_module("/home/gaurav/mojo-hotloop/audit/test_fast_rm.so")
fast_rm_buffer = getattr(mod, "fast_rm_buffer")

def py_running_max(values: list[float]) -> list[float]:
    if not values:
        return []
    result: list[float] = []
    current_max: float = values[0]
    for v in values:
        if v > current_max:
            current_max = v
        result.append(current_max)
    return result

# Full end-to-end Python-list in -> Python-list out using array buffer
def mojo_running_max_buffered(values: list[float]) -> list[float]:
    if not values:
        return []
    n = len(values)
    in_arr = array.array('d', values)
    # Fast pre-allocated array of size n
    out_arr = array.array('d', [0.0]) * n
    fast_rm_buffer(in_arr, out_arr)
    return out_arr.tolist()

# Test 50k floats
import random
rng = random.Random(42)
test_vals = [rng.uniform(-1000.0, 1000.0) for _ in range(50000)]

# Verify correctness
expected = py_running_max(test_vals)
actual = mojo_running_max_buffered(test_vals)
assert actual == expected, "Mismatch!"
print("Correctness verification: PASSED!")

def bench(fn, iters=20):
    for _ in range(2):
        fn()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn()
    t1 = time.perf_counter_ns()
    return (t1 - t0) / iters / 1e6

t_py = bench(lambda: py_running_max(test_vals))
t_buf = bench(lambda: mojo_running_max_buffered(test_vals))

print(f"Pure Python (list in/out)             : {t_py:.3f} ms")
print(f"Mojo Buffer path (list in/out)        : {t_buf:.3f} ms")
print(f"Speedup vs Python                     : {t_py / t_buf:.2f}x")
