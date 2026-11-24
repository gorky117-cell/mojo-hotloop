# Copyright 2026 Gaurav Kumar Singh
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import ast
import copy
import json
from . import _provenance
from . import _return_origin
import inspect
from typing import Dict, List, Optional, Set, Tuple

TYPE_MAP = {
    "int": "Int",
    "float": "Float64",
    "bool": "Bool",
    "str": "String",
    "list[int]": "List[Int]",
    "list[float]": "List[Float64]",
    "list[bool]": "List[Bool]",
    "list[str]": "List[String]",
}

PY_CONVERT_MAP = {
    "int": "Int(py={var})",
    "float": "Float64(py={var})",
    "bool": "Bool(py={var})",
    "str": "String(py={var})",
    "list[str]": "List[String]()",
}

MOJO_RESERVED_IDENTIFIERS = frozenset({
    "fn", "var", "struct", "ref", "trait", "comptime", "Self",
})
MOJO_PARAM_KEYWORDS = MOJO_RESERVED_IDENTIFIERS | frozenset({
    "mut", "out", "owned", "borrowed", "inout", "read",
})

def parse_type_annotation(node: Optional[ast.AST]) -> Tuple[str, str, Optional[str]]:
    """
    Parses a Python AST type annotation node.
    Returns:
        (canonical_py_type, mojo_type, item_type_or_none)
    """
    if node is None:
        raise ASTTranspileError("Missing type annotation")

    if isinstance(node, ast.Name):
        t_id = node.id
        if t_id == "int":
            return "int", "Int", None
        elif t_id == "float":
            return "float", "Float64", None
        elif t_id == "bool":
            return "bool", "Bool", None
        elif t_id == "str":
            return "str", "String", None
        elif t_id in ("ndarray", "NDArray"):
            return "list[float]", "List[Float64]", "float"
        elif t_id in ("list", "List"):
            raise ASTTranspileError("Generic list must have element type, e.g. list[float] or list[int]")
        else:
            raise ASTTranspileError(f"Unsupported type '{t_id}'. Supported: int, float, bool, str, list[int], list[float]")

    elif isinstance(node, ast.Attribute):
        if node.attr in ("ndarray", "NDArray") or (isinstance(node.value, ast.Name) and node.value.id in ("np", "numpy")):
            return "list[float]", "List[Float64]", "float"
        raise ASTTranspileError(f"Unsupported type annotation attribute: {ast.dump(node)}")

    elif isinstance(node, ast.Subscript):
        is_list = isinstance(node.value, ast.Name) and node.value.id in ("list", "List")
        is_ndarray = (
            (isinstance(node.value, ast.Name) and node.value.id in ("ndarray", "NDArray"))
            or (isinstance(node.value, ast.Attribute) and node.value.attr in ("ndarray", "NDArray"))
        )
        if is_list or is_ndarray:
            elem_node = node.slice
            elem_id = ""
            if isinstance(elem_node, ast.Name):
                elem_id = elem_node.id
            elif isinstance(elem_node, ast.Attribute):
                elem_id = elem_node.attr
            if elem_id in ("int", "int64", "Int64", "int32"):
                return "list[int]", "List[Int]", "int"
            elif elem_id in ("float", "float64", "Float64", "float32"):
                return "list[float]", "List[Float64]", "float"
            elif elem_id == "bool":
                return "list[bool]", "List[Bool]", "bool"
            elif elem_id == "str":
                return "list[str]", "List[String]", "str"
            else:
                if is_ndarray:
                    return "list[float]", "List[Float64]", "float"
                raise ASTTranspileError(f"Unsupported list element type '{elem_id}'. Supported: int, float, bool, str")
        else:
            raise ASTTranspileError(f"Unsupported subscripted type annotation: {ast.dump(node)}")

    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        parsed = ast.parse(node.value, mode="eval")
        return parse_type_annotation(parsed.body)

    raise ASTTranspileError(f"Unsupported type annotation expression: {type(node).__name__}")

CHECKED_HELPERS_MOJO = """# Checked Arithmetic and Error Signaling Helpers (Mojo 1.2.0)
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
def _checked_list_index(idx: Int, n: Int) raises -> Int:
    if UInt(idx) < UInt(n):
        return idx
    if idx < 0 and idx >= -n:
        return idx + n
    raise Error("HOTLOOP_INDEX_ERROR: list index out of range")

@always_inline
def _checked_list_assignment_index(idx: Int, n: Int) raises -> Int:
    if UInt(idx) < UInt(n):
        return idx
    if idx < 0 and idx >= -n:
        return idx + n
    raise Error("HOTLOOP_INDEX_ERROR: list assignment index out of range")

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
"""

class ASTTranspileError(Exception):
    """Raised when an AST node cannot be deterministically transpiled to Mojo."""
    pass


def _collect_reassigned_vars(func_def: ast.FunctionDef) -> Set[str]:
    reassigned: Set[str] = set()
    for node in ast.walk(ast.Module(body=func_def.body, type_ignores=[])):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    reassigned.add(t.id)
                elif isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name):
                    reassigned.add(t.value.id)
        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                reassigned.add(node.target.id)
            elif isinstance(node.target, ast.Subscript) and isinstance(node.target.value, ast.Name):
                reassigned.add(node.target.value.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            reassigned.add(node.target.id)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in ("append", "clear") and isinstance(node.func.value, ast.Name):
                reassigned.add(node.func.value.id)
    return reassigned


def _borrowed_list_is_read_only(func_def: ast.FunctionDef, arg_name: str) -> bool:
    """Only admit uses that cannot mutate, retain, alias or return the input list."""
    parent_map: Dict[int, ast.AST] = {}
    for parent in ast.walk(func_def):
        for child in ast.iter_child_nodes(parent):
            parent_map[id(child)] = parent

    body_nodes = ast.Module(body=func_def.body, type_ignores=[])
    for node in ast.walk(body_nodes):
        if isinstance(node, ast.Name) and node.id == arg_name:
            parent = parent_map.get(id(node))
            if isinstance(parent, ast.UnaryOp) and isinstance(parent.op, ast.Not):
                continue
            if isinstance(parent, (ast.If, ast.While)) and parent.test is node:
                continue
            if isinstance(parent, ast.For) and parent.iter is node:
                continue
            if (
                isinstance(parent, ast.Call)
                and isinstance(parent.func, ast.Name)
                and parent.func.id == "len"
                and len(parent.args) == 1
                and parent.args[0] is node
            ):
                continue
            if (
                isinstance(parent, ast.Subscript)
                and parent.value is node
                and isinstance(parent.ctx, ast.Load)
                and not isinstance(parent.slice, ast.Slice)
            ):
                continue
            return False
    return True


def _infer_list_mojo_type(elts: List[ast.expr]) -> Optional[str]:
    if not elts:
        return None
    has_float = False
    all_num = True
    all_bool = True
    all_str = True
    for e in elts:
        if isinstance(e, ast.Constant):
            if isinstance(e.value, bool):
                all_num = False
                all_str = False
            elif isinstance(e.value, int):
                all_bool = False
                all_str = False
            elif isinstance(e.value, float):
                has_float = True
                all_bool = False
                all_str = False
            elif isinstance(e.value, str):
                all_num = False
                all_bool = False
            else:
                return None
        elif isinstance(e, (ast.BinOp, ast.UnaryOp)):
            all_bool = False
            all_str = False
            if any(isinstance(c, ast.Constant) and isinstance(c.value, float) for c in ast.walk(e)):
                has_float = True
            if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Div):
                has_float = True
        else:
            return None
    if all_bool:
        return "List[Bool]"
    if all_str:
        return "List[String]"
    if all_num:
        return "List[Float64]" if has_float else "List[Int]"
    return None


