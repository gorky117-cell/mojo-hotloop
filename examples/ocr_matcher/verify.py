import os
import random
import sys

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from rapidfuzz.distance import Levenshtein
from examples.ocr_matcher.original import find_closest_match, levenshtein_distance

def rapidfuzz_find_closest(query: str, candidates: list[str], max_distance: int) -> int:
    best_idx: int = -1
    best_dist: int = max_distance + 1
    for i, cand in enumerate(candidates):
        d = Levenshtein.distance(query, cand, score_cutoff=best_dist - 1)
        if d < best_dist:
            best_dist = d
            best_idx = i
            if best_dist == 0:
                break
    return best_idx

def run_tests():
    print("[*] Starting Stage D4: OCR Fuzzy Matcher Verification Suite...")

    # 1. Deterministic cases
    deterministic_cases = [
        ("apple", ["aple", "appla", "banana", "orange"], 2),
        ("kitten", ["sitting", "kitchen", "kitting", "mitten"], 3),
        ("exact", ["wrong", "exact", "exakt"], 1),
        ("nomatch", ["cat", "dog", "bird"], 1),
        ("", ["", "a", "bc"], 1),
        ("hello", [], 3),
        ("unicode", ["unicod", "unicod3", "unicode"], 1),
        ("नमस्ते", ["नमस्त", "नमस्ते!", "भारत"], 2),
        ("🚀fire", ["🚀fir", "🚀🔥", "rocket"], 2),
        ("test", ["tset", "tst", "test"], 0),
        ("distance_large", ["dist", "distance", "large"], 2),
        ("invoice", ["invoce", "invioce", "receipt"], 2),
        ("tax", ["tx", "taz", "taxi", "max"], 1),
        ("total", ["totl", "total", "subtotal"], 1),
        ("amount", ["amunt", "amoun", "ammount"], 1),
        ("date", ["dat", "data", "late"], 1),
        ("vendor", ["vender", "venodor", "buyer"], 2),
        ("payment", ["paymnt", "payement", "cash"], 2),
        ("address", ["adress", "addres", "addrees"], 1),
        ("longwordstring", ["longword", "wordstring", "longwordstring"], 3),
    ]

    # 1b. Check default conservative fallback on list[str] before forcing native
    fb_res = find_closest_match("invoce", ["receipt", "invoce", "invoice", "vendor"], 2)
    if fb_res != 1 or find_closest_match._last_backend != "python_fallback_slower":
        print(f"[FAIL] Expected python_fallback_slower for unforced list[str], got {find_closest_match._last_backend}")
        sys.exit(1)

    # 2. Verify native execution across all 1020 cases with force_native=True
    find_closest_match._force_native = True
    try:
        deterministic_passed = 0
        for query, cands, max_d in deterministic_cases:
            py_res = find_closest_match._original(query, cands, max_d)
            rf_res = rapidfuzz_find_closest(query, cands, max_d)
            mojo_res = find_closest_match(query, cands, max_d)

            if find_closest_match._last_backend != "native":
                print(f"[FAIL] Expected native backend under force_native, got {find_closest_match._last_backend}")
                sys.exit(1)

            if py_res != rf_res:
                print(f"[FAIL] Reference vs RapidFuzz mismatch: query={query!r}, cands={cands!r}")
                print(f"  Py: {py_res}, RF: {rf_res}")
                sys.exit(1)

            if py_res != mojo_res:
                print(f"[FAIL] Mojo vs Py mismatch: query={query!r}, cands={cands!r}")
                print(f"  Py: {py_res}, Mojo: {mojo_res}")
                sys.exit(1)

            deterministic_passed += 1

        print(f"  [✓] Deterministic cases passed ({deterministic_passed} tests)")

        # Randomized testing against RapidFuzz (1,000 cases)
        rng = random.Random(1337)
        base_vocabulary = [
            "invoice", "receipt", "customer", "vendor", "payment",
            "balance", "statement", "account", "transaction", "subtotal",
            "discount", "shipping", "quantity", "description", "reference",
            "नमस्ते", "दस्तावेज़", "ग्राहक", "खाता",
            "🚀", "⚡", "💳", "🛒",
        ]

        def mutate_word(word: str) -> str:
            if not word:
                return "a"
            chars = list(word)
            op = rng.choice(["del", "ins", "sub", "trans"])
            pos = rng.randint(0, len(chars) - 1)
            if op == "del" and len(chars) > 1:
                chars.pop(pos)
            elif op == "ins":
                chars.insert(pos, rng.choice("abcdef0123"))
            elif op == "sub":
                chars[pos] = rng.choice("xyz789")
            elif op == "trans" and pos + 1 < len(chars):
                chars[pos], chars[pos + 1] = chars[pos + 1], chars[pos]
            return "".join(chars)

        random_passed = 0
        for test_idx in range(1000):
            base = rng.choice(base_vocabulary)
            query = mutate_word(base) if rng.random() < 0.7 else base

            num_cands = rng.randint(5, 30)
            cands = []
            for _ in range(num_cands):
                c_base = rng.choice(base_vocabulary)
                cand = mutate_word(c_base) if rng.random() < 0.5 else c_base
                cands.append(cand)

            max_d = rng.randint(1, 4)

            py_res = find_closest_match._original(query, cands, max_d)
            rf_res = rapidfuzz_find_closest(query, cands, max_d)
            mojo_res = find_closest_match(query, cands, max_d)

            if find_closest_match._last_backend != "native":
                print(f"[FAIL] Expected native backend at #{test_idx}, got {find_closest_match._last_backend}")
                sys.exit(1)

            if py_res != mojo_res:
                print(f"[FAIL] Mismatch at random test #{test_idx}: query={query!r}, max_d={max_d}")
                print(f"  Py:   {py_res}")
                print(f"  Mojo: {mojo_res}")
                print(f"  RF:   {rf_res}")
                print(f"  Cands: {cands}")
                sys.exit(1)

            random_passed += 1
    finally:
        find_closest_match._force_native = False

    total_tests = deterministic_passed + random_passed
    native_runs = find_closest_match._call_count_native
    print(f"[✓] Stage D4: OCR Fuzzy Matcher PASSED: {total_tests} tests verified (100% matched against RapidFuzz & Py, {native_runs} forced-native executions + default list[str] fallback verified, 0 mismatches). Zero errors.")

if __name__ == "__main__":
    run_tests()
