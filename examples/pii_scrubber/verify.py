import os
import re
import random
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from examples.pii_scrubber.original import scrub_pii, check_luhn, check_verhoeff, check_phone, check_pan

# 1. Equivalent Compiled Python Regular Expressions Implementation
RE_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
RE_CC = re.compile(r"\b(?:\d{4}[ -]?){3}\d{1,7}\b")
RE_AADHAAR = re.compile(r"\b[2-9]\d{3}[ -]?\d{4}[ -]?\d{4}\b")
RE_PHONE = re.compile(r"(?:\+91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}\b")

def scrub_cc_match(m):
    digits = [ord(c) - 48 for c in m.group(0) if "0" <= c <= "9"]
    return "[REDACTED_CC]" if check_luhn(digits) else m.group(0)

def scrub_aadhaar_match(m):
    digits = [ord(c) - 48 for c in m.group(0) if "0" <= c <= "9"]
    return "[REDACTED_AADHAAR]" if check_verhoeff(digits) else m.group(0)

def scrub_phone_match(m):
    digits = [ord(c) - 48 for c in m.group(0) if "0" <= c <= "9"]
    return "[REDACTED_PHONE]" if check_phone(digits) else m.group(0)

def regex_scrub_pii(text: str) -> str:
    text = RE_PAN.sub("[REDACTED_PAN]", text)
    text = RE_CC.sub(scrub_cc_match, text)
    text = RE_AADHAAR.sub(scrub_aadhaar_match, text)
    return RE_PHONE.sub(scrub_phone_match, text)

# Helper generators for synthetic test data (NO REAL PII EVER)
def gen_synthetic_card(rng: random.Random) -> str:
    base = "".join(str(rng.randint(0, 9)) for _ in range(15))
    total = 0
    num_digits = len(base) + 1
    parity = num_digits % 2
    for i in range(len(base)):
        d = int(base[i])
        if i % 2 == parity:
            d = d * 2
            if d > 9:
                d = d - 9
        total += d
    check_digit = (10 - (total % 10)) % 10
    card_digits = base + str(check_digit)
    sep_choice = rng.choice(["none", "hyphen", "space"])
    if sep_choice == "hyphen":
        return f"{card_digits[:4]}-{card_digits[4:8]}-{card_digits[8:12]}-{card_digits[12:]}"
    elif sep_choice == "space":
        return f"{card_digits[:4]} {card_digits[4:8]} {card_digits[8:12]} {card_digits[12:]}"
    return card_digits

def gen_synthetic_aadhaar(rng: random.Random) -> str:
    VERHOEFF_D = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        1, 2, 3, 4, 0, 6, 7, 8, 9, 5,
        2, 3, 4, 0, 1, 7, 8, 9, 5, 6,
        3, 4, 0, 1, 2, 8, 9, 5, 6, 7,
        4, 0, 1, 2, 3, 9, 5, 6, 7, 8,
        5, 9, 8, 7, 6, 0, 4, 3, 2, 1,
        6, 5, 9, 8, 7, 1, 0, 4, 3, 2,
        7, 6, 5, 9, 8, 2, 1, 0, 4, 3,
        8, 7, 6, 5, 9, 3, 2, 1, 0, 4,
        9, 8, 7, 6, 5, 4, 3, 2, 1, 0
    ]
    VERHOEFF_P = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        1, 5, 7, 6, 2, 8, 3, 0, 9, 4,
        5, 8, 0, 3, 7, 9, 6, 1, 4, 2,
        8, 9, 1, 6, 0, 4, 3, 5, 2, 7,
        9, 4, 5, 3, 1, 2, 6, 8, 7, 0,
        4, 2, 8, 6, 5, 7, 3, 9, 0, 1,
        2, 7, 9, 3, 8, 0, 6, 4, 1, 5,
        7, 0, 4, 6, 9, 1, 3, 2, 5, 8
    ]
    INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]
    first_digit = str(rng.randint(2, 9))
    rest = "".join(str(rng.randint(0, 9)) for _ in range(10))
    base = first_digit + rest
    c = 0
    for i in range(len(base)):
        digit = int(base[len(base) - 1 - i])
        c = VERHOEFF_D[c * 10 + VERHOEFF_P[((i + 1) % 8) * 10 + digit]]
    check_digit = INV[c]
    aadhaar_digits = base + str(check_digit)
    sep_choice = rng.choice(["none", "hyphen", "space"])
    if sep_choice == "hyphen":
        return f"{aadhaar_digits[:4]}-{aadhaar_digits[4:8]}-{aadhaar_digits[8:]}"
    elif sep_choice == "space":
        return f"{aadhaar_digits[:4]} {aadhaar_digits[4:8]} {aadhaar_digits[8:]}"
    return aadhaar_digits

