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
        m.def_function[_pywrap_get_int]("get_int")
        m.def_function[_pywrap_get_float]("get_float")
        m.def_function[_pywrap_get_bool]("get_bool")
        m.def_function[_pywrap_get_str]("get_str")
        m.def_function[_pywrap_compute]("compute")
        m.def_function[_pywrap_local_read]("local_read")
        m.def_function[_pywrap_literal_read]("literal_read")
        m.def_function[_pywrap_helper_list]("helper_list")
        m.def_function[_pywrap_nested_index]("nested_index")
        m.def_function[_pywrap_read_before_div]("read_before_div")
        m.def_function[_pywrap_div_before_read]("div_before_read")
        m.def_function[_pywrap_local_store]("local_store")
        m.def_function[_pywrap_local_aug]("local_aug")
        m.def_function[_pywrap_store_rhs_first]("store_rhs_first")
        m.def_function[_pywrap_aug_read_first]("aug_read_first")
        m.def_function[_pywrap_effect_read]("effect_read")
        m.def_function[_pywrap_effect_store]("effect_store")
        m.def_function[_hotloop_context_spec_impl]("_hotloop_provenance_v1")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def _pywrap_get_int(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[int]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[Int](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(Int(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _hotloop_origin_result = _native_return_origin_get_int(xs, i)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == 0:
        if _hotloop_origin_result[2] >= 0:
            return _input0[_hotloop_origin_result[2]]
        return arg0
    if _hotloop_origin_result[1] == 1:
        return arg1
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_get_float(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[float]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[Float64](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(Float64(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _hotloop_origin_result = _native_return_origin_get_float(xs, i)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == 0:
        if _hotloop_origin_result[2] >= 0:
            return _input0[_hotloop_origin_result[2]]
        return arg0
    if _hotloop_origin_result[1] == 1:
        return arg1
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_get_bool(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[bool]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[Bool](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(Bool(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _hotloop_origin_result = _native_return_origin_get_bool(xs, i)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == 0:
        if _hotloop_origin_result[2] >= 0:
            return _input0[_hotloop_origin_result[2]]
        return arg0
    if _hotloop_origin_result[1] == 1:
        return arg1
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_get_str(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[str]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[String](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(String(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _hotloop_origin_result = _native_return_origin_get_str(xs, i)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == -3:
        var _owners = Python.import_module("hotloop._provenance")
        return _owners.fresh_string(PythonObject(_hotloop_origin_result[0]))
    if _hotloop_origin_result[1] == 0:
        if _hotloop_origin_result[2] >= 0:
            return _input0[_hotloop_origin_result[2]]
        return arg0
    if _hotloop_origin_result[1] == 1:
        return arg1
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_compute(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[int]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[Int](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(Int(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _res = _native_compute(xs, i)
    return PythonObject(_res)

def _pywrap_local_read(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var i = Int(py=_input0)
    var _res = _native_local_read(i)
    return PythonObject(_res)

def _pywrap_literal_read(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var i = Int(py=_input0)
    var _res = _native_literal_read(i)
    return PythonObject(_res)

def _pywrap_helper_list(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:

    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _pywrap_nested_index(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[int]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[Int](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(Int(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _hotloop_origin_result = _native_return_origin_nested_index(xs, i)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == 0:
        if _hotloop_origin_result[2] >= 0:
            return _input0[_hotloop_origin_result[2]]
        return arg0
    if _hotloop_origin_result[1] == 1:
        return arg1
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_read_before_div(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject, arg2: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[int]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[Int](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(Int(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _input2 = _guard.checked_argument(arg2, "int")
    var divisor = Int(py=_input2)
    var _res = _native_read_before_div(xs, i, divisor)
    return PythonObject(_res)

def _pywrap_div_before_read(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject, arg2: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "list[int]")
    var _n_xs = Int(py=_input0.__len__())
    var xs = List[Int](capacity=_n_xs)
    for _i in range(_n_xs):
        xs.append(Int(py=_input0[_i]))
    var _input1 = _guard.checked_argument(arg1, "int")
    var i = Int(py=_input1)
    var _input2 = _guard.checked_argument(arg2, "int")
    var divisor = Int(py=_input2)
    var _res = _native_div_before_read(xs, i, divisor)
    return PythonObject(_res)

def _pywrap_local_store(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var i = Int(py=_input0)
    var _input1 = _guard.checked_argument(arg1, "int")
    var value = Int(py=_input1)
    var _res = _native_local_store(i, value)
    return PythonObject(_res)

def _pywrap_local_aug(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var i = Int(py=_input0)
    var _input1 = _guard.checked_argument(arg1, "int")
    var value = Int(py=_input1)
    var _res = _native_local_aug(i, value)
    return PythonObject(_res)

def _pywrap_store_rhs_first(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var i = Int(py=_input0)
    var _input1 = _guard.checked_argument(arg1, "int")
    var divisor = Int(py=_input1)
    var _hotloop_origin_result = _native_return_origin_store_rhs_first(i, divisor)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == 0:
        return arg0
    if _hotloop_origin_result[1] == 1:
        return arg1
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_aug_read_first(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _guard = Python.import_module("hotloop._arguments")
    var _input0 = _guard.checked_argument(arg0, "int")
    var i = Int(py=_input0)
    var _input1 = _guard.checked_argument(arg1, "int")
    var divisor = Int(py=_input1)
    var _hotloop_origin_result = _native_return_origin_aug_read_first(i, divisor)
    if _hotloop_origin_result[1] == -2:
        return _hotloop_origin_context[_hotloop_origin_result[2]]
    if _hotloop_origin_result[1] == 0:
        return arg0
    if _hotloop_origin_result[1] == 1:
        return arg1
    var _res = _hotloop_origin_result[0]
    return PythonObject(_res)

def _pywrap_effect_read(_hotloop_origin_context: PythonObject, arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:

    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _pywrap_effect_store(_hotloop_origin_context: PythonObject, arg0: PythonObject) raises -> PythonObject:

    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _hotloop_context_spec_impl() raises -> PythonObject:
    return PythonObject(String('{"builtins":{"aug_read_first":[],"compute":[],"div_before_read":[],"effect_index":[],"effect_read":[],"effect_store":[],"effect_value":[],"get_bool":[],"get_float":[],"get_int":[],"get_str":[],"helper_list":[],"index_value":[],"literal_read":[],"local_aug":[],"local_read":[],"local_store":[],"make_values":[],"nested_index":[],"read_before_div":[],"shift":[],"store_rhs_first":[]},"calls":{"aug_read_first":[],"compute":[],"div_before_read":[],"effect_index":[],"effect_read":["effect_index"],"effect_store":["effect_index","effect_value"],"effect_value":[],"get_bool":[],"get_float":[],"get_int":[],"get_str":[],"helper_list":["make_values"],"index_value":["shift"],"literal_read":[],"local_aug":[],"local_read":[],"local_store":[],"make_values":[],"nested_index":["index_value"],"read_before_div":[],"shift":[],"store_rhs_first":[]},"canonical":[0,1,2,3,6,9,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35],"codes":{"aug_read_first":"da6444bf59b55aaf035fccc8591dfaf30333a0c30aca1f13dcb924e9e71030ce","compute":"8f0d95ac8743d3cd958e746ac093d1e99e9de71f5c07a042fa083eb9597032fa","div_before_read":"c0a499a4d935be3c1b8d86dca433ac214a4e8e88b911e5969c552a1417af5f23","effect_index":"8c2a61bfc5d36286f66114c3c4ad155fe8b30e74a980c9a61d5e4bc194910fa0","effect_read":"5f2fa1a9c2e49fe48b3fc09098ea84b7ec15ca73d03c5a56c88d95755d670ef3","effect_store":"e2aedcadaec78174b7224d569be83dd73e1717b0268c61570e06372756580ea4","effect_value":"ad7d77c16adc7a8d52420c20253483d0e6a515b8750d8fdc4eab4a98d9b4b199","get_bool":"1bfc6ac10d29e296ad20b81071030d2ade4c658afc70bb420ff12ed96fffdc41","get_float":"88ea43d7fa8d9364f724f544c5f61bdb77df95a07160fedd97fb17238683d09b","get_int":"c5d58dc206d330c8851100c19557dcb11c272d23b61b4a36819d191f875c51b0","get_str":"42078a03911fbfe9c730e4ec21983998b0bf43575439cd4ba48709d231fc7829","helper_list":"5b35bbbfc1c63b7c1681e2da022875d162cf17d456cc66bc61f26458695fc0ca","index_value":"d2c353dd893bb9b57f4cc9e9a594b2b2bdcb53bc39e736a06cbac5bd3a26770c","literal_read":"0eb22151728bf098db8f405d37aaefdd50a336093da6c789a2495b5d5f1cf307","local_aug":"627b3bf34b15f7bd6154b28bb4ce2541eeb7f45144dc1b5c47e07f835b973321","local_read":"4ea6ebf31b62a162a44089ed8d820120cafd73f618df4af1decb06bc0247069b","local_store":"5e0987c5de870232f887d527f666832cddb208d147141ae0890f8c83e9160054","make_values":"9651e335ac8c5c81b5633a7f50e86a81f1952f4b040fb704c241909b29c1c4fa","nested_index":"6afbcb88cbd8a91a858cb8dd440d56c4dd13b74d9c0a73024d08ca3d37ed51d1","read_before_div":"c2685a69a0ab8b96ef356a24c2651968402b4cc0a90ae4f20243eb98d76f3aa1","shift":"577007abb85608ff84fbc07a92a7a1d400f653cdae893cb5f7d63a171e6157e4","store_rhs_first":"933557d0e879820d26a1d3a5e7c4584f3c29d9a631aae10a620063acc108806e"},"constants":[["make_values",1],["make_values",2],["shift",1],["index_value",1],["effect_index",1],["effect_value",1],["compute",1],["local_read",1],["local_read",2],["local_read",3],["literal_read",1],["literal_read",2],["literal_read",3],["helper_list",1],["read_before_div",1],["div_before_read",1],["local_store",1],["local_store",2],["local_store",3],["local_store",1],["local_aug",1],["local_aug",2],["local_aug",3],["local_aug",1],["store_rhs_first",1],["store_rhs_first",2],["store_rhs_first",3],["store_rhs_first",4],["aug_read_first",1],["aug_read_first",2],["aug_read_first",3],["aug_read_first",4],["effect_store",1],["effect_store",2],["effect_store",3],["effect_store",4]],"math":{"aug_read_first":[],"compute":[],"div_before_read":[],"effect_index":[],"effect_read":[],"effect_store":[],"effect_value":[],"get_bool":[],"get_float":[],"get_int":[],"get_str":[],"helper_list":[],"index_value":[],"literal_read":[],"local_aug":[],"local_read":[],"local_store":[],"make_values":[],"nested_index":[],"read_before_div":[],"shift":[],"store_rhs_first":[]},"profile":"cpython-3.12.16-pylong30-linux-x86_64-gil","version":1}'))

def _native_make_values() raises -> List[Int]:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _native_shift(i: Int) raises -> Int:
    return _checked_add(i, 1)

def _native_index_value(i: Int) raises -> Int:
    return _checked_sub(_native_shift(i), 1)

def _native_effect_index(i: Int) raises -> Int:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _native_effect_value(value: Int) raises -> Int:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _native_get_int(xs: List[Int], i: Int) raises -> Int:
    return xs[_checked_index(i, len(xs))]

def _native_return_origin_get_int(xs: List[Int], i: Int) raises -> Tuple[Int, Int, Int]:
    var _hotloop_origin_index_1 = _checked_index(i, len(xs))
    var _hotloop_origin_index_2 = xs[_hotloop_origin_index_1]
    return (_hotloop_origin_index_2, 0, _hotloop_origin_index_1)

def _native_get_float(xs: List[Float64], i: Int) raises -> Float64:
    return xs[_checked_index(i, len(xs))]

def _native_return_origin_get_float(xs: List[Float64], i: Int) raises -> Tuple[Float64, Int, Int]:
    var _hotloop_origin_index_1 = _checked_index(i, len(xs))
    var _hotloop_origin_index_2 = xs[_hotloop_origin_index_1]
    return (_hotloop_origin_index_2, 0, _hotloop_origin_index_1)

def _native_get_bool(xs: List[Bool], i: Int) raises -> Bool:
    return xs[_checked_index(i, len(xs))]

def _native_return_origin_get_bool(xs: List[Bool], i: Int) raises -> Tuple[Bool, Int, Int]:
    var _hotloop_origin_index_1 = _checked_index(i, len(xs))
    var _hotloop_origin_index_2 = xs[_hotloop_origin_index_1]
    return (_hotloop_origin_index_2, 0, _hotloop_origin_index_1)

def _native_get_str(xs: List[String], i: Int) raises -> String:
    return xs[_checked_index(i, len(xs))]

def _native_return_origin_get_str(xs: List[String], i: Int) raises -> Tuple[String, Int, Int]:
    var _hotloop_origin_index_1 = _checked_index(i, len(xs))
    var _hotloop_origin_index_2 = xs[_hotloop_origin_index_1]
    return (_hotloop_origin_index_2^, 0, _hotloop_origin_index_1)

def _native_compute(xs: List[Int], i: Int) raises -> Int:
    return _checked_add(xs[_checked_index(i, len(xs))], 1)

def _native_local_read(i: Int) raises -> Int:
    var xs: List[Int] = [1000, 2000]
    return _checked_add(xs[_checked_index(i, len(xs))], 1)

def _native_literal_read(i: Int) raises -> Int:
    return _checked_add([1000, 2000][_checked_index(i, len([1000, 2000]))], 1)

def _native_helper_list(i: Int) raises -> Int:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _native_nested_index(xs: List[Int], i: Int) raises -> Int:
    return xs[_checked_index(_native_index_value(i), len(xs))]

def _native_return_origin_nested_index(xs: List[Int], i: Int) raises -> Tuple[Int, Int, Int]:
    var _hotloop_origin_index_1 = _checked_index(_native_index_value(i), len(xs))
    var _hotloop_origin_index_2 = xs[_hotloop_origin_index_1]
    return (_hotloop_origin_index_2, 0, _hotloop_origin_index_1)

def _native_read_before_div(xs: List[Int], i: Int, divisor: Int) raises -> Int:
    return _checked_add(xs[_checked_index(i, len(xs))], _checked_floordiv(4, divisor))

def _native_div_before_read(xs: List[Int], i: Int, divisor: Int) raises -> Int:
    return _checked_add(_checked_floordiv(4, divisor), xs[_checked_index(i, len(xs))])

def _native_local_store(i: Int, value: Int) raises -> Int:
    var xs: List[Int] = [1, 2]
    xs[_checked_index(i, len(xs))] = value
    return _checked_add(xs[_checked_index(0, len(xs))], xs[_checked_index(1, len(xs))])

def _native_local_aug(i: Int, value: Int) raises -> Int:
    var xs: List[Int] = [1, 2]
    var _hot_idx_1 = _checked_index(i, len(xs))
    xs[_hot_idx_1] = _checked_add(xs[_hot_idx_1], value)
    return _checked_add(xs[_checked_index(0, len(xs))], xs[_checked_index(1, len(xs))])

def _native_store_rhs_first(i: Int, divisor: Int) raises -> Int:
    var xs: List[Int] = [1, 2]
    xs[_checked_index(i, len(xs))] = _checked_floordiv(4, divisor)
    return 0

def _native_return_origin_store_rhs_first(i: Int, divisor: Int) raises -> Tuple[Int, Int, Int]:
    var xs: List[Int] = [1, 2]
    xs[_checked_index(i, len(xs))] = _checked_floordiv(4, divisor)
    return (0, -2, 27)

def _native_aug_read_first(i: Int, divisor: Int) raises -> Int:
    var xs: List[Int] = [1, 2]
    var _hot_idx_1 = _checked_index(i, len(xs))
    xs[_hot_idx_1] = _checked_add(xs[_hot_idx_1], _checked_floordiv(4, divisor))
    return 0

def _native_return_origin_aug_read_first(i: Int, divisor: Int) raises -> Tuple[Int, Int, Int]:
    var xs: List[Int] = [1, 2]
    var _hot_idx_1 = _checked_index(i, len(xs))
    xs[_hot_idx_1] = _checked_add(xs[_hot_idx_1], _checked_floordiv(4, divisor))
    return (0, -2, 31)

def _native_effect_read(xs: List[Int], i: Int) raises -> Int:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")

def _native_effect_store(i: Int) raises -> Int:
    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")
