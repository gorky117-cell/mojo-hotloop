import os
import sys
import random

# Add project root
sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from audit.unseen_text.newline_positions.original import unicode_newline_positions

# Reference pure python implementation
def py_newline_positions(text: str) -> list[int]:
    positions: list[int] = []
    idx: int = 0
    for ch in text:
        if ch == "\n" or ch == "\r":
            positions.append(idx)
        idx += 1
    return positions

def run_tests():
    print("[*] Starting verification of unicode_newline_positions...")
    
    # Verify native backend is active
    assert hasattr(unicode_newline_positions, "_last_backend"), "Function must be decorated with @hotloop"
    
    edge_cases = [
        "",
        "\n",
        "\r",
        "\r\n",
        "\n\r",
        "a",
        "hello world",
        "\n\n\n\n\n",
        "\r\r\r\r\r",
        "\r\n\r\n\r\n",
        "Line 1\nLine 2\rLine 3\r\nLine 4\n",
        "नमस्ते दुनिया\nयह एक परीक्षण है\r\nअंतिम पंक्ति",
        "🚀 Hello 🌍\nWorld 🔥\r\n✨",
        "Combining: e\u0301\ncafe\u0301\r\nmixed",
        "Spaces and tabs \t \n \r \t done",
        "\n" * 1000,
        "x" * 10000 + "\n" + "y" * 10000,
    ]
    
    total_tests = 0
    native_tests = 0
    
    # 1. Edge cases
    for s in edge_cases:
        expected = py_newline_positions(s)
        actual = unicode_newline_positions(s)
        assert actual == expected, f"Mismatch on edge case: {repr(s)}: expected {expected}, got {actual}"
        assert unicode_newline_positions._last_backend == "native", f"Expected native backend, got {unicode_newline_positions._last_backend}"
        total_tests += 1
        native_tests += 1
        
    # 2. 1,000 Seeded Randomized Tests
    rng = random.Random(42)
    sample_pool = [
        "a", "b", "c", "1", "2", "3", " ", "\t", "\n", "\r",
        "न", "म", "स", "्", "त", "े", "द", "ु", "न", "ि", "य", "ा",
        "🌍", "🚀", "🎉", "🔥", "✨", "é", "ñ", "ü"
    ]
    
    for trial in range(1, 1001):
        length = rng.randint(0, 300)
        s = "".join(rng.choice(sample_pool) for _ in range(length))
        expected = py_newline_positions(s)
        actual = unicode_newline_positions(s)
        assert actual == expected, f"Mismatch on trial {trial}: {repr(s)}: expected {expected}, got {actual}"
        assert unicode_newline_positions._last_backend == "native", f"Expected native backend, got {unicode_newline_positions._last_backend}"
        total_tests += 1
        native_tests += 1
        
    # 3. Lone surrogate fallback tests
    surrogates = [
        "hello\ud800world",
        "\ud800",
        "\udfff",
        "prefix\ud83d\ude00\udc00suffix\nnew",
    ]
    for s in surrogates:
        expected = py_newline_positions(s)
        actual = unicode_newline_positions(s)
        assert actual == expected, f"Mismatch on surrogate test: expected {expected}, got {actual}"
        assert unicode_newline_positions._last_backend == "python_fallback_surrogate", f"Expected surrogate fallback, got {unicode_newline_positions._last_backend}"
        total_tests += 1

    print(f"[✓] unicode_newline_positions PASSED: {total_tests} tests verified ({native_tests} native, {len(surrogates)} surrogate fallback). Zero errors.")
    return total_tests

if __name__ == "__main__":
    run_tests()