def gen_synthetic_phone(rng: random.Random) -> str:
    first_digit = str(rng.randint(6, 9))
    rest = "".join(str(rng.randint(0, 9)) for _ in range(9))
    phone_10 = first_digit + rest
    prefix = rng.choice(["none", "+91 ", "+91-", "0", "+91"])
    if prefix == "none":
        return phone_10
    elif prefix == "+91 ":
        return f"+91 {phone_10[:5]} {phone_10[5:]}"
    elif prefix == "+91-":
        return f"+91-{phone_10}"
    elif prefix == "0":
        return f"0{phone_10}"
    else:
        return f"+91{phone_10}"

def gen_synthetic_pan(rng: random.Random) -> str:
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    digits = "0123456789"
    first_5 = "".join(rng.choice(letters) for _ in range(5))
    num_4 = "".join(rng.choice(digits) for _ in range(4))
    last_1 = rng.choice(letters)
    return first_5 + num_4 + last_1

def run_tests():
    print("[*] Starting Stage D1: PII Scrubber Verification Suite...")
    
    deterministic_cases = [
        "",
        "Hello world, no PII here.",
        "Card 4000-1234-5678-9017 is valid.",
        "Card 4000 1234 5678 9017 with spaces.",
        "Bad card 4000 1234 5678 9011 invalid.",
        "Aadhaar 2345 6789 0124 for KYC.",
        "Bad Aadhaar 2345 6789 0125 invalid.",
        "Bad Aadhaar starting with zero: 0123 4567 8901.",
        "Call +91 98765 43210 or 09876543210 now.",
        "Call 9876543210 today.",
        "Invalid phone 5876543210 starts with 5.",
        "PAN ABCDE1234F verified.",
        "Fake PAN 12345ABCDE not pan.",
        "Fake PAN ABCDE12345 not pan.",
        "Invoice 4532 paid on 2026-11-15.",
        "Order 1234 and 5678.",
        "Mixed text: नमस्ते 2345 6789 0124 ग्राहक 🚀 Phone: 9876543210, Card: 4000-1234-5678-9017, PAN: XYZAB5678K.",
        "Short: A",
        "Punctuation only: ... --- ,,, !!! ???",
    ]
    
    total_tests = 0
    native_tests = 0
    py_ref = scrub_pii._original
    
    for text in deterministic_cases:
        expected_py = py_ref(text)
        actual_mojo = scrub_pii(text)
        
        assert actual_mojo == expected_py, (
            f"Mojo vs Python mismatch on case {repr(text)}:\n"
            f"  Expected: {repr(expected_py)}\n"
            f"  Actual:   {repr(actual_mojo)}"
        )
        assert scrub_pii._last_backend == "native", f"Expected native execution, got {scrub_pii._last_backend}"
        total_tests += 1
        native_tests += 1
        
    print(f"  [✓] Deterministic cases passed ({len(deterministic_cases)} tests)")
    
    rng = random.Random(42)
    templates = [
        "Customer {pii} placed an order.",
        "Verified {pii} successfully at branch.",
        "Ref {word} with ID {pii} and code {num}.",
        "Transaction fee ₹{num} charged to {pii}.",
        "नमस्ते {pii} विवरण अद्यतन 🚀",
        "Record {pii} - Status: ACTIVE ({word})",
        "Alert: {pii} failed verification on {num}.",
    ]
    filler_words = ["account", "system", "payment", "invoice", "report", "auth", "audit", "status", "data", "token"]
    
    for trial in range(1, 1001):
        choice = rng.randint(0, 5)
        if choice == 0:
            pii = gen_synthetic_card(rng)
        elif choice == 1:
            pii = gen_synthetic_aadhaar(rng)
        elif choice == 2:
            pii = gen_synthetic_phone(rng)
        elif choice == 3:
            pii = gen_synthetic_pan(rng)
        elif choice == 4:
            pii = gen_synthetic_card(rng)
            pii = pii[:-1] + str((int(pii[-1]) + 1) % 10)
        else:
            pii = str(rng.randint(100, 999999))
            
        tmpl = rng.choice(templates)
        text = tmpl.format(pii=pii, word=rng.choice(filler_words), num=rng.randint(10, 9999))
        
        expected = py_ref(text)
        actual = scrub_pii(text)
        
        assert actual == expected, (
            f"Mismatch on trial {trial} ({repr(text)}):\n"
            f"  Expected: {repr(expected)}\n"
            f"  Actual:   {repr(actual)}"
        )
        assert scrub_pii._last_backend == "native", f"Expected native execution, got {scrub_pii._last_backend}"
        total_tests += 1
        native_tests += 1

    print(f"[✓] Stage D1: PII Scrubber PASSED: {total_tests} tests verified ({native_tests} native executions, 0 mismatches, 0 fallbacks). Zero errors.")
    return total_tests

if __name__ == "__main__":
    run_tests()
