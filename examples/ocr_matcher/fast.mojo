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
        m.def_function[find_closest_match]("find_closest_match")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def find_closest_match(arg0: PythonObject, arg1: PythonObject, arg2: PythonObject) raises -> PythonObject:
    var query = String(py=arg0)
    var candidates = List[String]()
    var _n_candidates = Int(py=arg1.__len__())
    for _i in range(_n_candidates):
        candidates.append(String(py=arg1[_i]))
    var max_distance = Int(py=arg2)
    var _res = _native_find_closest_match(query, candidates, max_distance)
    return PythonObject(_res)

@always_inline
def _is_ascii(s: String) -> Bool:
    var b = s.as_bytes()
    for i in range(len(b)):
        if Int(b[i]) >= 128:
            return False
    return True

def _native_levenshtein_distance(_arg_s1: String, _arg_s2: String, max_dist: Int) raises -> Int:
    var m = _arg_s1.byte_length()
    var n = _arg_s2.byte_length()
    var diff = m - n if m >= n else n - m
    if diff > max_dist:
        return max_dist + 1
    if m <= 64 and n <= 64 and _is_ascii(_arg_s1) and _is_ascii(_arg_s2):
        var s1_bytes = _arg_s1.as_bytes()
        var s2_bytes = _arg_s2.as_bytes()
        var peq = List[UInt64]()
        for _ in range(128):
            peq.append(0)
        for i in range(m):
            var c = Int(s1_bytes[i])
            if c < 128:
                peq[c] |= (UInt64(1) << UInt64(i))
        var score = m
        var vp: UInt64 = (UInt64(1) << UInt64(m)) - 1
        var vn: UInt64 = 0
        for j in range(n):
            var c = Int(s2_bytes[j])
            var pm = peq[c] if c < 128 else UInt64(0)
            var d0 = (((pm & vp) + vp) ^ vp) | pm | vn
            var hp = vn | ~(d0 | vp)
            var hn = d0 & vp
            if (hp & (UInt64(1) << UInt64(m - 1))) != 0:
                score += 1
            elif (hn & (UInt64(1) << UInt64(m - 1))) != 0:
                score -= 1
            hp = (hp << UInt64(1)) | 1
            hn = hn << UInt64(1)
            d0 = (d0 >> UInt64(1)) | (UInt64(1) << UInt64(63))
            vp = hn | ~(d0 | hp)
            vn = hp & d0
        return score

    # Fallback to standard dynamic programming for non-ASCII or long strings
    var s1: _PyStr = _PyStr(_arg_s1)
    var s2: _PyStr = _PyStr(_arg_s2)
    var m_cp: Int = _len(s1)
    var n_cp: Int = _len(s2)
    var prev: List[Int] = List[Int]()
    var curr: List[Int] = List[Int]()
    for j in range(_checked_add(n_cp, 1)):
        prev.append(j)
        curr.append(0)
    for i in range(1, _checked_add(m_cp, 1)):
        curr[0] = i
        var min_row: Int = i
        var ch1: String = s1[_checked_sub(i, 1)]
        for j in range(1, _checked_add(n_cp, 1)):
            var cost: Int = 1
            if (ch1 == s2[_checked_sub(j, 1)]):
                cost = 0
            var del_cost: Int = _checked_add(prev[j], 1)
            var ins_cost: Int = _checked_add(curr[_checked_sub(j, 1)], 1)
            var sub_cost: Int = _checked_add(prev[_checked_sub(j, 1)], cost)
            var val: Int = del_cost
            if (ins_cost < val):
                val = ins_cost
            if (sub_cost < val):
                val = sub_cost
            curr[j] = val
            if (val < min_row):
                min_row = val
        if (min_row > max_dist):
            return _checked_add(max_dist, 1)
        for j in range(_checked_add(n_cp, 1)):
            prev[j] = curr[j]
    return prev[n_cp]

def _native_find_closest_match(query: String, candidates: List[String], max_distance: Int) raises -> Int:
    var best_idx: Int = _checked_neg(1)
    var best_dist: Int = _checked_add(max_distance, 1)
    var num_candidates: Int = _len(candidates)
    var m = query.byte_length()

    if m <= 64 and _is_ascii(query):
        var s1_bytes = query.as_bytes()
        var peq = List[UInt64]()
        for _ in range(128):
            peq.append(0)
        for i in range(m):
            var c = Int(s1_bytes[i])
            if c < 128:
                peq[c] |= (UInt64(1) << UInt64(i))

        for i in range(num_candidates):
            var cand = candidates[i]
            var n = cand.byte_length()
            var diff = m - n if m >= n else n - m
            if diff > best_dist - 1:
                continue
            if n <= 64 and _is_ascii(cand):
                var s2_bytes = cand.as_bytes()
                var score = m
                var vp: UInt64 = (UInt64(1) << UInt64(m)) - 1
                var vn: UInt64 = 0
                for j in range(n):
                    var c = Int(s2_bytes[j])
                    var pm = peq[c] if c < 128 else UInt64(0)
                    var d0 = (((pm & vp) + vp) ^ vp) | pm | vn
                    var hp = vn | ~(d0 | vp)
                    var hn = d0 & vp
                    if (hp & (UInt64(1) << UInt64(m - 1))) != 0:
                        score += 1
                    elif (hn & (UInt64(1) << UInt64(m - 1))) != 0:
                        score -= 1
                    hp = (hp << UInt64(1)) | 1
                    hn = hn << UInt64(1)
                    d0 = (d0 >> UInt64(1)) | (UInt64(1) << UInt64(63))
                    vp = hn | ~(d0 | hp)
                    vn = hp & d0
                if score < best_dist:
                    best_dist = score
                    best_idx = i
                    if best_dist == 0:
                        break
            else:
                var dist: Int = _native_levenshtein_distance(query, cand, _checked_sub(best_dist, 1))
                if (dist < best_dist):
                    best_dist = dist
                    best_idx = i
                    if (best_dist == 0):
                        break
        return best_idx

    for i in range(num_candidates):
        var cand: String = candidates[i]
        var dist: Int = _native_levenshtein_distance(query, cand, _checked_sub(best_dist, 1))
        if (dist < best_dist):
            best_dist = dist
            best_idx = i
            if (best_dist == 0):
                break
    return best_idx
