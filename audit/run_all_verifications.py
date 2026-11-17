import subprocess
import sys

workloads = [
    'quant_backtest',
    'ar_spatial',
    'geo_distance',
    'ocr_matcher',
    'pdf_cleaner',
    'pii_scrubber',
    'rag_chunker'
]

all_passed = True
for name in workloads:
    p = subprocess.run(['.venv/bin/python3', f'examples/{name}/verify.py'], capture_output=True, text=True)
    if p.returncode != 0:
        print(f'[-] {name} FAILED:')
        print(p.stdout)
        print(p.stderr)
        all_passed = False
    else:
        last_line = p.stdout.strip().splitlines()[-1] if p.stdout.strip() else "OK"
        print(f'[+] {name} PASSED: {last_line}')

if not all_passed:
    sys.exit(1)
print('[✓] ALL 7 WORKLOADS VERIFIED SUCCESSFULLY!')
