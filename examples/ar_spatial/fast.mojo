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
def PyInit_fast() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("fast")
        m.def_function[find_closest_point_to_ray]("find_closest_point_to_ray")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def find_closest_point_to_ray(arg0: PythonObject, arg1: PythonObject, arg2: PythonObject, arg3: PythonObject, arg4: PythonObject, arg5: PythonObject, arg6: PythonObject, arg7: PythonObject, arg8: PythonObject) raises -> PythonObject:
    var _builtins = Python.import_module("builtins")
    var _has_ctypes = Bool(py=_builtins.hasattr(arg0, "ctypes")) and Bool(py=_builtins.hasattr(arg1, "ctypes")) and Bool(py=_builtins.hasattr(arg2, "ctypes"))
    if _has_ctypes:
        var _n_xs = Int(py=arg0.__len__())
        var _n_ys = Int(py=arg1.__len__())
        var _n_zs = Int(py=arg2.__len__())
        var _xs_addr = Int(py=arg0.ctypes.data)
        var _ys_addr = Int(py=arg1.ctypes.data)
        var _zs_addr = Int(py=arg2.ctypes.data)
        var _xs_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_xs_addr)
        var _ys_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_ys_addr)
        var _zs_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_zs_addr)
        var _res = _ptr_find_closest_point_to_ray(_xs_op, _n_xs, _ys_op, _n_ys, _zs_op, _n_zs, Float64(py=arg3), Float64(py=arg4), Float64(py=arg5), Float64(py=arg6), Float64(py=arg7), Float64(py=arg8))
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
        var zs = List[Float64]()
        var _n_zs = Int(py=arg2.__len__())
        for _i in range(_n_zs):
            zs.append(Float64(py=arg2[_i]))
        var ray_ox = Float64(py=arg3)
        var ray_oy = Float64(py=arg4)
        var ray_oz = Float64(py=arg5)
        var ray_dx = Float64(py=arg6)
        var ray_dy = Float64(py=arg7)
        var ray_dz = Float64(py=arg8)
        var _res = _native_find_closest_point_to_ray(xs, ys, zs, ray_ox, ray_oy, ray_oz, ray_dx, ray_dy, ray_dz)
        return PythonObject(_res)

@always_inline
def _ptr_find_closest_point_to_ray(xs_ptr: OpaquePointer[MutUntrackedOrigin], _n_xs: Int, ys_ptr: OpaquePointer[MutUntrackedOrigin], _n_ys: Int, zs_ptr: OpaquePointer[MutUntrackedOrigin], _n_zs: Int, ray_ox: Float64, ray_oy: Float64, ray_oz: Float64, ray_dx: Float64, ray_dy: Float64, ray_dz: Float64) raises -> Int:
    var xs = xs_ptr.unsafe_bitcast[Float64]()
    var ys = ys_ptr.unsafe_bitcast[Float64]()
    var zs = zs_ptr.unsafe_bitcast[Float64]()
    var n: Int = _n_xs
    if ((n == 0) or (_n_ys != n) or (_n_zs != n)):
        return _checked_neg(1)
    var dir_len_sq: Float64 = _checked_add(_checked_add(_checked_mul(ray_dx, ray_dx), _checked_mul(ray_dy, ray_dy)), _checked_mul(ray_dz, ray_dz))
    if (dir_len_sq <= 0.0):
        return _checked_neg(1)
    var inv_len: Float64 = _checked_div(1.0, math.sqrt(dir_len_sq))
    var dx: Float64 = _checked_mul(ray_dx, inv_len)
    var dy: Float64 = _checked_mul(ray_dy, inv_len)
    var dz: Float64 = _checked_mul(ray_dz, inv_len)
    var best_idx: Int = _checked_neg(1)
    var min_dist_sq: Float64 = 1e+30
    for i in range(n):
        var vx: Float64 = _checked_sub(xs[i], ray_ox)
        var vy: Float64 = _checked_sub(ys[i], ray_oy)
        var vz: Float64 = _checked_sub(zs[i], ray_oz)
        var t: Float64 = _checked_add(_checked_add(_checked_mul(vx, dx), _checked_mul(vy, dy)), _checked_mul(vz, dz))
        if (t < 0.0):
            t = 0.0
        var wx: Float64 = _checked_sub(vx, _checked_mul(t, dx))
        var wy: Float64 = _checked_sub(vy, _checked_mul(t, dy))
        var wz: Float64 = _checked_sub(vz, _checked_mul(t, dz))
        var dist_sq: Float64 = _checked_add(_checked_add(_checked_mul(wx, wx), _checked_mul(wy, wy)), _checked_mul(wz, wz))
        if (dist_sq < min_dist_sq):
            min_dist_sq = dist_sq
            best_idx = i
    return best_idx

def _native_find_closest_point_to_ray(xs: List[Float64], ys: List[Float64], zs: List[Float64], ray_ox: Float64, ray_oy: Float64, ray_oz: Float64, ray_dx: Float64, ray_dy: Float64, ray_dz: Float64) raises -> Int:
    var n: Int = _len(xs)
    if ((n == 0) or (_len(ys) != n) or (_len(zs) != n)):
        return _checked_neg(1)
    var dir_len_sq: Float64 = _checked_add(_checked_add(_checked_mul(ray_dx, ray_dx), _checked_mul(ray_dy, ray_dy)), _checked_mul(ray_dz, ray_dz))
    if (dir_len_sq <= 0.0):
        return _checked_neg(1)
    var inv_len: Float64 = _checked_div(1.0, math.sqrt(dir_len_sq))
    var dx: Float64 = _checked_mul(ray_dx, inv_len)
    var dy: Float64 = _checked_mul(ray_dy, inv_len)
    var dz: Float64 = _checked_mul(ray_dz, inv_len)
    var best_idx: Int = _checked_neg(1)
    var min_dist_sq: Float64 = 1e+30
    for i in range(n):
        var vx: Float64 = _checked_sub(xs[i], ray_ox)
        var vy: Float64 = _checked_sub(ys[i], ray_oy)
        var vz: Float64 = _checked_sub(zs[i], ray_oz)
        var t: Float64 = _checked_add(_checked_add(_checked_mul(vx, dx), _checked_mul(vy, dy)), _checked_mul(vz, dz))
        if (t < 0.0):
            t = 0.0
        var wx: Float64 = _checked_sub(vx, _checked_mul(t, dx))
        var wy: Float64 = _checked_sub(vy, _checked_mul(t, dy))
        var wz: Float64 = _checked_sub(vz, _checked_mul(t, dz))
        var dist_sq: Float64 = _checked_add(_checked_add(_checked_mul(wx, wx), _checked_mul(wy, wy)), _checked_mul(wz, wz))
        if (dist_sq < min_dist_sq):
            min_dist_sq = dist_sq
            best_idx = i
    return best_idx
