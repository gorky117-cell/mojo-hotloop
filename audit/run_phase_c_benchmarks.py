import gc
import json
import os
import random
import sys
import time
from typing import Callable, Dict, List, Tuple

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from audit.unseen_text.newline_positions.original import unicode_newline_positions
from audit.unseen_text.digit_runs.original import count_ascii_digit_runs
from audit.unseen_text.mask_digits.original import mask_ascii_digits

def generate_payloads() -> Dict[str, Dict[str, str]]:
    rng = random.Random(9999)
    
    # 1. Short strings (~30-40 chars)
    short_ascii = "Invoice #84920: Amount $149.99 paid\n"
    short_mixed = "ग्राहक #58210: ₹1450 भुगतान\n🚀 OK! 2026"
    
    # 2. Medium strings (~8 KB = 8192 chars)
    words_ascii = ["function", "item123", "45678", "total_sum", "\n", "result", "val99", "check_status", "42", "run_test"]
    med_ascii_list = []
    curr_len = 0
    while curr_len < 8192:
        w = rng.choice(words_ascii) + (" " if rng.random() > 0.2 else "\n")
        med_ascii_list.append(w)
        curr_len += len(w)
    med_ascii = "".join(med_ascii_list)[:8192]
    
    words_mixed = ["नमस्ते", "दस्तावेज़", "12345", "धारा_420", "\n", "🌍", "विश्व", "🚀_99", "मूल्य_₹500", "खाता_98765"]
    med_mixed_list = []
    curr_len = 0
    while curr_len < 8192:
        w = rng.choice(words_mixed) + (" " if rng.random() > 0.2 else "\n")
        med_mixed_list.append(w)
        curr_len += len(w)
    med_mixed = "".join(med_mixed_list)[:8192]
    
    # 3. Large strings (~100 KB = 100,000 chars)
    large_ascii = (med_ascii * (100000 // len(med_ascii) + 1))[:100000]
    large_mixed = (med_mixed * (100000 // len(med_mixed) + 1))[:100000]
    
    return {
        "short_ascii": {"text": short_ascii, "len": len(short_ascii), "desc": "Short ASCII (36 chars)"},
        "short_mixed": {"text": short_mixed, "len": len(short_mixed), "desc": "Short Multilingual (38 chars)"},
        "med_ascii": {"text": med_ascii, "len": len(med_ascii), "desc": "Medium ASCII (8,192 chars)"},
        "med_mixed": {"text": med_mixed, "len": len(med_mixed), "desc": "Medium Multilingual (8,192 chars)"},
        "large_ascii": {"text": large_ascii, "len": len(large_ascii), "desc": "Large ASCII (100,000 chars)"},
        "large_mixed": {"text": large_mixed, "len": len(large_mixed), "desc": "Large Multilingual (100,000 chars)"},
    }

def time_callable(fn: Callable, arg: str, iters: int) -> float:
    """Returns elapsed time in milliseconds for iters calls."""
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(arg)
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

def benchmark_function(name: str, wrapped_fn: Callable, payloads: Dict[str, Dict[str, str]]):
    pure_py = wrapped_fn._original
    direct_mojo = wrapped_fn._compiled
    
    print(f"\n=======================================================")
    print(f"BENCHMARK: {name}")
    print(f"=======================================================")
    
    results = {}
    
    for p_key, p_info in payloads.items():
        text = p_info["text"]
        p_desc = p_info["desc"]
        length = p_info["len"]
        
        # Decide iterations based on payload size
        if length < 100:
            iters = 10000
        elif length < 10000:
            iters = 500
        else:
            iters = 50
            
        # Warmup
        for _ in range(min(iters // 5 + 2, 50)):
            pure_py(text)
            wrapped_fn(text)
            direct_mojo(text)
            
        trials_py = []
        trials_direct = []
        trials_wrapped = []
        
        for _ in range(5):
            trials_py.append(time_callable(pure_py, text, iters))
            trials_direct.append(time_callable(direct_mojo, text, iters))
            trials_wrapped.append(time_callable(wrapped_fn, text, iters))
            
        py_mean = sum(trials_py) / len(trials_py)
        direct_mean = sum(trials_direct) / len(trials_direct)
        wrapped_mean = sum(trials_wrapped) / len(trials_wrapped)
        
        speedup_direct = py_mean / direct_mean if direct_mean > 0 else 0
        speedup_wrapped = py_mean / wrapped_mean if wrapped_mean > 0 else 0
        
        print(f"\n[{p_desc}] (iters={iters})")
        print(f"  Python 3.12:    {py_mean * 1000:8.2f} µs  (trial p50: {sorted(trials_py)[2] * 1000:8.2f} µs)")
        print(f"  Mojo Direct:    {direct_mean * 1000:8.2f} µs  (trial p50: {sorted(trials_direct)[2] * 1000:8.2f} µs) -> {speedup_direct:6.2f}x speedup")
        print(f"  Mojo @hotloop:  {wrapped_mean * 1000:8.2f} µs  (trial p50: {sorted(trials_wrapped)[2] * 1000:8.2f} µs) -> {speedup_wrapped:6.2f}x speedup")
        print(f"  Decorator cost: {(wrapped_mean - direct_mean) * 1000:8.2f} µs")
        
        results[p_key] = {
            "desc": p_desc,
            "len": length,
            "iters": iters,
            "py_ms": py_mean,
            "mojo_direct_ms": direct_mean,
            "mojo_wrapped_ms": wrapped_mean,
            "speedup_direct": speedup_direct,
            "speedup_wrapped": speedup_wrapped,
            "trials_py_ms": trials_py,
            "trials_direct_ms": trials_direct,
            "trials_wrapped_ms": trials_wrapped,
        }
    return results

def main():
    payloads = generate_payloads()
    all_results = {}
    
    all_results["unicode_newline_positions"] = benchmark_function(
        "unicode_newline_positions", unicode_newline_positions, payloads
    )
    all_results["count_ascii_digit_runs"] = benchmark_function(
        "count_ascii_digit_runs", count_ascii_digit_runs, payloads
    )
    all_results["mask_ascii_digits"] = benchmark_function(
        "mask_ascii_digits", mask_ascii_digits, payloads
    )
    
    out_file = "/home/gaurav/mojo-hotloop/audit/phase_c_benchmarks.json"
    with open(out_file, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n[✓] All benchmarks complete. Saved results to {out_file}")

if __name__ == "__main__":
    main()
