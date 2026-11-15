import math
import sys
import os
import random

# Pure functions matching original.py verbatim (no @hotloop)
def stateful_trailing_backtest(ticks: int, start_price: float, stop_pct: float, fee_rate: float) -> float:
    if ticks <= 0:
        return start_price
    price = start_price
    peak_price = start_price
    cash = 0.0
    units = 1.0
    in_position = True
    cooldown = 0
    lcg_state = 42
    for _ in range(ticks):
        lcg_state = (1664525 * lcg_state + 1013904223) & 0xFFFFFFFF
        rand_val = lcg_state / 4294967296.0
        price = price * (1.0 + (rand_val - 0.5) * 0.02)
        if in_position:
            if price > peak_price:
                peak_price = price
            elif stop_pct > 0.0 and price <= peak_price * (1.0 - stop_pct):
                cash = units * price * (1.0 - fee_rate)
                units = 0.0
                in_position = False
                cooldown = 5
        else:
            if cooldown > 0:
                cooldown -= 1
            if cooldown == 0:
                units = (cash * (1.0 - fee_rate)) / price
                cash = 0.0
                in_position = True
                peak_price = price
    if in_position:
        return units * price
    else:
        return cash

def find_closest_point_to_ray(xs, ys, zs, ray_ox: float, ray_oy: float, ray_oz: float, ray_dx: float, ray_dy: float, ray_dz: float) -> int:
    n: int = len(xs)
    if n == 0 or len(ys) != n or len(zs) != n:
        return -1
    dir_len_sq: float = ray_dx * ray_dx + ray_dy * ray_dy + ray_dz * ray_dz
    if dir_len_sq <= 0.0:
        return -1
    inv_len: float = 1.0 / math.sqrt(dir_len_sq)
    dx: float = ray_dx * inv_len
    dy: float = ray_dy * inv_len
    dz: float = ray_dz * inv_len
    best_idx: int = -1
    min_dist_sq: float = 1e30
    for i in range(n):
        vx: float = xs[i] - ray_ox
        vy: float = ys[i] - ray_oy
        vz: float = zs[i] - ray_oz
        t: float = vx * dx + vy * dy + vz * dz
        if t < 0.0:
            t = 0.0
        wx: float = vx - t * dx
        wy: float = vy - t * dy
        wz: float = vz - t * dz
        dist_sq: float = wx * wx + wy * wy + wz * wz
        if dist_sq < min_dist_sq:
            min_dist_sq = dist_sq
            best_idx = i
    return best_idx

def accumulate_haversine_distance(lats, lons) -> float:
    n: int = len(lats)
    if n <= 1:
        return 0.0
    total_dist: float = 0.0
    r: float = 6371.0
    rad_factor: float = 3.141592653589793 / 180.0
    for i in range(1, n):
        lat1: float = lats[i - 1] * rad_factor
        lon1: float = lons[i - 1] * rad_factor
        lat2: float = lats[i] * rad_factor
        lon2: float = lons[i] * rad_factor
        dlat: float = lat2 - lat1
        dlon: float = lon2 - lon1
        half_dlat: float = dlat * 0.5
        half_dlon: float = dlon * 0.5
        sin_dlat: float = math.sin(half_dlat)
        sin_dlon: float = math.sin(half_dlon)
        a: float = sin_dlat * sin_dlat + math.cos(lat1) * math.cos(lat2) * sin_dlon * sin_dlon
        if a > 1.0:
            a = 1.0
        elif a < 0.0:
            a = 0.0
        c: float = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        total_dist = total_dist + r * c
    return total_dist

