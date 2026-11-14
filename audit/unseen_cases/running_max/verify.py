import os
import random
import sys

# Ensure local packages
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, repo_root)

# Import pure python reference
def py_running_max(values: list[float]) -> list[float]:
    if len(values) == 0:
        return []
    current_max: float = values[0]
    result: list[float] = []
    for v in values:
        if v > current_max:
            current_max = v
        result.append(current_max)
    return result

from audit.unseen_cases.running_max.original import running_max

def run_tests():
    total = 0
    passed = 0

    print("=================================================================")
    print("Running Verification for Function A: Running Maximum")
    print("=================================================================")

    # 1. Edge cases
    edge_cases = [
        [],
        [42.0],
        [-10.0],
        [1.0, 2.0, 3.0, 4.0, 5.0],
        [5.0, 4.0, 3.0, 2.0, 1.0],
        [3.0, 3.0, 3.0, 3.0],
        [-5.0, -1.0, -10.0, -0.5, -2.0],
        [0.0, -0.0, 0.0],
        [1e30, -1e30, 2e30, 1.5e30],
        [1e-100, 2e-100, 1.5e-100],
    ]

    for ec in edge_cases:
        total += 1
        input_copy = list(ec)
        res = running_max(ec)
        expected = py_running_max(ec)
        assert res == expected, f"Mismatch on {ec}: got {res}, expected {expected}"
        assert ec == input_copy, f"Input mutated! {ec} != {input_copy}"
        assert running_max._last_backend == "native", f"Did not run natively on {ec}"
        passed += 1

    # 2. 1,000 Seeded randomized tests
    rng = random.Random(42)
    for i in range(1000):
        total += 1
        length = rng.randint(0, 100)
        vals = [rng.uniform(-10000.0, 10000.0) for _ in range(length)]
        vals_copy = list(vals)

        res = running_max(vals)
        expected = py_running_max(vals)

        assert res == expected, f"Random test {i} mismatch: got {res[:5]}..., expected {expected[:5]}..."
        assert vals == vals_copy, f"Input was mutated during execution!"
        assert running_max._last_backend == "native", "Backend was not native"
        passed += 1

    # 3. Large scale test (50,000 items)
    total += 1
    large_vals = [rng.uniform(-1e6, 1e6) for _ in range(50000)]
    large_copy = list(large_vals)
    res_large = running_max(large_vals)
    expected_large = py_running_max(large_vals)
    assert res_large == expected_large, "Large scale mismatch"
    assert large_vals == large_copy, "Large input mutated!"
    assert running_max._last_backend == "native"
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
