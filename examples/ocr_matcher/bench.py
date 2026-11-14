import gc
import json
import os
import random
import sys
import time
from typing import Callable, Dict, List

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from rapidfuzz.distance import Levenshtein
from examples.ocr_matcher.original import find_closest_match
from examples.ocr_matcher.verify import rapidfuzz_find_closest

def generate_bench_payloads() -> Dict[str, Dict]:
    rng = random.Random(42)
    vocab = [
        "invoice", "receipt", "customer", "vendor", "payment",
        "balance", "statement", "account", "transaction", "subtotal",
        "discount", "shipping", "quantity", "description", "reference",
        "inventory", "department", "organization", "authorized", "signature",
    ]

    def mutate(w: str) -> str:
        chars = list(w)
        if len(chars) > 2:
            chars.pop(rng.randint(0, len(chars) - 1))
        chars.insert(rng.randint(0, len(chars)), rng.choice("abcde"))
        return "".join(chars)

    # 1. Small corpus (20 candidates, query ~8 chars)
    s_cands = [mutate(rng.choice(vocab)) for _ in range(20)]
    s_query = mutate("invoice")

    # 2. Medium corpus (200 candidates, query ~10 chars)
    m_cands = [mutate(rng.choice(vocab)) for _ in range(200)]
    m_query = mutate("transaction")

    # 3. Large corpus (2,000 candidates, query ~12 chars)
    l_cands = [mutate(rng.choice(vocab)) for _ in range(2000)]
    l_query = mutate("organization")

    return {
        "small": {"query": s_query, "candidates": s_cands, "max_d": 3, "desc": f"Small corpus (20 candidates)"},
        "medium": {"query": m_query, "candidates": m_cands, "max_d": 3, "desc": f"Medium corpus (200 candidates)"},
        "large": {"query": l_query, "candidates": l_cands, "max_d": 3, "desc": f"Large corpus (2,000 candidates)"},
    }

def time_callable(fn: Callable, query: str, cands: List[str], max_d: int, iters: int) -> float:
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(query, cands, max_d)
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

def main():
    print("=" * 65)
    print("STAGE D4 BENCHMARK: OCR FUZZY MATCHER")
    print("=" * 65)

    py_ref = find_closest_match._original
    direct_mojo = find_closest_match._compiled

    # Use force_native wrapper
    os.environ["HOTLOOP_FORCE_NATIVE"] = "1"
    wrapped_mojo = find_closest_match

    payloads = generate_bench_payloads()
    results = {}

    for p_key, p_info in payloads.items():
        query = p_info["query"]
        cands = p_info["candidates"]
        max_d = p_info["max_d"]
        p_desc = p_info["desc"]
        num_cands = len(cands)

        if num_cands < 50:
            iters = 500
        elif num_cands < 500:
            iters = 50
        else:
            iters = 10

        # Warmup
        for _ in range(min(iters // 5 + 2, 10)):
            py_ref(query, cands, max_d)
            rapidfuzz_find_closest(query, cands, max_d)
            direct_mojo(query, cands, max_d)
            wrapped_mojo(query, cands, max_d)

        trials_py = []
        trials_rf = []
        trials_direct = []
        trials_wrapped = []

        for _ in range(5):
            trials_py.append(time_callable(py_ref, query, cands, max_d, iters))
            trials_rf.append(time_callable(rapidfuzz_find_closest, query, cands, max_d, iters))
            trials_direct.append(time_callable(direct_mojo, query, cands, max_d, iters))
            trials_wrapped.append(time_callable(wrapped_mojo, query, cands, max_d, iters))

        py_mean = sum(trials_py) / len(trials_py)
        rf_mean = sum(trials_rf) / len(trials_rf)
        direct_mean = sum(trials_direct) / len(trials_direct)
        wrapped_mean = sum(trials_wrapped) / len(trials_wrapped)

        speedup_vs_py = py_mean / wrapped_mean if wrapped_mean > 0 else 0
        speedup_vs_rf = rf_mean / wrapped_mean if wrapped_mean > 0 else 0

        print(f"\n[{p_desc}] (iters={iters})")
        print(f"  Python 3.12:    {py_mean * 1000:8.2f} µs  (p50: {sorted(trials_py)[2] * 1000:8.2f} µs)")
        print(f"  RapidFuzz (C):  {rf_mean * 1000:8.2f} µs  (p50: {sorted(trials_rf)[2] * 1000:8.2f} µs) -> {rf_mean / wrapped_mean:5.2f}x vs Mojo @hotloop")
        print(f"  Mojo Direct:    {direct_mean * 1000:8.2f} µs  (p50: {sorted(trials_direct)[2] * 1000:8.2f} µs)")
        print(f"  Mojo @hotloop:  {wrapped_mean * 1000:8.2f} µs  (p50: {sorted(trials_wrapped)[2] * 1000:8.2f} µs) -> {speedup_vs_py:5.2f}x vs Python")

        results[p_key] = {
            "desc": p_desc,
            "candidates": num_cands,
            "py_ms": py_mean,
            "rapidfuzz_ms": rf_mean,
            "mojo_direct_ms": direct_mean,
            "mojo_wrapped_ms": wrapped_mean,
            "speedup_vs_py": speedup_vs_py,
            "speedup_vs_rf": speedup_vs_rf,
        }

    out_file = "/home/gaurav/mojo-hotloop/examples/ocr_matcher/bench_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Stage D4 benchmarks saved to {out_file}")

if __name__ == "__main__":
    main()
