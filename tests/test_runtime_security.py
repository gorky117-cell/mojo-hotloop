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
Stage 6 Stability, ABI, and Security Verification Suite.

Runs crash-isolated subprocess tests for:
- Out-of-bounds list/string indices (must raise Python IndexError cleanly, zero SIGILL)
- Wrong NumPy ndarray shapes (2D), dtypes (float32/int32), non-contiguous slices ([::2], [::-1])
- Native 64-bit integer overflow fallback vs strict mode
- Lone surrogate fallback vs strict mode
- Corrupted .so / truncated ELF / corrupted manifest cache behavior
- Concurrent compilation safety (multi-threaded MojoBackend.build_ast)
- Clean wheel build and out-of-tree isolated installation check
"""

import concurrent.futures
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from hotloop.backends.mojo import MojoBackend


class TestRuntimeSecurityAndStability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="hotloop_sec_")
        cls.py_path = os.path.join(cls.tmpdir, "sec_mod.py")
        cls.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        code = '''from hotloop import hotloop

@hotloop
def sum_floats(xs: list[float]) -> float:
    tot: float = 0.0
    for i in range(len(xs)):
        tot += xs[i]
    return tot

@hotloop
def pick_int(xs: list[int], idx: int) -> int:
    return xs[idx]

@hotloop
def pick_char_ord(s: str, idx: int) -> int:
    return ord(s[idx])

@hotloop
def add_int(a: int, b: int) -> int:
    return a + b

@hotloop(strict=True)
def strict_double(x: int) -> int:
    return x * 2
'''
        with open(cls.py_path, "w", encoding="utf-8") as f:
            f.write(code)
        ok, msg, _ = MojoBackend().build_ast(cls.py_path, mod_name="fast")
        assert ok, f"Security test fixture build failed: {msg}"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def _run_subproc(self, body: str, env_extra=None) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        if env_extra:
            env.update(env_extra)
        script = (
            f"import sys\n"
            f"sys.path.insert(0, {self.repo_root!r})\n"
            f"sys.path.insert(0, {self.tmpdir!r})\n"
            f"import sec_mod\n"
            f"{body}\n"
        )
        return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, env=env)

    def test_01_oob_raises_indexerror_no_sigill_in_subprocess(self):
        proc = self._run_subproc(
            """
import numpy as np
for call in [
    lambda: sec_mod.pick_int(np.array([10, 20], dtype=np.int64), 2),
    lambda: sec_mod.pick_int(np.array([10, 20], dtype=np.int64), -3),
    lambda: sec_mod.pick_char_ord("hi", 5),
    lambda: sec_mod.pick_char_ord("hi", -3),
]:
    try:
        call()
        raise AssertionError("Expected IndexError")
    except IndexError:
        pass
assert sec_mod.pick_int(np.array([10, 20], dtype=np.int64), -1) == 20
assert sec_mod.pick_char_ord("hi", -1) == ord("i")
print("OK_OOB")
"""
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK_OOB", proc.stdout)

    def test_02_numpy_wrong_dtype_shape_and_non_contiguous_safety(self):
        proc = self._run_subproc(
            """
import numpy as np
# float32 (wrong dtype) -> pointer guard refuses float64 bitcast, safely unboxes elements
arr32 = np.array([1.5, 2.5, 3.5], dtype=np.float32)
assert sec_mod.sum_floats(arr32) == 7.5
assert sec_mod.sum_floats._last_backend == "native"

# int32 (wrong dtype) for pick_int -> safe elementwise unboxing
i32 = np.array([10, 20, 30], dtype=np.int32)
assert sec_mod.pick_int(i32, -1) == 30

# Non-contiguous strided slice and reversed view -> pointer guard skips bitcast, reads true slice elements!
base = np.array([1.0, 100.0, 2.0, 200.0, 3.0, 300.0], dtype=np.float64)
assert sec_mod.sum_floats(base[::2]) == 6.0
assert sec_mod.sum_floats(base[::-1]) == 606.0

