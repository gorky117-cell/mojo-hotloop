from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.collections import List
from std.os import abort
import std.math as math

# Checked Arithmetic and Error Signaling Helpers (Mojo 1.2.0)
@always_inline
def _checked_add(a: Int, b: Int) raises -> Int:
    if (a ^ b) < 0:
        return a + b
    if a >= 0:
        if a <= 4611686018427387903 and b <= 4611686018427387903:
            return a + b
        if a > 9223372036854775807 - b:
            raise Error("HOTLOOP_INTEGER_OVERFLOW: integer addition overflow")
        return a + b
    if a >= -4611686018427387904 and b >= -4611686018427387904:
        return a + b
    if a < -9223372036854775808 - b:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer addition underflow")
    return a + b

@always_inline
def _checked_add(a: Float64, b: Float64) raises -> Float64:
    return a + b

@always_inline
def _checked_add(a: Float64, b: Int) raises -> Float64:
    return a + Float64(b)

@always_inline
def _checked_add(a: Int, b: Float64) raises -> Float64:
    return Float64(a) + b

@always_inline
def _checked_sub(a: Int, b: Int) raises -> Int:
    if (a >= 0 and b >= 0) or (a < 0 and b > -9223372036854775808 and b <= 0):
        return a - b
    if b > 0 and a < -9223372036854775808 + b:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer subtraction underflow")
    if b < 0 and a > 9223372036854775807 + b:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer subtraction overflow")
    return a - b

@always_inline
def _checked_sub(a: Float64, b: Float64) raises -> Float64:
    return a - b

@always_inline
def _checked_sub(a: Float64, b: Int) raises -> Float64:
    return a - Float64(b)

@always_inline
def _checked_sub(a: Int, b: Float64) raises -> Float64:
    return Float64(a) - b

@always_inline
def _checked_mul(a: Int, b: Int) raises -> Int:
    var abs_a = -a if a < 0 else a
    var abs_b = -b if b < 0 else b
    if abs_a <= 3037000499 and abs_b <= 3037000499:
        return a * b
    if a == 0 or b == 0:
        return 0
    if a == -1 and b == -9223372036854775808:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication overflow")
    if b == -1 and a == -9223372036854775808:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication overflow")
    if a == -9223372036854775808 or b == -9223372036854775808:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication overflow")
    if a > 0:
        if b > 0 and a > 9223372036854775807 // b:
            raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication overflow")
        if b < 0 and b < -9223372036854775808 // a:
            raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication underflow")
    else:
        if b > 0 and a < -9223372036854775808 // b:
            raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication underflow")
        if b < 0 and b < 9223372036854775807 // a:
            raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication overflow")
    return a * b

@always_inline
def _checked_mul(a: Float64, b: Float64) raises -> Float64:
    return a * b

@always_inline
def _checked_mul(a: Float64, b: Int) raises -> Float64:
    return a * Float64(b)

@always_inline
def _checked_mul(a: Int, b: Float64) raises -> Float64:
    return Float64(a) * b

@always_inline
def _checked_neg(a: Int) raises -> Int:
    if a == -9223372036854775808:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer negation overflow")
    return -a

@always_inline
def _checked_neg(a: Float64) raises -> Float64:
    return -a

@always_inline
def _checked_div(a: Float64, b: Float64) raises -> Float64:
    if b == 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float division by zero")
    return a / b

@always_inline
def _checked_div(a: Int, b: Int) raises -> Float64:
    if b == 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: division by zero")
    return Float64(a) / Float64(b)

@always_inline
def _checked_div(a: Float64, b: Int) raises -> Float64:
    if b == 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float division by zero")
    return a / Float64(b)

@always_inline
def _checked_div(a: Int, b: Float64) raises -> Float64:
    if b == 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float division by zero")
    return Float64(a) / b

@always_inline
def _checked_floordiv(a: Int, b: Int) raises -> Int:
    if b == 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: integer division or modulo by zero")
    if a == -9223372036854775808 and b == -1:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer division overflow")
    return a // b

@always_inline
def _checked_floordiv(a: Float64, b: Float64) raises -> Float64:
    if b == 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float division by zero")
    return math.floor(a / b)

@always_inline
def _checked_mod(a: Int, b: Int) raises -> Int:
    if b == 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: integer division or modulo by zero")
    if a == -9223372036854775808 and b == -1:
        return 0
    return a % b

@always_inline
def _checked_mod(a: Float64, b: Float64) raises -> Float64:
    if b == 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float modulo by zero")
    return a % b

