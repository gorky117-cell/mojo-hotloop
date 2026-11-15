"""Run CPython, AST Mojo Direct, Public @hotloop, Numba, NumPy, RapidFuzz, Compiled Regex benchmarks."""
import gc
import json
import math
import os
import resource
import statistics
import sys
import time
from typing import Any, Callable, Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

import numpy as np
from numba import njit

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
from examples.ar_spatial.verify import numpy_closest_point_to_ray
from examples.geo_distance.original import accumulate_haversine_distance
from examples.ocr_matcher.original import find_closest_match
from examples.ocr_matcher.verify import rapidfuzz_find_closest
from examples.pdf_cleaner.original import clean_pdf_text
from examples.pdf_cleaner.verify import regex_clean_pdf
from examples.pii_scrubber.original import scrub_pii
from examples.pii_scrubber.verify import regex_scrub_pii
from examples.quant_backtest.original import stateful_trailing_backtest
from examples.rag_chunker.original import chunk_document


@njit
def numba_backtest(ticks: int, start_price: float, stop_pct: float, fee_rate: float) -> float:
    if ticks <= 0:
        return start_price
    price = start_price
    peak_price = start_price
    cash = 0.0
    units = 1.0
    in_position = True
    cooldown = 0
    lcg_state = 42
    for _ in range(ticks):
        lcg_state = (1664525 * lcg_state + 1013904223) & 0xFFFFFFFF
        rand_val = lcg_state / 4294967296.0
        price = price * (1.0 + (rand_val - 0.5) * 0.02)
        if in_position:
            if price > peak_price:
                peak_price = price
            elif stop_pct > 0.0 and price <= peak_price * (1.0 - stop_pct):
                cash = units * price * (1.0 - fee_rate)
                units = 0.0
                in_position = False
                cooldown = 5
        else:
            if cooldown > 0:
                cooldown -= 1
            if cooldown == 0:
                units = (cash * (1.0 - fee_rate)) / price
                cash = 0.0
                in_position = True
                peak_price = price
    return units * price if in_position else cash


@njit
def numba_closest_point_to_ray(xs: np.ndarray, ys: np.ndarray, zs: np.ndarray, ray_ox: float, ray_oy: float, ray_oz: float, ray_dx: float, ray_dy: float, ray_dz: float) -> int:
    n = len(xs)
    if n == 0 or len(ys) != n or len(zs) != n:
        return -1
    dir_len_sq = ray_dx * ray_dx + ray_dy * ray_dy + ray_dz * ray_dz
    if dir_len_sq <= 0.0:
        return -1
    inv_len = 1.0 / math.sqrt(dir_len_sq)
    dx, dy, dz = ray_dx * inv_len, ray_dy * inv_len, ray_dz * inv_len
    best_idx = -1
    min_dist_sq = 1e30
    for i in range(n):
        vx, vy, vz = xs[i] - ray_ox, ys[i] - ray_oy, zs[i] - ray_oz
        t = vx * dx + vy * dy + vz * dz
        if t < 0.0:
            t = 0.0
        wx, wy, wz = vx - t * dx, vy - t * dy, vz - t * dz
        dist_sq = wx * wx + wy * wy + wz * wz
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_idx = i
    return best_idx


@njit
def numba_haversine(lats: np.ndarray, lons: np.ndarray) -> float:
    n = len(lats)
    if n <= 1:
        return 0.0
    total_dist = 0.0
    r = 6371.0
    rad_factor = 3.141592653589793 / 180.0
    for i in range(1, n):
        lat1 = lats[i - 1] * rad_factor
        lon1 = lons[i - 1] * rad_factor
        lat2 = lats[i] * rad_factor
        lon2 = lons[i] * rad_factor
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        sdlat = math.sin(dlat * 0.5)
        sdlon = math.sin(dlon * 0.5)
        a = sdlat * sdlat + math.cos(lat1) * math.cos(lat2) * sdlon * sdlon
        if a > 1.0:
            a = 1.0
        elif a < 0.0:
            a = 0.0
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        total_dist += r * c
    return total_dist


