# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Runnable benchmark demonstration: Pure Python vs Mojo Hotloop zero-copy NumPy pointer dispatch.
"""

import math
import os
import sys
import time
import numpy as np

# Ensure repository root is on path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, repo_root)

from examples.numpy_vector.original import exponential_decay_filter


def pure_python_filter(signal: list[float], decay: float) -> float:
    n = len(signal)
    if n == 0:
        return 0.0
    state = signal[0]
    weight = 1.0 - decay
    for i in range(1, n):
        state = state * decay + signal[i] * weight
    return state


def main():
    print("=" * 70)
    print("Mojo Hotloop — NumPy ndarray Zero-Copy Acceleration Benchmark")
    print("=" * 70)

    # Generate 1,000,000 synthetic float64 measurements
    N = 1_000_000
    decay = 0.95
    print(f"[*] Generating {N:,} elements (1-D C-contiguous float64 array)...")
    np_signal = np.ascontiguousarray(np.sin(np.linspace(0, 1000, N)), dtype=np.float64)
    py_signal = np_signal.tolist()

    # 1. Warmup and verify numerical parity
    print("[*] Verifying numerical parity...")
    py_res = pure_python_filter(py_signal, decay)
    hotloop_res = exponential_decay_filter(np_signal, decay)
    backend = getattr(exponential_decay_filter, "_last_backend", "unknown")
    print(f"    Pure Python Result : {py_res:.10f}")
    print(f"    Hotloop Result     : {hotloop_res:.10f}")
    print(f"    Active Backend     : {backend}")
    assert math.isclose(py_res, hotloop_res, rel_tol=1e-12), "Numerical mismatch detected!"
    assert backend == "native", f"Expected 'native' backend but got '{backend}'"
    print("    [✓] Exact parity confirmed! (0 mismatches, rel_tol=1e-12)")

    # 2. Benchmark Pure Python
    print("\n[*] Benchmarking Pure Python loop (5 trials)...")
    py_times = []
    for _ in range(5):
        t0 = time.perf_counter()
        _ = pure_python_filter(py_signal, decay)
        py_times.append(time.perf_counter() - t0)
    py_med_ms = sorted(py_times)[len(py_times) // 2] * 1000.0
    print(f"    Pure Python Latency : {py_med_ms:.2f} ms")

    # 3. Benchmark Mojo Hotloop with NumPy Zero-Copy Dispatch
    print("\n[*] Benchmarking Mojo Hotloop zero-copy pointer dispatch (20 trials)...")
    hotloop_times = []
    for _ in range(20):
        t0 = time.perf_counter()
        _ = exponential_decay_filter(np_signal, decay)
        hotloop_times.append(time.perf_counter() - t0)
    hotloop_med_ms = sorted(hotloop_times)[len(hotloop_times) // 2] * 1000.0
    print(f"    Hotloop Latency     : {hotloop_med_ms:.2f} ms")

    # 4. Summary & Speedup
    speedup = py_med_ms / hotloop_med_ms if hotloop_med_ms > 0 else 0.0
    print("\n" + "=" * 70)
    print(f"RESULTS SUMMARY ({N:,} elements, float64):")
    print(f"  • Pure Python loop : {py_med_ms:8.2f} ms")
    print(f"  • Mojo Hotloop     : {hotloop_med_ms:8.2f} ms")
    print(f"  • Speedup Factor   : {speedup:8.1f}x faster than pure Python")
    print("=" * 70)


if __name__ == "__main__":
    main()
