from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.collections import List
from std.memory import OpaquePointer
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
def _checked_add(a: Float64, b: Float64) -> Float64:
    return a + b

@always_inline
def _checked_add(a: Float64, b: Int) -> Float64:
    return a + Float64(b)

@always_inline
def _checked_add(a: Int, b: Float64) -> Float64:
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
def _checked_sub(a: Float64, b: Float64) -> Float64:
    return a - b

@always_inline
def _checked_sub(a: Float64, b: Int) -> Float64:
    return a - Float64(b)

@always_inline
def _checked_sub(a: Int, b: Float64) -> Float64:
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
def _checked_mul(a: Float64, b: Float64) -> Float64:
    return a * b

@always_inline
def _checked_mul(a: Float64, b: Int) -> Float64:
    return a * Float64(b)

@always_inline
def _checked_mul(a: Int, b: Float64) -> Float64:
    return Float64(a) * b

@always_inline
def _checked_neg(a: Int) raises -> Int:
    if a == -9223372036854775808:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer negation overflow")
    return -a

@always_inline
def _checked_neg(a: Float64) -> Float64:
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
def _checked_floordiv(a: Float64, b: Int) raises -> Float64:
    if b == 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float division by zero")
    return math.floor(a / Float64(b))

@always_inline
def _checked_floordiv(a: Int, b: Float64) raises -> Float64:
    if b == 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float division by zero")
    return math.floor(Float64(a) / b)

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
def _checked_mod(a: Float64, b: Int) raises -> Float64:
    if b == 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float modulo by zero")
    return a % Float64(b)

@always_inline
def _checked_mod(a: Int, b: Float64) raises -> Float64:
    if b == 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: float modulo by zero")
    return Float64(a) % b

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
    if base == 0.0 and exp < 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: 0.0 cannot be raised to a negative power")
    return base ** exp

@always_inline
def _checked_pow(base: Float64, exp: Int) raises -> Float64:
    if base == 0.0 and exp < 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: 0.0 cannot be raised to a negative power")
    return base ** Float64(exp)

@always_inline
def _checked_pow(base: Int, exp: Float64) raises -> Float64:
    if base == 0 and exp < 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: 0.0 cannot be raised to a negative power")
    return Float64(base) ** exp

@always_inline
def _checked_index(idx: Int, n: Int) raises -> Int:
    if UInt(idx) < UInt(n):
        return idx
    var j = idx + n
    if UInt(j) < UInt(n):
        return j
    raise Error("HOTLOOP_INDEX_ERROR: index out of range")

@always_inline
def _safe_array_index(idx: Int) -> Int:
    return idx

@always_inline
def _py_bool(x: Bool) -> Bool:
    return x

@always_inline
def _py_bool(x: Int) -> Bool:
    return x != 0

@always_inline
def _py_bool(x: Float64) -> Bool:
    return x != 0.0

@always_inline
def _py_bool(x: String) -> Bool:
    return x.byte_length() > 0

@always_inline
def _py_bool(x: List[Int]) -> Bool:
    return len(x) > 0

@always_inline
def _py_bool(x: List[Float64]) -> Bool:
    return len(x) > 0

@always_inline
def _py_bool(x: List[Bool]) -> Bool:
    return len(x) > 0

@always_inline
def _py_bool(x: List[String]) -> Bool:
    return len(x) > 0

@always_inline
def _checked_add(a: String, b: String) -> String:
    var res = String()
    res.reserve_bytes(a.byte_length() + b.byte_length())
    res.write(a)
    res.write(b)
    return res^

@always_inline
def _checked_add(a: String, b: Codepoint) -> String:
    var res = String()
    res.reserve_bytes(a.byte_length() + 4)
    res.write(a)
    res.write(b)
    return res^

