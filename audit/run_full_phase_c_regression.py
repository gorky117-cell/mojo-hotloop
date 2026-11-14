import os
import sys
import time
import subprocess
import re

# Add project root
sys.path.insert(0, "/home/gaurav/mojo-hotloop")

def run_test_module(name: str, cmd: list[str]) -> tuple[bool, int, str]:
    t0 = time.perf_counter()
    res = subprocess.run(cmd, capture_output=True, text=True, cwd="/home/gaurav/mojo-hotloop")
    elapsed = time.perf_counter() - t0
    
    output = res.stdout + "\n" + res.stderr
    success = (res.returncode == 0)
    
    tests_count = 0
    # Match unittest "Ran X tests"
    m_unittest = re.search(r"Ran (\d+) tests", output)
    if m_unittest:
        tests_count = int(m_unittest.group(1))
    
    # Match "X tests verified"
    m_verified = re.search(r"(\d+) tests verified", output)
    if m_verified:
        tests_count = max(tests_count, int(m_verified.group(1)))
        
    # Match "passed: X"
    m_passed = re.search(r"PASSED:\s*(\d+)", output)
    if m_passed:
        tests_count = max(tests_count, int(m_passed.group(1)))
        
    if tests_count == 0 and success:
        tests_count = 1  # Suite passed as a whole
                    
    return success, tests_count, output

def main():
    print("=" * 70)
    print("MOJO-HOTLOOP: MASTER PHASE C FULL REGRESSION & SECURITY AUDIT")
    print("=" * 70)
    
    suites = [
        ("Phase A: Dispatch, C-ABI & Strict Mode", [sys.executable, "audit/test_milestone1_dispatch.py"]),
        ("Phase A & B: Checked Arithmetic & Exception Parity", [sys.executable, "audit/test_milestones_2_3.py"]),
        ("Phase B: Cache Invalidation, Concurrency & Security", [sys.executable, "audit/test5_reliability_security.py"]),
        ("Phase C: Unicode Semantics Proof (ASCII, Hindi, Emojis)", [sys.executable, "audit/test_unicode_semantics.py"]),
        ("Phase C: Text Boundary Immutability & Memory Stability", [sys.executable, "audit/test_text_boundary_memory.py"]),
        ("Phase C: Unseen Function A (newline_positions)", [sys.executable, "audit/unseen_text/newline_positions/verify.py"]),
        ("Phase C: Unseen Function B (digit_runs)", [sys.executable, "audit/unseen_text/digit_runs/verify.py"]),
        ("Phase C: Unseen Function C (mask_digits)", [sys.executable, "audit/unseen_text/mask_digits/verify.py"]),
    ]
    
    total_passed = 0
    total_failed = 0
    total_checks = 0
    results_summary = []
    
    for title, cmd in suites:
        print(f"\n[RUNNING] {title}...")
        success, count, out = run_test_module(title, cmd)
        
        if success:
            print(f"  --> PASSED ({count} checks recorded)")
            total_passed += 1
            total_checks += count
            results_summary.append((title, "PASS", count, ""))
        else:
            print(f"  --> FAILED!")
            print(out[-1000:])
            total_failed += 1
            results_summary.append((title, "FAIL", count, out[-300:]))
            
    print("\n" + "=" * 70)
    print("REGRESSION AUDIT SUMMARY")
    print("=" * 70)
    for title, status, count, err in results_summary:
        print(f"[{status}] {title:<55} ({count:>4} checks)")
        if err:
            print(f"      Error: {err.strip()}")
            
    print("-" * 70)
    print(f"Suites Passed: {total_passed}/{len(suites)}")
    print(f"Suites Failed: {total_failed}/{len(suites)}")
    print(f"Total Verified Checks: {total_checks}")
    print("=" * 70)
    
    if total_failed > 0:
        print("[!] REGRESSION FAILED")
        sys.exit(1)
    else:
        print("[✓] ALL REGRESSION & SECURITY CHECKS PASSED PERFECTLY!")
        sys.exit(0)

if __name__ == "__main__":
    main()
