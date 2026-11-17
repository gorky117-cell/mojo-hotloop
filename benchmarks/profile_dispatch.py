"""Detailed profiling harness for @hotloop dispatch path and execution stages."""
import gc
import json
import math
import os
import statistics
import sys
import time
from typing import Any, Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

import numpy as np

from benchmarks.payload_gen import (
    get_ar_spatial_payloads,
    get_geo_payloads,
    get_ocr_payloads,
    get_pdf_payloads,
    get_pii_payloads,
    get_quant_payloads,
    get_rag_payloads,
)
from examples.ar_spatial.original import find_closest_point_to_ray
from examples.geo_distance.original import accumulate_haversine_distance
from examples.ocr_matcher.original import find_closest_match
from examples.pdf_cleaner.original import clean_pdf_text
from examples.pii_scrubber.original import scrub_pii
from examples.quant_backtest.original import stateful_trailing_backtest
from examples.rag_chunker.original import chunk_document
from hotloop.decorator import _is_slower_workload, _has_unsupported_surrogates


def profile_workload(name: str, fn, args, iters: int = 500, trials: int = 20) -> Dict[str, Any]:
    # Ensure warmup
    for _ in range(10):
        fn(*args)

    # 1. Total wrapper time (end-to-end @hotloop)
    wrapper_times_ns: List[float] = []
    for _ in range(trials):
        gc.disable()
        t0 = time.perf_counter_ns()
        for _ in range(iters):
            fn(*args)
        t1 = time.perf_counter_ns()
        gc.enable()
        wrapper_times_ns.append((t1 - t0) / iters)

    total_wrapper_ns = statistics.median(wrapper_times_ns)

    # 2. Native direct call time (_compiled)
    native_times_ns: List[float] = []
    if getattr(fn, "_compiled", None) is not None:
        compiled_fn = fn._compiled
        for _ in range(trials):
            gc.disable()
            t0 = time.perf_counter_ns()
            for _ in range(iters):
                compiled_fn(*args)
            t1 = time.perf_counter_ns()
            gc.enable()
            native_times_ns.append((t1 - t0) / iters)
        native_kernel_ns = statistics.median(native_times_ns)
    else:
        native_kernel_ns = 0.0

    # 3. Pure Python original time (_original)
    original_times_ns: List[float] = []
    orig_fn = fn._original
    for _ in range(trials):
        gc.disable()
        t0 = time.perf_counter_ns()
        for _ in range(max(iters // 5, 5)):
            orig_fn(*args)
        t1 = time.perf_counter_ns()
        gc.enable()
        original_times_ns.append((t1 - t0) / max(iters // 5, 5))
    orig_python_ns = statistics.median(original_times_ns)

    # 4. Measure isolated dispatch components
    # 4a. Signature binding / validation overhead
    _sig = getattr(fn, "_sig", None)
    t0 = time.perf_counter_ns()
    for _ in range(10000):
        # Emulate decorator binding check
        _ = (kwargs or len(args) != 4) if False else args
    t1 = time.perf_counter_ns()
    arg_bind_ns = (t1 - t0) / 10000

    # 4b. Slower workload check (_is_slower_workload)
    t0 = time.perf_counter_ns()
    for _ in range(10000):
        _is_slower_workload(args, {}, fn._original)
    t1 = time.perf_counter_ns()
    qualification_ns = (t1 - t0) / 10000

    # 4c. Surrogate check (_has_unsupported_surrogates)
    t0 = time.perf_counter_ns()
    for _ in range(10000):
        _has_unsupported_surrogates(args, {})
    t1 = time.perf_counter_ns()
    surrogate_check_ns = (t1 - t0) / 10000

    # 4d. Cache / mtime check
    mod_file = getattr(fn, "_mod_file", None)
    t0 = time.perf_counter_ns()
    for _ in range(10000):
        _ = time.monotonic()
        if mod_file:
            _ = os.path.getmtime(mod_file)
    t1 = time.perf_counter_ns()
    cache_check_ns = (t1 - t0) / 10000

    dispatch_overhead_ns = max(0.0, total_wrapper_ns - native_kernel_ns)

    return {
        "name": name,
        "total_wrapper_us": total_wrapper_ns / 1000.0,
        "native_kernel_us": native_kernel_ns / 1000.0,
        "pure_python_us": orig_python_ns / 1000.0,
        "dispatch_overhead_us": dispatch_overhead_ns / 1000.0,
        "dispatch_overhead_pct": (dispatch_overhead_ns / total_wrapper_ns * 100.0) if total_wrapper_ns > 0 else 0.0,
        "components_ns": {
            "arg_bind_ns": arg_bind_ns,
            "qualification_ns": qualification_ns,
            "surrogate_check_ns": surrogate_check_ns,
            "cache_check_ns": cache_check_ns,
        },
    }


def main():
    print("=== PROFILING @hotloop DISPATCH & EXECUTION BREAKDOWN ===")

    # 1. Quant Backtest
    qp = get_quant_payloads()["ticks_100k"]
    q_args = (qp["ticks"], qp["start_price"], qp["stop_pct"], qp["fee_rate"])
    prof_quant = profile_workload("quant_backtest", stateful_trailing_backtest, q_args, iters=50, trials=15)

    # 2. AR Spatial
    ap = get_ar_spatial_payloads()["large"]
    ar_np_args = (np.array(ap["xs"], dtype=np.float64), np.array(ap["ys"], dtype=np.float64), np.array(ap["zs"], dtype=np.float64), *ap["ray"])
    prof_ar = profile_workload("ar_spatial_large", find_closest_point_to_ray, ar_np_args, iters=200, trials=15)

    # 3. Geo Distance
    gp = get_geo_payloads()["large"]
    geo_np_args = (np.array(gp["lats"], dtype=np.float64), np.array(gp["lons"], dtype=np.float64))
    prof_geo = profile_workload("geo_distance_large", accumulate_haversine_distance, geo_np_args, iters=100, trials=15)

    # 4. PDF Cleaner
    pdf_p = get_pdf_payloads()["large"]
    pdf_args = (pdf_p["text"],)
    prof_pdf = profile_workload("pdf_cleaner_large", clean_pdf_text, pdf_args, iters=20, trials=15)

    # 5. PII Scrubber
    pii_p = get_pii_payloads()["large"]
    pii_args = (pii_p["text"],)
    prof_pii = profile_workload("pii_scrubber_large", scrub_pii, pii_args, iters=10, trials=15)

    # 6. OCR Matcher (Forced Native)
    ocr_p = get_ocr_payloads()["large"]
    ocr_args = (ocr_p["query"], ocr_p["candidates"], ocr_p["max_d"])
    find_closest_match._force_native = True
    prof_ocr = profile_workload("ocr_matcher_large_forced", find_closest_match, ocr_args, iters=30, trials=15)
    find_closest_match._force_native = False

    # 7. RAG Chunker (Forced Native)
    rag_p = get_rag_payloads()["large"]
    rag_args = (rag_p["text"], rag_p["size"], rag_p["overlap"])
    chunk_document._force_native = True
    prof_rag = profile_workload("rag_chunker_large_forced", chunk_document, rag_args, iters=10, trials=10)
    chunk_document._force_native = False

    results = [prof_quant, prof_ar, prof_geo, prof_pdf, prof_pii, prof_ocr, prof_rag]

    for r in results:
        print(f"\n--- {r['name']} ---")
        print(f"Total @hotloop wrapper: {r['total_wrapper_us']:.2f} us")
        print(f"Native kernel (_compiled): {r['native_kernel_us']:.2f} us")
        print(f"Pure Python (_original): {r['pure_python_us']:.2f} us")
        print(f"Dispatch overhead: {r['dispatch_overhead_us']:.2f} us ({r['dispatch_overhead_pct']:.2f}%)")
        print(f"Breakdown: bind={r['components_ns']['arg_bind_ns']:.1f}ns | qualify={r['components_ns']['qualification_ns']:.1f}ns | surrogate={r['components_ns']['surrogate_check_ns']:.1f}ns | cache_mtime={r['components_ns']['cache_check_ns']:.1f}ns")

    out_file = os.path.join(REPO_ROOT, "benchmarks", "profile_dispatch_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved profile results to {out_file}")


if __name__ == "__main__":
    main()
