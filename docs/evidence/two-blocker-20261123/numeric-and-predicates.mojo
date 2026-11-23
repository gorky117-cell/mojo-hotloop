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
        m.def_function[_pywrap_sin_float]("sin_float")
        m.def_function[_pywrap_cos_float]("cos_float")
        m.def_function[_pywrap_sqrt_float]("sqrt_float")
        m.def_function[_pywrap_log_float]("log_float")
        m.def_function[_pywrap_exp_float]("exp_float")
        m.def_function[_pywrap_atan2_float]("atan2_float")
        m.def_function[_pywrap_isnan_float]("isnan_float")
        m.def_function[_pywrap_isinf_float]("isinf_float")
        m.def_function[_pywrap_sin_int]("sin_int")
        m.def_function[_pywrap_cos_int]("cos_int")
        m.def_function[_pywrap_sqrt_int]("sqrt_int")
        m.def_function[_pywrap_log_int]("log_int")
        m.def_function[_pywrap_exp_int]("exp_int")
        m.def_function[_pywrap_atan2_int]("atan2_int")
        m.def_function[_pywrap_isnan_int]("isnan_int")
        m.def_function[_pywrap_isinf_int]("isinf_int")
        m.def_function[_pywrap_sin_bool]("sin_bool")
        m.def_function[_pywrap_cos_bool]("cos_bool")
        m.def_function[_pywrap_sqrt_bool]("sqrt_bool")
        m.def_function[_pywrap_log_bool]("log_bool")
        m.def_function[_pywrap_exp_bool]("exp_bool")
        m.def_function[_pywrap_atan2_bool]("atan2_bool")
        m.def_function[_pywrap_isnan_bool]("isnan_bool")
        m.def_function[_pywrap_isinf_bool]("isinf_bool")
        m.def_function[_pywrap_helper_expression]("helper_expression")
        m.def_function[_pywrap_temporary_expression]("temporary_expression")
        m.def_function[_pywrap_predicates]("predicates")
        m.def_function[_pywrap_effects]("effects")
        m.def_function[_hotloop_context_spec_impl]("_hotloop_provenance_v1")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def _pywrap_sin_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_sin_float(x)
    return PythonObject(_res)

def _pywrap_cos_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_cos_float(x)
    return PythonObject(_res)

def _pywrap_sqrt_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_sqrt_float(x)
    return PythonObject(_res)

def _pywrap_log_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_log_float(x)
    return PythonObject(_res)

def _pywrap_exp_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_exp_float(x)
    return PythonObject(_res)

def _pywrap_atan2_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_atan2_float(x)
    return PythonObject(_res)

def _pywrap_isnan_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_isnan_float(x)
    return PythonObject(_res)

