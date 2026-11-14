import os
import random
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, repo_root)

def py_count_greater(values: list[float], threshold: float) -> int:
    count: int = 0
    for v in values:
        if v > threshold:
            count += 1
    return count

from audit.unseen_cases.count_greater.original import count_greater

def run_tests():
    total = 0
    passed = 0

    print("=================================================================")
    print("Running Verification for Function B: Count Greater")
    print("=================================================================")

    # 1. Edge cases
    edge_cases = [
        ([], 0.0),
        ([10.0], 5.0),
        ([10.0], 15.0),
        ([10.0], 10.0),  # strictly greater
        ([1.0, 2.0, 3.0, 4.0, 5.0], 2.5),
        ([1.0, 2.0, 3.0, 4.0, 5.0], 0.0),
        ([1.0, 2.0, 3.0, 4.0, 5.0], 10.0),
        ([-10.0, -5.0, -1.0, 0.0, 1.0], -5.0),
        ([0.0, 0.0, 0.0], 0.0),
        ([1e18, 1e18, -1e18], 0.0),
    ]

    for vals, thresh in edge_cases:
        total += 1
        input_copy = list(vals)
        res = count_greater(vals, thresh)
        expected = py_count_greater(vals, thresh)
        assert res == expected, f"Mismatch on {vals}, {thresh}: got {res}, expected {expected}"
        assert vals == input_copy, "Input mutated!"
        assert count_greater._last_backend == "native"
        passed += 1

    # 2. 1,000 Seeded randomized tests
    rng = random.Random(42)
    for i in range(1000):
        total += 1
        length = rng.randint(0, 100)
        vals = [rng.uniform(-1000.0, 1000.0) for _ in range(length)]
        thresh = rng.uniform(-1000.0, 1000.0)
        vals_copy = list(vals)

        res = count_greater(vals, thresh)
        expected = py_count_greater(vals, thresh)

        assert res == expected, f"Random test {i} mismatch: got {res}, expected {expected}"
        assert vals == vals_copy, "Input was mutated!"
        assert count_greater._last_backend == "native"
        passed += 1

    # 3. Large scale test (100,000 items)
    total += 1
    large_vals = [rng.uniform(-100.0, 100.0) for _ in range(100000)]
    large_copy = list(large_vals)
    thresh = 0.0
    res_large = count_greater(large_vals, thresh)
    expected_large = py_count_greater(large_vals, thresh)
    assert res_large == expected_large, "Large scale mismatch"
    assert large_vals == large_copy, "Input mutated!"
    assert count_greater._last_backend == "native"
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
