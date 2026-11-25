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
    # A product of two signed 64-bit operands always fits in signed Int128.
    # Narrow and sign-extend to check whether the result still fits in Int.
    var wide = Int128(a) * Int128(b)
    var result = Int(wide)
    if wide != Int128(result):
        if wide < Int128(0):
            raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication underflow")
        raise Error("HOTLOOP_INTEGER_OVERFLOW: integer multiplication overflow")
    return result

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
def _checked_lshift(a: Int, count: Int) raises -> Int:
    if count < 0:
        raise Error("HOTLOOP_VALUE_ERROR: negative shift count")
    if a == 0:
        return 0
    if count > 63:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: left shift overflow")
    var wide = Int128(a) << Int128(count)
    var result = Int(wide)
    if Int128(result) != wide:
        raise Error("HOTLOOP_INTEGER_OVERFLOW: left shift overflow")
    return result

@always_inline
def _checked_rshift(a: Int, count: Int) raises -> Int:
    if count < 0:
        raise Error("HOTLOOP_VALUE_ERROR: negative shift count")
    return a >> min(count, 63)

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
    if a > 9007199254740992 or a < -9007199254740992 or b > 9007199254740992 or b < -9007199254740992:
        raise Error("HOTLOOP_PYTHON_SEMANTICS: integer true division requires exact rounding")
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
    raise Error("HOTLOOP_PYTHON_SEMANTICS: floating divmod requires Python rounding")

@always_inline
def _checked_floordiv(a: Float64, b: Int) raises -> Float64:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: floating divmod requires Python rounding")

@always_inline
def _checked_floordiv(a: Int, b: Float64) raises -> Float64:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: floating divmod requires Python rounding")

@always_inline
def _checked_mod(a: Int, b: Int) raises -> Int:
    if b == 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: integer division or modulo by zero")
    if a == -9223372036854775808 and b == -1:
        return 0
    return a % b

@always_inline
def _checked_mod(a: Float64, b: Float64) raises -> Float64:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: floating divmod requires Python rounding")

@always_inline
def _checked_mod(a: Float64, b: Int) raises -> Float64:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: floating divmod requires Python rounding")

@always_inline
def _checked_mod(a: Int, b: Float64) raises -> Float64:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: floating divmod requires Python rounding")

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
        raise Error("HOTLOOP_PYTHON_SEMANTICS: negative integer exponent requires Python")
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
    if base < 0.0:
        raise Error("HOTLOOP_PYTHON_SEMANTICS: negative real power")
    var result = base ** exp
    if not math.isfinite(result):
        raise Error("HOTLOOP_PYTHON_SEMANTICS: non-finite real power")
    return result

@always_inline
def _checked_pow(base: Float64, exp: Int) raises -> Float64:
    if base == 0.0 and exp < 0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: 0.0 cannot be raised to a negative power")
    if exp > 9007199254740992 or exp < -9007199254740992:
        raise Error("HOTLOOP_PYTHON_SEMANTICS: exponent exceeds exact float range")
    return _checked_pow(base, Float64(exp))

@always_inline
def _checked_pow(base: Int, exp: Float64) raises -> Float64:
    if base == 0 and exp < 0.0:
        raise Error("HOTLOOP_ZERO_DIVISION_ERROR: 0.0 cannot be raised to a negative power")
    return _checked_pow(Float64(base), exp)

@always_inline
def _checked_index(idx: Int, n: Int) raises -> Int:
    if UInt(idx) < UInt(n):
        return idx
    if idx < 0 and idx >= -n:
        return idx + n
    raise Error("HOTLOOP_INDEX_ERROR: index out of range")

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
                    if step_val >= e_c - k:
                        break
                    k += step_val
            else:
                while k > e_c:
                    res.write(Codepoint(raw[k]))
                    if step_val <= e_c - k:
                        break
                    k += step_val
        else:
            res.reserve_bytes(n * 4)
            var k = s_c
            if step_val > 0:
                while k < e_c:
                    res.write(self._cps[k])
                    if step_val >= e_c - k:
                        break
                    k += step_val
            else:
                while k > e_c:
                    res.write(self._cps[k])
                    if step_val <= e_c - k:
                        break
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
    def startswith(self, prefix: String) -> Bool:
        return self._s.startswith(prefix)

    @always_inline
    def startswith(self, prefix: _PyStr) -> Bool:
        return self._s.startswith(prefix._s)

    @always_inline
    def startswith(self, prefix: String, start: Int) -> Bool:
        if self._is_ascii:
            return self._s.startswith(prefix, start)
        return self[start:].startswith(prefix)

    @always_inline
    def startswith(self, prefix: String, start: Int, end: Int) -> Bool:
        if self._is_ascii:
            return self._s.startswith(prefix, start, end)
        return self[start:end].startswith(prefix)

    @always_inline
    def endswith(self, suffix: String) -> Bool:
        return self._s.endswith(suffix)

    @always_inline
    def endswith(self, suffix: _PyStr) -> Bool:
        return self._s.endswith(suffix._s)

    @always_inline
    def endswith(self, suffix: String, start: Int) -> Bool:
        if self._is_ascii:
            return self._s.endswith(suffix, start)
        return self[start:].endswith(suffix)

    @always_inline
    def endswith(self, suffix: String, start: Int, end: Int) -> Bool:
        if self._is_ascii:
            return self._s.endswith(suffix, start, end)
        return self[start:end].endswith(suffix)

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

