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
Verification script for numpy_vector example.
Checks numerical correctness across various input sizes, layouts, and edge cases.
"""

import math
import os
import sys
import numpy as np

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, repo_root)

from examples.numpy_vector.original import exponential_decay_filter


def py_filter(signal: list[float], decay: float) -> float:
    n = len(signal)
    if n == 0:
        return 0.0
    state = signal[0]
    weight = 1.0 - decay
    for i in range(1, n):
        state = state * decay + signal[i] * weight
    return state


def run_checks():
    checks = 0
    mismatches = 0

    print("[*] Running numpy_vector verification checks...")

    # 1. Edge case: Empty array
    checks += 1
    empty_arr = np.array([], dtype=np.float64)
    res_empty = exponential_decay_filter(empty_arr, 0.9)
    if res_empty != 0.0:
        print(f"[-] Mismatch on empty array: got {res_empty}, expected 0.0")
        mismatches += 1

    # 2. Edge case: Single element
    checks += 1
    single_arr = np.array([42.5], dtype=np.float64)
    res_single = exponential_decay_filter(single_arr, 0.8)
    if not math.isclose(res_single, 42.5, rel_tol=1e-12):
        print(f"[-] Mismatch on single element: got {res_single}, expected 42.5")
        mismatches += 1

    # 3. Small arrays with diverse decay factors
    for size in [5, 10, 50, 200, 1000]:
        for decay in [0.0, 0.1, 0.5, 0.9, 0.99, 1.0]:
            checks += 1
            arr = np.ascontiguousarray(np.linspace(-10, 10, size), dtype=np.float64)
            expected = py_filter(arr.tolist(), decay)
            actual = exponential_decay_filter(arr, decay)
            if not math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12):
                print(f"[-] Mismatch at size={size}, decay={decay}: actual={actual}, expected={expected}")
                mismatches += 1
            if getattr(exponential_decay_filter, "_last_backend", None) != "native":
                print(f"[-] Expected native backend, got {exponential_decay_filter._last_backend}")
                mismatches += 1

    # 4. Large array (100,000 elements)
    checks += 1
    large_arr = np.ascontiguousarray(np.random.RandomState(42).randn(100_000), dtype=np.float64)
    expected_large = py_filter(large_arr.tolist(), 0.95)
    actual_large = exponential_decay_filter(large_arr, 0.95)
    if not math.isclose(actual_large, expected_large, rel_tol=1e-12):
        print(f"[-] Mismatch on large array: actual={actual_large}, expected={expected_large}")
        mismatches += 1

    # 5. Non-contiguous array fallback check (slices)
    checks += 1
    strided_arr = large_arr[::2]  # non-contiguous slice
    res_strided = exponential_decay_filter(strided_arr, 0.95)
    expected_strided = py_filter(strided_arr.tolist(), 0.95)
    if not math.isclose(res_strided, expected_strided, rel_tol=1e-12):
        print(f"[-] Mismatch on strided array: actual={res_strided}, expected={expected_strided}")
        mismatches += 1

    print(f"[+] numpy_vector verification finished: {checks} checks, {mismatches} mismatches.")
    if mismatches > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_checks()
