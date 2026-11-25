import resource
import unittest

# Standalone audit of the locally built Unicode fixture.
from unicode_primitives import (
    native_codepoint_len,
    native_codepoint_to_byte_offsets,
    native_reverse_codepoints,
)


class TestTextBoundary(unittest.TestCase):
    def test_01_caller_string_immutability(self):
        """Input Python string is never mutated or corrupted by native boundary."""
        original = "Hello 🌍! नमस्ते"
        input_copy = "Hello 🌍! नमस्ते"
        _ = native_codepoint_len(original)
        _ = native_reverse_codepoints(original)
        _ = native_codepoint_to_byte_offsets(original)
        self.assertEqual(original, input_copy)

    def test_02_memory_stability_leak_check(self):
        """Repeated text calls remain within the existing peak RSS growth limit."""
        doc = ("The quick brown fox 🦊 jumps over the lazy dog 🐶 with Hindi नमस्ते!\n") * 10
        
        # Warmup
        for _ in range(500):
            _ = native_codepoint_len(doc)
            _ = native_reverse_codepoints(doc)
            _ = native_codepoint_to_byte_offsets(doc)

        rss_start = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        for i in range(5000):
            l = native_codepoint_len(doc)
            rev = native_reverse_codepoints(doc)
            offs = native_codepoint_to_byte_offsets(doc)

        rss_end = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        growth = rss_end - rss_start
        print(f"\nMemory Check: Start={rss_start} KB | End={rss_end} KB | Growth={growth} KB across 15,000 text calls")
        self.assertLessEqual(growth, 2048, f"Memory growth exceeded threshold: {growth} KB")

if __name__ == "__main__":
    unittest.main()
