import gc
import sys
import time

sys.path.insert(0, "/home/gaurav/mojo-hotloop")
sys.path.insert(0, "/home/gaurav/mojo-hotloop/audit")

from examples.rag_chunker.original import chunk_document
from examples.rag_chunker.bench import generate_bench_payloads

p = generate_bench_payloads()
l_text = p["large"]["text"]

import fast_rag

# Warmup
py_res = chunk_document._original(l_text, 1000, 200)
mojo_res = fast_rag.chunk_document(l_text, 1000, 200)
assert py_res == mojo_res, f"Mismatch: {len(py_res)} vs {len(mojo_res)}"

def time_fn(fn, iters=50):
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn()
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

t_py = time_fn(lambda: chunk_document._original(l_text, 1000, 200))
t_mojo = time_fn(lambda: fast_rag.chunk_document(l_text, 1000, 200))

print(f"Large document (100k chars):")
print(f"  Pure Python: {t_py:.4f} ms")
print(f"  Fast Mojo:   {t_mojo:.4f} ms")
print(f"  Speedup vs Python: {t_py / t_mojo:.2f}x")
