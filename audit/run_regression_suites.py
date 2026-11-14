import os
import subprocess
import sys

audit_scripts = [
    "audit/test_d8_integration.py",
    "audit/test_text_boundary_memory.py",
    "audit/test_unicode_semantics.py",
    "audit/test_collections_memory.py",
    "audit/test_numpy_interop.py",
    "audit/test_performance_dispatch.py",
    "audit/test5_reliability_security.py",
]

total_failed = 0
for script in audit_scripts:
    if not os.path.exists(script):
        print(f"Skipping {script} (not found)")
        continue
    print(f"\n--- Running {script} ---")
    proc = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"FAILED (code {proc.returncode}):")
        print(proc.stderr or proc.stdout)
        total_failed += 1
    else:
        lines = proc.stdout.strip().splitlines()
        last_line = lines[-1] if lines else ""
        print(f"PASSED: {last_line}")

print("\n=======================================================")
if total_failed == 0:
    print("ALL AUDIT REGRESSION SUITES PASSED!")
else:
    print(f"{total_failed} AUDIT SUITES FAILED")
    sys.exit(1)