def _collect_codepoint_vars(func_def: ast.FunctionDef, pystr_vars: Set[str]) -> Set[str]:
    """Identify local single-char `str` variables (from `_PyStr[i]`) safe to represent as `Codepoint`."""
    if not pystr_vars:
        return set()

    param_names = {a.arg for a in func_def.args.args}
    parent_map: Dict[int, ast.AST] = {}
    body_mod = ast.Module(body=func_def.body, type_ignores=[])
    for parent in ast.walk(body_mod):
        for child in ast.iter_child_nodes(parent):
            parent_map[id(child)] = parent

    def _is_pystr_single_sub(n: Optional[ast.expr]) -> bool:
        return (
            isinstance(n, ast.Subscript)
            and isinstance(n.value, ast.Name)
            and n.value.id in pystr_vars
            and not isinstance(n.slice, ast.Slice)
        )

    candidates: Set[str] = set()
    disqualified: Set[str] = set(param_names)

    for node in ast.walk(body_mod):
        if isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                v = node.target.id
                ann_is_str = isinstance(node.annotation, ast.Name) and node.annotation.id == "str"
                if ann_is_str and _is_pystr_single_sub(node.value):
                    candidates.add(v)
                else:
                    disqualified.add(v)
        elif isinstance(node, ast.Assign):
            if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                v = node.targets[0].id
                if _is_pystr_single_sub(node.value):
                    candidates.add(v)
                else:
                    disqualified.add(v)
            else:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        disqualified.add(t.id)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            disqualified.add(node.target.id)
        elif isinstance(node, ast.For) and isinstance(node.target, ast.Name):
            disqualified.add(node.target.id)

    candidates -= disqualified
    if not candidates:
        return set()

    def _is_single_char_const(n: ast.expr) -> bool:
        return isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) == 1

    changed = True
    while changed and candidates:
        changed = False
        for node in ast.walk(body_mod):
            if isinstance(node, ast.Name) and node.id in candidates and isinstance(node.ctx, ast.Load):
                parent = parent_map.get(id(node))
                ok = False
                if isinstance(parent, ast.Compare):
                    items = [parent.left] + list(parent.comparators)
                    if all(
                        _is_pystr_single_sub(x)
                        or _is_single_char_const(x)
                        or (isinstance(x, ast.Name) and x.id in candidates)
                        for x in items
                    ):
                        ok = True
                elif (
                    isinstance(parent, ast.AugAssign)
                    and isinstance(parent.op, ast.Add)
                    and parent.value is node
                    and isinstance(parent.target, ast.Name)
                    and parent.target.id not in candidates
                ):
                    ok = True
                elif (
                    isinstance(parent, ast.Call)
                    and isinstance(parent.func, ast.Name)
                    and parent.func.id == "ord"
                    and len(parent.args) == 1
                    and parent.args[0] is node
                ):
                    ok = True
                if not ok:
                    candidates.remove(node.id)
                    changed = True
                    break

    return candidates


def _eval_constant_expr(node: ast.expr) -> Optional[object]:
    """
    Evaluates constant math and literals at transpile time.
    Returns Python scalar value or None if not statically evaluable.
    """
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return node.value
        return None
    elif isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "math":
            if node.attr == "pi":
                return 3.141592653589793
            elif node.attr == "e":
                return 2.718281828459045
            elif node.attr == "tau":
                return 6.283185307179586
        return None
    elif isinstance(node, ast.UnaryOp):
        val = _eval_constant_expr(node.operand)
        if val is not None and isinstance(val, (int, float, bool)):
            if isinstance(node.op, ast.USub):
                return -val
            elif isinstance(node.op, ast.UAdd):
                return +val
            elif isinstance(node.op, ast.Not):
                return not val
            elif isinstance(node.op, ast.Invert) and isinstance(val, int):
                return ~val
        return None
    elif isinstance(node, ast.BinOp):
        left = _eval_constant_expr(node.left)
        right = _eval_constant_expr(node.right)
        if left is not None and right is not None and isinstance(left, (int, float, bool)) and isinstance(right, (int, float, bool)):
            try:
                if isinstance(node.op, ast.Add):
                    return left + right
                elif isinstance(node.op, ast.Sub):
                    return left - right
                elif isinstance(node.op, ast.Mult):
                    return left * right
                elif isinstance(node.op, ast.Div):
                    return left / right if right != 0 else None
                elif isinstance(node.op, ast.FloorDiv):
                    return left // right if right != 0 else None
                elif isinstance(node.op, ast.Mod):
                    return left % right if right != 0 else None
                elif isinstance(node.op, ast.Pow):
                    if -100 < right < 100:
                        return left ** right
            except (ArithmeticError, ValueError):
                return None
        return None
    elif isinstance(node, ast.Call):
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "math"
        ):
            fn_name = node.func.attr
            c_args = [_eval_constant_expr(a) for a in node.args]
            if all(a is not None and isinstance(a, (int, float)) for a in c_args):
                try:
                    import math as _py_math
                    fn = getattr(_py_math, fn_name, None)
                    if fn and callable(fn):
                        return fn(*c_args)
                except Exception:
                    return None
    return None


