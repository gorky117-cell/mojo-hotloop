import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

class TestCacheInvalidation(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="hotloop_cache_test_")
        self.py_file = os.path.join(self.test_dir, "calc_mod.py")
        self.venv_hotloop = "/home/gaurav/mojo-hotloop/.venv/bin/hotloop"
        self.venv_python = "/home/gaurav/mojo-hotloop/.venv/bin/python"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def write_source(self, multiplier: int):
        code = f"""from hotloop import hotloop

@hotloop
def calc(x: int) -> int:
    return x * {multiplier}
"""
        with open(self.py_file, "w", encoding="utf-8") as f:
            f.write(code)

    def build_so(self):
        proc = subprocess.run(
            [self.venv_hotloop, "build", self.py_file, "--engine=ast", "--no-verify"],
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Build failed:\nSTDOUT: {proc.stdout}\nSTDERR: {proc.stderr}")

    def run_check(self, x_val: int, env=None):
        script = f"""import sys
sys.path.insert(0, {repr(self.test_dir)})
sys.path.insert(0, "/home/gaurav/mojo-hotloop")
from calc_mod import calc

try:
    val = calc({x_val})
    print(f"RESULT:{{val}}:BACKEND:{{calc._last_backend}}")
except Exception as e:
    print(f"EXCEPTION:{{type(e).__name__}}:{{e}}")
"""
        proc = subprocess.run(
            [self.venv_python, "-c", script],
            capture_output=True,
            text=True,
            env=env or os.environ.copy()
        )
        return proc.stdout.strip(), proc.stderr.strip()

    def test_01_fresh_build_native_execution(self):
        """Freshly built module executes natively."""
        self.write_source(multiplier=10)
        self.build_so()

        out, _ = self.run_check(5)
        self.assertIn("RESULT:50:BACKEND:native", out)

    def test_02_stale_binary_between_runs_fallback(self):
        """Modifying source between runs without rebuild triggers python_fallback_stale_cache."""
        self.write_source(multiplier=10)
        self.build_so()

        # Verify initial native execution
        out, _ = self.run_check(5)
        self.assertIn("RESULT:50:BACKEND:native", out)

        # Modify source without rebuilding: change multiplier to 20
        time.sleep(0.05)  # Ensure mtime advancement
        self.write_source(multiplier=20)

        out, err = self.run_check(5)
        # MUST return 100 (from new Python code), NOT 50 (stale native code)
        self.assertIn("RESULT:100:BACKEND:python_fallback_stale_cache", out)
        self.assertIn("HotloopFallbackWarning", err)
        self.assertIn("Stale native binary detected", err)

    def test_03_stale_binary_strict_mode_rejection(self):
        """Strict mode raises HotloopNativeExecutionError on stale binary."""
        self.write_source(multiplier=10)
        self.build_so()

        time.sleep(0.05)
        self.write_source(multiplier=20)

        env = os.environ.copy()
        env["HOTLOOP_STRICT"] = "1"
        out, _ = self.run_check(5, env=env)
        self.assertIn("EXCEPTION:HotloopNativeExecutionError", out)
        self.assertIn("Stale native binary detected", out)

    def test_04_rebuild_restores_native_execution(self):
        """Rebuilding after source edit restores native execution with updated logic."""
        self.write_source(multiplier=10)
        self.build_so()

        time.sleep(0.05)
        self.write_source(multiplier=20)
        self.build_so()

        out, _ = self.run_check(5)
        self.assertIn("RESULT:100:BACKEND:native", out)

    def test_05_content_addressed_cache_restoration(self):
        """Reverting source code to previously compiled state hits content-addressed __mojocache__."""
        # 1. Build multiplier 10
        self.write_source(multiplier=10)
        self.build_so()

        # 2. Build multiplier 20
        time.sleep(0.05)
        self.write_source(multiplier=20)
        self.build_so()

        # 3. Revert source back to multiplier 10 WITHOUT running build
        time.sleep(0.05)
        self.write_source(multiplier=10)

        # Should find __mojocache__/fast_<hash10>.so and run native!
        out, _ = self.run_check(5)
        self.assertIn("RESULT:50:BACKEND:native", out)

    def test_06_runtime_source_modification_detection(self):
        """Modifying source while Python process is running invalidates loaded native cache."""
        self.write_source(multiplier=10)
        self.build_so()

        script = f"""import sys
import time
sys.path.insert(0, {repr(self.test_dir)})
sys.path.insert(0, "/home/gaurav/mojo-hotloop")
from calc_mod import calc

r1 = calc(5)
backend1 = calc._last_backend

# Modify file during runtime
time.sleep(0.05)
with open({repr(self.py_file)}, "w", encoding="utf-8") as f:
    f.write('''from hotloop import hotloop
@hotloop
def calc(x: int) -> int:
    return x * 99
''')

r2 = calc(5)
backend2 = calc._last_backend
print(f"R1:{{r1}}:{{backend1}}|R2:{{r2}}:{{backend2}}")
"""
        proc = subprocess.run([self.venv_python, "-c", script], capture_output=True, text=True)
        self.assertIn("R1:50:native|R2:50:python_fallback_stale_cache", proc.stdout)

if __name__ == "__main__":
    unittest.main()
