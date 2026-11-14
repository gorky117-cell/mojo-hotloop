import gc
import json
import os
import random
import sys
import time
from typing import Callable, Dict, List

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from examples.rag_chunker.original import chunk_document

def generate_bench_payloads() -> Dict[str, Dict]:
    rng = random.Random(2026)
    words = [
        "retrieval-augmented", "generation", "pipeline", "documents", "embedding",
        "semantic", "vector", "database", "transformer", "attention", "context",
        "knowledge", "graph", "chunking", "strategy", "sliding", "window",
        "नमस्ते", "प्रणाली", "दस्तावेज़", "सूचना", "प्रौद्योगिकी",
        "🚀", "⚡", "🔍", "📊", "🧠",
        "section", "paragraph", "tokenization", "optimization", "latency",
    ]

    # 1. Small (~1 KB)
    s_parts = []
    while sum(len(p) for p in s_parts) < 1024:
        s_parts.append(rng.choice(words) + rng.choice([" ", " ", "\n", ", "]))
    s_text = "".join(s_parts)[:1024]

    # 2. Medium (~10 KB)
    m_parts = []
    while sum(len(p) for p in m_parts) < 10240:
        m_parts.append(rng.choice(words) + rng.choice([" ", " ", "\n", ". ", "; "]))
    m_text = "".join(m_parts)[:10240]

    # 3. Large (~100 KB)
    l_text = (m_text * 10)[:100000]

    return {
        "small": {"text": s_text, "size": 250, "overlap": 50, "desc": f"Small document ({len(s_text)} chars, size=250, ovlp=50)"},
        "medium": {"text": m_text, "size": 500, "overlap": 100, "desc": f"Medium document ({len(m_text)} chars, size=500, ovlp=100)"},
        "large": {"text": l_text, "size": 1000, "overlap": 200, "desc": f"Large corpus ({len(l_text)} chars, size=1000, ovlp=200)"},
    }

def time_callable(fn: Callable, text: str, c_size: int, c_overlap: int, iters: int) -> float:
    gc.disable()
    t0 = time.perf_counter_ns()
    for _ in range(iters):
        fn(text, c_size, c_overlap)
    t1 = time.perf_counter_ns()
    gc.enable()
    return (t1 - t0) / (iters * 1_000_000.0)

def main():
    print("=" * 65)
    print("STAGE D2 BENCHMARK: RAG DOCUMENT CHUNKER")
    print("=" * 65)

    py_ref = chunk_document._original
    direct_mojo = chunk_document._compiled
    wrapped_mojo = chunk_document

    payloads = generate_bench_payloads()
    results = {}

    for p_key, p_info in payloads.items():
        text = p_info["text"]
        c_size = p_info["size"]
        c_overlap = p_info["overlap"]
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
            py_ref(text, c_size, c_overlap)
            direct_mojo(text, c_size, c_overlap)
            wrapped_mojo(text, c_size, c_overlap)

        trials_py = []
        trials_direct = []
        trials_wrapped = []

        for _ in range(5):
            trials_py.append(time_callable(py_ref, text, c_size, c_overlap, iters))
            trials_direct.append(time_callable(direct_mojo, text, c_size, c_overlap, iters))
            trials_wrapped.append(time_callable(wrapped_mojo, text, c_size, c_overlap, iters))

        py_mean = sum(trials_py) / len(trials_py)
        direct_mean = sum(trials_direct) / len(trials_direct)
        wrapped_mean = sum(trials_wrapped) / len(trials_wrapped)

        speedup_vs_py = py_mean / wrapped_mean if wrapped_mean > 0 else 0

        print(f"\n[{p_desc}] (iters={iters})")
        print(f"  Python 3.12:    {py_mean * 1000:8.2f} µs  (p50: {sorted(trials_py)[2] * 1000:8.2f} µs)")
        print(f"  Mojo Direct:    {direct_mean * 1000:8.2f} µs  (p50: {sorted(trials_direct)[2] * 1000:8.2f} µs)")
        print(f"  Mojo @hotloop:  {wrapped_mean * 1000:8.2f} µs  (p50: {sorted(trials_wrapped)[2] * 1000:8.2f} µs) -> {speedup_vs_py:5.2f}x vs Python")

        results[p_key] = {
            "desc": p_desc,
            "len": length,
            "py_ms": py_mean,
            "mojo_direct_ms": direct_mean,
            "mojo_wrapped_ms": wrapped_mean,
            "speedup_vs_py": speedup_vs_py,
        }

    out_file = "/home/gaurav/mojo-hotloop/examples/rag_chunker/bench_results.json"
    with open(out_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[✓] Stage D2 benchmarks saved to {out_file}")

if __name__ == "__main__":
    main()