def _pywrap_isinf_float(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_isinf_float(x)
    return PythonObject(_res)

def _pywrap_sin_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_sin_int(x)
    return PythonObject(_res)

def _pywrap_cos_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_cos_int(x)
    return PythonObject(_res)

def _pywrap_sqrt_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_sqrt_int(x)
    return PythonObject(_res)

def _pywrap_log_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_log_int(x)
    return PythonObject(_res)

def _pywrap_exp_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_exp_int(x)
    return PythonObject(_res)

def _pywrap_atan2_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_atan2_int(x)
    return PythonObject(_res)

def _pywrap_isnan_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_isnan_int(x)
    return PythonObject(_res)

def _pywrap_isinf_int(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var x = Int(py=_input0)
    var _res = _native_isinf_int(x)
    return PythonObject(_res)

def _pywrap_sin_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_sin_bool(x)
    return PythonObject(_res)

def _pywrap_cos_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_cos_bool(x)
    return PythonObject(_res)

def _pywrap_sqrt_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_sqrt_bool(x)
    return PythonObject(_res)

def _pywrap_log_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_log_bool(x)
    return PythonObject(_res)

def _pywrap_exp_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_exp_bool(x)
    return PythonObject(_res)

def _pywrap_atan2_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_atan2_bool(x)
    return PythonObject(_res)

def _pywrap_isnan_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_isnan_bool(x)
    return PythonObject(_res)

def _pywrap_isinf_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "bool")
    var x = Bool(py=_input0)
    var _res = _native_isinf_bool(x)
    return PythonObject(_res)

def _pywrap_helper_expression(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_helper_expression(x)
    return PythonObject(_res)

def _pywrap_temporary_expression(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _res = _native_temporary_expression(x)
    return PythonObject(_res)

def _pywrap_predicates(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "float")
    var x = Float64(py=_input0)
    var _hotloop_origin_result = _native_return_origin_predicates(x)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == 0:
        return arg0
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_effects(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:

    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _hotloop_context_spec_impl() raises -> PythonObject:
    return PythonObject(String('{"builtins":{"atan2_bool":[],"atan2_float":[],"atan2_int":[],"cos_bool":[],"cos_float":[],"cos_int":[],"effect":[],"effects":[],"exp_bool":[],"exp_float":[],"exp_int":[],"helper_expression":[],"isinf_bool":[],"isinf_float":[],"isinf_int":[],"isnan_bool":[],"isnan_float":[],"isnan_int":[],"log_bool":[],"log_float":[],"log_int":[],"numeric_helper":[],"predicates":[],"sin_bool":[],"sin_float":[],"sin_int":[],"sqrt_bool":[],"sqrt_float":[],"sqrt_int":[],"temporary_expression":[]},"calls":{"atan2_bool":[],"atan2_float":[],"atan2_int":[],"cos_bool":[],"cos_float":[],"cos_int":[],"effect":[],"effects":["effect"],"exp_bool":[],"exp_float":[],"exp_int":[],"helper_expression":["numeric_helper"],"isinf_bool":[],"isinf_float":[],"isinf_int":[],"isnan_bool":[],"isnan_float":[],"isnan_int":[],"log_bool":[],"log_float":[],"log_int":[],"numeric_helper":[],"predicates":[],"sin_bool":[],"sin_float":[],"sin_int":[],"sqrt_bool":[],"sqrt_float":[],"sqrt_int":[],"temporary_expression":[]},"canonical":[7],"codes":{"atan2_bool":"dea23cae4adbadcf146840fd758b7fb0195822988102ecdd50588b8a6a7dc37b","atan2_float":"59a89b8a51e83d2a1fd4a3f26b663d3be93a3b9d17c7d4e3b2a92040a7b879c3","atan2_int":"c56ac47c3b50d5f62fed7a7ed04e41143c61624134a8c41de8e85ac0d777dc23","cos_bool":"478632752ff931d33de783fe87f0bdcc7826905c4354400b720fb2927a994f3f","cos_float":"801ae33610b5e4978bdaa8c31986d4945a2fcedcaff678027407bc70a1b6a62e","cos_int":"30c803dbf4f1c7ae91d514b53d48837d15ab14d2dbabd142178dada7abb34544","effect":"edec08db333ad93ac8a5c3bad5ff0665cf40161dd338ab7137ecb1cb51abeb51","effects":"9b953f27fb8d4ee237d8786552e5f85a837b6cc217ab47cbfa5a09158638ee05","exp_bool":"921623d089b8ad2803750d6c1d30dde2dc026d8bb1f4ee3e439af6178d81606a","exp_float":"d1cf6212e2aebbf344b5e4941e0ca7b60bb2fdc5b4255d49032c65e3e13b28ae","exp_int":"e234ae64f8d616a572f10c7febf1dca91d29a94cc0000fc11803b15ed2e73385","helper_expression":"34dfc1ae14c6479c6a23b4cb8c508496053ce438915ea6a317f6cbb62b2eb9ba","isinf_bool":"9b298275bdf892fdf29dd17b2fba100d8bb76c4495ecbd971888f5c777bafa80","isinf_float":"3a6a13e2995edbaef11ec94f79a936e092edc39ce596f14d6ceb59bfb495393b","isinf_int":"8f7e51f322b6d0670f3d22960933056d3328f9216c8901495b68cc5112f3ca01","isnan_bool":"a2d6463c0aad0a417d82891f1cc88f3f6334356a15f218a1c164674d73e47928","isnan_float":"b86d38d190031db943ca8730efb16c4fd169fae03aef01354382d2fb400dca78","isnan_int":"f6e514d2cd564e0b31bea8cb9eb1ea7fbd4895dae9b9a1e3407f568495a2ec89","log_bool":"54d1a13bf078b2fccab36da476906f0aa0956cb656d0f13a57562252ffcfaf95","log_float":"9a0f8add88d3616fefe02724229eeb58310984388150e17ede0c25805a30d2d1","log_int":"7e1511e610c3c5cd7d92e1328e27ed6be5b9e33fa54c59423778833adc3fbe57","numeric_helper":"3dda8d28b1717b8c35147f8a7276d4750bc1b1d7b1013626089b285fec4bfc95","predicates":"c9c6646f303318f3b2c91993bfb2b1e46a1a99e638b4cec18376946a30dfd248","sin_bool":"480c9742675d30200edf6b27b594d43789da531d75f236dd11e13830afe2d50a","sin_float":"7115ccc01b632f25413abab8de1d881932035362bc1b41b5693b3ef74a99fb16","sin_int":"4cc6496500c8fb74ddb5ae467b3e8012aa16a939f82d6432fdf800874401be3b","sqrt_bool":"b4ef168d82f162c727fbeb92a26acb533398fb5889ac2b9068df1a85f753ac68","sqrt_float":"0c60c94b66f04ab7f9718371b45214dab4fd4dc395a7dc7748ddff53db1a6e42","sqrt_int":"0ddbf4e39de7b4fd80efd698d3671d4c4eaac856658e84c54ad1e58afcae35b5","temporary_expression":"dfee399ae28618959c71feb92ea2d49340ed74c6f7b45314216614ccc6584b34"},"constants":[["numeric_helper",1],["effect",1],["temporary_expression",1],["predicates",1],["predicates",2],["predicates",3],["predicates",4],["predicates",5]],"math":{"atan2_bool":["atan2"],"atan2_float":["atan2"],"atan2_int":["atan2"],"cos_bool":["cos"],"cos_float":["cos"],"cos_int":["cos"],"effect":[],"effects":["log"],"exp_bool":["exp"],"exp_float":["exp"],"exp_int":["exp"],"helper_expression":["log"],"isinf_bool":["isinf"],"isinf_float":["isinf"],"isinf_int":["isinf"],"isnan_bool":["isnan"],"isnan_float":["isnan"],"isnan_int":["isnan"],"log_bool":["log"],"log_float":["log"],"log_int":["log"],"numeric_helper":[],"predicates":["isinf","isnan"],"sin_bool":["sin"],"sin_float":["sin"],"sin_int":["sin"],"sqrt_bool":["sqrt"],"sqrt_float":["sqrt"],"sqrt_int":["sqrt"],"temporary_expression":["log"]},"profile":"cpython-3.12.16-pylong30-linux-x86_64-gil","version":1}'))

def _native_numeric_helper(x: Float64) raises -> Float64:
    return _checked_add(x, 1.0)

def _native_effect(x: Float64) raises -> Float64:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _native_sin_float(x: Float64) raises -> Float64:
    return _checked_math_sin(_math_operand(x))

def _native_cos_float(x: Float64) raises -> Float64:
    return _checked_math_cos(_math_operand(x))

def _native_sqrt_float(x: Float64) raises -> Float64:
    return _checked_sqrt(_math_operand(x))

def _native_log_float(x: Float64) raises -> Float64:
    return _checked_math_log(_math_operand(x))

def _native_exp_float(x: Float64) raises -> Float64:
    return _checked_math_exp(_math_operand(x))

def _native_atan2_float(x: Float64) raises -> Float64:
    return _checked_math_atan2(_math_operand(x), _math_operand(x))

def _native_isnan_float(x: Float64) raises -> Bool:
    return _checked_math_isnan(_math_operand(x))

def _native_isinf_float(x: Float64) raises -> Bool:
    return _checked_math_isinf(_math_operand(x))

def _native_sin_int(x: Int) raises -> Float64:
    return _checked_math_sin(_math_operand(x))

def _native_cos_int(x: Int) raises -> Float64:
    return _checked_math_cos(_math_operand(x))

def _native_sqrt_int(x: Int) raises -> Float64:
    return _checked_sqrt(_math_operand(x))

def _native_log_int(x: Int) raises -> Float64:
    return _checked_math_log(_math_operand(x))

def _native_exp_int(x: Int) raises -> Float64:
    return _checked_math_exp(_math_operand(x))

def _native_atan2_int(x: Int) raises -> Float64:
    return _checked_math_atan2(_math_operand(x), _math_operand(x))

def _native_isnan_int(x: Int) raises -> Bool:
    return _checked_math_isnan(_math_operand(x))

def _native_isinf_int(x: Int) raises -> Bool:
    return _checked_math_isinf(_math_operand(x))

def _native_sin_bool(x: Bool) raises -> Float64:
    return _checked_math_sin(_math_operand(x))

def _native_cos_bool(x: Bool) raises -> Float64:
    return _checked_math_cos(_math_operand(x))

def _native_sqrt_bool(x: Bool) raises -> Float64:
    return _checked_sqrt(_math_operand(x))

def _native_log_bool(x: Bool) raises -> Float64:
    return _checked_math_log(_math_operand(x))

def _native_exp_bool(x: Bool) raises -> Float64:
    return _checked_math_exp(_math_operand(x))

def _native_atan2_bool(x: Bool) raises -> Float64:
    return _checked_math_atan2(_math_operand(x), _math_operand(x))

def _native_isnan_bool(x: Bool) raises -> Bool:
    return _checked_math_isnan(_math_operand(x))

def _native_isinf_bool(x: Bool) raises -> Bool:
    return _checked_math_isinf(_math_operand(x))

def _native_helper_expression(x: Float64) raises -> Float64:
    return _checked_math_log(_math_operand(_native_numeric_helper(x)))

def _native_temporary_expression(x: Float64) raises -> Float64:
    var y = _checked_add(x, 1.0)
    return _checked_math_log(_math_operand(y))

def _native_predicates(x: Float64) raises -> Int:
    if _py_bool(_checked_math_isnan(_math_operand(x))):
        return -999
    if _py_bool(_checked_math_isinf(_math_operand(x))):
        if (x > 0.0):
            return 999
        return -888
    return 0

def _native_return_origin_predicates(x: Float64) raises -> Tuple[Int, Int, Int]:
    if _py_bool(_checked_math_isnan(_math_operand(x))):
        return (-999, -2, 3)
    if _py_bool(_checked_math_isinf(_math_operand(x))):
        if (x > 0.0):
            return (999, -2, 5)
        return (-888, -2, 6)
    return (0, -2, 7)

def _native_effects(x: Float64) raises -> Float64:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")
