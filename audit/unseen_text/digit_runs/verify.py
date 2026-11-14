import os
import sys
import random

# Add project root
sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from audit.unseen_text.digit_runs.original import count_ascii_digit_runs

# Reference pure python implementation
def py_count_ascii_digit_runs(text: str) -> int:
    runs: int = 0
    in_run: bool = False
    for ch in text:
        if ch >= "0" and ch <= "9":
            if not in_run:
                runs += 1
                in_run = True
        else:
            in_run = False
    return runs

def run_tests():
    print("[*] Starting verification of count_ascii_digit_runs...")
    
    # Verify native backend is active
    assert hasattr(count_ascii_digit_runs, "_last_backend"), "Function must be decorated with @hotloop"
    
    edge_cases = [
        "",
        "a",
        "1",
        "123",
        "abc123def",
        "abc 123 def 456 ghi",
        "1a2b3c4d5",
        "1234567890",
        "no digits here at all",
        "000000",
        "नमस्ते 123 दुनिया 45678",
        "🚀 42 🔥 999 ✨ 00",
        "1\n2\r3\t4",
        "Combining e\u0301 with 1234 digits",
        "0" * 5000,
        ("a" * 100 + "99" + "b" * 100) * 50,
    ]
    
    total_tests = 0
    native_tests = 0
    
    # 1. Edge cases
    for s in edge_cases:
        expected = py_count_ascii_digit_runs(s)
        actual = count_ascii_digit_runs(s)
        assert actual == expected, f"Mismatch on edge case: {repr(s)}: expected {expected}, got {actual}"
        assert count_ascii_digit_runs._last_backend == "native", f"Expected native backend, got {count_ascii_digit_runs._last_backend}"
        total_tests += 1
        native_tests += 1
        
    # 2. 1,000 Seeded Randomized Tests
    rng = random.Random(1337)
    sample_pool = [
        "a", "b", "c", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        " ", "\t", "\n", "-", "_", ".", "/",
        "न", "म", "स", "्", "त", "े",
        "🌍", "🚀", "🎉", "🔥", "✨", "é", "ö"
    ]
    
    for trial in range(1, 1001):
        length = rng.randint(0, 300)
        s = "".join(rng.choice(sample_pool) for _ in range(length))
        expected = py_count_ascii_digit_runs(s)
        actual = count_ascii_digit_runs(s)
        assert actual == expected, f"Mismatch on trial {trial}: {repr(s)}: expected {expected}, got {actual}"
        assert count_ascii_digit_runs._last_backend == "native", f"Expected native backend, got {count_ascii_digit_runs._last_backend}"
        total_tests += 1
        native_tests += 1
        
    # 3. Lone surrogate fallback tests
    surrogates = [
        "digits123\ud800and456",
        "\ud800",
        "\udfff",
        "prefix\ud83d\ude00\udc00 999 suffix",
    ]
    for s in surrogates:
        expected = py_count_ascii_digit_runs(s)
        actual = count_ascii_digit_runs(s)
        assert actual == expected, f"Mismatch on surrogate test: expected {expected}, got {actual}"
        assert count_ascii_digit_runs._last_backend == "python_fallback_surrogate", f"Expected surrogate fallback, got {count_ascii_digit_runs._last_backend}"
        total_tests += 1

    print(f"[✓] count_ascii_digit_runs PASSED: {total_tests} tests verified ({native_tests} native, {len(surrogates)} surrogate fallback). Zero errors.")
    return total_tests

if __name__ == "__main__":
    run_tests()
