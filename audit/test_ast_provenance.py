import os
import subprocess
import sys

examples = [
    "quant_backtest",
    "ar_spatial",
    "ocr_matcher",
    "geo_distance",
    "pii_scrubber",
    "pdf_cleaner",
    "rag_chunker",
]

for ex in examples:
    target = f"/home/gaurav/mojo-hotloop/examples/{ex}/original.py"
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
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(f"Return code: {p.returncode}")
    print(f"STDOUT:\n{p.stdout}")
    if p.stderr:
        print(f"STDERR:\n{p.stderr}")