def clean_pdf_text(text: str) -> str:
    n: int = len(text)
    if n == 0:
        return ""
    result: str = ""
    i: int = 0
    while i < n:
        ch: str = text[i]
        if ch == "-" and i + 1 < n and (text[i + 1] == "\n" or text[i + 1] == "\r"):
            if i > 0 and ((text[i - 1] >= "a" and text[i - 1] <= "z") or (text[i - 1] >= "A" and text[i - 1] <= "Z")):
                i += 1
                while i < n and (text[i] == "\n" or text[i] == "\r" or text[i] == " " or text[i] == "\t"):
                    i += 1
                continue
        if ch == "\f":
            result += "\n\n"
            i += 1
            while i < n and (text[i] == " " or text[i] == "\t" or text[i] == "\n" or text[i] == "\r"):
                i += 1
            continue
        if ch == "\n" and i + 1 < n:
            if i + 6 <= n and text[i + 1:i + 6] == "Page ":
                j: int = i + 6
                while j < n and text[j] >= "0" and text[j] <= "9":
                    j += 1
                if j == n or text[j] == "\n" or text[j] == "\r":
                    i = j
                    continue
        if ch == " " or ch == "\t":
            result += " "
            i += 1
            while i < n and (text[i] == " " or text[i] == "\t"):
                i += 1
            continue
        if ch == "\n":
            nl_count: int = 0
            while i < n and (text[i] == "\n" or text[i] == "\r"):
                if text[i] == "\n":
                    nl_count += 1
                i += 1
            if nl_count >= 2:
                result += "\n\n"
            else:
                result += "\n"
            continue
        result += ch
        i += 1
    return result

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

def scrub_pii(text: str) -> str:
    result: str = ""
    n: int = len(text)
    i: int = 0
    while i < n:
        ch: str = text[i]
        if ch >= "A" and ch <= "Z" and (i == 0 or not ((text[i-1] >= "A" and text[i-1] <= "Z") or (text[i-1] >= "0" and text[i-1] <= "9"))):
            if i + 10 <= n:
                candidate: str = text[i : i + 10]
                boundary_after: bool = (i + 10 == n or not ((text[i+10] >= "A" and text[i+10] <= "Z") or (text[i+10] >= "0" and text[i+10] <= "9")))
                if boundary_after and check_pan(candidate):
                    result += "[REDACTED_PAN]"
                    i += 10
                    continue
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

def levenshtein_distance(s1: str, s2: str, max_dist: int) -> int:
    m: int = len(s1)
    n: int = len(s2)
    diff: int = m - n
    if diff < 0:
        diff = -diff
    if diff > max_dist:
        return max_dist + 1
    prev: list[int] = []
    curr: list[int] = []
    for j in range(n + 1):
        prev.append(j)
        curr.append(0)
    for i in range(1, m + 1):
        curr[0] = i
        min_row: int = i
        ch1: str = s1[i - 1]
        for j in range(1, n + 1):
            cost: int = 1
            if ch1 == s2[j - 1]:
                cost = 0
            del_cost: int = prev[j] + 1
            ins_cost: int = curr[j - 1] + 1
            sub_cost: int = prev[j - 1] + cost
            val: int = del_cost
            if ins_cost < val:
                val = ins_cost
            if sub_cost < val:
                val = sub_cost
            curr[j] = val
            if val < min_row:
                min_row = val
        if min_row > max_dist:
            return max_dist + 1
        for j in range(n + 1):
            prev[j] = curr[j]
    return prev[n]

def find_closest_match(query: str, candidates: list[str], max_distance: int) -> int:
    best_idx: int = -1
    best_dist: int = max_distance + 1
    num_candidates: int = len(candidates)
    for i in range(num_candidates):
        cand: str = candidates[i]
        dist: int = levenshtein_distance(query, cand, best_dist - 1)
        if dist < best_dist:
            best_dist = dist
            best_idx = i
            if best_dist == 0:
                break
    return best_idx

def chunk_document(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    chunks: list[str] = []
    n: int = len(text)
    if n == 0 or chunk_size <= 0:
        return chunks
    step: int = chunk_size - chunk_overlap
    if step <= 0:
        step = 1
    start: int = 0
    while start < n:
        ideal_end: int = start + chunk_size
        if ideal_end >= n:
            chunks.append(text[start:n])
            break
        lookback_limit: int = ideal_end - chunk_overlap
        if lookback_limit < start:
            lookback_limit = start
        boundary: int = -1
        idx: int = ideal_end
        while idx > lookback_limit:
            ch: str = text[idx]
            if ch == " " or ch == "\n" or ch == "\t":
                boundary = idx
                break
            idx -= 1
        end: int = ideal_end
        if boundary > start:
            end = boundary
        chunks.append(text[start:end])
        next_start: int = end - chunk_overlap
        if next_start <= start:
            next_start = start + step
            if next_start <= start:
                next_start = start + 1
        start = next_start
    return chunks
