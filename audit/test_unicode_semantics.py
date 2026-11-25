import unittest

# Standalone audit of the locally built Unicode fixture.
from unicode_primitives import (
    native_codepoint_at,
    native_codepoint_len,
    native_codepoint_slice,
    native_codepoint_to_byte_offsets,
    native_reverse_codepoints,
)


class TestUnicodeSemantics(unittest.TestCase):
    def setUp(self):
        self.samples = {
            "ascii": "The quick brown fox jumps over the lazy dog 12345!?",
            "hindi": "नमस्ते दुनिया! यह एक परीक्षण संदेश है।",
            "emoji": "Hello 🌍! 🚀 Exploring the universe ✨🔥",
            "combining": "e\u0301 a\u0300 c\u0327 n\u0303",  # acute, grave, cedilla, tilde
            "mixed": "English / हिन्दी / 🌍 Emoji / 123 Numbers / Mixed \u00e9\u00e8\u00ea!"
        }

    def test_01_codepoint_length_parity(self):
        """Mojo codepoints length matches Python len(s) on all scripts."""
        for label, s in self.samples.items():
            py_len = len(s)
            mj_len = native_codepoint_len(s)
            self.assertEqual(mj_len, py_len, f"Length mismatch on {label}: Python={py_len}, Mojo={mj_len}")

    def test_02_codepoint_indexing_parity(self):
        """Mojo codepoint indexing matches Python s[i] for positive and negative indices."""
        for label, s in self.samples.items():
            n = len(s)
            # Test every index
            for i in range(n):
                py_ch = s[i]
                mj_ch = native_codepoint_at(s, i)
                self.assertEqual(mj_ch, py_ch, f"Char mismatch at index {i} on {label}")
            # Test negative indices
            for i in range(1, min(n + 1, 10)):
                py_ch = s[-i]
                mj_ch = native_codepoint_at(s, -i)
                self.assertEqual(mj_ch, py_ch, f"Negative index mismatch at {-i} on {label}")

    def test_03_codepoint_slicing_parity(self):
        """Mojo codepoint slicing matches Python s[start:end]."""
        for label, s in self.samples.items():
            n = len(s)
            slice_pairs = [(0, 5), (2, 8), (0, n), (n - 5, n), (3, 3), (8, 4)]
            for start, end in slice_pairs:
                py_slice = s[start:end]
                mj_slice = native_codepoint_slice(s, start, end)
                self.assertEqual(mj_slice, py_slice, f"Slice mismatch [{start}:{end}] on {label}")

    def test_04_codepoint_to_byte_offset_mapping(self):
        """Mojo UTF-8 byte scanning accurately identifies codepoint starting byte offsets."""
        for label, s in self.samples.items():
            utf8_bytes = s.encode("utf-8")
            mj_offsets = native_codepoint_to_byte_offsets(s)
            
            # Python reference calculation of UTF-8 byte offsets
            py_offsets = []
            for i in range(len(utf8_bytes)):
                # Leading byte in UTF-8: (byte & 0xC0) != 0x80
                if (utf8_bytes[i] & 0xC0) != 0x80:
                    py_offsets.append(i)
                    
            self.assertEqual(mj_offsets, py_offsets, f"Byte offset mapping mismatch on {label}")
            self.assertEqual(len(mj_offsets), len(s), f"Offset count must equal codepoint count on {label}")

    def test_05_reversal_reconstruction(self):
        """Mojo codepoint reversal exactly matches Python [::-1] character reversal."""
        for label, s in self.samples.items():
            py_reversed = s[::-1]
            mj_reversed = native_reverse_codepoints(s)
            self.assertEqual(mj_reversed, py_reversed, f"Reversal mismatch on {label}")

    def test_06_index_out_of_bounds_exception(self):
        """Out-of-bounds codepoint indexing raises error."""
        s = "Hello"
        with self.assertRaises(Exception):
            native_codepoint_at(s, 100)
        with self.assertRaises(Exception):
            native_codepoint_at(s, -100)

if __name__ == "__main__":
    unittest.main()
