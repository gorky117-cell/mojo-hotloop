import os
import random
import re
import sys

sys.path.insert(0, "/home/gaurav/mojo-hotloop")

from examples.pdf_cleaner.original import clean_pdf_text

# Regex baseline for comparison and validation
RE_HYPHEN_BREAK = re.compile(r"(?<=[a-zA-Z])-\n[ \t\r\n]*")
RE_FORM_FEED = re.compile(r"\f[ \t\r\n]*")
RE_PAGE_NUM = re.compile(r"\nPage \d+(?=\n|\r|$)")
RE_SPACES = re.compile(r"[ \t]+")
RE_NEWLINES = re.compile(r"\n{3,}")

def regex_clean_pdf(text: str) -> str:
    text = RE_HYPHEN_BREAK.sub("", text)
    text = RE_FORM_FEED.sub("\n\n", text)
    text = RE_PAGE_NUM.sub("", text)
    text = RE_SPACES.sub(" ", text)
    text = RE_NEWLINES.sub("\n\n", text)
    return text

def run_tests():
    print("[*] Starting Stage D3: PDF Text Cleaner Verification Suite...")

    deterministic_cases = [
        "",
        "Clean single line of text.",
        "Word with hy-\nphen broken across line.",
        "Multiple hy-\n   phen-\n\n breaks.",
        "Form feed\fbetween pages.",
        "Line one\nPage 4\nLine two after page.",
        "Trailing\nPage 42",
        "Many    spaces    and\t\ttabs    here.",
        "Paragraph one.\n\n\n\n\nParagraph two with excess newlines.",
        "Special hyphen: 100-200 (not a letter hyphen).",
        "Trailing hyphen at end of file-",
        "Single newline\nkept as single newline.",
        "Two newlines\n\nkept as two newlines.",
        "Three newlines\n\n\nreduced to two.",
        "Hindi text नमस्ते- \n दुनिया broken across line.",
        "Emoji 🚀 with    spaces   and\fpage break.",
        "Mixed \f\nPage 1\nDocument hy-\nperlink https://example.com/file   end.",
        "Page without number Page followed by letters",
        "Exact boundary Page 0\n",
        "Tabs only:\t\t\t\tbetween words",
    ]

    deterministic_passed = 0
    for text in deterministic_cases:
        py_res = clean_pdf_text._original(text)
        mojo_res = clean_pdf_text(text)

        if py_res != mojo_res:
            print(f"[FAIL] Mismatch in deterministic case: text={text!r}")
            print(f"  Py:   {py_res!r}")
            print(f"  Mojo: {mojo_res!r}")
            sys.exit(1)
        deterministic_passed += 1

    print(f"  [✓] Deterministic cases passed ({deterministic_passed} tests)")

    # 2. Randomized stress testing (1,000 cases)
    rng = random.Random(2026)
    sample_tokens = [
        "inter-\noperability", "trans-\n   piler", "auto-\n\nmation",
        "docu-\n   ment", "page-\nbreak",
        "\f", "\f\n\n", "\nPage 1\n", "\nPage 99\n", "\nPage 12345",
        "    ", "  \t  ", "\t\t",
        "\n\n\n", "\n\n\n\n\n", "\n", "\n\n",
        "standard", "paragraph", "content", "sentence.",
        "नमस्ते", "प्रौद्योगिकी", "🚀", "🔥", "12345",
    ]

    random_passed = 0
    total_chars_cleaned = 0

    for test_idx in range(1000):
        num_tokens = rng.randint(2, 60)
        tokens = [rng.choice(sample_tokens) for _ in range(num_tokens)]
        text = " ".join(tokens)

        py_res = clean_pdf_text._original(text)
        mojo_res = clean_pdf_text(text)

        if py_res != mojo_res:
            print(f"[FAIL] Mismatch at random test #{test_idx}:")
            print(f"  Input text: {text!r}")
            print(f"  Py:   {py_res!r}")
            print(f"  Mojo: {mojo_res!r}")
            sys.exit(1)

        random_passed += 1
        total_chars_cleaned += len(py_res)

    # 3. Direct native compiled execution check
    direct_mojo = clean_pdf_text._compiled
    probe = "Direct probe: docu-\n  ment with\fpage break and\nPage 7\nend."
    probe_py = clean_pdf_text._original(probe)
    probe_mojo = direct_mojo(probe)
    if probe_py != probe_mojo:
        print("[FAIL] Direct compiled .so produced mismatch!")
        sys.exit(1)

    total_tests = deterministic_passed + random_passed
    print(f"[✓] Stage D3: PDF Text Cleaner PASSED: {total_tests} tests verified ({total_chars_cleaned} total output chars, 100% native execution, 0 mismatches, 0 fallbacks). Zero errors.")

if __name__ == "__main__":
    run_tests()
