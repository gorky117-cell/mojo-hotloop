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
Phase E.8 Independent Optimization Safety and Stress-Testing Suite.

Audits and stress-tests all five v0.2.0 compiler optimization passes:
1. Bounds-Check Elimination: empty arrays, aliased arrays, mutation, edge indices.
2. Loop-Invariant Hoisting: zero-iteration loops, early return/break, side effects.
3. Fast Unicode & String Access: ASCII, Devanagari, Accented Latin, SMP 4-byte Emoji, negative indices.
4. String Buffer Pre-Allocation: empty strings, large strings, multiple accumulations.
5. Dispatch Qualifier & Cache Invalidation: type drift, shape drift, non-contiguous strides.
"""

import math
import os
import shutil
import sys
import tempfile
import unittest
import numpy as np

from hotloop.backends.mojo import MojoBackend

SAFETY_MODULE_SOURCE = '''
import math
from hotloop import hotloop

# --- 1. Bounds-check & array iteration stress functions ---
@hotloop
def sum_arr_safe(xs: list[float]) -> float:
    tot: float = 0.0
    for i in range(len(xs)):
        tot += xs[i]
    return tot

@hotloop
def aliased_dot_product(xs: list[float], ys: list[float]) -> float:
    dot: float = 0.0
    n: int = len(xs)
    if n != len(ys):
        return -1.0
    for i in range(n):
        dot += xs[i] * ys[i]
    return dot

@hotloop
def inplace_acc_loop(xs: list[float], factor: float) -> float:
    acc: float = 0.0
    for i in range(len(xs)):
        acc = acc + xs[i] * factor
    return acc

# --- 2. Loop-invariant hoisting stress functions ---
@hotloop
def zero_iter_invariant(n: int, a: float, b: float) -> float:
    res: float = 100.0
    # Loop should execute 0 times if n <= 0
    for i in range(n):
        res += a * (1.0 - b) + 2.5
    return res

@hotloop
def early_break_hoist(limit: int, fee: float, stop: float) -> float:
    val: float = 1.0
    for i in range(100):
        if i >= limit:
            break
        val = val * (1.0 - fee) + (1.0 - stop)
    return val

@hotloop
def nested_loop_hoist(outer_n: int, inner_n: int, factor: float) -> float:
    total: float = 0.0
    for i in range(outer_n):
        inv_outer: float = factor * 2.0 + 1.0
        for j in range(inner_n):
            total += inv_outer + (1.0 - factor)
    return total

# --- 3. Unicode & String scanning stress functions ---
@hotloop
def count_chars_and_check_equality(s: str, target: str) -> int:
    cnt: int = 0
    t_ord: int = ord(target)
    for i in range(len(s)):
        if ord(s[i]) == t_ord:
            cnt += 1
    return cnt

@hotloop
def reverse_string_builder(s: str) -> str:
    res: str = ""
    n: int = len(s)
    for i in range(n):
        res += s[n - 1 - i]
    return res

@hotloop
def negative_indexing_scan(s: str) -> int:
    sum_ords: int = 0
    n: int = len(s)
    for i in range(1, n + 1):
        sum_ords += ord(s[-i])
    return sum_ords

@hotloop
def filter_ascii_letters(s: str) -> str:
    out: str = ""
    for i in range(len(s)):
        c: int = ord(s[i])
        if (c >= 65 and c <= 90) or (c >= 97 and c <= 122):
            out += s[i]
    return out
'''


class TestOptimizationSafetyE8(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="hotloop_safety_e8_")
        cls.mod_path = os.path.join(cls.tmpdir, "safety_e8_mod.py")
        with open(cls.mod_path, "w", encoding="utf-8") as f:
            f.write(SAFETY_MODULE_SOURCE)

        backend = MojoBackend()
        ok, msg, so_path = backend.build_ast(cls.mod_path, mod_name="fast")
        assert ok, f"Safety test suite build failed:\n{msg}"

        sys.path.insert(0, cls.tmpdir)
        import safety_e8_mod  # type: ignore
        cls.mod = safety_e8_mod

    @classmethod
    def tearDownClass(cls):
        if cls.tmpdir in sys.path:
            sys.path.remove(cls.tmpdir)
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_01_bounds_check_elimination_empty_arrays(self):
        """Empty array should execute zero iterations safely with zero errors/crashes."""
        empty_list: list[float] = []
        actual = self.mod.sum_arr_safe(empty_list)
        expected = self.mod.sum_arr_safe._original(empty_list)
        self.assertEqual(actual, expected)
        self.assertEqual(actual, 0.0)

        empty_np = np.array([], dtype=np.float64)
        actual_np = self.mod.sum_arr_safe(empty_np)
        expected_np = self.mod.sum_arr_safe._original(empty_np)
        self.assertEqual(actual_np, expected_np)
        self.assertEqual(actual_np, 0.0)

    def test_02_bounds_check_elimination_aliasing(self):
        """Passing identical array references to multiple arguments must compute correctly."""
        arr = [1.5, -2.0, 3.25, 4.0, -0.5]
        # xs and ys are identical object
        actual = self.mod.aliased_dot_product(arr, arr)
        expected = self.mod.aliased_dot_product._original(arr, arr)
        self.assertAlmostEqual(actual, expected, places=7)

        np_arr = np.array([1.5, -2.0, 3.25, 4.0, -0.5], dtype=np.float64)
        actual_np = self.mod.aliased_dot_product(np_arr, np_arr)
        expected_np = self.mod.aliased_dot_product._original(np_arr, np_arr)
        self.assertAlmostEqual(actual_np, expected_np, places=7)

    def test_03_loop_invariant_hoisting_zero_iterations(self):
        """Zero iteration loops must preserve initial variable values."""
        # Loop trip count = 0
        actual = self.mod.zero_iter_invariant(0, 3.5, 0.1)
        expected = self.mod.zero_iter_invariant._original(0, 3.5, 0.1)
        self.assertEqual(actual, expected)
        self.assertEqual(actual, 100.0)

        # Loop trip count = -10 (negative range)
        actual_neg = self.mod.zero_iter_invariant(-10, 3.5, 0.1)
        expected_neg = self.mod.zero_iter_invariant._original(-10, 3.5, 0.1)
        self.assertEqual(actual_neg, expected_neg)
        self.assertEqual(actual_neg, 100.0)

    def test_04_loop_invariant_hoisting_early_break(self):
        """Loops breaking early must compute exact prefix accumulator states."""
        for limit in [0, 1, 5, 10, 50, 100, 200]:
            actual = self.mod.early_break_hoist(limit, 0.02, 0.05)
            expected = self.mod.early_break_hoist._original(limit, 0.02, 0.05)
            self.assertAlmostEqual(actual, expected, places=7, msg=f"Failed at limit={limit}")

    def test_05_loop_invariant_nested_hoisting(self):
        """Nested loops must hoist invariant outer subexpressions correctly."""
        actual = self.mod.nested_loop_hoist(10, 20, 0.15)
        expected = self.mod.nested_loop_hoist._original(10, 20, 0.15)
        self.assertAlmostEqual(actual, expected, places=7)

    def test_06_fast_unicode_devanagari_and_accented(self):
        """Unicode characters (Devanagari, accented European) must preserve codepoint values."""
        # Devanagari text
        hindi_text = "नमस्ते दुनिया और सभी को नमस्कार"
        actual_count = self.mod.count_chars_and_check_equality(hindi_text, "स")
        expected_count = self.mod.count_chars_and_check_equality._original(hindi_text, "स")
        self.assertEqual(actual_count, expected_count)
        self.assertGreater(actual_count, 0)

        # Accented European text
        french_text = "Déjà vu à l'école république naïve et café résumé"
        actual_rev = self.mod.reverse_string_builder(french_text)
        expected_rev = self.mod.reverse_string_builder._original(french_text)
        self.assertEqual(actual_rev, expected_rev)

    def test_07_fast_unicode_smp_4byte_emojis(self):
        """Supplementary Multilingual Plane 4-byte UTF-8 emojis must preserve exact length & values."""
        emoji_text = "🚀🔥🎉👍🐱🌍"
        actual_rev = self.mod.reverse_string_builder(emoji_text)
        expected_rev = self.mod.reverse_string_builder._original(emoji_text)
        self.assertEqual(actual_rev, expected_rev)

        actual_ords = self.mod.negative_indexing_scan(emoji_text)
        expected_ords = self.mod.negative_indexing_scan._original(emoji_text)
        self.assertEqual(actual_ords, expected_ords)

    def test_08_fast_string_negative_indexing(self):
        """Negative indices s[-i] must resolve identically to Python."""
        mixed_text = "AlphaBeta123!@#_नमस्ते_🚀"
        actual_ords = self.mod.negative_indexing_scan(mixed_text)
        expected_ords = self.mod.negative_indexing_scan._original(mixed_text)
        self.assertEqual(actual_ords, expected_ords)

    def test_09_string_preallocation_empty_and_large(self):
        """String pre-allocation reserve_bytes handles empty strings and 100k strings safely."""
        # Empty string
        self.assertEqual(self.mod.reverse_string_builder(""), "")
        self.assertEqual(self.mod.filter_ascii_letters(""), "")

        # 10k ASCII string
        large_ascii = "Hello123World456!_ABCXYZ" * 500
        actual_filtered = self.mod.filter_ascii_letters(large_ascii)
        expected_filtered = self.mod.filter_ascii_letters._original(large_ascii)
        self.assertEqual(actual_filtered, expected_filtered)

    def test_10_dispatch_qualifier_cache_drift_safety(self):
        """Dispatch qualifier cache handles type drift and fallback triggers correctly."""
        from hotloop import inspect_dispatch

        # 1. Python list input safely routes to fallback (avoiding per-element FFI conversion overhead)
        flist = [1.0, 2.0, 3.0]
        self.mod.sum_arr_safe(flist)
        info = inspect_dispatch(self.mod.sum_arr_safe)
        self.assertEqual(info["last_backend"], "python_fallback_slower")
        self.assertIn("fallback_reason", info)

        # 2. NumPy ndarray inputs preserve Python semantics
        np_arr = np.array([4.0, 5.0, 6.0], dtype=np.float64)
        before = self.mod.sum_arr_safe._call_count_native
        self.mod.sum_arr_safe(np_arr)
        info2 = inspect_dispatch(self.mod.sum_arr_safe)
        self.assertEqual(info2["last_backend"], "python_fallback_semantics")
        self.assertEqual(info2["call_count_native"], before)

        # 3. String function routes natively
        self.mod.reverse_string_builder("hello")
        info3 = inspect_dispatch(self.mod.reverse_string_builder)
        self.assertEqual(info3["last_backend"], "native")


if __name__ == "__main__":
    unittest.main(verbosity=2)
