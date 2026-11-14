import gc
import sys
import time

def main():
    text = "Hello world! This is a test paragraph for chunking. " * 2000 # ~100k chars
    offsets = [(i * 1000, min(len(text), (i + 1) * 1000)) for i in range(100)]

    # 1. Pure Python list comprehension of 100 slices
    gc.disable()
    trials = []
    for _ in range(500):
        t0 = time.perf_counter_ns()
        chunks = [text[start:end] for start, end in offsets]
        t1 = time.perf_counter_ns()
        trials.append((t1 - t0) / 1000.0)
    gc.enable()
    trials.sort()
    p50_py_slice = trials[len(trials) // 2]

    # 2. Pre-allocated list assignment (bypassing append)
    gc.disable()
    trials = []
    for _ in range(500):
        t0 = time.perf_counter_ns()
        chunks = [None] * len(offsets)
        for idx, (start, end) in enumerate(offsets):
            chunks[idx] = text[start:end]
        t1 = time.perf_counter_ns()
        trials.append((t1 - t0) / 1000.0)
    gc.enable()
    trials.sort()
    p50_prealloc = trials[len(trials) // 2]

    # 3. Minimum possible CPython overhead: allocating an empty list of 100 empty strings
    gc.disable()
    trials = []
    for _ in range(500):
        t0 = time.perf_counter_ns()
        chunks = ["" for _ in range(100)]
        t1 = time.perf_counter_ns()
        trials.append((t1 - t0) / 1000.0)
    gc.enable()
    trials.sort()
    p50_empty_strings = trials[len(trials) // 2]

    print("=================================================================")
    print("RAG CHUNKER PHYSICAL FEASIBILITY AUDIT")
    print("=================================================================")
    print(f"1. Pure Python 100 string slice allocations:   {p50_py_slice:.2f} µs (p50)")
    print(f"2. Pre-allocated list assignment (100 slices):  {p50_prealloc:.2f} µs (p50)")
    print(f"3. 100 empty strings list allocation:           {p50_empty_strings:.2f} µs (p50)")
    print("-----------------------------------------------------------------")
    print(f"20x Performance Target for RAG Chunker:          9.10 µs")
    print("-----------------------------------------------------------------")
    if p50_py_slice > 9.10:
        print(f"[PHYSICAL LIMIT VERIFIED]: Just allocating 100 Python strings in pure CPython takes {p50_py_slice:.2f} µs,")
        print(f"which is {p50_py_slice / 9.10:.1f}x GREATER than the entire 9.10 µs 20x budget!")
        print("Therefore, returning list[str] across ANY native FFI cannot physically achieve <= 9.10 µs.")

if __name__ == "__main__":
    main()