class MojoASTTranspiler:
    def __init__(self, mod_name: str, known_funcs: Optional[Set[str]] = None, return_origins=None):
        self.mod_name = mod_name
        self.return_origins = return_origins or {}
        self.origin_plan = None
        self.used_native_names = {"_native_" + name for name in (known_funcs or ())}
        self.known_funcs: Set[str] = known_funcs or set()
        self.tagged_names = {}
        for name in sorted(self.known_funcs):
            tagged = "_native_return_origin_" + name
            while tagged in self.used_native_names:
                tagged += "_"
            self.used_native_names.add(tagged)
            self.tagged_names[name] = tagged
        self.indent_level = 0
        self.scopes: List[Set[str]] = [set()]
        self.var_types: Dict[str, str] = {}
        self.has_math = False
        self.ret_mojo_type: str = "Int"
        self.ret_elem_type: Optional[str] = None
        self.codepoint_vars: Set[str] = set()
        self._tmp_counter: int = 0

    def indent(self) -> str:
        return "    " * self.indent_level

    def _next_tmp(self, prefix: str = "_hot_tmp") -> str:
        self._tmp_counter += 1
        return f"{prefix}_{self._tmp_counter}"

    def _emit_cond_expr(self, node: ast.expr) -> str:
        expr_code = self.visit_expr(node)
        if isinstance(node, (ast.Compare, ast.BoolOp)):
            return expr_code
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return expr_code
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return expr_code
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "bool":
            return expr_code
        if isinstance(node, ast.Name) and self.var_types.get(node.id) == "Bool":
            return expr_code
        return f"_py_bool({expr_code})"

    def _is_python_list(self, node: ast.expr) -> bool:
        # Only emitted native List types with exact-list argument guards or
        # Python list construction qualify. Never infer from an IndexError.
        if isinstance(node, ast.List):
            return True
        if isinstance(node, ast.Name):
            return self.var_types.get(node.id, "").startswith("List[")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            plan = self.return_origins.get(node.func.id)
            return bool(plan and plan.fn.returns
                        and parse_type_annotation(plan.fn.returns)[1].startswith("List["))
        return False

    def _box_return_block(self, res_expr: str, indent: str, has_builtins: bool) -> str:
        if self.ret_elem_type is not None:
            lines = [f"{indent}var _res = {res_expr}"]
            if not has_builtins:
                lines.append(f'{indent}var _builtins = Python.import_module("builtins")')
            lines.extend([
                f"{indent}var _py_res = _builtins.list()",
                f"{indent}for _i in range(len(_res)):",
                f"{indent}    _py_res.append(_res[_i])",
                f"{indent}return _py_res",
            ])
            return "\n".join(lines)
        return f"{indent}var _res = {res_expr}\n{indent}return PythonObject(_res)"

    def _emit_slice_expr(self, val: str, sl: ast.Slice, as_method: bool = True) -> str:
        if sl.step is not None:
            has_s = "True" if sl.lower is not None else "False"
            s_val = self.visit_expr(sl.lower) if sl.lower is not None else "0"
            has_e = "True" if sl.upper is not None else "False"
            e_val = self.visit_expr(sl.upper) if sl.upper is not None else "0"
            step_val = self.visit_expr(sl.step)
            if as_method:
                return f"{val}.slice_step({has_s}, {s_val}, {has_e}, {e_val}, {step_val})"
            return f"_str_slice({val}, {has_s}, {s_val}, {has_e}, {e_val}, {step_val})"
        start = self.visit_expr(sl.lower) if sl.lower else "0"
        end = self.visit_expr(sl.upper) if sl.upper else f"_len({val})"
        if as_method:
            return f"{val}[{start}:{end}]"
        return f"_str_slice({val}, True, {start}, True, {end}, 1)"

    def _transpile_body(
        self,
        func_def: ast.FunctionDef,
        args: List[Tuple[str, str, str, Optional[str]]],
        subscripted_args: Set[str],
        reassigned_vars: Set[str],
    ) -> Tuple[List[str], str]:
        self.scopes = [set()]
        self.var_types.clear()
        self.primary_str_arg = next((name for name, py_t, _, _ in args if py_t == "str"), None)
        pystr_arg_names = {
            name for name, _, mojo_type, _ in args
            if name in subscripted_args and mojo_type == "String"
        }
        self.codepoint_vars = _collect_codepoint_vars(func_def, pystr_arg_names)
        self._tmp_counter = 0
        # The existing provenance prefix excludes every source name.
        self._list_rhs_prefix = self.return_origins[func_def.name].prefix + "_list_rhs"
        self.borrowed_names = set()

        sig_args: List[str] = []
        body_prep: List[str] = []

        for name, py_type, mojo_type, elem_type in args:
            self.scopes[0].add(name)
            self.var_types[name] = mojo_type
            if name in subscripted_args and mojo_type == "String":
                sig_args.append(f"_arg_{name}: String")
                body_prep.append(f"    var {name}: _PyStr = _PyStr(_arg_{name})")
                self.var_types[name] = "_PyStr"
            elif name in reassigned_vars:
                sig_args.append(f"_arg_{name}: {mojo_type}")
                if elem_type is not None:
                    body_prep.append(f"    var {name}: {mojo_type} = _arg_{name}.copy()")
                else:
                    body_prep.append(f"    var {name}: {mojo_type} = _arg_{name}")
            else:
                sig_args.append(f"{name}: {mojo_type}")
                self.borrowed_names.add(name)

        self.indent_level = 1
        if self.origin_plan is not None:
            for name, tag in self.origin_plan.tags.items():
                initial = self.origin_plan.arguments.get(name, -1)
                body_prep.append(f"    var {tag}: Int = {initial}")
                body_prep.append(f"    var {self.origin_plan.slots[name]}: Int = -1")
        body_lines = list(body_prep)
        for stmt in func_def.body:
            body_lines.append(self.visit_stmt(stmt))
        return sig_args, "\n".join(body_lines)

    def transpile_function_components(self, func_def: ast.FunctionDef) -> Tuple[str, str, str]:
        """
        Transpiles a single FunctionDef.
        Returns:
            export_registration: e.g. 'm.def_function[name]("name")'
            c_abi_wrapper: wrapper function callable from Python
            native_function: native compiled implementation
        """
        # 1. Validate argument types and reserved Mojo identifiers
        args = []
        for arg in func_def.args.args:
            arg_name = arg.arg
            if arg_name in MOJO_PARAM_KEYWORDS:
                raise ASTTranspileError(f"Parameter name '{arg_name}' conflicts with a Mojo reserved keyword")
            if not arg.annotation:
                raise ASTTranspileError(f"Argument '{arg_name}' must have explicit type annotation (e.g. int, float, list[float])")
            py_type, mojo_type, elem_type = parse_type_annotation(arg.annotation)
            args.append((arg_name, py_type, mojo_type, elem_type))
        for n in ast.walk(func_def):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store) and n.id in MOJO_RESERVED_IDENTIFIERS:
                raise ASTTranspileError(f"Variable name '{n.id}' conflicts with a Mojo reserved keyword")

        # 2. Validate return type
        if not func_def.returns:
            raise ASTTranspileError(f"Function '{func_def.name}' must have explicit return type annotation")
        ret_py_type, ret_mojo_type, ret_elem_type = parse_type_annotation(func_def.returns)
        self.ret_mojo_type = ret_mojo_type
        self.ret_elem_type = ret_elem_type

        # 2b. Analyze subscripted str arguments and reassigned/mutated variables
        subscripted_args = set()
        for arg in func_def.args.args:
            arg_name = arg.arg
            if any(isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == arg_name for n in ast.walk(func_def)):
                subscripted_args.add(arg_name)
        reassigned_vars = _collect_reassigned_vars(func_def)

        # 3. Transpile standard native implementation
        native_args, body_code = self._transpile_body(func_def, args, subscripted_args, reassigned_vars)

        # Copy qualified Python lists through Python indexing. No borrowed addresses.
        context_name = self.return_origins[func_def.name].prefix + "_context"
        wrapper_args_def = ", ".join([f"{context_name}: PythonObject", *[f"arg{i}: PythonObject" for i in range(len(args))]])

        def _build_list_unbox(idx: int, name: str, mojo_type: str, elem_type: str, indent: str) -> str:
            inner_mojo = "Float64" if elem_type == "float" else ("Int" if elem_type == "int" else ("String" if elem_type == "str" else "Bool"))
            return (
                f"{indent}var _n_{name} = Int(py=_input{idx}.__len__())\n"
                f"{indent}var {name} = {mojo_type}(capacity=_n_{name})\n"
                f"{indent}for _i in range(_n_{name}):\n"
                f"{indent}    {name}.append({inner_mojo}(py=_input{idx}[_i]))"
            )

        wrapper_conversions = ['    var _guard = Python.import_module("hotloop._arguments")'] if args else []
        call_args = []
        for i, (name, py_type, mojo_type, elem_type) in enumerate(args):
            wrapper_conversions.append(f'    var _input{i} = _guard.checked_argument(arg{i}, "{py_type}")')
            if elem_type is not None:
                wrapper_conversions.append(_build_list_unbox(i, name, mojo_type, elem_type, "    "))
            else:
                wrapper_conversions.append(f"    var {name} = {mojo_type}(py=_input{i})")
            call_args.append(name)

        call_block = self._box_return_block(f"_native_{func_def.name}({', '.join(call_args)})", "    ", has_builtins=False)
        native_code = f"""def _native_{func_def.name}({", ".join(native_args)}) raises -> {ret_mojo_type}:
{body_code}"""
        plan = self.return_origins.get(func_def.name)
        if plan is not None and (plan.scalar and plan.returned or plan.reason):
            if plan.reason:
                call_block = '    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")'
                wrapper_conversions = []
                # Internal callers are restricted transitively as well. Do not
                # leave a value-only native path around this semantic gate.
                native_code = (f"def _native_{func_def.name}({', '.join(native_args)}) raises -> {ret_mojo_type}:\n"
                               '    raise Error("HOTLOOP_PYTHON_SEMANTICS: return-object provenance is unproven")')
            else:
                tagged_name = self.tagged_names[func_def.name]
                self.origin_plan = plan
                try:
                    tagged_args, tagged_body = self._transpile_body(
                        func_def, args, subscripted_args, reassigned_vars)
                finally:
                    self.origin_plan = None
                native_code += f"""

def {tagged_name}({", ".join(tagged_args)}) raises -> Tuple[{ret_mojo_type}, Int, Int]:
{tagged_body}"""
                result = plan.prefix + "_result"
                lines = [f"    var {result} = {tagged_name}({', '.join(call_args)})"]
                lines += [f"    if {result}[1] == -2:", f"        return {context_name}[{result}[2]]"]
                if ret_mojo_type=="String":
                    lines += [f"    if {result}[1] == -3:",
                              '        var _owners = Python.import_module("hotloop._provenance")',
                              f"        return _owners.fresh_string(PythonObject({result}[0]))"]
                for i, (_, _, _, element) in enumerate(args):
                    lines.append(f"    if {result}[1] == {i}:")
                    if element is not None:
                        lines += [f"        if {result}[2] >= 0:",
                                  f"            return _input{i}[{result}[2]]"]
                    lines.append(f"        return arg{i}")
                lines.append(self._box_return_block(f"{result}[0]", "    ", has_builtins=False))
                call_block = "\n".join(lines)

        conv_block_4 = "\n".join(wrapper_conversions)
        wrapper_code = f"""def _pywrap_{func_def.name}({wrapper_args_def}) raises -> PythonObject:
{conv_block_4}
{call_block}"""
        export_reg = f'        m.def_function[_pywrap_{func_def.name}]("{func_def.name}")'

        return export_reg, wrapper_code, native_code

    def _origin_expr(self, node):
        """Emit each application expression once, in its original evaluation order."""
        plan=self.origin_plan
        kind,source=plan.descriptor(node)
        emit=lambda code: self.indent()+code
        if kind=="int_mod":
            # CPython 3.12.16 l_mod/long_rem: digit-count and top-digit
            # shortcut, excluding the single-digit allocating fast path.
            lines,left,lt,ls=self._origin_expr(source.left)
            lv,rv,value,tag,slot,ua,ub,da,db,ha,hb=(plan.temporary() for _ in range(11))
            lines += [emit(f"var {lv} = {left}"),emit(f"var {rv} = {self.visit_expr(source.right)}"),
                emit(f"var {value} = _checked_mod({lv}, {rv})"),
                emit(f"var {ua} = UInt64({lv}) if {lv} >= 0 else UInt64(-1 - {lv}) + 1"),
                emit(f"var {ub} = UInt64({rv}) if {rv} >= 0 else UInt64(-1 - {rv}) + 1"),
                emit(f"var {da} = 0 if {ua} == 0 else (1 if {ua} < 1073741824 else (2 if {ua} < 1152921504606846976 else 3))"),
                emit(f"var {db} = 0 if {ub} == 0 else (1 if {ub} < 1073741824 else (2 if {ub} < 1152921504606846976 else 3))"),
                emit(f"var {ha} = {ua} if {da} <= 1 else ({ua} >> 30 if {da} == 2 else {ua} >> 60)"),
                emit(f"var {hb} = {ub} if {db} <= 1 else ({ub} >> 30 if {db} == 2 else {ub} >> 60)"),
                emit(f"var {tag}: Int = -1"),emit(f"var {slot}: Int = -1"),
                emit(f"if not ({da} == 1 and {db} == 1) and ({da} < {db} or ({da} == {db} and {ha} < {hb})) and (({rv} > 0 and {lv} >= 0) or ({rv} < 0 and {lv} <= 0)):"),
                emit(f"    {tag} = {lt}"),emit(f"    {slot} = {ls}")]
            return lines,value,tag,slot
        if kind=="format_int":
            return [],f"String({self.visit_expr(source)})","-3","-1"
        if kind=="string_identity":
            return self._origin_expr(source)
        if kind=="constant":
            return [],self.visit_expr(node),"-2",str(source)
        if kind=="name":
            tag,slot=plan.reference(source)
            return [],self.visit_expr(node),tag,slot
        if kind=="value":
            return [],self.visit_expr(node),"-1","-1"
        if kind=="item":
            index=plan.temporary()
            container=source.value.id
            lines=[emit(f"var {index} = _checked_list_index({self.visit_expr(source.slice)}, len({container}))")]
            return lines,f"{container}[{index}]",str(plan.arguments[container]),index
        if kind=="slice":
            container=node.value.id
            sl=node.slice
            names=[]
            lines=[]
            for value,default in ((sl.lower,"0"),(sl.upper,f"_len({container})"),(sl.step,"1")):
                temp=plan.temporary()
                lines.append(emit(f"var {temp} = {self.visit_expr(value) if value is not None else default}"))
                names.append(temp)
            lower,upper,step=names
            replacement=copy.deepcopy(node)
            replacement.slice=ast.Slice(
                lower=ast.Name(id=lower,ctx=ast.Load()) if sl.lower is not None else None,
                upper=ast.Name(id=upper,ctx=ast.Load()) if sl.upper is not None else None,
                step=ast.Name(id=step,ctx=ast.Load()) if sl.step is not None else None)
            result,tag,slot=(plan.temporary() for _ in range(3))
            original_tag,original_slot=plan.reference(container)
            lines += [emit(f"var {result} = {self.visit_expr(replacement)}"),
                      emit(f"var {tag}: Int = -3 if {step} != 1 else -1"),emit(f"var {slot}: Int = -1"),
                      emit(f"if {step} == 1 and ({lower} == 0 or {lower} <= -_len({container})) and {upper} >= _len({container}):"),
                      emit(f"    {tag} = {original_tag}"),emit(f"    {slot} = {original_slot}")]
            self.var_types[result]="String"
            return lines,result,tag,slot
        if kind=="concat":
            left,lval,lt,ls=self._origin_expr(node.left)
            # Capture the left operand before evaluating the right operand.
            lv=plan.temporary()
            ltype=self.var_types.get(lval)
            left.append(emit(f"var {lv} = {lval}.to_string()" if ltype=="_PyStr" else f"var {lv} = String({lval})"))
            right,rval,rt,rs=self._origin_expr(node.right)
            rv=plan.temporary()
            rtype=self.var_types.get(rval)
            right.append(emit(f"var {rv} = {rval}.to_string()" if rtype=="_PyStr" else f"var {rv} = String({rval})"))
            result,tag,slot=(plan.temporary() for _ in range(3))
            lines=left+right+[emit(f"var {result} = _checked_add({lv}, {rv})"),
                emit(f"var {tag}: Int = -1"),emit(f"var {slot}: Int = -1"),
                emit(f"if {lv}.byte_length() == 0:"),emit(f"    {tag} = {rt}"),emit(f"    {slot} = {rs}"),
                emit(f"elif {rv}.byte_length() == 0:"),emit(f"    {tag} = {lt}"),emit(f"    {slot} = {ls}")]
            self.var_types[result]="String"
            return lines,result,tag,slot
        if kind=="helper":
            callee=node.func.id
            callee_plan=self.return_origins[callee]
            if node.keywords or len(node.args)!=len(callee_plan.arguments) or not callee_plan.scalar or callee_plan.reason:
                raise ASTTranspileError("Unproven helper return provenance")
            lines=[]
            values=[]
            owners=[]
            for arg in node.args:
                prep,value,tag,slot=self._origin_expr(arg)
                lines.extend(prep)
                tmp=plan.temporary()
                value=value+".to_string()" if self.var_types.get(value)=="_PyStr" else value
                lines.append(emit(f"var {tmp} = {value}"))
                values.append(tmp)
                owners.append((tag,slot))
            result,tag,slot,value=(plan.temporary() for _ in range(4))
            # A helper with fresh-only returns uses the ordinary native ABI.
            if not callee_plan.returned:
                lines.append(emit(f"var {value} = _native_{callee}({', '.join(values)})"))
                return lines,value,"-1","-1"
            lines += [emit(f"var {result} = {self.tagged_names[callee]}({', '.join(values)})"),
                emit(f"var {tag} = {result}[1]"),emit(f"var {slot} = {result}[2]")]
            for index,(owner,item) in enumerate(owners):
                lines += [emit(f"if {result}[1] == {index}:"),emit(f"    {tag} = {owner}"),emit(f"    {slot} = {item}")]
            lines.append(emit(f"var {value} = {result}[0]"))
            self.var_types[value]=parse_type_annotation(callee_plan.fn.returns)[1]
            return lines,value,tag,slot
        raise ASTTranspileError("Unproven return expression")

    def visit_stmt(self, node: ast.stmt) -> str:
        plan=self.origin_plan
        if plan is None:
            return self._visit_stmt(node)
        targets=_return_origin._targets(node)
        tracked=[name for name in targets if name in plan.tags]
        if isinstance(node,ast.AugAssign) and tracked and isinstance(node.op,ast.Mod) and self.var_types.get(targets[0])=="Int":
            expression=ast.copy_location(ast.BinOp(left=copy.deepcopy(node.target),op=ast.Mod(),right=node.value),node)
            replacement=ast.copy_location(ast.Assign(targets=[node.target],value=expression),node)
            return self.visit_stmt(replacement)
        if isinstance(node,ast.AugAssign) and tracked and self.var_types.get(targets[0])=="String" and isinstance(node.op,ast.Add):
            name=targets[0]
            lines,value,tag,slot=self._origin_expr(node.value)
            target_tag,target_slot=plan.reference(name)
            # Materialize a nontrivial RHS before both its empty test and write.
            # Otherwise a fresh-return helper or formatting call would run twice.
            typ=self.var_types.get(value)
            if not isinstance(node.value,(ast.Name,ast.Constant)) or typ=="_PyStr":
                temp=plan.temporary()
                expression=value+".to_string()" if typ=="_PyStr" else value
                lines.append(self.indent()+f"var {temp} = {expression}")
                self.var_types[temp]="String" if typ=="_PyStr" or plan.expression_type(node.value)=="str" else (typ or "String")
                value=temp
            # Empty concatenation preserves an operand; nonempty construction is fresh.
            # Byte length is O(1); never scan UTF-8 output on every append.
            constant=isinstance(node.value,ast.Constant) and type(node.value.value) is str
            typ=self.var_types.get(value)
            rhs_empty=("True" if node.value.value=="" else "False") if constant else ("False" if typ=="Codepoint" else f"not _py_bool({value})")
            if rhs_empty!="True":
                outer=[] if rhs_empty=="False" else [self.indent()+f"if not ({rhs_empty}):"]
                level=self.indent()+("" if rhs_empty=="False" else "    ")
                lines+=outer+[level+f"if {name}.byte_length() == 0:",level+f"    {target_tag} = {tag}",level+f"    {target_slot} = {slot}",
                    level+"else:",level+f"    {target_tag} = -1",level+f"    {target_slot} = -1"]
            replacement=copy.deepcopy(node)
            if lines:
                temp=plan.temporary()
                # The lowered expression may be a string literal or a Codepoint.
                lines.append(self.indent()+f"var {temp} = {value}")
                self.var_types[temp]=typ or "String"
                replacement.value=ast.Name(id=temp,ctx=ast.Load())
            return "\n".join([*lines,self._visit_stmt(replacement)])
        if isinstance(node,ast.Return) or (tracked and not isinstance(node,ast.AugAssign)):
            value=node.value
            if value is None:
                raise ASTTranspileError("Unproven annotation-only/empty return")
            lines,code,tag,slot=self._origin_expr(value)
            replacement=copy.deepcopy(node)
            # Simple aliases keep existing _PyStr/Codepoint-aware statement lowering.
            if lines or code!=self.visit_expr(value):
                tmp=plan.temporary()
                lines.append(self.indent()+f"var {tmp} = {code}")
                if code in self.var_types: self.var_types[tmp]=self.var_types[code]
                replacement.value=ast.Name(id=tmp,ctx=ast.Load())
            result=self._visit_stmt(replacement)
            if isinstance(node,ast.Assign) and isinstance(replacement.value,ast.Name):
                source_type=self.var_types.get(replacement.value.id)
                if source_type:
                    for name in targets:
                        self.var_types.setdefault(name,"String" if source_type=="_PyStr" else source_type)
            if isinstance(node,ast.Return):
                prefix=self.indent()+"return "
                result=prefix+f"({result[len(prefix):]}, {tag}, {slot})"
            else:
                for name in tracked:
                    result+=f"\n{self.indent()}{plan.tags[name]} = {tag}\n{self.indent()}{plan.slots[name]} = {slot}"
            return "\n".join([*lines,result])
        result=self._visit_stmt(node)
        for name in tracked:
            result+=f"\n{self.indent()}{plan.tags[name]} = -1\n{self.indent()}{plan.slots[name]} = -1"
        return result

    def _visit_stmt(self, node: ast.stmt) -> str:
        if isinstance(node, ast.Return):
            if node.value is None:
                return f"{self.indent()}return"
            if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                return f"{self.indent()}return {self.ret_mojo_type}()"
            val = self.visit_expr(node.value)
            if self.ret_mojo_type == "String" and isinstance(node.value, ast.Name) and self.var_types.get(node.value.id) == "_PyStr":
                return f"{self.indent()}return {val}.to_string()"
            if (self.ret_elem_type is not None or self.ret_mojo_type == "String") and isinstance(node.value, ast.Name):
                if node.value.id in self.borrowed_names:
                    return f"{self.indent()}return {val}.copy()"
                return f"{self.indent()}return {val}^"
            return f"{self.indent()}return {val}"

        elif isinstance(node, ast.AnnAssign):
            if not isinstance(node.target, ast.Name):
                raise ASTTranspileError("Annotated assignment target must be a simple variable name")
            var_name = node.target.id
            py_type, mojo_type, elem_type = parse_type_annotation(node.annotation)
            self.var_types[var_name] = mojo_type

            if node.value is None:
                self.scopes[-1].add(var_name)
                return f"{self.indent()}var {var_name}: {mojo_type}"

            elif var_name in self.codepoint_vars and isinstance(node.value, ast.Subscript) and isinstance(node.value.value, ast.Name):
                src_name = node.value.value.id
                idx_code = self.visit_expr(node.value.slice)
                mojo_type = "Codepoint"
                self.var_types[var_name] = "Codepoint"
                expr_code = f"{src_name}.get_cp({idx_code})"
            elif isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                expr_code = f"{mojo_type}()"
            elif mojo_type == "String" and isinstance(node.value, ast.Constant) and node.value.value == "":
                reserve_call = f"\n{self.indent()}{var_name}.reserve_bytes(_len({self.primary_str_arg}))" if self.primary_str_arg else ""
                expr_code = f"String(){reserve_call}"
            elif mojo_type == "String" and isinstance(node.value, ast.Name) and self.var_types.get(node.value.id) == "_PyStr":
                expr_code = f"{node.value.id}.to_string()"
            else:
                expr_code = self.visit_expr(node.value)

            is_declared = any(var_name in s for s in self.scopes)
            if not is_declared:
                self.scopes[-1].add(var_name)
                return f"{self.indent()}var {var_name}: {mojo_type} = {expr_code}"
            else:
                return f"{self.indent()}{var_name} = {expr_code}"

        elif isinstance(node, ast.Assign):
            if len(node.targets) != 1:
                raise ASTTranspileError("Only single variable assignments are currently supported")
            target = node.targets[0]
            if isinstance(target, ast.Subscript):
                target_code = self.visit_expr(target)
                expr_code = self.visit_expr(node.value)
                if self._is_python_list(target.value):
                    # Python evaluates the RHS before the list/index target.
                    value = self._next_tmp(self._list_rhs_prefix)
                    return (f"{self.indent()}var {value} = {expr_code}\n"
                            f"{self.indent()}{target_code} = {value}")
                return f"{self.indent()}{target_code} = {expr_code}"
            elif isinstance(target, ast.Name):
                var_name = target.id
                is_declared = any(var_name in s for s in self.scopes)
                inferred_annot = ""
                if var_name in self.codepoint_vars and isinstance(node.value, ast.Subscript) and isinstance(node.value.value, ast.Name):
                    src_name = node.value.value.id
                    idx_code = self.visit_expr(node.value.slice)
                    self.var_types[var_name] = "Codepoint"
                    inferred_annot = ": Codepoint"
                    expr_code = f"{src_name}.get_cp({idx_code})"
                elif isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                    inferred_type = self.var_types.get(var_name, self.ret_mojo_type)
                    self.var_types.setdefault(var_name, inferred_type)
                    expr_code = f"{inferred_type}()"
                elif isinstance(node.value, ast.List):
                    inferred_list = _infer_list_mojo_type(node.value.elts)
                    expr_code = self.visit_expr(node.value)
                    if not is_declared and inferred_list:
                        self.var_types[var_name] = inferred_list
                        inferred_annot = f": {inferred_list}"
                elif isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    self.var_types.setdefault(var_name, "String")
                    if node.value.value == "":
                        reserve_call = f"\n{self.indent()}{var_name}.reserve_bytes(_len({self.primary_str_arg}))" if self.primary_str_arg and not is_declared else ""
                        expr_code = f"String(){reserve_call}"
                    else:
                        expr_code = f"String({repr(node.value.value)})"
                elif isinstance(node.value, ast.Name) and self.var_types.get(node.value.id) == "_PyStr":
                    self.var_types.setdefault(var_name, "String")
                    expr_code = f"{node.value.id}.to_string()"
                else:
                    if isinstance(node.value, ast.Constant):
                        if isinstance(node.value.value, bool):
                            self.var_types.setdefault(var_name, "Bool")
                        elif isinstance(node.value.value, int):
                            self.var_types.setdefault(var_name, "Int")
                        elif isinstance(node.value.value, float):
                            self.var_types.setdefault(var_name, "Float64")
                    expr_code = self.visit_expr(node.value)

                if not is_declared:
                    self.scopes[-1].add(var_name)
                    return f"{self.indent()}var {var_name}{inferred_annot} = {expr_code}"
                else:
                    return f"{self.indent()}{var_name} = {expr_code}"
            else:
                raise ASTTranspileError(f"Unsupported assignment target: {type(target).__name__}")

        elif isinstance(node, ast.AugAssign):
            op_helper_map = {
                ast.Add: "_checked_add",
                ast.Sub: "_checked_sub",
                ast.Mult: "_checked_mul",
                ast.Div: "_checked_div",
                ast.FloorDiv: "_checked_floordiv",
                ast.Mod: "_checked_mod",
                ast.Pow: "_checked_pow",
                ast.LShift: "_checked_lshift",
                ast.RShift: "_checked_rshift",
            }
            if isinstance(node.target, ast.Subscript):
                if not isinstance(node.target.value, ast.Name):
                    raise ASTTranspileError("Augmented subscript target must be a variable")
                if isinstance(node.target.slice, ast.Slice):
                    raise ASTTranspileError("Slice augmented assignment is not supported")
                arr_name = node.target.value.id
                arr_type = self.var_types.get(arr_name)
                idx_code = self.visit_expr(node.target.slice)
                val_code = self.visit_expr(node.value)
                len_expr = f"len({arr_name})"
                tmp_idx = self._next_tmp("_hot_idx")
                index_helper = "_checked_list_index" if self._is_python_list(node.target.value) else "_checked_index"
                lines = [f"{self.indent()}var {tmp_idx} = {index_helper}({idx_code}, {len_expr})"]
                target_elem = f"{arr_name}[{tmp_idx}]"
                helper = next((h for cls, h in op_helper_map.items() if isinstance(node.op, cls)), None)
                if helper and arr_type in ("List[Int]", "List[Float64]"):
                    lines.append(f"{self.indent()}{target_elem} = {helper}({target_elem}, {val_code})")
                else:
                    op = self.visit_op(node.op)
                    lines.append(f"{self.indent()}{target_elem} {op}= {val_code}")
                return "\n".join(lines)

            if not isinstance(node.target, ast.Name):
                raise ASTTranspileError("Only variable or subscript augmented assignments are supported")
            var_name = node.target.id
            if self.var_types.get(var_name) == "String" and isinstance(node.op, ast.Add):
                if (
                    isinstance(node.value, ast.Subscript)
                    and isinstance(node.value.value, ast.Name)
                    and self.var_types.get(node.value.value.id) == "_PyStr"
                    and not isinstance(node.value.slice, ast.Slice)
                ):
                    src_name = node.value.value.id
                    idx_expr = self.visit_expr(node.value.slice)
                    return f"{self.indent()}{var_name}.write({src_name}.get_cp({idx_expr}))"
                expr_code = self.visit_expr(node.value)
                return f"{self.indent()}{var_name}.write({expr_code})"

            expr_code = self.visit_expr(node.value)
            helper = next((h for cls, h in op_helper_map.items() if isinstance(node.op, cls)), None)
            if helper:
                return f"{self.indent()}{var_name} = {helper}({var_name}, {expr_code})"
            op = self.visit_op(node.op)
            return f"{self.indent()}{var_name} {op}= {expr_code}"

        elif isinstance(node, ast.If):
            test_code = self._emit_cond_expr(node.test)
            lines = [f"{self.indent()}if {test_code}:"]
            self.indent_level += 1
            self.scopes.append(set())
            for s in node.body:
                lines.append(self.visit_stmt(s))
            self.scopes.pop()
            self.indent_level -= 1
            curr_orelse = node.orelse
            while curr_orelse:
                if len(curr_orelse) == 1 and isinstance(curr_orelse[0], ast.If):
                    elif_stmt = curr_orelse[0]
                    lines.append(f"{self.indent()}elif {self._emit_cond_expr(elif_stmt.test)}:")
                    self.indent_level += 1
                    self.scopes.append(set())
                    for s in elif_stmt.body:
                        lines.append(self.visit_stmt(s))
                    self.scopes.pop()
                    self.indent_level -= 1
                    curr_orelse = elif_stmt.orelse
                else:
                    lines.append(f"{self.indent()}else:")
                    self.indent_level += 1
                    self.scopes.append(set())
                    for s in curr_orelse:
                        lines.append(self.visit_stmt(s))
                    self.scopes.pop()
                    self.indent_level -= 1
                    break
            return "\n".join(lines)

        elif isinstance(node, ast.For):
            if not isinstance(node.target, ast.Name):
                raise ASTTranspileError("Only simple variable loop targets are supported")
            var_name = node.target.id
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                range_args = [self.visit_expr(a) for a in node.iter.args]
                iter_code = f"range({', '.join(range_args)})"
                loop_var_type = "Int"

            else:
                iter_expr = self.visit_expr(node.iter)
                iter_t = self.var_types.get(iter_expr)
                if iter_t in ("String", "_PyStr"):
                    iter_code = f"{iter_expr}.codepoints()"
                    loop_var_type = "Codepoint"
                else:
                    iter_code = iter_expr
                    elem_t_map = {
                        "List[Int]": "Int",
                        "List[Float64]": "Float64",
                        "List[Bool]": "Bool",
                        "List[String]": "String",
                    }
                    loop_var_type = elem_t_map.get(iter_t or "", "")

            lines = []
            lines.append(f"{self.indent()}for {var_name} in {iter_code}:")
            self.indent_level += 1
            self.scopes.append({var_name})
            prev_t = self.var_types.get(var_name)
            if loop_var_type:
                self.var_types[var_name] = loop_var_type
            for s in node.body:
                lines.append(self.visit_stmt(s))
            if prev_t is not None:
                self.var_types[var_name] = prev_t
            else:
                self.var_types.pop(var_name, None)
            self.scopes.pop()
            self.indent_level -= 1
            return "\n".join(lines)

        elif isinstance(node, ast.While):
            lines = []
            test_code = self._emit_cond_expr(node.test)
            lines.append(f"{self.indent()}while {test_code}:")
            self.indent_level += 1
            self.scopes.append(set())
            for s in node.body:
                lines.append(self.visit_stmt(s))
            self.scopes.pop()
            self.indent_level -= 1
            return "\n".join(lines)

        elif isinstance(node, ast.Pass):
            return f"{self.indent()}pass"

        elif isinstance(node, ast.Break):
            return f"{self.indent()}break"

        elif isinstance(node, ast.Continue):
            return f"{self.indent()}continue"

        elif isinstance(node, ast.Expr):
            expr_code = self.visit_expr(node.value)
            return f"{self.indent()}{expr_code}"

        else:
            raise ASTTranspileError(f"Unsupported statement type: {type(node).__name__}")

    def visit_expr(self, node: ast.expr) -> str:
        if not isinstance(node, ast.Constant):
            c_val = _eval_constant_expr(node)
            if c_val is not None:
                if isinstance(c_val, bool):
                    return "True" if c_val else "False"
                return repr(c_val)

        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "True" if node.value else "False"
            elif isinstance(node.value, (int, float)):
                return repr(node.value)
            elif isinstance(node.value, str):
                return repr(node.value)
            else:
                raise ASTTranspileError(f"Unsupported constant type: {type(node.value).__name__}")

        elif isinstance(node, ast.Name):
            return node.id

        elif isinstance(node, ast.Subscript):
            val = self.visit_expr(node.value)
            val_type = self.var_types.get(node.value.id) if isinstance(node.value, ast.Name) else None
            if val_type == "_PyStr":
                if isinstance(node.slice, ast.Slice):
                    return self._emit_slice_expr(val, node.slice, as_method=True)
                idx = self.visit_expr(node.slice)
                return f"{val}[{idx}]"
            elif val_type == "String":
                if isinstance(node.slice, ast.Slice):
                    return self._emit_slice_expr(val, node.slice, as_method=False)
                idx = self.visit_expr(node.slice)
                return f"_str_get({val}, {idx})"
            else:
                if isinstance(node.slice, ast.Slice):
                    raise ASTTranspileError("List slicing is not supported in native AST compilation")
                idx = self.visit_expr(node.slice)

                helper = "_checked_index"
                if self._is_python_list(node.value):
                    helper = ("_checked_list_assignment_index" if isinstance(node.ctx, ast.Store)
                              else "_checked_list_index")
                return f"{val}[{helper}({idx}, len({val}))]"

        elif isinstance(node, ast.List):
            if len(node.elts) == 0:
                return f"{self.ret_mojo_type}()"
            elts = [self.visit_expr(e) for e in node.elts]
            return f"[{', '.join(elts)}]"

        elif isinstance(node, ast.BinOp):
            left = self.visit_expr(node.left)
            right = self.visit_expr(node.right)
            if isinstance(node.op, ast.Add):
                return f"_checked_add({left}, {right})"
            elif isinstance(node.op, ast.Sub):
                return f"_checked_sub({left}, {right})"
            elif isinstance(node.op, ast.Mult):
                return f"_checked_mul({left}, {right})"
            elif isinstance(node.op, ast.Div):
                return f"_checked_div({left}, {right})"
            elif isinstance(node.op, ast.FloorDiv):
                return f"_checked_floordiv({left}, {right})"
            elif isinstance(node.op, ast.Mod):
                return f"_checked_mod({left}, {right})"
            elif isinstance(node.op, ast.Pow):
                return f"_checked_pow({left}, {right})"
            elif isinstance(node.op, ast.LShift):
                return f"_checked_lshift({left}, {right})"
            elif isinstance(node.op, ast.RShift):
                return f"_checked_rshift({left}, {right})"
            elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor)):
                op = self.visit_op(node.op)
                return f"({left} {op} {right})"
            else:
                op = self.visit_op(node.op)
                return f"({left} {op} {right})"

        elif isinstance(node, ast.UnaryOp):
            operand = self.visit_expr(node.operand)
            if isinstance(node.op, ast.Not):
                return f"(not {self._emit_cond_expr(node.operand)})"
            elif isinstance(node.op, ast.USub):
                return f"_checked_neg({operand})"
            elif isinstance(node.op, ast.UAdd):
                return f"(+{operand})"
            elif isinstance(node.op, ast.Invert):
                return f"(~{operand})"
            else:
                raise ASTTranspileError(f"Unsupported unary operator: {type(node.op).__name__}")

        elif isinstance(node, ast.Compare):
            def _is_pystr_sub(n: ast.expr) -> bool:
                return (
                    isinstance(n, ast.Subscript)
                    and isinstance(n.value, ast.Name)
                    and self.var_types.get(n.value.id) == "_PyStr"
                    and not isinstance(n.slice, ast.Slice)
                )

            def _is_cp_var(n: ast.expr) -> bool:
                return isinstance(n, ast.Name) and self.var_types.get(n.id) == "Codepoint"

            def _is_single_char_const(n: ast.expr) -> bool:
                return isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) == 1

            all_items = [node.left] + list(node.comparators)
            has_char_subj = any(_is_pystr_sub(x) or _is_cp_var(x) for x in all_items)
            all_char_compat = all(_is_pystr_sub(x) or _is_cp_var(x) or _is_single_char_const(x) for x in all_items)

            if has_char_subj and all_char_compat:
                def _as_ord(n: ast.expr) -> str:
                    if _is_pystr_sub(n):
                        vname = n.value.id  # type: ignore[attr-defined]
                        return f"{vname}.get_ord({self.visit_expr(n.slice)})"  # type: ignore[attr-defined]
                    if _is_cp_var(n):
                        return f"Int({self.visit_expr(n)})"
                    return str(ord(n.value))  # type: ignore[attr-defined]

                parts = [_as_ord(node.left)]
                for op, comparator in zip(node.ops, node.comparators):
                    parts.append(f"{self.visit_cmp_op(op)} {_as_ord(comparator)}")
                return f"({' '.join(parts)})"

            if len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq)):
                def _match_pystr_slice_lit(a: ast.expr, b: ast.expr) -> Optional[str]:
                    if (
                        isinstance(a, ast.Subscript)
                        and isinstance(a.value, ast.Name)
                        and self.var_types.get(a.value.id) == "_PyStr"
                        and isinstance(a.slice, ast.Slice)
                        and a.slice.step is None
                        and isinstance(b, ast.Constant)
                        and isinstance(b.value, str)
                    ):
                        vname = a.value.id
                        s_c = self.visit_expr(a.slice.lower) if a.slice.lower else "0"
                        e_c = self.visit_expr(a.slice.upper) if a.slice.upper else f"_len({vname})"
                        eq_expr = f"{vname}.eq_slice({s_c}, {e_c}, String({repr(b.value)}))"
                        return f"(not {eq_expr})" if isinstance(node.ops[0], ast.NotEq) else eq_expr
                    return None

                sl_opt = _match_pystr_slice_lit(node.left, node.comparators[0]) or _match_pystr_slice_lit(node.comparators[0], node.left)
                if sl_opt is not None:
                    return sl_opt

            def _cmp_expr(n: ast.expr) -> str:
                if isinstance(n, ast.Name) and self.var_types.get(n.id) == "_PyStr":
                    return f"{n.id}.to_string()"
                return self.visit_expr(n)

            parts = [_cmp_expr(node.left)]
            for op, comparator in zip(node.ops, node.comparators):
                parts.append(f"{self.visit_cmp_op(op)} {_cmp_expr(comparator)}")
            return f"({' '.join(parts)})"

        elif isinstance(node, ast.BoolOp):
            op = "and" if isinstance(node.op, ast.And) else "or"
            values = [self._emit_cond_expr(v) for v in node.values]
            return f"({(' ' + op + ' ').join(values)})"

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fn_name = node.func.id
                args = [self.visit_expr(a) for a in node.args]
                if fn_name == "len":
                    return f"_len({', '.join(args)})"
                elif fn_name == "ord":
                    if len(node.args) != 1:
                        raise ASTTranspileError("ord() expects exactly 1 argument")
                    a0 = node.args[0]
                    if (
                        isinstance(a0, ast.Subscript)
                        and isinstance(a0.value, ast.Name)
                        and self.var_types.get(a0.value.id) == "_PyStr"
                        and not isinstance(a0.slice, ast.Slice)
                    ):
                        return f"{a0.value.id}.get_ord({self.visit_expr(a0.slice)})"
                    if isinstance(a0, ast.Constant) and isinstance(a0.value, str) and len(a0.value) == 1:
                        return str(ord(a0.value))
                    if isinstance(a0, ast.Name) and self.var_types.get(a0.id) == "Codepoint":
                        return f"Int({args[0]})"
                    return f"_py_ord({args[0]})"
                elif fn_name == "chr":
                    return f"_py_chr({', '.join(args)})"
                elif fn_name == "abs":
                    return f"_checked_abs({', '.join(args)})"
                elif fn_name == "bool":
                    return f"_py_bool({', '.join(args)})"
                elif fn_name == "str":
                    if len(node.args) == 1 and isinstance(node.args[0], ast.Name) and self.var_types.get(node.args[0].id) == "_PyStr":
                        return f"{args[0]}.to_string()"
                    return f"String({', '.join(args)})"
                elif fn_name in ("min", "max", "int", "float"):
                    if fn_name == "int":
                        return f"Int({', '.join(args)})"
                    if fn_name == "float":
                        return f"Float64({', '.join(args)})"
                    return f"{fn_name}({', '.join(args)})"
                elif fn_name == "range":
                    return f"range({', '.join(args)})"
                elif fn_name in self.known_funcs:
                    conv_args = [
                        f"{a_str}.to_string()" if isinstance(a_node, ast.Name) and self.var_types.get(a_node.id) == "_PyStr" else a_str
                        for a_node, a_str in zip(node.args, args)
                    ]
                    return f"_native_{fn_name}({', '.join(conv_args)})"
                else:
                    return f"{fn_name}({', '.join(args)})"
            elif isinstance(node.func, ast.Attribute):
                if node.func.attr == "append":
                    obj = self.visit_expr(node.func.value)
                    arg = self.visit_expr(node.args[0])
                    return f"{obj}.append({arg})"
                elif node.func.attr == "clear":
                    obj = self.visit_expr(node.func.value)
                    return f"{obj}.clear()"
                elif node.func.attr == "write":
                    obj = self.visit_expr(node.func.value)
                    arg = self.visit_expr(node.args[0])
                    return f"{obj}.write({arg})"
                elif node.func.attr in ("startswith", "endswith"):
                    if len(node.args) < 1 or len(node.args) > 3:
                        raise ASTTranspileError(f"{node.func.attr}() expects 1 to 3 arguments")
                    obj = self.visit_expr(node.func.value)
                    # Support tuple of prefixes/suffixes: line.startswith(('a', 'b'))
                    if isinstance(node.args[0], ast.Tuple):
                        tuple_elts = node.args[0].elts
                        if not tuple_elts:
                            return "False"
                        rest_args = [self.visit_expr(a) for a in node.args[1:]]
                        rest_suffix = (", " + ", ".join(rest_args)) if rest_args else ""
                        disjuncts = []
                        for elt in tuple_elts:
                            elt_expr = self.visit_expr(elt)
                            elt_type = self.var_types.get(elt.id) if isinstance(elt, ast.Name) else None
                            if elt_type == "_PyStr":
                                elt_expr = f"{elt_expr}.to_string()"
                            disjuncts.append(f"{obj}.{node.func.attr}({elt_expr}{rest_suffix})")
                        return f"({' or '.join(disjuncts)})"

                    arg_strs = []
                    for a in node.args:
                        a_expr = self.visit_expr(a)
                        a_type = self.var_types.get(a.id) if isinstance(a, ast.Name) else None
                        if a_type == "_PyStr":
                            a_expr = f"{a_expr}.to_string()"
                        arg_strs.append(a_expr)
                    return f"{obj}.{node.func.attr}({', '.join(arg_strs)})"
                elif isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
                    if not _return_origin.native_math_call(node):
                        return "_unqualified_math()"
                    fn_name = node.func.attr
                    args = [f"_math_operand({self.visit_expr(a)})" for a in node.args]
                    helper = "_checked_sqrt" if fn_name == "sqrt" else f"_checked_math_{fn_name}"
                    return f"{helper}({', '.join(args)})"
                else:
                    raise ASTTranspileError(f"Unsupported method call: {ast.dump(node.func)}")
            else:
                raise ASTTranspileError(f"Unsupported function call expression: {type(node.func).__name__}")

        elif isinstance(node, ast.Attribute):
            val = self.visit_expr(node.value)
            return f"{val}.{node.attr}"

        else:
            raise ASTTranspileError(f"Unsupported expression type: {type(node).__name__}")

    def visit_op(self, op: ast.operator) -> str:
        op_map = {
            ast.Add: "+",
            ast.Sub: "-",
            ast.Mult: "*",
            ast.Div: "/",
            ast.FloorDiv: "//",
            ast.Mod: "%",
            ast.Pow: "**",
            ast.BitAnd: "&",
            ast.BitOr: "|",
            ast.BitXor: "^",
            ast.LShift: "<<",
            ast.RShift: ">>",
        }
        for cls, sym in op_map.items():
            if isinstance(op, cls):
                return sym
        raise ASTTranspileError(f"Unsupported binary operator: {type(op).__name__}")

    def visit_cmp_op(self, op: ast.cmpop) -> str:
        cmp_map = {
            ast.Eq: "==",
            ast.NotEq: "!=",
            ast.Lt: "<",
            ast.LtE: "<=",
            ast.Gt: ">",
            ast.GtE: ">=",
        }
        for cls, sym in cmp_map.items():
            if isinstance(op, cls):
                return sym
        raise ASTTranspileError(f"Unsupported comparison operator: {type(op).__name__}")

