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


@export
def PyInit_fast() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast")
        m.def_function[simple_moving_average]("simple_moving_average")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def simple_moving_average(arg0: PythonObject, arg1: PythonObject) raises -> PythonObject:
    var values = List[Float64]()
    var _n_values = Int(py=arg0.__len__())
    for _i in range(_n_values):
        values.append(Float64(py=arg0[_i]))
    var window = Int(py=arg1)
    var _res = _native_simple_moving_average(values, window)
    var _builtins = Python.import_module("builtins")
    var _py_res = _builtins.list()
    for _i in range(len(_res)):
        _py_res.append(_res[_i])
    return _py_res

def _native_simple_moving_average(values: List[Float64], window: Int) raises -> List[Float64]:
    if ((len(values) < window) or (window <= 0)):
        return List[Float64]()
    var result: List[Float64] = List[Float64]()
    var window_sum: Float64 = 0.0
    for i in range(window):
        window_sum = _checked_add(window_sum, values[i])
    result.append(_checked_div(window_sum, window))
    for i in range(window, len(values)):
        window_sum = _checked_add(window_sum, _checked_sub(values[i], values[_checked_sub(i, window)]))
        result.append(_checked_div(window_sum, window))
    return result^
