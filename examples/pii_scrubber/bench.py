import gc
import json
import os
import random
import sys
import time
from typing import Callable, Dict, List

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from examples.pii_scrubber.original import scrub_pii
from examples.pii_scrubber.verify import regex_scrub_pii, gen_synthetic_card, gen_synthetic_aadhaar, gen_synthetic_phone, gen_synthetic_pan

def generate_bench_payloads() -> Dict[str, Dict[str, str]]:
    rng = random.Random(1337)
    
    # 1. Short text (~50 chars)
    short_text = f"Notice: Account card {gen_synthetic_card(rng)} charged $45."
    
    # 2. Medium document (~8 KB = 8,192 chars)
    med_lines = []
    curr_len = 0
    templates = [
        "Audit log entry #{id}: Customer with PAN {pan} updated phone to {phone}.\n",
        "Transaction verification: Card {card} approved, Aadhaar {aadhaar} KYC verified.\n",
        "System notification: User {id} invoice paid on 2026-11-15 for ₹5,000.\n",
        "नमस्ते ग्राहक #{id}: आधार {aadhaar} सफलतापूर्वक सत्यापित 🚀\n",
    ]
    uid = 1000
    while curr_len < 8192:
        tmpl = rng.choice(templates)
        line = tmpl.format(
            id=uid,
            card=gen_synthetic_card(rng),
            aadhaar=gen_synthetic_aadhaar(rng),
            phone=gen_synthetic_phone(rng),
            pan=gen_synthetic_pan(rng),
        )
        med_lines.append(line)
        curr_len += len(line)
        uid += 1
    med_text = "".join(med_lines)[:8192]
    
    # 3. Large document (~100 KB = 100,000 chars)
    large_text = (med_text * (100000 // len(med_text) + 1))[:100000]
    
    return {
        "short": {"text": short_text, "len": len(short_text), "desc": f"Short record ({len(short_text)} chars)"},
        "medium": {"text": med_text, "len": len(med_text), "desc": f"Medium document ({len(med_text)} chars)"},
        "large": {"text": large_text, "len": len(large_text), "desc": f"Large corpus ({len(large_text)} chars)"},
    }

def time_callable(fn: Callable, arg: str, iters: int) -> float:
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(arg)
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

def main():
    print("=" * 65)
    print("STAGE D1 BENCHMARK: PII SCRUBBER")
    print("=" * 65)
    
    py_ref = scrub_pii._original
    direct_mojo = scrub_pii._compiled
    wrapped_mojo = scrub_pii
    
    payloads = generate_bench_payloads()
    results = {}
    
    for p_key, p_info in payloads.items():
        text = p_info["text"]
        p_desc = p_info["desc"]
        length = p_info["len"]
        
        if length < 200:
            iters = 5000
        elif length < 20000:
            iters = 300
        else:
            iters = 30
            
        # Warmup
        for _ in range(min(iters // 5 + 2, 20)):
            py_ref(text)
            regex_scrub_pii(text)
            direct_mojo(text)
            wrapped_mojo(text)
            
        trials_py = []
        trials_regex = []
        trials_direct = []
        trials_wrapped = []
        
        for _ in range(5):
            trials_py.append(time_callable(py_ref, text, iters))
            trials_regex.append(time_callable(regex_scrub_pii, text, iters))
            trials_direct.append(time_callable(direct_mojo, text, iters))
            trials_wrapped.append(time_callable(wrapped_mojo, text, iters))
            
        py_mean = sum(trials_py) / len(trials_py)
        regex_mean = sum(trials_regex) / len(trials_regex)
        direct_mean = sum(trials_direct) / len(trials_direct)
        wrapped_mean = sum(trials_wrapped) / len(trials_wrapped)
        
        speedup_vs_py = py_mean / wrapped_mean if wrapped_mean > 0 else 0
        speedup_vs_regex = regex_mean / wrapped_mean if wrapped_mean > 0 else 0
        
        print(f"\n[{p_desc}] (iters={iters})")
        print(f"  Python 3.12:    {py_mean * 1000:8.2f} µs  (p50: {sorted(trials_py)[2] * 1000:8.2f} µs)")
        print(f"  Compiled Regex: {regex_mean * 1000:8.2f} µs  (p50: {sorted(trials_regex)[2] * 1000:8.2f} µs) -> {regex_mean / wrapped_mean:5.2f}x vs Mojo @hotloop")
        print(f"  Mojo Direct:    {direct_mean * 1000:8.2f} µs  (p50: {sorted(trials_direct)[2] * 1000:8.2f} µs)")
        print(f"  Mojo @hotloop:  {wrapped_mean * 1000:8.2f} µs  (p50: {sorted(trials_wrapped)[2] * 1000:8.2f} µs) -> {speedup_vs_py:5.2f}x vs Python")
        
        results[p_key] = {
            "desc": p_desc,
            "len": length,
            "py_ms": py_mean,
            "regex_ms": regex_mean,
            "mojo_direct_ms": direct_mean,
            "mojo_wrapped_ms": wrapped_mean,
            "speedup_vs_py": speedup_vs_py,
            "speedup_vs_regex": speedup_vs_regex,
        }
        
    out_file = "/home/gaurav/mojo-hotloop/examples/pii_scrubber/bench_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Stage D1 benchmarks saved to {out_file}")

if __name__ == "__main__":
    main()
