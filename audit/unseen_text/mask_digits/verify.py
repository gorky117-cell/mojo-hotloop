import os
import sys
import random

# Add project root
sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from audit.unseen_text.mask_digits.original import mask_ascii_digits

# Reference pure python implementation
def py_mask_ascii_digits(text: str) -> str:
    result: str = ""
    for ch in text:
        if ch >= "0" and ch <= "9":
            result += "*"
        else:
            result += ch
    return result

def run_tests():
    print("[*] Starting verification of mask_ascii_digits...")
    
    # Verify native backend is active
    assert hasattr(mask_ascii_digits, "_last_backend"), "Function must be decorated with @hotloop"
    
    edge_cases = [
        "",
        "a",
        "0",
        "9",
        "5",
        "1234567890",
        "Phone: 555-123-4567!",
        "No digits here at all.",
        "000000",
        "Mixed: नमस्ते 123 दुनिया 45678",
        "Emojis: 🚀 42 🔥 999 ✨ 00",
        "CRLF and digits: Line 1\r\nLine 2\nLine 3",
        "Combining e\u0301 with 1234 digits: e\u0301 987",
        "0" * 2000,
        ("abc" + "12345" + "def") * 100,
    ]
    
    total_tests = 0
    native_tests = 0
    
    # 1. Edge cases
    for s in edge_cases:
        expected = py_mask_ascii_digits(s)
        actual = mask_ascii_digits(s)
        assert actual == expected, f"Mismatch on edge case: {repr(s)}: expected {expected}, got {actual}"
        assert mask_ascii_digits._last_backend == "native", f"Expected native backend, got {mask_ascii_digits._last_backend}"
        total_tests += 1
        native_tests += 1
        
    # 2. 1,000 Seeded Randomized Tests
    rng = random.Random(2026)
    sample_pool = [
        "a", "b", "c", "x", "y", "z", "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
        " ", "\t", "\n", "\r", "-", "_", ".", "/", "@", "#",
        "न", "म", "स", "्", "त", "े",
        "🌍", "🚀", "🎉", "🔥", "✨", "é", "ö"
    ]
    
    for trial in range(1, 1001):
        length = rng.randint(0, 300)
        s = "".join(rng.choice(sample_pool) for _ in range(length))
        expected = py_mask_ascii_digits(s)
        actual = mask_ascii_digits(s)
        assert actual == expected, f"Mismatch on trial {trial}: {repr(s)}: expected {expected}, got {actual}"
        assert mask_ascii_digits._last_backend == "native", f"Expected native backend, got {mask_ascii_digits._last_backend}"
        total_tests += 1
        native_tests += 1
        
    # 3. Lone surrogate fallback tests
    surrogates = [
        "card_number_1234\ud800and_5678",
        "\ud800",
        "\udfff",
        "prefix\ud83d\ude00\udc00 999 suffix",
    ]
    for s in surrogates:
        expected = py_mask_ascii_digits(s)
        actual = mask_ascii_digits(s)
        assert actual == expected, f"Mismatch on surrogate test: expected {expected}, got {actual}"
        assert mask_ascii_digits._last_backend == "python_fallback_surrogate", f"Expected surrogate fallback, got {mask_ascii_digits._last_backend}"
        total_tests += 1

    print(f"[✓] mask_ascii_digits PASSED: {total_tests} tests verified ({native_tests} native, {len(surrogates)} surrogate fallback). Zero errors.")
    return total_tests

if __name__ == "__main__":
    run_tests()
