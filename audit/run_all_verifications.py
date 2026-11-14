import glob
import os
import subprocess
import sys

def main():
    verify_scripts = sorted(glob.glob("examples/*/verify.py"))
    total_passed = 0
    total_failed = 0
    failures = []

    print(f"Discovered {len(verify_scripts)} verification suites.")
    for script in verify_scripts:
        print(f"\n--- Running {script} ---")
        proc = subprocess.run([sys.executable, script], capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"FAILED (code {proc.returncode}):")
            print(proc.stderr or proc.stdout)
            total_failed += 1
            failures.append(script)
        else:
            lines = proc.stdout.strip().splitlines()
            last_line = lines[-1] if lines else ""
            print(f"PASSED: {last_line}")
            # Try parsing test count
            for line in lines:
                if "tests passed" in line.lower() or "tests verified" in line.lower() or "passed:" in line.lower():
                    print(f"  {line}")

    print("\n=======================================================")
    print(f"Verification Suites Summary: {len(verify_scripts) - total_failed}/{len(verify_scripts)} Passed")
    if failures:
        print(f"Failures: {failures}")
        sys.exit(1)
    else:
        print("ALL VERIFICATION SUITES PASSED!")

if __name__ == "__main__":
    main()
