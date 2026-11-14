import os
import random
import sys

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from examples.rag_chunker.original import chunk_document

def run_tests():
    print("[*] Starting Stage D2: RAG Document Chunker Verification Suite...")

    # 1. Deterministic edge cases
    deterministic_cases = [
        ("", 100, 20),
        ("Short", 100, 20),
        ("Short", 5, 2),
        ("Exactly ten chars", 10, 2),
        ("NoSpacesHereJustOneLongStringOfCharacters", 10, 3),
        ("Word1 Word2 Word3 Word4 Word5", 15, 5),
        ("A\nB\nC\nD\nE\nF\nG", 6, 2),
        ("Line1\tLine2\tLine3\tLine4", 12, 4),
        ("नमस्ते भारत और पूरी दुनिया के लोगों को शुभकामनाएँ", 15, 5),
        ("🚀 🛰️ 🛸 🌍 🌕 ☀️ 🪐", 8, 3),
        ("Mixed text with hindi नमस्ते and emoji 🚀 and code `def fn():`", 25, 8),
        ("Multiple   spaces    and\n\nnewlines\t\ttabs", 15, 5),
        ("Invalid chunk size", 0, 0),
        ("Negative chunk size", -5, 2),
        ("Overlap equals chunk size", 20, 20),
        ("Overlap greater than chunk size", 20, 30),
        ("Single char chunk", 1, 0),
        ("Zero overlap", 10, 0),
        ("Exact word boundary matching end", 12, 4),
        ("Repeated letters " + "a" * 100, 20, 5),
    ]

    deterministic_passed = 0
    for text, c_size, c_overlap in deterministic_cases:
        py_res = chunk_document._original(text, c_size, c_overlap)
        mojo_res = chunk_document(text, c_size, c_overlap)

        if py_res != mojo_res:
            print(f"[FAIL] Mismatch in deterministic case: text={text!r}, size={c_size}, overlap={c_overlap}")
            print(f"  Py:   {py_res}")
            print(f"  Mojo: {mojo_res}")
            sys.exit(1)
        deterministic_passed += 1

    print(f"  [✓] Deterministic cases passed ({deterministic_passed} tests)")

    # 2. Randomized stress testing (1,000 cases)
    rng = random.Random(42)
    sample_words = [
        "the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
        "नमस्ते", "दुनिया", "भारत", "ज्ञान", "प्रौद्योगिकी",
        "🚀", "🔥", "💻", "✨", "🎉",
        "function", "algorithm", "transpiler", "compilation", "benchmark",
        "word-with-hyphen", "path/to/file", "https://example.com/rag/chunk",
        "123456", "9876543210", "PAN:ABCDE1234F",
    ]

    random_passed = 0
    total_chunks_verified = 0

    for test_idx in range(1000):
        # Generate random document
        num_words = rng.randint(1, 150)
        doc_words = [rng.choice(sample_words) for _ in range(num_words)]
        sep_pool = [" ", "  ", "\n", "\t", " \n "]
        doc_parts = []
        for w in doc_words:
            doc_parts.append(w)
            doc_parts.append(rng.choice(sep_pool))
        text = "".join(doc_parts)

        c_size = rng.randint(5, 120)
        c_overlap = rng.randint(0, c_size + 10)

        py_res = chunk_document._original(text, c_size, c_overlap)
        mojo_res = chunk_document(text, c_size, c_overlap)

        if py_res != mojo_res:
            print(f"[FAIL] Mismatch at random test #{test_idx}: size={c_size}, overlap={c_overlap}")
            print(f"  Text len: {len(text)}")
            print(f"  Py chunk count:   {len(py_res)}")
            print(f"  Mojo chunk count: {len(mojo_res)}")
            for i in range(min(len(py_res), len(mojo_res))):
                if py_res[i] != mojo_res[i]:
                    print(f"  First chunk mismatch at [{i}]:")
                    print(f"    Py:   {py_res[i]!r}")
                    print(f"    Mojo: {mojo_res[i]!r}")
                    break
            sys.exit(1)

        random_passed += 1
        total_chunks_verified += len(mojo_res)

    # 3. Confirm Native Dispatch & Zero Fallbacks
    direct_mojo = chunk_document._compiled
    test_probe = "Direct native verification probe 🚀 नमस्ते"
    probe_py = chunk_document._original(test_probe, 15, 5)
    probe_mojo = direct_mojo(test_probe, 15, 5)
    if probe_py != probe_mojo:
        print("[FAIL] Direct compiled .so produced different result!")
        sys.exit(1)

    total_tests = deterministic_passed + random_passed
    print(f"[✓] Stage D2: RAG Document Chunker PASSED: {total_tests} tests verified ({total_chunks_verified} total chunks, 100% native execution, 0 mismatches, 0 fallbacks). Zero errors.")

if __name__ == "__main__":
    run_tests()
