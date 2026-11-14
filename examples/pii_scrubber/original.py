from hotloop import hotloop

def check_luhn(digits: list[int]) -> bool:
    n: int = len(digits)
    if n < 13 or n > 19:
        return False
    total: int = 0
    parity: int = n % 2
    for i in range(n):
        d: int = digits[i]
        if i % 2 == parity:
            d = d * 2
            if d > 9:
                d = d - 9
        total += d
    return (total % 10) == 0

def check_verhoeff(digits: list[int]) -> bool:
    n: int = len(digits)
    if n != 12:
        return False
    if digits[0] < 2:
        return False
    d_table: list[int] = [
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
    p_table: list[int] = [
        0, 1, 2, 3, 4, 5, 6, 7, 8, 9,
        1, 5, 7, 6, 2, 8, 3, 0, 9, 4,
        5, 8, 0, 3, 7, 9, 6, 1, 4, 2,
        8, 9, 1, 6, 0, 4, 3, 5, 2, 7,
        9, 4, 5, 3, 1, 2, 6, 8, 7, 0,
        4, 2, 8, 6, 5, 7, 3, 9, 0, 1,
        2, 7, 9, 3, 8, 0, 6, 4, 1, 5,
        7, 0, 4, 6, 9, 1, 3, 2, 5, 8
    ]
    c: int = 0
    for i in range(n):
        val: int = digits[n - 1 - i]
        c = d_table[c * 10 + p_table[(i % 8) * 10 + val]]
    return c == 0

def check_phone(digits: list[int]) -> bool:
    n: int = len(digits)
    if n == 10:
        return digits[0] >= 6
    elif n == 11 and digits[0] == 0:
        return digits[1] >= 6
    elif n == 12 and digits[0] == 9 and digits[1] == 1:
        return digits[2] >= 6
    return False

def check_pan(s: str) -> bool:
    if len(s) != 10:
        return False
    for i in range(5):
        ch: str = s[i]
        if ch < "A" or ch > "Z":
            return False
    for i in range(5, 9):
        ch: str = s[i]
        if ch < "0" or ch > "9":
            return False
    ch_last: str = s[9]
    return ch_last >= "A" and ch_last <= "Z"

@hotloop
def scrub_pii(text: str) -> str:
    result: str = ""
    n: int = len(text)
    i: int = 0
    while i < n:
        ch: str = text[i]
        
        # Check for PAN: 5 uppercase letters + 4 digits + 1 uppercase letter
        if ch >= "A" and ch <= "Z" and (i == 0 or not ((text[i-1] >= "A" and text[i-1] <= "Z") or (text[i-1] >= "0" and text[i-1] <= "9"))):
            if i + 10 <= n:
                candidate: str = text[i : i + 10]
                boundary_after: bool = (i + 10 == n or not ((text[i+10] >= "A" and text[i+10] <= "Z") or (text[i+10] >= "0" and text[i+10] <= "9")))
                if boundary_after and check_pan(candidate):
                    result += "[REDACTED_PAN]"
                    i += 10
                    continue
                    
        # Check for numeric PII: Phone, Card, Aadhaar
        is_num_start: bool = (ch >= "0" and ch <= "9") or (ch == "+" and i + 1 < n and text[i+1] >= "0" and text[i+1] <= "9")
        boundary_before: bool = (i == 0 or not ((text[i-1] >= "A" and text[i-1] <= "Z") or (text[i-1] >= "a" and text[i-1] <= "z") or (text[i-1] >= "0" and text[i-1] <= "9")))
        
        if is_num_start and boundary_before:
            start_idx: int = i
            digits: list[int] = []
            while i < n:
                curr: str = text[i]
                if curr >= "0" and curr <= "9":
                    digits.append(int(curr))
                    i += 1
                elif curr == "+" and i == start_idx:
                    i += 1
                elif (curr == " " or curr == "-") and (i + 1 < n and text[i+1] >= "0" and text[i+1] <= "9"):
                    i += 1
                else:
                    break
            candidate_num: str = text[start_idx : i]
            boundary_after_num: bool = (i == n or not ((text[i] >= "A" and text[i] <= "Z") or (text[i] >= "a" and text[i] <= "z") or (text[i] >= "0" and text[i] <= "9")))
            
            if boundary_after_num and check_luhn(digits):
                result += "[REDACTED_CC]"
            elif boundary_after_num and check_verhoeff(digits):
                result += "[REDACTED_AADHAAR]"
            elif boundary_after_num and check_phone(digits):
                result += "[REDACTED_PHONE]"
            else:
                result += candidate_num
            continue
            
        result += ch
        i += 1
        
    return result