def transpile_python_to_mojo(source_code: str, mod_name: str) -> str:
    """Parses Python source, finds ALL @hotloop functions and helpers, and transpiles them into a unified Mojo module."""
    tree = ast.parse(source_code)
    hotloop_nodes = []
    helper_nodes = []
    all_func_names = set()

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            all_func_names.add(node.name)
            is_hotloop = any(
                (isinstance(d, ast.Name) and d.id == "hotloop") or
                (isinstance(d, ast.Attribute) and d.attr == "hotloop") or
                (isinstance(d, ast.Call) and (
                    (isinstance(d.func, ast.Name) and d.func.id == "hotloop") or
                    (isinstance(d.func, ast.Attribute) and d.func.attr == "hotloop")
                ))
                for d in node.decorator_list
            )
            if is_hotloop:
                hotloop_nodes.append(node)
            else:
                helper_nodes.append(node)

    # If no explicit @hotloop decorator, default to all functions if only 1 exists
    target_nodes = hotloop_nodes if hotloop_nodes else (helper_nodes if len(helper_nodes) == 1 else [])
    if not target_nodes:
        raise ASTTranspileError("No @hotloop-decorated function found in source file.")

    if not hotloop_nodes and len(helper_nodes) == 1:
        helper_nodes = []

    # Withhold an entry if copying its list arguments can change Python behavior.
    # Propagate the restriction to native callers before generating any wrappers.
    restricted = set()
    calls = {}
    for node in (*helper_nodes, *target_nodes):
        calls[node.name] = {call.func.id for call in ast.walk(node)
                            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)}
        for arg in node.args.args:
            if arg.annotation and parse_type_annotation(arg.annotation)[2] is not None:
                if not _borrowed_list_is_read_only(node, arg.arg):
                    restricted.add(node.name)
        if any(isinstance(item, (ast.For, ast.While)) and item.orelse for item in ast.walk(node)):
            restricted.add(node.name)
    while callers := {name for name, targets in calls.items() if targets & restricted} - restricted:
        restricted.update(callers)

    try:
        layout = _provenance.Layout(source_code,[*helper_nodes,*target_nodes])
    except (ValueError,TypeError) as exc:
        raise ASTTranspileError(f"Unproven Python code mapping: {exc}") from exc
    return_origins = _return_origin.analyze([*helper_nodes, *target_nodes],layout)
    # An unproven helper must not be reached through an otherwise fresh return.
    # Its native value may also differ (for example Python's operand-selecting or).
    for name, plan in return_origins.items():
        pending=list(calls[name])
        visited=set()
        while pending:
            callee=pending.pop()
            if callee==name:
                plan.reason="Python recursion semantics require Python"
                break
            if callee not in visited:
                visited.add(callee)
                pending.extend(calls.get(callee,()))
    unproven = {name for name, plan in return_origins.items() if plan.reason}
    while callers := {name for name, targets in calls.items() if targets & unproven} - unproven:
        for name in callers:
            return_origins[name].reason = "callee return semantics are unproven"
        unproven.update(callers)
    transpiler = MojoASTTranspiler(mod_name, known_funcs=all_func_names, return_origins=return_origins)
    export_regs = []
    wrappers = []
    native_funcs = []

    # First, transpile unexported helper functions as native functions
    for node in helper_nodes:
        _, _, nat = transpiler.transpile_function_components(node)
        if node.name not in restricted:
            native_funcs.append(nat)

    # Next, transpile @hotloop target functions with C-ABI wrappers and module export
    for node in target_nodes:
        reg, wrap, nat = transpiler.transpile_function_components(node)
        if node.name in restricted:
            continue
        export_regs.append(reg)
        wrappers.append(wrap)
        native_funcs.append(nat)

    if "_hotloop_provenance_v1" in all_func_names:
        raise ASTTranspileError("Function name is reserved for private provenance metadata")
    export_regs.append('        m.def_function[_hotloop_context_spec_impl]("_hotloop_provenance_v1")')
    spec_literal = repr(json.dumps(layout.spec(),sort_keys=True,separators=(",",":")))
    wrappers.append(f"def _hotloop_context_spec_impl() raises -> PythonObject:\n    return PythonObject(String({spec_literal}))")
    export_block = "\n".join(export_regs)
    wrappers_block = "\n\n".join(wrappers)
    native_block = "\n\n".join(native_funcs)

    mojo_source = f"""from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.collections import List
from std.os import abort
import std.math as math

{CHECKED_HELPERS_MOJO}

# Python-only entries: {", ".join(sorted(restricted))}
@export
def PyInit_{mod_name}() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("{mod_name}")
{export_block}
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

{wrappers_block}

{native_block}
"""
    return mojo_source
