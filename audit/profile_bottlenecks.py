import gc
import os
import sys
import time

sys.path.insert(0, '/home/gaurav/mojo-hotloop')

def measure(fn, iters=100):
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn()
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

print('=== PROFILING BOTTLENECK COMPONENTS ===')

# 1. PII Scrubber
from examples.pii_scrubber.original import scrub_pii
from examples.pii_scrubber.bench import generate_bench_payloads
p_payloads = generate_bench_payloads()
p_text = p_payloads['large']['text']
# Measure wrapped vs direct
t_wrapped = measure(lambda: scrub_pii(p_text), iters=20)
t_direct = measure(lambda: scrub_pii._compiled(p_text), iters=20)
print(f'PII Scrubber:  Wrapped={t_wrapped:.3f} ms | Direct={t_direct:.3f} ms | Decorator Overhead={t_wrapped - t_direct:.3f} ms')

# 2. RAG Chunker
from examples.rag_chunker.original import chunk_document
from examples.rag_chunker.bench import generate_bench_payloads as r_payloads
r_p = r_payloads()
r_text = r_p['large']['text']
t_wrapped = measure(lambda: chunk_document(r_text, 1000, 200), iters=20)
t_direct = measure(lambda: chunk_document._compiled(r_text, 1000, 200), iters=20)
print(f'RAG Chunker:   Wrapped={t_wrapped:.3f} ms | Direct={t_direct:.3f} ms | Decorator Overhead={t_wrapped - t_direct:.3f} ms')

# 3. PDF Cleaner
from examples.pdf_cleaner.original import clean_pdf_text
from examples.pdf_cleaner.bench import generate_bench_payloads as pdf_payloads
pdf_p = pdf_payloads()
pdf_text = pdf_p['large']['text']
t_wrapped = measure(lambda: clean_pdf_text(pdf_text), iters=20)
t_direct = measure(lambda: clean_pdf_text._compiled(pdf_text), iters=20)
print(f'PDF Cleaner:   Wrapped={t_wrapped:.3f} ms | Direct={t_direct:.3f} ms | Decorator Overhead={t_wrapped - t_direct:.3f} ms')

# 4. OCR Matcher
from examples.ocr_matcher.original import find_closest_match
from examples.ocr_matcher.bench import generate_bench_payloads as ocr_payloads
ocr_p = ocr_payloads()
ocr_q = ocr_p['medium']['query']
ocr_c = ocr_p['medium']['candidates']
t_wrapped = measure(lambda: find_closest_match(ocr_q, ocr_c, 3), iters=50)
t_direct = measure(lambda: find_closest_match._compiled(ocr_q, ocr_c, 3), iters=50)
print(f'OCR Matcher:   Wrapped={t_wrapped:.3f} ms | Direct={t_direct:.3f} ms | Decorator Overhead={t_wrapped - t_direct:.3f} ms')

# 5. Quant Backtest
from examples.quant_backtest.original import stateful_trailing_backtest
t_wrapped = measure(lambda: stateful_trailing_backtest(100000, 100.0, 0.05, 0.001), iters=50)
t_direct = measure(lambda: stateful_trailing_backtest._compiled(100000, 100.0, 0.05, 0.001), iters=50)
print(f'Quant Backtest: Wrapped={t_wrapped:.3f} ms | Direct={t_direct:.3f} ms | Decorator Overhead={t_wrapped - t_direct:.3f} ms')

# 6. Geo Distance
from examples.geo_distance.original import accumulate_haversine_distance
from examples.geo_distance.bench import generate_trail
lats, lons, np_lats, np_lons = generate_trail(1000)
t_wrapped = measure(lambda: accumulate_haversine_distance(lats, lons), iters=50)
t_direct = measure(lambda: accumulate_haversine_distance._compiled(lats, lons), iters=50)
print(f'Geo Distance:  Wrapped={t_wrapped:.3f} ms | Direct={t_direct:.3f} ms | Decorator Overhead={t_wrapped - t_direct:.3f} ms')

# 7. AR Spatial 3D
from examples.ar_spatial.original import find_closest_point_to_ray
from examples.ar_spatial.bench import generate_cloud
xs, ys, zs, np_xs, np_ys, np_zs, ray = generate_cloud(1000)
t_wrapped = measure(lambda: find_closest_point_to_ray(xs, ys, zs, *ray), iters=50)
t_direct = measure(lambda: find_closest_point_to_ray._compiled(xs, ys, zs, *ray), iters=50)
print(f'AR Spatial 3D: Wrapped={t_wrapped:.3f} ms | Direct={t_direct:.3f} ms | Decorator Overhead={t_wrapped - t_direct:.3f} ms')
