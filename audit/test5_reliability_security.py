import os
import sys
import subprocess
import time
import math
import json
import resource
import shutil

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
quant_dir = os.path.join(repo_root, "examples", "quant_backtest")
audit_dir = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, repo_root)
sys.path.insert(0, quant_dir)

import fast
import original

def test_reliability_and_security():
    print("=== TEST 5: RELIABILITY AND SECURITY AUDIT ===")
    findings = {}

    # 1. Integer Overflow and Out-of-Bounds C-ABI conversions
    print("\n--- 5.1: Integer Limits & Out-of-Range Arguments ---")
    int_tests = {}
    # Python int outside 64-bit signed range: 2**63 = 9223372036854775808
    large_int = 2**63
    try:
        res = fast.stateful_trailing_backtest(large_int, 100.0, 0.05, 0.001)
        int_tests["overflow_2_pow_63"] = {
            "status": "SILENT_WRAPPING_OR_PASS",
            "result": str(res)
        }
        print(f"  Passed 2**63 to Mojo Int: returned {res} (silent truncation/wrapping!)")
    except Exception as e:
        int_tests["overflow_2_pow_63"] = {
            "status": "EXCEPTION_RAISED",
            "exception": f"{type(e).__name__}: {e}"
        }
        print(f"  Passed 2**63 to Mojo Int: caught exception {type(e).__name__}: {e}")

    # Very large Python int: 2**128
    huge_int = 2**128
    try:
        res = fast.stateful_trailing_backtest(huge_int, 100.0, 0.05, 0.001)
        int_tests["overflow_2_pow_128"] = {
            "status": "SILENT_WRAPPING_OR_PASS",
            "result": str(res)
        }
        print(f"  Passed 2**128 to Mojo Int: returned {res}")
    except Exception as e:
        int_tests["overflow_2_pow_128"] = {
            "status": "EXCEPTION_RAISED",
            "exception": f"{type(e).__name__}: {e}"
        }
        print(f"  Passed 2**128 to Mojo Int: caught exception {type(e).__name__}: {e}")

    # Negative integer
    try:
        res_neg = fast.stateful_trailing_backtest(-10, 100.0, 0.05, 0.001)
        int_tests["negative_int"] = {
            "status": "SAFE",
            "result": res_neg
        }
        print(f"  Passed -10 to Mojo Int: returned {res_neg} (safe)")
    except Exception as e:
        int_tests["negative_int"] = {"status": "ERROR", "exception": str(e)}

    findings["integer_limits"] = int_tests

    # 2. Numerical Edge Cases (NaN, Inf, Zero Division)
    print("\n--- 5.2: Floating Point Edge Cases (NaN, Inf, Zero) ---")
    fp_tests = {}
    cases_fp = [
        ("nan_start_price", 10, float("nan"), 0.05, 0.001),
        ("inf_start_price", 10, float("inf"), 0.05, 0.001),
        ("neg_inf_start_price", 10, float("-inf"), 0.05, 0.001),
        ("zero_price", 10, 0.0, 0.05, 0.001),
        ("zero_stop_pct", 10, 100.0, 0.0, 0.001),
        ("zero_fee_rate", 10, 100.0, 0.05, 0.0),
        ("extreme_volatility", 1000, 1e20, 0.99, 0.5),
        ("subnormal_price", 10, 1e-310, 0.05, 0.001),
    ]

    for name, ticks, p, s, f in cases_fp:
        py_out = None
        py_err = None
        try:
            py_out = original.stateful_trailing_backtest._original(ticks, p, s, f)
        except Exception as e:
            py_err = f"{type(e).__name__}: {e}"

        mojo_out = None
        mojo_err = None
        try:
            mojo_out = fast.stateful_trailing_backtest(ticks, p, s, f)
        except Exception as e:
            mojo_err = f"{type(e).__name__}: {e}"

        match = False
        if py_err and mojo_err:
            match = True
        elif py_out is not None and mojo_out is not None:
            if math.isnan(py_out) and math.isnan(mojo_out):
                match = True
            elif math.isinf(py_out) and math.isinf(mojo_out):
                match = (py_out > 0) == (mojo_out > 0)
            else:
                match = math.isclose(py_out, mojo_out, rel_tol=1e-9, abs_tol=1e-12)

        fp_tests[name] = {
            "py": py_out if py_out is not None else py_err,
            "mojo": mojo_out if mojo_out is not None else mojo_err,
            "match": match
        }
        print(f"  Case {name:20s}: py={py_out} | mojo={mojo_out} | match={match}")

    findings["floating_point_edge_cases"] = fp_tests

    # 3. Unicode Handling (Hindi & Emoji)
    print("\n--- 5.3: Unicode String Handling in AST Transpiler ---")
    unicode_source = """from hotloop import hotloop

@hotloop
def greet(name: str) -> str:
    return "नमस्ते " + name + " 🚀"
"""
    from hotloop.ast_transpiler import transpile_python_to_mojo, ASTTranspileError
    unicode_test = {}
    try:
        code = transpile_python_to_mojo(unicode_source, "greet_mod")
        unicode_test["status"] = "ACCEPTED"
        unicode_test["generated_lines"] = len(code.splitlines())
        print("  Unicode function transpile: ACCEPTED")
    except ASTTranspileError as e:
        unicode_test["status"] = "REJECTED_CLEANLY"
        unicode_test["error"] = str(e)
        print(f"  Unicode function transpile: REJECTED_CLEANLY -> {e}")
    except Exception as e:
        unicode_test["status"] = "UNEXPECTED_ERROR"
        unicode_test["error"] = str(e)
        print(f"  Unicode function transpile: UNEXPECTED_ERROR -> {e}")

    findings["unicode_handling"] = unicode_test

    # 4. Compilation Failure & Diagnostic Handling
    print("\n--- 5.4: Compilation Failure and Diagnostic Handling ---")
    invalid_py_file = os.path.join(audit_dir, "invalid_target.py")
    with open(invalid_py_file, "w") as f:
        f.write("""from hotloop import hotloop

@hotloop
def bad_func(x: int) -> int:
    # Unsupported complex construct
    return [i for i in range(x)]
""")
    comp_fail_test = {}
    p_fail = subprocess.run(
        [sys.executable, "-m", "hotloop.cli", "build", invalid_py_file, "--engine=ast"],
        capture_output=True,
        text=True
    )
    comp_fail_test["exit_code"] = p_fail.returncode
    comp_fail_test["stderr"] = p_fail.stderr.strip()
    comp_fail_test["stdout"] = p_fail.stdout.strip()
    print(f"  Build with unsupported AST node: Exit code {p_fail.returncode}")
    print(f"  Output:\n{p_fail.stdout.strip()}")
    findings["compilation_failure_diagnostics"] = comp_fail_test

    # 5. Python Fallback Correctness
    print("\n--- 5.5: Python Fallback Correctness ---")
    fallback_test = {}
    # When no .so exists
    no_so_py = os.path.join(audit_dir, "standalone_func.py")
    with open(no_so_py, "w") as f:
        f.write("""import sys, os
sys.path.insert(0, '{repo_root}')
from hotloop import hotloop

@hotloop
def standalone_add(a: int, b: int) -> int:
    return a + b
""")
    test_fb_script = f"""
import sys
sys.path.insert(0, '{audit_dir}')
import standalone_func
res = standalone_func.standalone_add(10, 20)
assert res == 30, f'Expected 30, got {{res}}'
print('FALLBACK_RESULT:', res)
"""
    p_fb = subprocess.run([sys.executable, "-c", test_fb_script], capture_output=True, text=True)
    fallback_test["missing_so_fallback"] = {
        "status": "PASS" if p_fb.returncode == 0 else "FAIL",
        "output": p_fb.stdout.strip(),
        "error": p_fb.stderr.strip()
    }
    print(f"  Missing .so fallback: {fallback_test['missing_so_fallback']['status']} -> {p_fb.stdout.strip()}")

    # Corrupt .so test
    corrupt_dir = os.path.join(audit_dir, "corrupt_test")
    os.makedirs(corrupt_dir, exist_ok=True)
    corrupt_so = os.path.join(corrupt_dir, "fast.so")
    with open(corrupt_so, "w") as f:
        f.write("CORRUPT_NOT_AN_ELF_FILE")
    corrupt_py = os.path.join(corrupt_dir, "original.py")
    with open(corrupt_py, "w") as f:
        f.write(f"""import sys
sys.path.insert(0, '{repo_root}')
from hotloop import hotloop

@hotloop
def add_fn(a: int, b: int) -> int:
    return a + b
""")
    test_corrupt_script = f"""
import sys
sys.path.insert(0, '{corrupt_dir}')
import original
res = original.add_fn(5, 5)
assert res == 10, f'Expected 10, got {{res}}'
print('CORRUPT_FALLBACK_RESULT:', res)
"""
    p_corrupt = subprocess.run([sys.executable, "-c", test_corrupt_script], capture_output=True, text=True)
    fallback_test["corrupted_so_fallback"] = {
        "status": "PASS" if p_corrupt.returncode == 0 else "FAIL",
        "output": p_corrupt.stdout.strip(),
        "error": p_corrupt.stderr.strip()
    }
    print(f"  Corrupt .so fallback: {fallback_test['corrupted_so_fallback']['status']} -> {p_corrupt.stdout.strip()}")
    findings["fallback_behavior"] = fallback_test

    # 6. Cache Invalidation
    print("\n--- 5.6: Cache Invalidation Audit ---")
    cache_inval_test = {
        "transpiler_tracks_mtime": False,
        "decorator_tracks_mtime": False,
        "behavior": "Decorator loads any existing matching .so unconditionally regardless of whether the Python source has been modified since compilation. No hash or timestamp check exists."
    }
    print(f"  Cache invalidation: {cache_inval_test['behavior']}")
    findings["cache_invalidation"] = cache_inval_test

    # 7. Subprocess Segfault / Native Crash Isolation
    print("\n--- 5.7: Native Crash & Segfault Isolation Test ---")
    # Build a Mojo module that explicitly aborts
    abort_mojo = os.path.join(audit_dir, "abort_mod.mojo")
    abort_so = os.path.join(audit_dir, "abort_mod.so")
    with open(abort_mojo, "w") as f:
        f.write("""from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

@export
def PyInit_abort_mod() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("abort_mod")
        m.def_function[crash]("crash")
        return m.finalize()
    except e:
        abort(String("error creating module:", e))

def crash(a: PythonObject) raises -> PythonObject:
    abort("INTENTIONAL_NATIVE_ABORT_FOR_AUDIT")
    return PythonObject(0)
""")
    mojo_bin = shutil.which("mojo") or os.path.join(os.path.dirname(sys.executable), "mojo")
    subprocess.run([mojo_bin, "build", abort_mojo, "--emit", "shared-lib", "-o", abort_so], capture_output=True)

    # Test crash in subprocess runner
    crash_runner_script = f"""
import sys, subprocess
script = '''
import sys
sys.path.insert(0, '{audit_dir}')
import abort_mod
abort_mod.crash(1)
'''
proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
print(f"CHILD_RETURNCODE: {{proc.returncode}}")
print(f"CHILD_STDERR: {{proc.stderr.strip()[:100]}}")
"""
    p_crash = subprocess.run([sys.executable, "-c", crash_runner_script], capture_output=True, text=True)
    crash_test = {
        "output": p_crash.stdout.strip(),
        "runner_survived": p_crash.returncode == 0
    }
    print(f"  Crash isolation test: Runner survived = {crash_test['runner_survived']}")
    print(f"  Output: {p_crash.stdout.strip()}")
    findings["native_crash_isolation"] = crash_test

    # 8. Memory Leaks / Memory Stability
    print("\n--- 5.8: Memory Stability under Repeated Calls (100,000 iterations) ---")
    mem_leak_script = f"""
import sys, resource
sys.path.insert(0, '{quant_dir}')
import fast

initial_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
for i in range(100000):
    _ = fast.stateful_trailing_backtest(10, 100.0, 0.05, 0.001)
final_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

print(f"INITIAL_RSS_KB: {{initial_rss}}")
print(f"FINAL_RSS_KB: {{final_rss}}")
print(f"RSS_DIFF_KB: {{final_rss - initial_rss}}")
"""
    p_mem = subprocess.run([sys.executable, "-c", mem_leak_script], capture_output=True, text=True)
    mem_test = {"output": p_mem.stdout.strip()}
    print(f"  Memory leak test: {p_mem.stdout.strip()}")
    findings["memory_stability"] = mem_test

    with open(os.path.join(audit_dir, "test5_results.json"), "w") as f:
        json.dump(findings, f, indent=2)

if __name__ == "__main__":
    test_reliability_and_security()
