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
        m.def_function[_pywrap_find_closest_point_to_ray]("find_closest_point_to_ray")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def _pywrap_find_closest_point_to_ray(arg0: PythonObject, arg1: PythonObject, arg2: PythonObject, arg3: PythonObject, arg4: PythonObject, arg5: PythonObject, arg6: PythonObject, arg7: PythonObject, arg8: PythonObject) raises -> PythonObject:
    var _builtins = Python.import_module("builtins")
    var _has_ctypes = True
    if _has_ctypes:
        if not (Bool(py=_builtins.hasattr(arg0, "ctypes")) and Bool(py=_builtins.hasattr(arg0, "ndim")) and Bool(py=_builtins.hasattr(arg0, "dtype")) and Bool(py=_builtins.hasattr(arg0, "flags"))):
            _has_ctypes = False
        elif Int(py=arg0.ndim) != 1 or String(py=arg0.dtype.name) != "float64" or not Bool(py=arg0.flags.c_contiguous):
            _has_ctypes = False
    if _has_ctypes:
        if not (Bool(py=_builtins.hasattr(arg1, "ctypes")) and Bool(py=_builtins.hasattr(arg1, "ndim")) and Bool(py=_builtins.hasattr(arg1, "dtype")) and Bool(py=_builtins.hasattr(arg1, "flags"))):
            _has_ctypes = False
        elif Int(py=arg1.ndim) != 1 or String(py=arg1.dtype.name) != "float64" or not Bool(py=arg1.flags.c_contiguous):
            _has_ctypes = False
    if _has_ctypes:
        if not (Bool(py=_builtins.hasattr(arg2, "ctypes")) and Bool(py=_builtins.hasattr(arg2, "ndim")) and Bool(py=_builtins.hasattr(arg2, "dtype")) and Bool(py=_builtins.hasattr(arg2, "flags"))):
            _has_ctypes = False
        elif Int(py=arg2.ndim) != 1 or String(py=arg2.dtype.name) != "float64" or not Bool(py=arg2.flags.c_contiguous):
            _has_ctypes = False
    if _has_ctypes:
        var _n_xs = Int(py=arg0.__len__())
        var _xs_addr = Int(py=arg0.ctypes.data)
        var _xs_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_xs_addr)
        var _n_ys = Int(py=arg1.__len__())
        var _ys_addr = Int(py=arg1.ctypes.data)
        var _ys_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_ys_addr)
        var _n_zs = Int(py=arg2.__len__())
        var _zs_addr = Int(py=arg2.ctypes.data)
        var _zs_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_zs_addr)
        var _res = _ptr_find_closest_point_to_ray(_xs_op, _n_xs, _ys_op, _n_ys, _zs_op, _n_zs, Float64(py=arg3), Float64(py=arg4), Float64(py=arg5), Float64(py=arg6), Float64(py=arg7), Float64(py=arg8))
        return PythonObject(_res)
    else:
        var _n_xs = Int(py=arg0.__len__())
        var xs = List[Float64](capacity=_n_xs)
        for _i in range(_n_xs):
            xs.append(Float64(py=arg0[_i]))
        var _n_ys = Int(py=arg1.__len__())
        var ys = List[Float64](capacity=_n_ys)
        for _i in range(_n_ys):
            ys.append(Float64(py=arg1[_i]))
        var _n_zs = Int(py=arg2.__len__())
        var zs = List[Float64](capacity=_n_zs)
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
        var vx: Float64 = _checked_sub(xs[unsafe_offset=i], ray_ox)
        var vy: Float64 = _checked_sub(ys[unsafe_offset=i], ray_oy)
        var vz: Float64 = _checked_sub(zs[unsafe_offset=i], ray_oz)
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