@always_inline
def _checked_pow(base: Int, exp: Int) raises -> Int:
    if exp == 2:
        return _checked_mul(base, base)
    if exp == 1:
        return base
    if exp == 0:
        return 1
    if exp == 3:
        var b2 = _checked_mul(base, base)
        return _checked_mul(b2, base)
    if exp < 0:
        raise Error("HOTLOOP_VALUE_ERROR: negative power exponent")
    if base == 0:
        return 0
    if base == 1:
        return 1
    if base == -1:
        return 1 if (exp % 2 == 0) else -1
    if exp > 62:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer power overflow")
    var res: Int = 1
    var cur_base: Int = base
    var cur_exp: Int = exp
    while cur_exp > 0:
        if cur_exp % 2 == 1:
            res = _checked_mul(res, cur_base)
        cur_exp = cur_exp // 2
        if cur_exp > 0:
            cur_base = _checked_mul(cur_base, cur_base)
    return res

@always_inline
def _checked_pow(base: Float64, exp: Float64) raises -> Float64:
    return base ** exp

@always_inline
def _checked_pow(base: Float64, exp: Int) raises -> Float64:
    return base ** Float64(exp)

@always_inline
def _checked_pow(base: Int, exp: Float64) raises -> Float64:
    return Float64(base) ** exp

@always_inline
def _checked_add(a: String, b: String) -> String:
    var res = a
    res.write(b)
    return res^

@always_inline
def _checked_add(a: String, b: Codepoint) -> String:
    var res = a
    res.write(b)
    return res^

@always_inline
def _len(s: String) -> Int:
    return len(s.codepoints())

@always_inline
def _len(l: List[Int]) -> Int:
    return len(l)

@always_inline
def _len(l: List[Float64]) -> Int:
    return len(l)

@always_inline
def _len(l: List[Bool]) -> Int:
    return len(l)

@always_inline
def _len(l: List[String]) -> Int:
    return len(l)

struct _PyStr(Sized):
    var _cps: List[Codepoint]

    @always_inline
    def __init__(out self, s: String):
        self._cps = List[Codepoint]()
        for cp in s.codepoints():
            self._cps.append(cp)

    @always_inline
    def __len__(self) -> Int:
        return len(self._cps)

    @always_inline
    def __getitem__(self, idx: Int) -> String:
        var i = idx
        if i < 0:
            i += len(self._cps)
        return String(self._cps[i])

    @always_inline
    def __getitem__(self, s: Slice) -> String:
        var n = len(self._cps)
        var start = s.start.or_else(0)
        var end = s.end.or_else(n)
        if start < 0:
            start += n
        if end < 0:
            end += n
        var s_c = max(0, min(n, start))
        var e_c = max(0, min(n, end))
        var res = String()
        for k in range(s_c, e_c):
            res.write(self._cps[k])
        return res^

    @always_inline
    def codepoints(self) -> List[Codepoint]:
        return self._cps.copy()

@always_inline
def _len(s: _PyStr) -> Int:
    return len(s)


@export
def PyInit_fast() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast")
        m.def_function[scrub_pii]("scrub_pii")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def scrub_pii(arg0: PythonObject) raises -> PythonObject:
    var text = String(py=arg0)
    var _res = _native_scrub_pii(text)
    return PythonObject(_res)

def _native_check_luhn(digits: List[Int]) raises -> Bool:
    var n: Int = _len(digits)
    if ((n < 13) or (n > 19)):
        return False
    var total: Int = 0
    var parity: Int = _checked_mod(n, 2)
    for i in range(n):
        var d: Int = digits[i]
        if (_checked_mod(i, 2) == parity):
            d = _checked_mul(d, 2)
            if (d > 9):
                d = _checked_sub(d, 9)
        total = _checked_add(total, d)
    return (_checked_mod(total, 10) == 0)

