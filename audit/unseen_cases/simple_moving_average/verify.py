import math
import os
import random
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, repo_root)

def py_simple_moving_average(values: list[float], window: int) -> list[float]:
    if len(values) < window or window <= 0:
        return []
    result: list[float] = []
    window_sum: float = 0.0
    for i in range(window):
        window_sum += values[i]
    result.append(window_sum / window)
    for i in range(window, len(values)):
        window_sum += values[i] - values[i - window]
        result.append(window_sum / window)
    return result

from audit.unseen_cases.simple_moving_average.original import simple_moving_average

def compare_lists(l1, l2, rel_tol=1e-9, abs_tol=1e-9):
    if len(l1) != len(l2):
        return False
    for a, b in zip(l1, l2):
        if not math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol):
            return False
    return True

def run_tests():
    total = 0
    passed = 0

    print("=================================================================")
    print("Running Verification for Function C: Simple Moving Average")
    print("=================================================================")

    # 1. Edge cases
    edge_cases = [
        ([], 3),
        ([1.0, 2.0], 5),        # len < window
        ([1.0, 2.0, 3.0], 0),    # window == 0
        ([1.0, 2.0, 3.0], -1),   # window < 0
        ([10.0, 20.0, 30.0], 1), # window == 1
        ([10.0, 20.0, 30.0], 3), # window == len
        ([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], 3),
        ([5.0, 5.0, 5.0, 5.0, 5.0], 2),
        ([-10.0, -20.0, -30.0, -40.0], 2),
        ([0.0, 0.0, 0.0, 0.0], 2),
    ]

    for vals, win in edge_cases:
        total += 1
        input_copy = list(vals)
        res = simple_moving_average(vals, win)
        expected = py_simple_moving_average(vals, win)
        assert compare_lists(res, expected), f"Mismatch on {vals}, win={win}: got {res}, expected {expected}"
        assert vals == input_copy, "Input mutated!"
        assert simple_moving_average._last_backend == "native"
        passed += 1

    # 2. 1,000 Seeded randomized tests
    rng = random.Random(42)
    for i in range(1000):
        total += 1
        length = rng.randint(0, 80)
        vals = [rng.uniform(-500.0, 500.0) for _ in range(length)]
        win = rng.randint(-2, 30)
        vals_copy = list(vals)

        res = simple_moving_average(vals, win)
        expected = py_simple_moving_average(vals, win)

        assert compare_lists(res, expected), f"Random test {i} mismatch: got {res[:3]}, expected {expected[:3]}"
        assert vals == vals_copy, "Input was mutated!"
        assert simple_moving_average._last_backend == "native"
        passed += 1

    # 3. Large scale test (50,000 items, window=100)
    total += 1
    large_vals = [rng.uniform(10.0, 100.0) for _ in range(50000)]
    large_copy = list(large_vals)
    win = 100
    res_large = simple_moving_average(large_vals, win)
    expected_large = py_simple_moving_average(large_vals, win)
    assert len(res_large) == 50000 - 100 + 1
    assert compare_lists(res_large, expected_large, rel_tol=1e-7, abs_tol=1e-7), "Large scale mismatch"
    assert large_vals == large_copy, "Large input mutated!"
    assert simple_moving_average._last_backend == "native"
    passed += 1

    print(f"Total Tests Executed : {total}")
    print(f"Tests Passed         : {passed}")
    print(f"Tests Failed         : 0")
    print(f"Native Executions    : {total}")
    print(f"Python Fallbacks     : 0")
    print("Zero-Mutation Check  : PASSED (100% read-only)")
    print("RESULT: PASSED (0 mismatches)")
    return 0

if __name__ == "__main__":
    sys.exit(run_tests())
