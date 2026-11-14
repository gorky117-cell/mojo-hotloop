import os
import sys
import unittest
import numpy as np

repo_root = "/home/gaurav/mojo-hotloop"
sys.path.insert(0, repo_root)

from hotloop.decorator import hotloop, HotloopNativeExecutionError, HotloopFallbackWarning

class TestPerformanceDispatch(unittest.TestCase):
    def setUp(self):
        # Clear environment overrides
        os.environ.pop("HOTLOOP_FORCE_NATIVE", None)
        os.environ.pop("HOTLOOP_STRICT", None)
        os.environ.pop("HOTLOOP_STRICT_PERF", None)

    def test_01_scalar_function_defaults_to_native(self):
        """Scalar math functions are qualified as faster and execute natively by default."""
        from audit.bench_collatz.original import collatz_steps
        res = collatz_steps(27)
        self.assertEqual(res, 111)
        self.assertEqual(collatz_steps._last_backend, "native")

    def test_02_collection_function_defaults_to_python_fallback_slower(self):
        """Standard Python list inputs default to python_fallback_slower with warning."""
        from audit.unseen_cases.running_max.original import running_max
        with self.assertWarns(HotloopFallbackWarning):
            res = running_max([1.0, 5.0, 2.0, 8.0, 3.0])
        self.assertEqual(res, [1.0, 5.0, 5.0, 8.0, 8.0])
        self.assertEqual(running_max._last_backend, "python_fallback_slower")

    def test_03_force_native_env_override(self):
        """HOTLOOP_FORCE_NATIVE=1 overrides fallback and executes native Mojo."""
        os.environ["HOTLOOP_FORCE_NATIVE"] = "1"
        from audit.unseen_cases.running_max.original import running_max
        res = running_max([1.0, 5.0, 2.0, 8.0, 3.0])
        self.assertEqual(res, [1.0, 5.0, 5.0, 8.0, 8.0])
        self.assertEqual(running_max._last_backend, "native")

    def test_04_strict_flag_forces_native(self):
        """strict=True parameter forces native Mojo execution."""
        from hotloop import hotloop
        import audit.unseen_cases.count_greater.original as cg_mod
        
        # Test wrapper with strict=True
        strict_cg = hotloop(cg_mod.count_greater._original, strict=True)
        res = strict_cg([1.0, 2.0, 3.0, 4.0, 5.0], 2.5)
        self.assertEqual(res, 3)
        self.assertEqual(strict_cg._last_backend, "native")

    def test_05_force_native_parameter_forces_native(self):
        """force_native=True parameter forces native Mojo execution."""
        from hotloop import hotloop
        import audit.unseen_cases.simple_moving_average.original as sma_mod
        
        forced_sma = hotloop(sma_mod.simple_moving_average._original, force_native=True)
        res = forced_sma([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        self.assertEqual(len(res), 3)
        self.assertEqual(forced_sma._last_backend, "native")

    def test_06_strict_performance_mode_rejection(self):
        """HOTLOOP_STRICT_PERF=1 raises error with performance_not_qualified."""
        os.environ["HOTLOOP_STRICT_PERF"] = "1"
        from audit.unseen_cases.running_max.original import running_max
        with self.assertRaises(HotloopNativeExecutionError) as ctx:
            running_max([1.0, 2.0, 3.0])
        self.assertEqual(running_max._last_backend, "performance_not_qualified")
        self.assertIn("not qualified as faster", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