def _native_check_verhoeff(digits: List[Int]) raises -> Bool:
    var n: Int = _len(digits)
    if (n != 12):
        return False
    if (digits[0] < 2):
        return False
    var d_table: List[Int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4, 0, 6, 7, 8, 9, 5, 2, 3, 4, 0, 1, 7, 8, 9, 5, 6, 3, 4, 0, 1, 2, 8, 9, 5, 6, 7, 4, 0, 1, 2, 3, 9, 5, 6, 7, 8, 5, 9, 8, 7, 6, 0, 4, 3, 2, 1, 6, 5, 9, 8, 7, 1, 0, 4, 3, 2, 7, 6, 5, 9, 8, 2, 1, 0, 4, 3, 8, 7, 6, 5, 9, 3, 2, 1, 0, 4, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    var p_table: List[Int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 5, 7, 6, 2, 8, 3, 0, 9, 4, 5, 8, 0, 3, 7, 9, 6, 1, 4, 2, 8, 9, 1, 6, 0, 4, 3, 5, 2, 7, 9, 4, 5, 3, 1, 2, 6, 8, 7, 0, 4, 2, 8, 6, 5, 7, 3, 9, 0, 1, 2, 7, 9, 3, 8, 0, 6, 4, 1, 5, 7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    var c: Int = 0
    for i in range(n):
        var val: Int = digits[_checked_sub(_checked_sub(n, 1), i)]
        c = d_table[_checked_add(_checked_mul(c, 10), p_table[_checked_add(_checked_mul(_checked_mod(i, 8), 10), val)])]
    return (c == 0)

def _native_check_phone(digits: List[Int]) raises -> Bool:
    var n: Int = _len(digits)
    if (n == 10):
        return (digits[0] >= 6)
    elif ((n == 11) and (digits[0] == 0)):
        return (digits[1] >= 6)
    else:
        if ((n == 12) and (digits[0] == 9) and (digits[1] == 1)):
            return (digits[2] >= 6)
    return False

def _native_check_pan(_arg_s: String) raises -> Bool:
    if (_arg_s.byte_length() != 10):
        return False
    var b = _arg_s.as_bytes()
    for i in range(5):
        var c = Int(b[i])
        if ((c < 65) or (c > 90)):
            return False
    for i in range(5, 9):
        var c = Int(b[i])
        if ((c < 48) or (c > 57)):
            return False
    var c_last = Int(b[9])
    return ((c_last >= 65) and (c_last <= 90))

def _native_scrub_pii(_arg_text: String) raises -> String:
    var text: _PyStr = _PyStr(_arg_text)
    var result: String = String()
    result.reserve_bytes(_arg_text.byte_length())
    var n: Int = len(text._cps)
    var i: Int = 0
    while (i < n):
        var cp = text._cps[i]
        var c = Int(cp)
        if ((c >= 65) and (c <= 90)):
            var b_prev_ok = (i == 0)
            if not b_prev_ok:
                var prev_c = Int(text._cps[i - 1])
                b_prev_ok = not (((prev_c >= 65) and (prev_c <= 90)) or ((prev_c >= 48) and (prev_c <= 57)))
            if b_prev_ok and (_checked_add(i, 10) <= n):
                var boundary_after = (_checked_add(i, 10) == n)
                if not boundary_after:
                    var next_c = Int(text._cps[i + 10])
                    boundary_after = not (((next_c >= 65) and (next_c <= 90)) or ((next_c >= 48) and (next_c <= 57)))
                if boundary_after:
                    var candidate: String = text[i:_checked_add(i, 10)]
                    if _native_check_pan(candidate):
                        result.write('[REDACTED_PAN]')
                        i = _checked_add(i, 10)
                        continue

        var is_num_start: Bool = (((c >= 48) and (c <= 57)) or ((c == 43) and (_checked_add(i, 1) < n) and (Int(text._cps[i + 1]) >= 48) and (Int(text._cps[i + 1]) <= 57)))
        var boundary_before = (i == 0)
        if not boundary_before:
            var prev_c = Int(text._cps[i - 1])
            boundary_before = not (((prev_c >= 65) and (prev_c <= 90)) or ((prev_c >= 97) and (prev_c <= 122)) or ((prev_c >= 48) and (prev_c <= 57)))

        if (is_num_start and boundary_before):
            var start_idx: Int = i
            var digits: List[Int] = List[Int]()
            while (i < n):
                var curr_c = Int(text._cps[i])
                if ((curr_c >= 48) and (curr_c <= 57)):
                    digits.append(curr_c - 48)
                    i = _checked_add(i, 1)
                elif ((curr_c == 43) and (i == start_idx)):
                    i = _checked_add(i, 1)
                else:
                    if (((curr_c == 32) or (curr_c == 45)) and ((_checked_add(i, 1) < n) and (Int(text._cps[i + 1]) >= 48) and (Int(text._cps[i + 1]) <= 57))):
                        i = _checked_add(i, 1)
                    else:
                        break
            var candidate_num: String = text[start_idx:i]
            var boundary_after_num = (i == n)
            if not boundary_after_num:
                var next_c = Int(text._cps[i])
                boundary_after_num = not (((next_c >= 65) and (next_c <= 90)) or ((next_c >= 97) and (next_c <= 122)) or ((next_c >= 48) and (next_c <= 57)))

            if (boundary_after_num and _native_check_luhn(digits)):
                result.write('[REDACTED_CC]')
            elif (boundary_after_num and _native_check_verhoeff(digits)):
                result.write('[REDACTED_AADHAAR]')
            else:
                if (boundary_after_num and _native_check_phone(digits)):
                    result.write('[REDACTED_PHONE]')
                else:
                    result.write(candidate_num)
            continue
        result.write(cp)
        i = _checked_add(i, 1)
    return result^
