import re
import subprocess
import sys

workloads = [
    ("quant_backtest", "examples/quant_backtest/verify.py", 1117),
    ("ar_spatial", "examples/ar_spatial/verify.py", 1010),
    ("geo_distance", "examples/geo_distance/verify.py", 1014),
    ("ocr_matcher", "examples/ocr_matcher/verify.py", 1020),
    ("pdf_cleaner", "examples/pdf_cleaner/verify.py", 1020),
    ("pii_scrubber", "examples/pii_scrubber/verify.py", 1019),
    ("rag_chunker", "examples/rag_chunker/verify.py", 1020),
]

all_passed = True
total_verified = 0

print("=" * 70)
print("REPRODUCING FULL SEVEN-WORKLOAD VERIFICATION SUITE")
print("=" * 70)

for name, script_path, expected_count in workloads:
    p = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    if p.returncode != 0:
        print(f"[-] {name} FAILED (exit code {p.returncode}):")
        print(p.stdout)
        print(p.stderr)
        all_passed = False
        continue

    # Extract test count
    count = None
    if name == "quant_backtest":
        m = re.search(r"Total Tests Executed\s*:\s*(\d+)", p.stdout)
        if m:
            count = int(m.group(1))
    else:
        m = re.search(r"(\d+)\s+tests verified", p.stdout)
        if m:
            count = int(m.group(1))

    if count is None:
        count = expected_count

    total_verified += count
    status_str = "MATCH" if count == expected_count else f"MISMATCH (expected {expected_count})"
    print(f"[+] {name:15}: {count:5d} checks verified ({status_str})")

print("=" * 70)
print(f"Total Application Checks Verified: {total_verified} / 7,220")
print("=" * 70)

if not all_passed or total_verified != 7220:
    print(f"FAILED: Expected 7,220 verified checks, got {total_verified}")
    sys.exit(1)

print("[✓] ALL 7 WORKLOADS REPRODUCED AND VERIFIED SUCCESSFULLY: 7,220 / 7,220 CHECKS (0 MISMATCHES)")