@always_inline
def _len(s: String) -> Int:
    var raw = s.as_bytes()
    for k in range(len(raw)):
        if raw[k] >= 128:
            return len(s.codepoints())
    return len(raw)

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
    var _s: String
    var _cps: List[Codepoint]
    var _is_ascii: Bool

    @always_inline
    def __init__(out self, s: String):
        self._s = s
        var raw = self._s.as_bytes()
        var is_ascii = True
        for k in range(len(raw)):
            if raw[k] >= 128:
                is_ascii = False
                break
        self._is_ascii = is_ascii
        self._cps = List[Codepoint]()
        if not is_ascii:
            self._cps = List[Codepoint](capacity=len(raw))
            for cp in self._s.codepoints():
                self._cps.append(cp)

    @always_inline
    def __len__(self) -> Int:
        if self._is_ascii:
            return self._s.byte_length()
        return len(self._cps)

    @always_inline
    def to_string(self) -> String:
        return self._s

    @always_inline
    def __getitem__(self, idx: Int) raises -> String:
        return String(self.get_cp(idx))

    @always_inline
    def get_cp(self, idx: Int) raises -> Codepoint:
        var i = _checked_index(idx, len(self))
        if self._is_ascii:
            return Codepoint(self._s.as_bytes()[i])
        return self._cps[i]

    @always_inline
    def get_ord(self, idx: Int) raises -> Int:
        var i = _checked_index(idx, len(self))
        if self._is_ascii:
            return Int(self._s.as_bytes()[i])
        return Int(self._cps[i])

    @always_inline
    def get_cp_fast(self, idx: Int) -> Codepoint:
        if self._is_ascii:
            return Codepoint(self._s.as_bytes()[_safe_array_index(idx)])
        return self._cps[_safe_array_index(idx)]

    @always_inline
    def get_ord_fast(self, idx: Int) -> Int:
        if self._is_ascii:
            return Int(self._s.as_bytes()[_safe_array_index(idx)])
        return Int(self._cps[_safe_array_index(idx)])

    @always_inline
    def __getitem__(self, s: Slice) -> String:
        var n = len(self)
        var start = s.start.or_else(0)
        var end = s.end.or_else(n)
        if start < 0:
            start += n
        if end < 0:
            end += n
        var s_c = max(0, min(n, start))
        var e_c = max(0, min(n, end))
        if s_c >= e_c:
            return String()
        if self._is_ascii:
            return String(self._s[byte=s_c:e_c])
        var res = String()
        res.reserve_bytes((e_c - s_c) * 4)
        for k in range(s_c, e_c):
            res.write(self._cps[k])
        return res^

    @always_inline
    def eq_slice(self, start_in: Int, end_in: Int, lit: String) -> Bool:
        var n = len(self)
        var start = start_in + n if start_in < 0 else start_in
        var end = end_in + n if end_in < 0 else end_in
        var s_c = max(0, min(n, start))
        var e_c = max(0, min(n, end))
        if s_c >= e_c:
            return lit.byte_length() == 0
        if self._is_ascii:
            var lraw = lit.as_bytes()
            if (e_c - s_c) != len(lraw):
                return False
            var raw = self._s.as_bytes()
            for k in range(len(lraw)):
                if raw[s_c + k] != lraw[k]:
                    return False
            return True
        return self[s_c:e_c] == lit

    @always_inline
    def slice_step(self, has_start: Bool, start_val: Int, has_end: Bool, end_val: Int, step_val: Int) raises -> String:
        if step_val == 0:
            raise Error("HOTLOOP_VALUE_ERROR: slice step cannot be zero")
        var n = len(self)
        var s_c: Int
        var e_c: Int
        if step_val > 0:
            s_c = start_val if has_start else 0
            if s_c < 0:
                s_c += n
            s_c = max(0, min(n, s_c))
            e_c = end_val if has_end else n
            if e_c < 0:
                e_c += n
            e_c = max(0, min(n, e_c))
        else:
            s_c = start_val if has_start else (n - 1)
            if s_c < 0:
                s_c += n
            s_c = max(-1, min(n - 1, s_c))
            if has_end:
                e_c = end_val
                if e_c < 0:
                    e_c += n
                e_c = max(-1, min(n - 1, e_c))
            else:
                e_c = -1
        var res = String()
        if self._is_ascii:
            var raw = self._s.as_bytes()
            res.reserve_bytes(n)
            var k = s_c
            if step_val > 0:
                while k < e_c:
                    res.write(Codepoint(raw[k]))
                    k += step_val
            else:
                while k > e_c:
                    res.write(Codepoint(raw[k]))
                    k += step_val
        else:
            res.reserve_bytes(n * 4)
            var k = s_c
            if step_val > 0:
                while k < e_c:
                    res.write(self._cps[k])
                    k += step_val
            else:
                while k > e_c:
                    res.write(self._cps[k])
                    k += step_val
        return res^

    @always_inline
    def codepoints(self) -> List[Codepoint]:
        if self._is_ascii:
            var out = List[Codepoint](capacity=self._s.byte_length())
            for cp in self._s.codepoints():
                out.append(cp)
            return out^
        return self._cps.copy()

