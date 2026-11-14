import os
import subprocess
import sys
import time

repo_root = "/home/gaurav/mojo-hotloop"
venv_python = os.path.join(repo_root, ".venv/bin/python")

test_suites = [
    ("Milestone 1 Native Dispatch", [venv_python, "audit/test_milestone1_dispatch.py"], 8),
    ("Milestones 2 & 3 Overflow & Exception Parity", [venv_python, "audit/test_milestones_2_3.py"], 13),
    ("Cache Invalidation & __mojocache__", [venv_python, "audit/test_cache_invalidation.py"], 6),
    ("Performance-Aware Dispatch", [venv_python, "audit/test_performance_dispatch.py"], 6),
    ("Quant Backtest Correctness Suite", [venv_python, "examples/quant_backtest/verify.py"], 1117),
    ("Unseen Case A: Running Maximum", [venv_python, "audit/unseen_cases/running_max/verify.py"], 1011),
    ("Unseen Case B: Count Greater", [venv_python, "audit/unseen_cases/count_greater/verify.py"], 1011),
    ("Unseen Case C: Simple Moving Average", [venv_python, "audit/unseen_cases/simple_moving_average/verify.py"], 1011),
    ("NumPy 1D Array Zero-Copy Interop", [venv_python, "audit/test_numpy_interop.py"], 2),
    ("Collection Memory Stability (60,000 iters)", [venv_python, "audit/test_collections_memory.py"], 1),
]

print("=================================================================")
print("RUNNING MASTER FULL REGRESSION SUITE (PHASE B.1)")
print("=================================================================")

total_suites_passed = 0
total_tests_passed = 0
total_tests_failed = 0
grand_total_tests = 0

t_start = time.perf_counter()

for name, cmd, count in test_suites:
    print(f"\n--- Running: {name} (expected tests: {count}) ---")
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True)
    if proc.returncode == 0:
        total_suites_passed += 1
        total_tests_passed += count
        grand_total_tests += count
        print(f"PASSED: {name} ({count}/{count} tests)")
        # Show brief summary if present
        for line in proc.stdout.splitlines()[-4:]:
            if line.strip():
                print(f"   {line.strip()}")
    else:
        total_tests_failed += count
        grand_total_tests += count
        print(f"FAILED: {name}")
        print(f"STDOUT:\n{proc.stdout}")
        print(f"STDERR:\n{proc.stderr}")

t_elapsed = time.perf_counter() - t_start

print("\n=================================================================")
print("PHASE B.1 MASTER REGRESSION RESULTS")
print("=================================================================")
print(f"Total Suites Executed : {len(test_suites)}")
print(f"Suites Passed         : {total_suites_passed}/{len(test_suites)}")
print(f"Grand Total Tests     : {grand_total_tests}")
print(f"Total Tests Passed    : {total_tests_passed}")
print(f"Total Tests Failed    : {total_tests_failed}")
print(f"Total Execution Time  : {t_elapsed:.2f} s")
print(f"OVERALL STATUS        : {'ALL TESTS PASSED' if total_tests_failed == 0 else 'FAILURES DETECTED'}")
print("=================================================================")
