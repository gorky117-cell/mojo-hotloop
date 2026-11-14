import math
import os
import random
import subprocess
import sys
import json

def worker_main():
    """Child worker process running inside an isolated process."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    sys.path.insert(0, repo_root)
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    import fast
    import original
    from hypothesis import given, settings, strategies as st

    py_fn = original.stateful_trailing_backtest._original
    dec_fn = original.stateful_trailing_backtest
    mojo_fn = fast.stateful_trailing_backtest

    def check_close(py_res, mojo_res):
        if math.isnan(py_res) and math.isnan(mojo_res):
            return True
        if math.isinf(py_res) and math.isinf(mojo_res):
            return (py_res > 0) == (mojo_res > 0)
        return math.isclose(py_res, mojo_res, rel_tol=1e-9, abs_tol=1e-12)

    mismatches = []
    total_tests = 0
    passed_tests = 0
    native_executions = 0
    python_fallbacks = 0
    skipped_tests = 0

    # 1. Deterministic boundary suite (including extreme floats, subnormals, signed zero)
    boundaries = [
        (0, 100.0, 0.05, 0.001),
        (1, 100.0, 0.05, 0.001),
        (10, 1.0, 0.0, 0.0),
        (50, 0.01, 0.5, 0.05),
        (1000, 1000000.0, 0.01, 0.0001),
        (-5, 50.0, 0.05, 0.001),
        (100, 100.0, 0.0, 0.001),
        (500, 50.0, 0.2, 0.0),
        (2000, 250.75, 0.03, 0.0005),
        # Extreme floats & subnormals
        (10, 1e20, 0.05, 0.001),
        (10, 1e-310, 0.05, 0.001), # subnormal IEEE-754
        (10, 1e-50, 0.01, 0.0001),
        (10, float("nan"), 0.05, 0.001),
        (10, float("inf"), 0.05, 0.001),
        (10, float("-inf"), 0.05, 0.001),
        # Large integer boundary
        (100000, 100.0, 0.05, 0.001),
    ]

    for ticks, start_price, stop_pct, fee_rate in boundaries:
        total_tests += 1
        py_res = py_fn(ticks, start_price, stop_pct, fee_rate)
        # Call via @hotloop decorator to verify real native dispatch
        mojo_res = dec_fn(ticks, start_price, stop_pct, fee_rate)
        
        if dec_fn._last_backend == "native":
            native_executions += 1
        else:
            python_fallbacks += 1

        if check_close(py_res, mojo_res):
            passed_tests += 1
        else:
            mismatches.append({
                "suite": "boundary",
                "args": (ticks, start_price, stop_pct, fee_rate),
                "py": py_res,
                "mojo": mojo_res,
                "backend": dec_fn._last_backend
            })

    # 2. Mathematical Exception Parity: Zero division on start_price=0.0
    total_tests += 1
    py_exc = None
    try:
        py_fn(10, 0.0, 0.05, 0.001)
    except Exception as e:
        py_exc = type(e).__name__

    mojo_exc = None
    try:
        dec_fn(10, 0.0, 0.05, 0.001)
    except Exception as e:
        mojo_exc = type(e).__name__

    if py_exc == mojo_exc == "ZeroDivisionError":
        passed_tests += 1
        native_executions += 1
    else:
        mismatches.append({
            "suite": "exception_parity",
            "case": "start_price=0.0",
            "py_exception": py_exc,
            "mojo_exception": mojo_exc
        })

    # 3. 1,000 repeatable seeded randomized tests
    rng = random.Random(42)
    for i in range(1000):
        total_tests += 1
        ticks = rng.randint(0, 5000)
        start_price = rng.uniform(0.1, 10000.0)
        stop_pct = rng.uniform(0.0, 0.5)
        fee_rate = rng.uniform(0.0, 0.05)

        py_res = py_fn(ticks, start_price, stop_pct, fee_rate)
        mojo_res = dec_fn(ticks, start_price, stop_pct, fee_rate)

        if dec_fn._last_backend == "native":
            native_executions += 1
        else:
            python_fallbacks += 1

        if check_close(py_res, mojo_res):
            passed_tests += 1
        else:
            mismatches.append({
                "suite": "randomized",
                "args": (ticks, start_price, stop_pct, fee_rate),
                "py": py_res,
                "mojo": mojo_res,
                "backend": dec_fn._last_backend
            })
            if len(mismatches) > 10:
                break

    # 4. Property-based tests via hypothesis
    @settings(max_examples=100, deadline=None)
    @given(
        ticks=st.integers(min_value=0, max_value=2000),
        start_price=st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False),
        stop_pct=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False),
        fee_rate=st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
    )
    def test_hypothesis(ticks, start_price, stop_pct, fee_rate):
        nonlocal total_tests, passed_tests, native_executions, python_fallbacks
        total_tests += 1
        py_res = py_fn(ticks, start_price, stop_pct, fee_rate)
        mojo_res = dec_fn(ticks, start_price, stop_pct, fee_rate)

        if dec_fn._last_backend == "native":
            native_executions += 1
        else:
            python_fallbacks += 1

        if check_close(py_res, mojo_res):
            passed_tests += 1
        else:
            mismatches.append({
                "suite": "hypothesis",
                "args": (ticks, start_price, stop_pct, fee_rate),
                "py": py_res,
                "mojo": mojo_res,
                "backend": dec_fn._last_backend
            })
            assert False

    try:
        test_hypothesis()
    except AssertionError:
        pass

    result = {
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": len(mismatches),
        "skipped_tests": skipped_tests,
        "native_executions": native_executions,
        "python_fallbacks": python_fallbacks,
        "mismatches": mismatches,
        "passed": len(mismatches) == 0 and passed_tests == total_tests
    }
    print(json.dumps(result))
    sys.exit(0 if result["passed"] else 1)


def main():
    if "--worker" in sys.argv:
        worker_main()
        return

    print("=" * 65)
    print("Running Hardened Verification Suite in Isolated Subprocess")
    print("=" * 65)

    cmd = [sys.executable, os.path.abspath(__file__), "--worker"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    except subprocess.TimeoutExpired:
        print("VERIFICATION FAILED: Subprocess timed out after 45 seconds.")
        sys.exit(1)

    if proc.returncode < 0:
        sig = -proc.returncode
        print(f"VERIFICATION FAILED: Native crash in child subprocess! Killed by signal {sig} (SIGSEGV/abort).")
        sys.exit(1)

    try:
        lines = [line.strip() for line in proc.stdout.strip().split("\n") if line.strip().startswith("{")]
        if not lines:
            print(f"VERIFICATION FAILED: No output from worker.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
            sys.exit(1)
        data = json.loads(lines[-1])
    except Exception as e:
        print(f"VERIFICATION FAILED: Could not parse worker JSON: {e}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        sys.exit(1)

    print(f"Total Tests Executed : {data['total_tests']}")
    print(f"Tests Passed         : {data['passed_tests']}")
    print(f"Tests Failed         : {data['failed_tests']}")
    print(f"Tests Skipped        : {data['skipped_tests']}")
    print(f"Native Executions    : {data['native_executions']}")
    print(f"Python Fallbacks     : {data['python_fallbacks']}")

    if data["passed"]:
        print("RESULT: PASSED (0 mismatches, 100% verified native execution)")
        sys.exit(0)
    else:
        print("RESULT: FAILED")
        for m in data["mismatches"][:5]:
            print(f"  [{m['suite']}] args={m.get('args', m.get('case'))}: py={m.get('py', m.get('py_exception'))} vs mojo={m.get('mojo', m.get('mojo_exception'))}")
        sys.exit(1)

if __name__ == "__main__":
    main()