def numpy_haversine(lat_arr: np.ndarray, lon_arr: np.ndarray) -> float:
    if len(lat_arr) <= 1:
        return 0.0
    lat_r = np.radians(lat_arr)
    lon_r = np.radians(lon_arr)
    dlat = np.diff(lat_r)
    dlon = np.diff(lon_r)
    a = np.sin(dlat * 0.5) ** 2 + np.cos(lat_r[:-1]) * np.cos(lat_r[1:]) * np.sin(dlon * 0.5) ** 2
    a = np.clip(a, 0.0, 1.0)
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return float(np.sum(6371.0 * c))


def measure(fn: Callable, args: tuple, iters: int, trials: int = 5) -> Dict[str, Any]:
    # Warmup
    for _ in range(min(max(iters // 4, 2), 10)):
        res = fn(*args)
    samples_ms: List[float] = []
    for _ in range(trials):
        gc.disable()
        t0 = time.perf_counter_ns()
        for _ in range(iters):
            res = fn(*args)
        t1 = time.perf_counter_ns()
        gc.enable()
        samples_ms.append((t1 - t0) / (iters * 1_000_000.0))
    s = sorted(samples_ms)
    n = len(s)
    return {
        "p50_ms": statistics.median(s),
        "p95_ms": s[min(n - 1, int(math.ceil(0.95 * n)) - 1)],
        "mean_ms": statistics.mean(s),
        "stdev_ms": statistics.stdev(s) if n > 1 else 0.0,
        "min_ms": s[0],
        "max_ms": s[-1],
        "trials_ms": s,
    }


def main():
    out_path = sys.argv[1]
    results: Dict[str, Any] = {
        "compile_times_ms": {},
        "workloads": {},
        "parity_checks": {},
        "peak_rss_kb": 0,
    }

    # Measure Numba compile times
    t0 = time.perf_counter_ns()
    numba_backtest(10, 100.0, 0.05, 0.001)
    results["compile_times_ms"]["numba_quant"] = (time.perf_counter_ns() - t0) / 1_000_000.0

    d = np.array([1.0, 2.0], dtype=np.float64)
    t0 = time.perf_counter_ns()
    numba_closest_point_to_ray(d, d, d, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0)
    results["compile_times_ms"]["numba_ar_spatial"] = (time.perf_counter_ns() - t0) / 1_000_000.0

    t0 = time.perf_counter_ns()
    numba_haversine(d, d)
    results["compile_times_ms"]["numba_geo_distance"] = (time.perf_counter_ns() - t0) / 1_000_000.0

    # 1. quant_backtest
    qp = get_quant_payloads()["ticks_100k"]
    args = (qp["ticks"], qp["start_price"], qp["stop_pct"], qp["fee_rate"])
    py_r = stateful_trailing_backtest._original(*args)
    mj_r = stateful_trailing_backtest(*args)
    nb_r = numba_backtest(*args)
    results["parity_checks"]["quant_backtest"] = {
        "mojo_eq": abs(py_r - mj_r) < 1e-9,
        "numba_eq": abs(py_r - nb_r) < 1e-9,
        "backend": stateful_trailing_backtest._last_backend,
    }
    results["workloads"]["quant_backtest"] = {
        "ticks_100k": {
            "desc": qp["desc"],
            "cpython": measure(stateful_trailing_backtest._original, args, qp["iters"]),
            "mojo_direct": measure(stateful_trailing_backtest._compiled, args, qp["iters"]),
            "mojo_hotloop": measure(stateful_trailing_backtest, args, qp["iters"]),
            "numba": measure(numba_backtest, args, qp["iters"]),
        }
    }

    # 2. ar_spatial
    ar_out = {}
    ar_parity = {}
    for k, v in get_ar_spatial_payloads().items():
        py_args = (v["xs"], v["ys"], v["zs"], *v["ray"])
        np_args = (np.array(v["xs"], dtype=np.float64), np.array(v["ys"], dtype=np.float64), np.array(v["zs"], dtype=np.float64), *v["ray"])
        py_r = find_closest_point_to_ray._original(*py_args)
        mj_np_r = find_closest_point_to_ray(*np_args)
        mj_list_fb_r = find_closest_point_to_ray(*py_args)
        fb_backend = find_closest_point_to_ray._last_backend
        np_r = numpy_closest_point_to_ray(*np_args)
        nb_r = numba_closest_point_to_ray(*np_args)
        ar_parity[k] = {
            "mojo_np_eq": py_r == mj_np_r,
            "mojo_list_fallback_eq": py_r == mj_list_fb_r,
            "mojo_list_fallback_backend": fb_backend,
            "numpy_eq": py_r == np_r,
            "numba_eq": py_r == nb_r,
        }
        ar_out[k] = {
            "desc": v["desc"],
            "cpython": measure(find_closest_point_to_ray._original, py_args, v["iters"]),
            "numpy": measure(numpy_closest_point_to_ray, np_args, v["iters"]),
            "numba": measure(numba_closest_point_to_ray, np_args, v["iters"]),
            "mojo_direct": measure(find_closest_point_to_ray._compiled, np_args, v["iters"]),
            "mojo_hotloop": measure(find_closest_point_to_ray, np_args, v["iters"]),
        }
    results["workloads"]["ar_spatial"] = ar_out
    results["parity_checks"]["ar_spatial"] = ar_parity

    # 3. geo_distance
    geo_out = {}
    geo_parity = {}
    for k, v in get_geo_payloads().items():
        py_args = (v["lats"], v["lons"])
        np_args = (np.array(v["lats"], dtype=np.float64), np.array(v["lons"], dtype=np.float64))
        py_r = accumulate_haversine_distance._original(*py_args)
        mj_r = accumulate_haversine_distance(*np_args)
        mj_fb_r = accumulate_haversine_distance(*py_args)
        fb_backend = accumulate_haversine_distance._last_backend
        np_r = numpy_haversine(*np_args)
        nb_r = numba_haversine(*np_args)
        geo_parity[k] = {
            "mojo_np_eq": abs(py_r - mj_r) < 1e-6,
            "mojo_list_fallback_eq": abs(py_r - mj_fb_r) < 1e-6,
            "mojo_list_fallback_backend": fb_backend,
            "numpy_eq": abs(py_r - np_r) < 1e-6,
            "numba_eq": abs(py_r - nb_r) < 1e-6,
        }
        geo_out[k] = {
            "desc": v["desc"],
            "cpython": measure(accumulate_haversine_distance._original, py_args, v["iters"]),
            "numpy": measure(numpy_haversine, np_args, v["iters"]),
            "numba": measure(numba_haversine, np_args, v["iters"]),
            "mojo_direct": measure(accumulate_haversine_distance._compiled, np_args, v["iters"]),
            "mojo_hotloop": measure(accumulate_haversine_distance, np_args, v["iters"]),
        }
    results["workloads"]["geo_distance"] = geo_out
    results["parity_checks"]["geo_distance"] = geo_parity

    # 4. pdf_cleaner
    pdf_out = {}
    pdf_parity = {}
    for k, v in get_pdf_payloads().items():
        args = (v["text"],)
        py_r = clean_pdf_text._original(*args)
        mj_r = clean_pdf_text(*args)
        re_r = regex_clean_pdf(*args)
        pdf_parity[k] = {
            "mojo_eq": py_r == mj_r,
            "regex_eq": py_r == re_r,
            "backend": clean_pdf_text._last_backend,
        }
        pdf_out[k] = {
            "desc": v["desc"],
            "cpython": measure(clean_pdf_text._original, args, v["iters"]),
            "regex": measure(regex_clean_pdf, args, v["iters"]),
            "mojo_direct": measure(clean_pdf_text._compiled, args, v["iters"]),
            "mojo_hotloop": measure(clean_pdf_text, args, v["iters"]),
        }
    results["workloads"]["pdf_cleaner"] = pdf_out
    results["parity_checks"]["pdf_cleaner"] = pdf_parity

    # 5. pii_scrubber
    pii_out = {}
    pii_parity = {}
    for k, v in get_pii_payloads().items():
        args = (v["text"],)
        py_r = scrub_pii._original(*args)
        mj_r = scrub_pii(*args)
        re_r = regex_scrub_pii(*args)
        pii_parity[k] = {
            "mojo_eq": py_r == mj_r,
            "regex_eq": py_r == re_r,
            "backend": scrub_pii._last_backend,
        }
        pii_out[k] = {
            "desc": v["desc"],
            "cpython": measure(scrub_pii._original, args, v["iters"]),
            "regex": measure(regex_scrub_pii, args, v["iters"]),
            "mojo_direct": measure(scrub_pii._compiled, args, v["iters"]),
            "mojo_hotloop": measure(scrub_pii, args, v["iters"]),
        }
    results["workloads"]["pii_scrubber"] = pii_out
    results["parity_checks"]["pii_scrubber"] = pii_parity

    # 6. ocr_matcher (both default fallback AND forced native)
    ocr_out = {}
    ocr_parity = {}
    for k, v in get_ocr_payloads().items():
        args = (v["query"], v["candidates"], v["max_d"])
        py_r = find_closest_match._original(*args)
        rf_r = rapidfuzz_find_closest(*args)
        find_closest_match._force_native = False
        fb_r = find_closest_match(*args)
        fb_backend = find_closest_match._last_backend
        find_closest_match._force_native = True
        mj_r = find_closest_match(*args)
        native_backend = find_closest_match._last_backend
        ocr_parity[k] = {
            "mojo_eq": py_r == mj_r,
            "rapidfuzz_eq": py_r == rf_r,
            "default_backend": fb_backend,
            "forced_backend": native_backend,
        }
        find_closest_match._force_native = False
        m_default = measure(find_closest_match, args, v["iters"])
        find_closest_match._force_native = True
        m_forced = measure(find_closest_match, args, v["iters"])
        find_closest_match._force_native = False
        ocr_out[k] = {
            "desc": v["desc"],
            "cpython": measure(find_closest_match._original, args, v["iters"]),
            "rapidfuzz": measure(rapidfuzz_find_closest, args, v["iters"]),
            "mojo_direct": measure(find_closest_match._compiled, args, v["iters"]),
            "mojo_hotloop_default": m_default,
            "mojo_hotloop_forced": m_forced,
        }
    results["workloads"]["ocr_matcher"] = ocr_out
    results["parity_checks"]["ocr_matcher"] = ocr_parity

    # 7. rag_chunker (both default fallback AND forced native)
    rag_out = {}
    rag_parity = {}
    for k, v in get_rag_payloads().items():
        args = (v["text"], v["size"], v["overlap"])
        py_r = chunk_document._original(*args)
        chunk_document._force_native = False
        fb_r = chunk_document(*args)
        fb_backend = chunk_document._last_backend
        chunk_document._force_native = True
        mj_r = chunk_document(*args)
        native_backend = chunk_document._last_backend
        rag_parity[k] = {
            "mojo_eq": py_r == mj_r,
            "default_backend": fb_backend,
            "forced_backend": native_backend,
        }
        chunk_document._force_native = False
        m_default = measure(chunk_document, args, v["iters"])
        chunk_document._force_native = True
        m_forced = measure(chunk_document, args, v["iters"])
        chunk_document._force_native = False
        rag_out[k] = {
            "desc": v["desc"],
            "cpython": measure(chunk_document._original, args, v["iters"]),
            "mojo_direct": measure(chunk_document._compiled, args, v["iters"]),
            "mojo_hotloop_default": m_default,
            "mojo_hotloop_forced": m_forced,
        }
    results["workloads"]["rag_chunker"] = rag_out
    results["parity_checks"]["rag_chunker"] = rag_parity

    results["peak_rss_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[hotloop runner] wrote {out_path}")


if __name__ == "__main__":
    main()