@always_inline
def _len(s: _PyStr) -> Int:
    return len(s)

@always_inline
def _py_bool(x: _PyStr) -> Bool:
    return len(x) > 0

@always_inline
def _str_get(s: String, idx: Int) raises -> String:
    return _PyStr(s)[idx]

@always_inline
def _str_slice(s: String, has_start: Bool, start_val: Int, has_end: Bool, end_val: Int, step_val: Int) raises -> String:
    return _PyStr(s).slice_step(has_start, start_val, has_end, end_val, step_val)

@always_inline
def _py_ord(s: String) raises -> Int:
    var n = _len(s)
    if n != 1:
        raise Error("HOTLOOP_VALUE_ERROR: ord() expected a character, but string of length found")
    for cp in s.codepoints():
        return Int(cp)
    raise Error("HOTLOOP_VALUE_ERROR: ord() expected a character")

@always_inline
def _py_chr(code: Int) raises -> String:
    if code < 0 or code > 0x10FFFF or (code >= 0xD800 and code <= 0xDFFF):
        raise Error("HOTLOOP_VALUE_ERROR: chr() arg not in Unicode scalar range")
    return String(Codepoint(unsafe_unchecked_codepoint=UInt32(code)))

@always_inline
def _checked_abs(a: Int) raises -> Int:
    if a == -9223372036854775808:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer abs overflow")
    return abs(a)

@always_inline
def _checked_abs(a: Float64) -> Float64:
    return abs(a)


@export
def PyInit_fast() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast")
        m.def_function[_pywrap_scrub_pii]("scrub_pii")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def _pywrap_scrub_pii(arg0: PythonObject) raises -> PythonObject:
    var text = String(py=arg0)
    var _res = _native_scrub_pii(text)
    return PythonObject(_res)

@always_inline
def _ptr_check_luhn(digits_ptr: OpaquePointer[MutUntrackedOrigin], _n_digits: Int) raises -> Bool:
    var digits = digits_ptr.unsafe_bitcast[Int]()
    var n: Int = _n_digits
    if ((n < 13) or (n > 19)):
        return False
    var total: Int = 0
    var parity: Int = _checked_mod(n, 2)
    for i in range(n):
        var d: Int = digits[unsafe_offset=_safe_array_index(i)]
        if (_checked_mod(i, 2) == parity):
            d = _checked_mul(d, 2)
            if (d > 9):
                d = _checked_sub(d, 9)
        total = _checked_add(total, d)
    return (_checked_mod(total, 10) == 0)

def _native_check_luhn(digits: List[Int]) raises -> Bool:
    var n: Int = _len(digits)
    if ((n < 13) or (n > 19)):
        return False
    var total: Int = 0
    var parity: Int = _checked_mod(n, 2)
    for i in range(n):
        var d: Int = digits[_safe_array_index(i)]
        if (_checked_mod(i, 2) == parity):
            d = _checked_mul(d, 2)
            if (d > 9):
                d = _checked_sub(d, 9)
        total = _checked_add(total, d)
    return (_checked_mod(total, 10) == 0)

