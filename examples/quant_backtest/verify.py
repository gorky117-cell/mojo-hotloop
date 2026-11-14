import math
import os
import random
import subprocess
import sys
import json

def worker_main():
    """Child worker process running inside an isolated process."""
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    import fast
    import original
    from hypothesis import given, settings, strategies as st

    py_fn = original.stateful_trailing_backtest._original
    mojo_fn = fast.stateful_trailing_backtest

    def check_close(py_res, mojo_res):
        if math.isnan(py_res) and math.isnan(mojo_res):
            return True
        if math.isinf(py_res) and math.isinf(mojo_res):
            return (py_res > 0) == (mojo_res > 0)
        return math.isclose(py_res, mojo_res, rel_tol=1e-9, abs_tol=1e-12)

    mismatches = []
    total_tests = 0

    # 1. Deterministic boundary suite
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
    ]

    for ticks, start_price, stop_pct, fee_rate in boundaries:
        total_tests += 1
        py_res = py_fn(ticks, start_price, stop_pct, fee_rate)
        mojo_res = mojo_fn(ticks, start_price, stop_pct, fee_rate)
        if not check_close(py_res, mojo_res):
            mismatches.append({
                "suite": "boundary",
                "args": (ticks, start_price, stop_pct, fee_rate),
                "py": py_res,
                "mojo": mojo_res
            })

    # 2. 1,000 repeatable seeded randomized tests
    rng = random.Random(42)
    for i in range(1000):
        total_tests += 1
        ticks = rng.randint(0, 5000)
        start_price = rng.uniform(0.1, 10000.0)
        stop_pct = rng.uniform(0.0, 0.5)
        fee_rate = rng.uniform(0.0, 0.05)
        
        py_res = py_fn(ticks, start_price, stop_pct, fee_rate)
        mojo_res = mojo_fn(ticks, start_price, stop_pct, fee_rate)
        if not check_close(py_res, mojo_res):
            mismatches.append({
                "suite": "randomized",
                "args": (ticks, start_price, stop_pct, fee_rate),
                "py": py_res,
                "mojo": mojo_res
            })
            if len(mismatches) > 10:
                break

    # 3. Property-based tests via hypothesis
    @settings(max_examples=100, deadline=None)
    @given(
        ticks=st.integers(min_value=0, max_value=2000),
        start_price=st.floats(min_value=0.1, max_value=10000.0, allow_nan=False, allow_infinity=False),
        stop_pct=st.floats(min_value=0.0, max_value=0.5, allow_nan=False, allow_infinity=False),
        fee_rate=st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
    )
    def test_hypothesis(ticks, start_price, stop_pct, fee_rate):
        nonlocal total_tests
        total_tests += 1
        py_res = py_fn(ticks, start_price, stop_pct, fee_rate)
        mojo_res = mojo_fn(ticks, start_price, stop_pct, fee_rate)
        if not check_close(py_res, mojo_res):
            mismatches.append({
                "suite": "hypothesis",
                "args": (ticks, start_price, stop_pct, fee_rate),
                "py": py_res,
                "mojo": mojo_res
            })
            assert False

    try:
        test_hypothesis()
    except AssertionError:
        pass

    result = {
        "total_tests": total_tests,
        "mismatches": mismatches,
        "passed": len(mismatches) == 0
    }
    print(json.dumps(result))
    sys.exit(0 if len(mismatches) == 0 else 1)


def main():
    if "--worker" in sys.argv:
        worker_main()
        return

    print("=" * 60)
    print("Running Structured Verification in Isolated Subprocess")
    print("=" * 60)

    cmd = [sys.executable, os.path.abspath(__file__), "--worker"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        print("VERIFICATION FAILED: Subprocess timed out after 30 seconds.")
        sys.exit(1)

    if proc.returncode < 0:
        sig = -proc.returncode
        print(f"VERIFICATION FAILED: Native crash in child subprocess! Killed by signal {sig} (SIGSEGV/abort).")
        sys.exit(1)

    try:
        # Find JSON in output
        lines = [line.strip() for line in proc.stdout.strip().split("\n") if line.strip().startswith("{")]
        if not lines:
            print(f"VERIFICATION FAILED: No output from worker.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
            sys.exit(1)
        data = json.loads(lines[-1])
    except Exception as e:
        print(f"VERIFICATION FAILED: Could not parse worker JSON: {e}\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}")
        sys.exit(1)

    total = data["total_tests"]
    mismatches = data["mismatches"]
    
    print(f"Total Tests Executed: {total}")
    print(f"Mismatches: {len(mismatches)}")
    
    if len(mismatches) == 0:
        print("RESULT: PASSED (0 mismatches, 100% compliant with Numerical Tolerance Policy)")
        sys.exit(0)
    else:
        print("RESULT: FAILED")
        for m in mismatches[:5]:
            print(f"  [{m['suite']}] args={m['args']}: py={m['py']} vs mojo={m['mojo']}")
        sys.exit(1)

if __name__ == "__main__":
    main()
