import subprocess
import sys

tests = [
    'audit/test_text_boundary_memory.py',
    'audit/test_unicode_semantics.py',
    'audit/test_collections_memory.py',
    'audit/test_numpy_interop.py',
    'audit/test_performance_dispatch.py',
    'audit/test5_reliability_security.py',
    'audit/test_cache_invalidation.py'
]

for t in tests:
    print(f'=== Running {t} ===')
    p = subprocess.run([sys.executable, t], capture_output=True, text=True)
    if p.returncode != 0:
        print(f'FAILED {t}:')
        print(p.stdout)
        print(p.stderr)
        sys.exit(1)
    else:
        out_lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
        last_line = out_lines[-1] if out_lines else 'OK'
        print(f'PASSED: {last_line}')
print('\nALL REGRESSION SUITES PASSED!')