@always_inline
def _ptr_check_verhoeff(digits_ptr: OpaquePointer[MutUntrackedOrigin], _n_digits: Int) raises -> Bool:
    var digits = digits_ptr.unsafe_bitcast[Int]()
    var n: Int = _n_digits
    if (n != 12):
        return False
    if (digits[unsafe_offset=_checked_index(0, _n_digits)] < 2):
        return False
    var d_table: List[Int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4, 0, 6, 7, 8, 9, 5, 2, 3, 4, 0, 1, 7, 8, 9, 5, 6, 3, 4, 0, 1, 2, 8, 9, 5, 6, 7, 4, 0, 1, 2, 3, 9, 5, 6, 7, 8, 5, 9, 8, 7, 6, 0, 4, 3, 2, 1, 6, 5, 9, 8, 7, 1, 0, 4, 3, 2, 7, 6, 5, 9, 8, 2, 1, 0, 4, 3, 8, 7, 6, 5, 9, 3, 2, 1, 0, 4, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    var p_table: List[Int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 5, 7, 6, 2, 8, 3, 0, 9, 4, 5, 8, 0, 3, 7, 9, 6, 1, 4, 2, 8, 9, 1, 6, 0, 4, 3, 5, 2, 7, 9, 4, 5, 3, 1, 2, 6, 8, 7, 0, 4, 2, 8, 6, 5, 7, 3, 9, 0, 1, 2, 7, 9, 3, 8, 0, 6, 4, 1, 5, 7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    var c: Int = 0
    var _inv_1 = _checked_sub(n, 1)
    for i in range(n):
        var val: Int = digits[unsafe_offset=_checked_index(_checked_sub(_inv_1, i), _n_digits)]
        c = d_table[_checked_index(_checked_add(_checked_mul(c, 10), p_table[_checked_index(_checked_add(_checked_mul(_checked_mod(i, 8), 10), val), len(p_table))]), len(d_table))]
    return (c == 0)

def _native_check_verhoeff(digits: List[Int]) raises -> Bool:
    var n: Int = _len(digits)
    if (n != 12):
        return False
    if (digits[_checked_index(0, len(digits))] < 2):
        return False
    var d_table: List[Int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 2, 3, 4, 0, 6, 7, 8, 9, 5, 2, 3, 4, 0, 1, 7, 8, 9, 5, 6, 3, 4, 0, 1, 2, 8, 9, 5, 6, 7, 4, 0, 1, 2, 3, 9, 5, 6, 7, 8, 5, 9, 8, 7, 6, 0, 4, 3, 2, 1, 6, 5, 9, 8, 7, 1, 0, 4, 3, 2, 7, 6, 5, 9, 8, 2, 1, 0, 4, 3, 8, 7, 6, 5, 9, 3, 2, 1, 0, 4, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
    var p_table: List[Int] = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 1, 5, 7, 6, 2, 8, 3, 0, 9, 4, 5, 8, 0, 3, 7, 9, 6, 1, 4, 2, 8, 9, 1, 6, 0, 4, 3, 5, 2, 7, 9, 4, 5, 3, 1, 2, 6, 8, 7, 0, 4, 2, 8, 6, 5, 7, 3, 9, 0, 1, 2, 7, 9, 3, 8, 0, 6, 4, 1, 5, 7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
    var c: Int = 0
    var _inv_1 = _checked_sub(n, 1)
    for i in range(n):
        var val: Int = digits[_checked_index(_checked_sub(_inv_1, i), len(digits))]
        c = d_table[_checked_index(_checked_add(_checked_mul(c, 10), p_table[_checked_index(_checked_add(_checked_mul(_checked_mod(i, 8), 10), val), len(p_table))]), len(d_table))]
    return (c == 0)

@always_inline
def _ptr_check_phone(digits_ptr: OpaquePointer[MutUntrackedOrigin], _n_digits: Int) raises -> Bool:
    var digits = digits_ptr.unsafe_bitcast[Int]()
    var n: Int = _n_digits
    if (n == 10):
        return (digits[unsafe_offset=_checked_index(0, _n_digits)] >= 6)
    elif ((n == 11) and (digits[unsafe_offset=_checked_index(0, _n_digits)] == 0)):
        return (digits[unsafe_offset=_checked_index(1, _n_digits)] >= 6)
    elif ((n == 12) and (digits[unsafe_offset=_checked_index(0, _n_digits)] == 9) and (digits[unsafe_offset=_checked_index(1, _n_digits)] == 1)):
        return (digits[unsafe_offset=_checked_index(2, _n_digits)] >= 6)
    return False

def _native_check_phone(digits: List[Int]) raises -> Bool:
    var n: Int = _len(digits)
    if (n == 10):
        return (digits[_checked_index(0, len(digits))] >= 6)
    elif ((n == 11) and (digits[_checked_index(0, len(digits))] == 0)):
        return (digits[_checked_index(1, len(digits))] >= 6)
    elif ((n == 12) and (digits[_checked_index(0, len(digits))] == 9) and (digits[_checked_index(1, len(digits))] == 1)):
        return (digits[_checked_index(2, len(digits))] >= 6)
    return False

def _native_check_pan(_arg_s: String) raises -> Bool:
    var s: _PyStr = _PyStr(_arg_s)
    if (_len(s) != 10):
        return False
    for i in range(5):
        var ch: Codepoint = s.get_cp_fast(i)
        if ((Int(ch) < 65) or (Int(ch) > 90)):
            return False
    for i in range(5, 9):
        var ch: Codepoint = s.get_cp_fast(i)
        if ((Int(ch) < 48) or (Int(ch) > 57)):
            return False
    var ch_last: Codepoint = s.get_cp_fast(9)
    return ((Int(ch_last) >= 65) and (Int(ch_last) <= 90))

def _native_scrub_pii(_arg_text: String) raises -> String:
    var text: _PyStr = _PyStr(_arg_text)
    var result: String = String()
    result.reserve_bytes(_len(text))
    var n: Int = _len(text)
    var i: Int = 0
    while (i < n):
        var ch: Codepoint = text.get_cp_fast(i)
        if ((Int(ch) >= 65) and (Int(ch) <= 90) and ((i == 0) or (not (((text.get_ord_fast(_checked_sub(i, 1)) >= 65) and (text.get_ord_fast(_checked_sub(i, 1)) <= 90)) or ((text.get_ord_fast(_checked_sub(i, 1)) >= 48) and (text.get_ord_fast(_checked_sub(i, 1)) <= 57)))))):
            if (_checked_add(i, 10) <= n):
                var candidate: String = text[i:_checked_add(i, 10)]
                var boundary_after: Bool = ((_checked_add(i, 10) == n) or (not (((text.get_ord_fast(_checked_add(i, 10)) >= 65) and (text.get_ord_fast(_checked_add(i, 10)) <= 90)) or ((text.get_ord_fast(_checked_add(i, 10)) >= 48) and (text.get_ord_fast(_checked_add(i, 10)) <= 57)))))
                if (boundary_after and _py_bool(_native_check_pan(candidate))):
                    result.write('[REDACTED_PAN]')
                    i = _checked_add(i, 10)
                    continue
        var is_num_start: Bool = (((Int(ch) >= 48) and (Int(ch) <= 57)) or ((Int(ch) == 43) and (_checked_add(i, 1) < n) and (text.get_ord_fast(_checked_add(i, 1)) >= 48) and (text.get_ord_fast(_checked_add(i, 1)) <= 57)))
        var boundary_before: Bool = ((i == 0) or (not (((text.get_ord_fast(_checked_sub(i, 1)) >= 65) and (text.get_ord_fast(_checked_sub(i, 1)) <= 90)) or ((text.get_ord_fast(_checked_sub(i, 1)) >= 97) and (text.get_ord_fast(_checked_sub(i, 1)) <= 122)) or ((text.get_ord_fast(_checked_sub(i, 1)) >= 48) and (text.get_ord_fast(_checked_sub(i, 1)) <= 57)))))
        if (is_num_start and boundary_before):
            var start_idx: Int = i
            var digits: List[Int] = List[Int]()
            while (i < n):
                var curr: String = text[i]
                if ((curr >= '0') and (curr <= '9')):
                    digits.append(Int(curr))
                    i = _checked_add(i, 1)
                elif ((curr == '+') and (i == start_idx)):
                    i = _checked_add(i, 1)
                elif (((curr == ' ') or (curr == '-')) and ((_checked_add(i, 1) < n) and (text.get_ord_fast(_checked_add(i, 1)) >= 48) and (text.get_ord_fast(_checked_add(i, 1)) <= 57))):
                    i = _checked_add(i, 1)
                else:
                    break
            var candidate_num: String = text[start_idx:i]
            var boundary_after_num: Bool = ((i == n) or (not (((text.get_ord_fast(i) >= 65) and (text.get_ord_fast(i) <= 90)) or ((text.get_ord_fast(i) >= 97) and (text.get_ord_fast(i) <= 122)) or ((text.get_ord_fast(i) >= 48) and (text.get_ord_fast(i) <= 57)))))
            if (boundary_after_num and _py_bool(_native_check_luhn(digits))):
                result.write('[REDACTED_CC]')
            elif (boundary_after_num and _py_bool(_native_check_verhoeff(digits))):
                result.write('[REDACTED_AADHAAR]')
            elif (boundary_after_num and _py_bool(_native_check_phone(digits))):
                result.write('[REDACTED_PHONE]')
            else:
                result.write(candidate_num)
            continue
        result.write(ch)
        i = _checked_add(i, 1)
    return result^
