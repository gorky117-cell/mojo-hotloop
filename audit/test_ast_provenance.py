import os
import subprocess
import sys

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

examples = [
    "quant_backtest",
    "ar_spatial",
    "ocr_matcher",
    "geo_distance",
    "pii_scrubber",
    "pdf_cleaner",
    "rag_chunker",
]

failed = False
for ex in examples:
    target = os.path.join(repo_root, "examples", ex, "original.py")
    print(f"\n=======================================================")
    print(f"Testing {ex} with --engine=ast")
    print(f"=======================================================")
    cmd = [
        sys.executable,
        "-m", "hotloop.cli",
        "build", target,
        "--engine=ast",
        "--no-verify"
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
    print(f"Return code: {p.returncode}")
    print(f"STDOUT:\n{p.stdout}")
    if p.stderr:
        print(f"STDERR:\n{p.stderr}")
    if p.returncode != 0:
        failed = True

if failed:
    sys.exit(1)
