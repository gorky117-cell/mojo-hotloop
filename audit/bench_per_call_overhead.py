import os
import sys
import time

repo_root = "/home/gaurav/mojo-hotloop"
sys.path.insert(0, repo_root)

# 1. Pure Python no-op
def py_noop(x: int) -> int:
    return x

# 2. Minimal native Mojo no-op
# Let's create a minimal test module if not already present
mojo_code = """
from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

def noop(arg0: PythonObject) raises -> PythonObject:
    var x = Int(py=arg0)
    return PythonObject(x)

@export
def PyInit_fast() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast")
        m.def_function[noop]("noop")
        return m.finalize()
    except e:
        abort(String("error: ", e))
"""
noop_dir = os.path.join(repo_root, "audit", "noop_test")
os.makedirs(noop_dir, exist_ok=True)
with open(os.path.join(noop_dir, "fast.mojo"), "w") as f:
    f.write(mojo_code)

import subprocess
cmd = ["/home/gaurav/mojo-hotloop/.venv/bin/mojo", "build", os.path.join(noop_dir, "fast.mojo"), "--emit", "shared-lib", "-o", os.path.join(noop_dir, "fast.so")]
subprocess.run(cmd, check=True, capture_output=True)

# Build manifest for fast.so so it's not marked stale
import hashlib
py_noop_file = os.path.join(noop_dir, "noop_mod.py")
py_code = """from hotloop import hotloop
@hotloop
def noop(x: int) -> int:
    return x
"""
with open(py_noop_file, "w") as f:
    f.write(py_code)

h = hashlib.sha256(py_code.encode()).hexdigest()
import json
with open(os.path.join(noop_dir, "fast.hotloop_manifest.json"), "w") as f:
    json.dump({"source_file": "noop_mod.py", "source_sha256": h, "compiler_version": "mojo 1.2.0", "transpiler_version": "1.2.0-phaseB"}, f)

# Direct import of native_noop
from hotloop.decorator import _load_native_module
mod, _ = _load_native_module(os.path.join(noop_dir, "fast.so"))
native_noop = getattr(mod, "noop")

# Import decorated noop
sys.path.insert(0, noop_dir)
from noop_mod import noop as hotloop_noop

def time_bench(fn, arg, iters=100000):
    for _ in range(1000):
        fn(arg)
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(arg)
    t1 = time.perf_counter_ns()
    return (t1 - t0) / iters  # ns per call

print("=== MEASURING PER-CALL OVERHEAD ===")
t_py = time_bench(py_noop, 42)
t_direct = time_bench(native_noop, 42)
t_hotloop = time_bench(hotloop_noop, 42)

print(f"1. Pure Python no-op                : {t_py:7.1f} ns ({t_py/1000:.3f} µs)")
print(f"2. Direct native Mojo call (FFI)    : {t_direct:7.1f} ns ({t_direct/1000:.3f} µs)")
print(f"3. Mojo call via @hotloop decorator : {t_hotloop:7.1f} ns ({t_hotloop/1000:.3f} µs)")
print(f"-> Incremental decorator overhead   : {t_hotloop - t_direct:7.1f} ns ({(t_hotloop - t_direct)/1000:.3f} µs)")

# Isolate subcomponents:
# A. os.path.getmtime cost
t0 = time.perf_counter_ns()
for _ in range(100000):
    _ = os.path.getmtime(py_noop_file)
t1 = time.perf_counter_ns()
t_stat = (t1 - t0) / 100000
print(f"-> Cost of os.path.getmtime syscall : {t_stat:7.1f} ns ({t_stat/1000:.3f} µs)")

# B. os.environ.get cost
t0 = time.perf_counter_ns()
for _ in range(100000):
    _ = os.environ.get("HOTLOOP_STRICT", "")
t1 = time.perf_counter_ns()
t_env = (t1 - t0) / 100000
print(f"-> Cost of os.environ.get           : {t_env:7.1f} ns ({t_env/1000:.3f} µs)")

# C. time.monotonic cost
t0 = time.perf_counter_ns()
for _ in range(100000):
    _ = time.monotonic()
t1 = time.perf_counter_ns()
t_mono = (t1 - t0) / 100000
print(f"-> Cost of time.monotonic           : {t_mono:7.1f} ns ({t_mono/1000:.3f} µs)")

# Prototype 1: Fast wrapper (cache checked at import time, lazy strict check)
def make_fast_wrapper(compiled_fn, fn):
    def fast_wrapper(*args, **kwargs):
        fast_wrapper._last_backend = "native"
        fast_wrapper._call_count_native += 1
        try:
            return compiled_fn(*args, **kwargs)
        except Exception:
            raise
    fast_wrapper._last_backend = "native"
    fast_wrapper._call_count_native = 0
    return fast_wrapper

fast_w = make_fast_wrapper(native_noop, py_noop)
t_fast_w = time_bench(fast_w, 42)
print(f"4. Fast wrapper (import-time cache) : {t_fast_w:7.1f} ns ({t_fast_w/1000:.3f} µs)")
print(f"-> Incremental overhead of fast_w   : {t_fast_w - t_direct:7.1f} ns ({(t_fast_w - t_direct)/1000:.3f} µs)")

# Prototype 2: Throttled mtime wrapper (checks mtime at most once every 20ms)
def make_throttled_wrapper(compiled_fn, fn, mod_file, loaded_mtime, interval=0.02):
    last_check = 0.0
    def throttled_wrapper(*args, **kwargs):
        nonlocal last_check
        now = time.monotonic()
        if now - last_check > interval:
            last_check = now
            try:
                if os.path.getmtime(mod_file) > loaded_mtime:
                    pass
            except OSError:
                pass
        throttled_wrapper._last_backend = "native"
        throttled_wrapper._call_count_native += 1
        try:
            return compiled_fn(*args, **kwargs)
        except Exception:
            raise
    throttled_wrapper._last_backend = "native"
    throttled_wrapper._call_count_native = 0
    return throttled_wrapper

throttled_w = make_throttled_wrapper(native_noop, py_noop, py_noop_file, os.path.getmtime(py_noop_file))
t_throttled_w = time_bench(throttled_w, 42)
print(f"5. Throttled wrapper (20ms interval): {t_throttled_w:7.1f} ns ({t_throttled_w/1000:.3f} µs)")
print(f"-> Incremental overhead throttled_w : {t_throttled_w - t_direct:7.1f} ns ({(t_throttled_w - t_direct)/1000:.3f} µs)")
