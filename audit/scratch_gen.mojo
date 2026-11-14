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
        self._cps = List[Codepoint](capacity=len(s.codepoints()))
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
    def get_cp(self, idx: Int) -> Codepoint:
        var i = idx
        if i < 0:
            i += len(self._cps)
        return self._cps[i]

    @always_inline
    def get_ord(self, idx: Int) -> Int:
        var i = idx
        if i < 0:
            i += len(self._cps)
        return Int(self._cps[i])

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
        res.reserve_bytes(max(0, e_c - s_c) * 4)
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
def PyInit_scratch_gen() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("scratch_gen")
        m.def_function[trapezoidal_integration]("trapezoidal_integration")
        m.def_function[chebyshev_path_distance]("chebyshev_path_distance")
        m.def_function[exponential_moving_average]("exponential_moving_average")
        m.def_function[mask_digits]("mask_digits")
        m.def_function[hamming_distance]("hamming_distance")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def trapezoidal_integration(arg0: PythonObject, arg1: PythonObject, arg2: PythonObject) raises -> PythonObject:
    var a = Float64(py=arg0)
    var b = Float64(py=arg1)
    var n_steps = Int(py=arg2)
    var _res = _native_trapezoidal_integration(a, b, n_steps)
    return PythonObject(_res)

def chebyshev_path_distance(arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _builtins = Python.import_module("builtins")
    var _has_ctypes = Bool(py=_builtins.hasattr(arg0, "ctypes")) and Bool(py=_builtins.hasattr(arg1, "ctypes"))
    if _has_ctypes:
        var _n_xs = Int(py=arg0.__len__())
        var _n_ys = Int(py=arg1.__len__())
        var _xs_addr = Int(py=arg0.ctypes.data)
        var _ys_addr = Int(py=arg1.ctypes.data)
        var _xs_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_xs_addr)
        var _ys_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_ys_addr)
        var _res = _ptr_chebyshev_path_distance(_xs_op, _n_xs, _ys_op, _n_ys)
        return PythonObject(_res)
    else:
        var xs = List[Float64]()
        var _n_xs = Int(py=arg0.__len__())
        for _i in range(_n_xs):
            xs.append(Float64(py=arg0[_i]))
        var ys = List[Float64]()
        var _n_ys = Int(py=arg1.__len__())
        for _i in range(_n_ys):
            ys.append(Float64(py=arg1[_i]))
        var _res = _native_chebyshev_path_distance(xs, ys)
        return PythonObject(_res)

def exponential_moving_average(arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var _builtins = Python.import_module("builtins")
    var _has_ctypes = Bool(py=_builtins.hasattr(arg0, "ctypes"))
    if _has_ctypes:
        var _n_values = Int(py=arg0.__len__())
        var _values_addr = Int(py=arg0.ctypes.data)
        var _values_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_values_addr)
        var _res = _ptr_exponential_moving_average(_values_op, _n_values, Float64(py=arg1))
        return PythonObject(_res)
    else:
        var values = List[Float64]()
        var _n_values = Int(py=arg0.__len__())
        for _i in range(_n_values):
            values.append(Float64(py=arg0[_i]))
        var alpha = Float64(py=arg1)
        var _res = _native_exponential_moving_average(values, alpha)
        return PythonObject(_res)

def mask_digits(arg0: PythonObject) raises -> PythonObject:
    var text = String(py=arg0)
    var _res = _native_mask_digits(text)
    return PythonObject(_res)

def hamming_distance(arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var s1 = String(py=arg0)
    var s2 = String(py=arg1)
    var _res = _native_hamming_distance(s1, s2)
    return PythonObject(_res)

def _native_trapezoidal_integration(a: Float64, b: Float64, n_steps: Int) raises -> Float64:
    if (n_steps <= 0):
        return 0.0
    var h = _checked_div(_checked_sub(b, a), Float64(n_steps))
    var inv_sqrt_2pi = 0.3989422804014327
    var total = _checked_mul(0.5, _checked_add(math.exp(_checked_mul(_checked_mul(_checked_neg(a), a), 0.5)), math.exp(_checked_mul(_checked_mul(_checked_neg(b), b), 0.5))))
    var x = a
    for _ in range(1, n_steps):
        x = _checked_add(x, h)
        total = _checked_add(total, math.exp(_checked_mul(_checked_mul(_checked_neg(x), x), 0.5)))
    return _checked_mul(_checked_mul(total, h), inv_sqrt_2pi)

@always_inline
def _ptr_chebyshev_path_distance(xs_ptr: OpaquePointer[MutUntrackedOrigin], _n_xs: Int, ys_ptr: OpaquePointer[MutUntrackedOrigin], _n_ys: Int) raises -> Float64:
    var xs = xs_ptr.unsafe_bitcast[Float64]()
    var ys = ys_ptr.unsafe_bitcast[Float64]()
    var n = _n_xs
    if (n <= 1):
        return 0.0
    var total = 0.0
    for i in range(1, n):
        var dx = abs(_checked_sub(xs[i], xs[_checked_sub(i, 1)]))
        var dy = abs(_checked_sub(ys[i], ys[_checked_sub(i, 1)]))
        if (dx > dy):
            total = _checked_add(total, dx)
        else:
            total = _checked_add(total, dy)
    return total

def _native_chebyshev_path_distance(xs: List[Float64], ys: List[Float64]) raises -> Float64:
    var n = _len(xs)
    if (n <= 1):
        return 0.0
    var total = 0.0
    for i in range(1, n):
        var dx = abs(_checked_sub(xs[i], xs[_checked_sub(i, 1)]))
        var dy = abs(_checked_sub(ys[i], ys[_checked_sub(i, 1)]))
        if (dx > dy):
            total = _checked_add(total, dx)
        else:
            total = _checked_add(total, dy)
    return total

@always_inline
def _ptr_exponential_moving_average(values_ptr: OpaquePointer[MutUntrackedOrigin], _n_values: Int, alpha: Float64) raises -> Float64:
    var values = values_ptr.unsafe_bitcast[Float64]()
    var n = _n_values
    if (n == 0):
        return 0.0
    var ema = values[0]
    var one_minus_alpha = _checked_sub(1.0, alpha)
    for i in range(1, n):
        ema = _checked_add(_checked_mul(alpha, values[i]), _checked_mul(one_minus_alpha, ema))
    return ema

def _native_exponential_moving_average(values: List[Float64], alpha: Float64) raises -> Float64:
    var n = _len(values)
    if (n == 0):
        return 0.0
    var ema = values[0]
    var one_minus_alpha = _checked_sub(1.0, alpha)
    for i in range(1, n):
        ema = _checked_add(_checked_mul(alpha, values[i]), _checked_mul(one_minus_alpha, ema))
    return ema

def _native_mask_digits(_arg_text: String) raises -> String:
    var text: _PyStr = _PyStr(_arg_text)
    var n = _len(text)
    var res = ''
    for i in range(n):
        if ((text.get_ord(i) >= 48) and (text.get_ord(i) <= 57)):
            res = _checked_add(res, '*')
        else:
            res = _checked_add(res, text[i])
    return res^

def _native_hamming_distance(_arg_s1: String, _arg_s2: String) raises -> Int:
    var s1: _PyStr = _PyStr(_arg_s1)
    var s2: _PyStr = _PyStr(_arg_s2)
    var n1 = _len(s1)
    var n2 = _len(s2)
    var min_len = min(n1, n2)
    var dist = abs(_checked_sub(n1, n2))
    for i in range(min_len):
        if (s1[i] != s2[i]):
            dist = _checked_add(dist, 1)
    return dist