# Fixed C signatures: double op(double), double atan2(double, double).
# No borrowed storage, Python callback or GIL release crosses these calls.
from std.ffi import external_call, c_double
from std.memory import bitcast

# Overload resolution is the operand proof at every lowered call, including
# helper results and temporaries. Deliberately no String/PythonObject overload.
# Exact Python input types/ranges are checked before the native body.
@always_inline
def _math_operand(x: Float64) -> Float64:
    return x

@always_inline
def _math_operand(x: Int) -> Float64:
    return Float64(x)

@always_inline
def _math_operand(x: Bool) -> Float64:
    return Float64(Int(x))

@always_inline
def _checked_math_isnan(x: Float64) -> Bool:
    return math.isnan(x)

@always_inline
def _checked_math_isinf(x: Float64) -> Bool:
    return math.isinf(x)

@always_inline
def _checked_sqrt(x: Float64) raises -> Float64:
    if x < 0.0:
        raise Error("HOTLOOP_VALUE_ERROR: math domain error")
    return external_call["sqrt", c_double](c_double(x))

@always_inline
def _checked_math_sin(x: Float64) raises -> Float64:
    if math.isinf(x):
        raise Error("HOTLOOP_VALUE_ERROR: math domain error")
    return external_call["sin", c_double](c_double(x))

@always_inline
def _checked_math_cos(x: Float64) raises -> Float64:
    if math.isinf(x):
        raise Error("HOTLOOP_VALUE_ERROR: math domain error")
    return external_call["cos", c_double](c_double(x))

@always_inline
def _checked_math_log(x: Float64) raises -> Float64:
    if x <= 0.0:
        raise Error("HOTLOOP_VALUE_ERROR: math domain error")
    return external_call["log", c_double](c_double(x))

@always_inline
def _checked_math_exp(x: Float64) raises -> Float64:
    var result = external_call["exp", c_double](c_double(x))
    if math.isinf(result) and math.isfinite(x):
        raise Error("HOTLOOP_MATH_RANGE_ERROR: math range error")
    return result

@always_inline
def _checked_math_atan2(y: Float64, x: Float64) raises -> Float64:
    # CPython m_atan2 returns its canonical NaN, not either input payload.
    if math.isnan(y) or math.isnan(x):
        return bitcast[DType.float64](UInt64(0x7ff8000000000000))
    return external_call["atan2", c_double](c_double(y), c_double(x))

@always_inline
def _unqualified_math() raises -> Float64:
    # The entry and transitive callers are replaced by refusal stubs before
    # emission. Never produce a numeric sentinel or evaluate application args.
    raise Error("HOTLOOP_PYTHON_SEMANTICS: unqualified math operation")

@always_inline
def _py_chr(code: Int) raises -> String:
    if code >= 0xD800 and code <= 0xDFFF:
        raise Error("HOTLOOP_PYTHON_SEMANTICS: surrogate output requires Python")
    if code < 0 or code > 0x10FFFF:
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


# Python-only entries: 
@export
def PyInit_fast() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast")
        m.def_function[_pywrap_subject]("subject")
        m.def_function[_hotloop_context_spec_impl]("_hotloop_provenance_v1")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def _pywrap_subject(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "str")
    var x = String(py=_input0)
    var _res = _native_subject(x)
    return PythonObject(_res)

def _hotloop_context_spec_impl() raises -> PythonObject:
    return PythonObject(String('{"builtins":{"subject":[],"text":[]},"calls":{"subject":[],"text":[]},"canonical":[],"codes":{"subject":"385b6d0b6d7937259786958b1d4e6bc184a7527bf51c7cee50c5b0a345ee1016","text":"039124b1b3a77cacaea9e62eb2a3c42469d0d59f43d60d9630f85c2127bc8740"},"constants":[],"math":{"subject":["log"],"text":[]},"profile":"cpython-3.12.16-pylong30-linux-x86_64-gil","version":1}'))

def _native_text(x: String) raises -> String:
    return x.copy()

def _native_return_origin_text(x: String) raises -> Tuple[String, Int, Int]:
    return (x.copy(), 0, -1)

def _native_subject(x: String) raises -> Float64:
    return _checked_math_log(_math_operand(x))
