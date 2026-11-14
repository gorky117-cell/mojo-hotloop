import subprocess
import sys

scripts = [
    ('PII Scrubber', 'examples/pii_scrubber/bench.py'),
    ('RAG Chunker', 'examples/rag_chunker/bench.py'),
    ('PDF Cleaner', 'examples/pdf_cleaner/bench.py'),
    ('OCR Matcher', 'examples/ocr_matcher/bench.py'),
    ('Quant Backtest', 'examples/quant_backtest/bench.py'),
    ('Geo Distance', 'examples/geo_distance/bench.py'),
    ('AR Spatial 3D', 'examples/ar_spatial/bench.py'),
]

for name, script in scripts:
    print(f'=== Running {name} ({script}) ===')
    proc = subprocess.run([sys.executable, script], capture_output=True, text=True)
    if proc.returncode != 0:
        print(f'FAILED: {proc.stderr}')
    else:
        print(proc.stdout)