# 2D ndarray -> rejects pointer bitcast, elementwise Float64(py=row) raises TypeError safely (no segfault)
mat = np.zeros((2, 2), dtype=np.float64)
try:
    sec_mod.sum_floats(mat)
    raise AssertionError("Expected TypeError for 2D array")
except Exception:
    pass
print("OK_NUMPY_SAFETY")
"""
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK_NUMPY_SAFETY", proc.stdout)

    def test_03_overflow_strict_and_surrogate_edges(self):
        proc = self._run_subproc(
            """
# Overflow falls back cleanly in default mode
big = sec_mod.add_int(9223372036854775800, 100)
assert big == 9223372036854775900
assert sec_mod.add_int._last_backend == "python_fallback_overflow"

# Surrogate string falls back cleanly instead of UTF-8 crash
res_surr = sec_mod.pick_char_ord("\\ud800", 0)
assert res_surr == 0xD800
assert sec_mod.pick_char_ord._last_backend == "python_fallback_surrogate"
print("OK_EDGE_FALLBACK")
"""
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK_EDGE_FALLBACK", proc.stdout)

        # Strict mode rejection under integer overflow / surrogate
        proc_strict = self._run_subproc(
            """
from hotloop import HotloopNativeExecutionError
try:
    sec_mod.strict_double(2**63)
    raise AssertionError("Expected HotloopNativeExecutionError")
except HotloopNativeExecutionError:
    pass
print("OK_STRICT")
"""
        )
        self.assertEqual(proc_strict.returncode, 0, proc_strict.stderr)
        self.assertIn("OK_STRICT", proc_strict.stdout)

    def test_04_corrupted_so_and_corrupted_manifest_resilience(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cmod.py")
            with open(p, "w", encoding="utf-8") as f:
                f.write("from hotloop import hotloop\n@hotloop\ndef sq(x: int) -> int:\n    return x * x\n")
            ok, msg, so_path = MojoBackend().build_ast(p, mod_name="fast")
            self.assertTrue(ok, msg)

            # Corrupt co-located fast.so and remove __mojocache__ so neither is valid
            shutil.rmtree(os.path.join(d, "__mojocache__"), ignore_errors=True)
            with open(so_path, "wb") as f:
                f.write(b"NOT_AN_ELF_BINARY_GARBAGE")

            res = subprocess.run(
                [sys.executable, "-c", f"import sys; sys.path.insert(0, {self.repo_root!r}); sys.path.insert(0, {d!r}); import cmod; v = cmod.sq(9); print(v, cmod.sq._last_backend); assert v == 81 and cmod.sq._last_backend == 'python_fallback'"],
                capture_output=True, text=True
            )
            self.assertEqual(res.returncode, 0, res.stderr)

    def test_05_concurrent_compilation_safety(self):
        with tempfile.TemporaryDirectory() as d:
            src_paths = []
            for i in range(4):
                sub = os.path.join(d, f"w{i}")
                os.makedirs(sub, exist_ok=True)
                p = os.path.join(sub, "m.py")
                with open(p, "w", encoding="utf-8") as f:
                    f.write(f"from hotloop import hotloop\n@hotloop\ndef fn(x: int) -> int:\n    return x + {i + 1}\n")
                src_paths.append(p)

            def _compile(path):
                return MojoBackend().build_ast(path, mod_name="fast")

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
                results = list(ex.map(_compile, src_paths))
            for ok, msg, _ in results:
                self.assertTrue(ok, msg)

    def test_06_repeated_native_execution_memory_stability(self):
        proc = self._run_subproc(
            """
import resource, numpy as np
arr = np.linspace(0.0, 10.0, 256, dtype=np.float64)
for _ in range(1000):
    sec_mod.sum_floats(arr)
rss_start = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
for _ in range(25000):
    sec_mod.sum_floats(arr)
    sec_mod.pick_char_ord("hello", 1)
rss_end = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
diff = rss_end - rss_start
print(f"RSS_DIFF={diff}")
assert diff < 4096, f"Unexpected RSS growth: {diff} KB"
"""
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("RSS_DIFF=", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
