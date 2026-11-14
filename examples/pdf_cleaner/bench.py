import gc
import json
import os
import random
import sys
import time
from typing import Callable, Dict, List

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from examples.pdf_cleaner.original import clean_pdf_text
from examples.pdf_cleaner.verify import regex_clean_pdf

def generate_bench_payloads() -> Dict[str, Dict]:
    rng = random.Random(2026)
    tokens = [
        "inter-\noperability", "trans-\n   piler", "auto-\n\nmation",
        "docu-\n   ment", "page-\nbreak", "con-\nfiguration",
        "\f", "\f\n\n", "\nPage 1\n", "\nPage 99\n", "\nPage 12345\n",
        "    ", "  \t  ", "\t\t",
        "\n\n\n", "\n\n\n\n\n", "\n", "\n\n",
        "standard", "paragraph", "content", "sentence.", "court", "ruling", "statute",
        "नमस्ते", "प्रौद्योगिकी", "दस्तावेज़", "🚀", "🔥", "12345",
    ]

    # 1. Small (~1 KB)
    s_parts = []
    while sum(len(p) for p in s_parts) < 1024:
        s_parts.append(rng.choice(tokens) + " ")
    s_text = "".join(s_parts)[:1024]

    # 2. Medium (~10 KB)
    m_parts = []
    while sum(len(p) for p in m_parts) < 10240:
        m_parts.append(rng.choice(tokens) + " ")
    m_text = "".join(m_parts)[:10240]

    # 3. Large (~100 KB)
    l_text = (m_text * 10)[:100000]

    return {
        "small": {"text": s_text, "desc": f"Small extract ({len(s_text)} chars)"},
        "medium": {"text": m_text, "desc": f"Medium document ({len(m_text)} chars)"},
        "large": {"text": l_text, "desc": f"Large corpus ({len(l_text)} chars)"},
    }

def time_callable(fn: Callable, text: str, iters: int) -> float:
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(text)
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

def main():
    print("=" * 65)
    print("STAGE D3 BENCHMARK: PDF TEXT CLEANER")
    print("=" * 65)

    py_ref = clean_pdf_text._original
    direct_mojo = clean_pdf_text._compiled
    wrapped_mojo = clean_pdf_text

    payloads = generate_bench_payloads()
    results = {}

    for p_key, p_info in payloads.items():
        text = p_info["text"]
        p_desc = p_info["desc"]
        length = len(text)

        if length < 2000:
            iters = 1000
        elif length < 20000:
            iters = 200
        else:
            iters = 30

        # Warmup
        for _ in range(min(iters // 5 + 2, 20)):
            py_ref(text)
            regex_clean_pdf(text)
            direct_mojo(text)
            wrapped_mojo(text)

        trials_py = []
        trials_regex = []
        trials_direct = []
        trials_wrapped = []

        for _ in range(5):
            trials_py.append(time_callable(py_ref, text, iters))
            trials_regex.append(time_callable(regex_clean_pdf, text, iters))
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

    out_file = "/home/gaurav/mojo-hotloop/examples/pdf_cleaner/bench_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Stage D3 benchmarks saved to {out_file}")

if __name__ == "__main__":
    main()
