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
        elif t_id in ("list", "List"):
            raise ASTTranspileError("Generic list must have element type, e.g. list[float] or list[int]")
        else:
            raise ASTTranspileError(f"Unsupported type '{t_id}'. Supported: int, float, bool, str, list[int], list[float]")

    elif isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Name) and node.value.id in ("list", "List"):
            elem_node = node.slice
            if isinstance(elem_node, ast.Name):
                elem_id = elem_node.id
                if elem_id == "int":
                    return "list[int]", "List[Int]", "int"
                elif elem_id == "float":
                    return "list[float]", "List[Float64]", "float"
                elif elem_id == "bool":
                    return "list[bool]", "List[Bool]", "bool"
                elif elem_id == "str":
                    return "list[str]", "List[String]", "str"
                else:
                    raise ASTTranspileError(f"Unsupported list element type '{elem_id}'. Supported: int, float, bool, str")
            else:
                raise ASTTranspileError(f"Unsupported complex list element type: {ast.dump(elem_node)}")
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


def _is_ptr_safe_arg(func_def: ast.FunctionDef, arg_name: str) -> bool:
    """Returns True iff every occurrence of arg_name in func_def.body is len(arg) or read arg[idx]."""
    parent_map: Dict[int, ast.AST] = {}
    for parent in ast.walk(func_def):
        for child in ast.iter_child_nodes(parent):
            parent_map[id(child)] = parent

    body_nodes = ast.Module(body=func_def.body, type_ignores=[])
    for node in ast.walk(body_nodes):
        if isinstance(node, ast.Name) and node.id == arg_name:
            parent = parent_map.get(id(node))
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


class MojoASTTranspiler:
    def __init__(self, mod_name: str, known_funcs: Optional[Set[str]] = None):
        self.mod_name = mod_name
        self.known_funcs: Set[str] = known_funcs or set()
        self.indent_level = 0
        self.scopes: List[Set[str]] = [set()]
        self.var_types: Dict[str, str] = {}
        self.has_math = False
        self.ret_mojo_type: str = "Int"
        self.ret_elem_type: Optional[str] = None
        self.active_ptr_lens: Dict[str, str] = {}
        self.codepoint_vars: Set[str] = set()
        self.loop_inbounds: List[Dict[str, dict]] = []
        self.length_aliases: Dict[str, Set[str]] = {}
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
        ptr_coll_names: Dict[str, str],
    ) -> Tuple[List[str], str]:
        self.scopes = [set()]
        self.var_types.clear()
        self.active_ptr_lens = dict(ptr_coll_names)
        self.loop_inbounds = []
        self.length_aliases = {}
        for name in ptr_coll_names:
            self.length_aliases.setdefault(f"_n_{name}", set()).add(name)

        for stmt in ast.walk(func_def):
            if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                t_name = stmt.targets[0].id
                if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "len":
                    if len(stmt.value.args) == 1 and isinstance(stmt.value.args[0], ast.Name):
                        self.length_aliases.setdefault(t_name, set()).add(stmt.value.args[0].id)
                elif isinstance(stmt.value, ast.Name) and stmt.value.id in self.length_aliases:
                    self.length_aliases.setdefault(t_name, set()).update(self.length_aliases[stmt.value.id])
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                t_name = stmt.target.id
                if stmt.value and isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name) and stmt.value.func.id == "len":
                    if len(stmt.value.args) == 1 and isinstance(stmt.value.args[0], ast.Name):
                        self.length_aliases.setdefault(t_name, set()).add(stmt.value.args[0].id)
                elif stmt.value and isinstance(stmt.value, ast.Name) and stmt.value.id in self.length_aliases:
                    self.length_aliases.setdefault(t_name, set()).update(self.length_aliases[stmt.value.id])

        for node in ast.walk(func_def):
            if isinstance(node, ast.Compare):
                for op, comp in zip(node.ops, node.comparators):
                    if isinstance(op, (ast.Eq, ast.NotEq)):
                        for a, b in [(node.left, comp), (comp, node.left)]:
                            if isinstance(a, ast.Call) and isinstance(a.func, ast.Name) and a.func.id == "len":
                                if len(a.args) == 1 and isinstance(a.args[0], ast.Name) and isinstance(b, ast.Name):
                                    if b.id in self.length_aliases:
                                        self.length_aliases[b.id].add(a.args[0].id)
        pystr_arg_names = {
            name for name, _, mojo_type, _ in args
            if name in subscripted_args and mojo_type == "String"
        }
        self.codepoint_vars = _collect_codepoint_vars(func_def, pystr_arg_names)
        self._tmp_counter = 0

        sig_args: List[str] = []
        body_prep: List[str] = []

        for name, py_type, mojo_type, elem_type in args:
            self.scopes[0].add(name)
            self.var_types[name] = mojo_type
            if name in ptr_coll_names:
                inner_m = "Float64" if elem_type == "float" else "Int"
                sig_args.append(f"{name}_ptr: OpaquePointer[MutUntrackedOrigin]")
                sig_args.append(f"_n_{name}: Int")
                body_prep.append(f"    var {name} = {name}_ptr.unsafe_bitcast[{inner_m}]()")
            elif name in subscripted_args and mojo_type == "String":
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

        self.indent_level = 1
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
        native_args, body_code = self._transpile_body(func_def, args, subscripted_args, reassigned_vars, {})

        # 4. Identify pointer-eligible read-only numeric array arguments
        safe_coll_args = [
            (name, py_type, mojo_type, elem_type, i)
            for i, (name, py_type, mojo_type, elem_type) in enumerate(args)
            if elem_type in ("float", "int") and _is_ptr_safe_arg(func_def, name)
        ]

        ptr_native_code = ""
        safe_ptr_names = {name: f"_n_{name}" for name, _, _, _, _ in safe_coll_args}
        if safe_coll_args:
            ptr_args_def, ptr_body_code = self._transpile_body(
                func_def, args, subscripted_args, reassigned_vars, safe_ptr_names
            )
            ptr_native_code = f"""@always_inline\ndef _ptr_{func_def.name}({", ".join(ptr_args_def)}) raises -> {ret_mojo_type}:\n{ptr_body_code}"""

        # 5. Generate C-ABI wrapper
        wrapper_args_def = ", ".join([f"arg{i}: PythonObject" for i in range(len(args))])

        def _build_list_unbox(idx: int, name: str, mojo_type: str, elem_type: str, indent: str) -> str:
            inner_mojo = "Float64" if elem_type == "float" else ("Int" if elem_type == "int" else ("String" if elem_type == "str" else "Bool"))
            return (
                f"{indent}var _n_{name} = Int(py=arg{idx}.__len__())\n"
                f"{indent}var {name} = {mojo_type}(capacity=_n_{name})\n"
                f"{indent}for _i in range(_n_{name}):\n"
                f"{indent}    {name}.append({inner_mojo}(py=arg{idx}[_i]))"
            )

        wrapper_conversions = []
        call_args = []
        for i, (name, py_type, mojo_type, elem_type) in enumerate(args):
            if elem_type is not None:
                wrapper_conversions.append(_build_list_unbox(i, name, mojo_type, elem_type, "    "))
            else:
                wrapper_conversions.append(f"    var {name} = {mojo_type}(py=arg{i})")
            call_args.append(name)

        call_block = self._box_return_block(f"_native_{func_def.name}({', '.join(call_args)})", "    ", has_builtins=False)

        if safe_coll_args:
            dtype_checks = []
            for name, _, _, elem_type, i in safe_coll_args:
                expected_dtype = "float64" if elem_type == "float" else "int64"
                dtype_checks.append(
                    f'    if _has_ctypes:\n'
                    f'        if not (Bool(py=_builtins.hasattr(arg{i}, "ctypes")) and Bool(py=_builtins.hasattr(arg{i}, "ndim")) and Bool(py=_builtins.hasattr(arg{i}, "dtype")) and Bool(py=_builtins.hasattr(arg{i}, "flags"))):\n'
                    f'            _has_ctypes = False\n'
                    f'        elif Int(py=arg{i}.ndim) != 1 or String(py=arg{i}.dtype.name) != "{expected_dtype}" or not Bool(py=arg{i}.flags.c_contiguous):\n'
                    f'            _has_ctypes = False'
                )
            checks_block = "\n".join(dtype_checks)

            ptr_prep_lines = []
            ptr_calls = []
            for i, (name, py_type, mojo_type, elem_type) in enumerate(args):
                if name in safe_ptr_names:
                    ptr_prep_lines.append(f"        var _n_{name} = Int(py=arg{i}.__len__())")
                    ptr_prep_lines.append(f"        var _{name}_addr = Int(py=arg{i}.ctypes.data)")
                    ptr_prep_lines.append(f"        var _{name}_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_{name}_addr)")
                    ptr_calls.append(f"_{name}_op")
                    ptr_calls.append(f"_n_{name}")
                elif elem_type is not None:
                    ptr_prep_lines.append(_build_list_unbox(i, f"_p_{name}", mojo_type, elem_type, "        "))
                    ptr_calls.append(f"_p_{name}")
                else:
                    ptr_calls.append(f"{mojo_type}(py=arg{i})")

            ptr_prep_block = "\n".join(ptr_prep_lines)
            ptr_call_block = self._box_return_block(f"_ptr_{func_def.name}({', '.join(ptr_calls)})", "        ", has_builtins=True)

            conv_block_8 = "\n".join(["    " + l if l.strip() else "" for l in "\n".join(wrapper_conversions).splitlines()])
            else_call_block = self._box_return_block(f"_native_{func_def.name}({', '.join(call_args)})", "        ", has_builtins=True)

            wrapper_code = f"""def _pywrap_{func_def.name}({wrapper_args_def}) raises -> PythonObject:
    var _builtins = Python.import_module("builtins")
    var _has_ctypes = True
{checks_block}
    if _has_ctypes:
{ptr_prep_block}
{ptr_call_block}
    else:
{conv_block_8}
{else_call_block}"""
        else:
            conv_block_4 = "\n".join(wrapper_conversions)
            wrapper_code = f"""def _pywrap_{func_def.name}({wrapper_args_def}) raises -> PythonObject:
{conv_block_4}
{call_block}"""

        native_code = f"""def _native_{func_def.name}({", ".join(native_args)}) raises -> {ret_mojo_type}:
{body_code}"""
        if ptr_native_code:
            native_code = f"{ptr_native_code}\n\n{native_code}"

        export_reg = f'        m.def_function[_pywrap_{func_def.name}]("{func_def.name}")'

        return export_reg, wrapper_code, native_code

    def visit_stmt(self, node: ast.stmt) -> str:
        if isinstance(node, ast.Return):
            if node.value is None:
                return f"{self.indent()}return"
            if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                return f"{self.indent()}return {self.ret_mojo_type}()"
            val = self.visit_expr(node.value)
            if self.ret_mojo_type == "String" and isinstance(node.value, ast.Name) and self.var_types.get(node.value.id) == "_PyStr":
                return f"{self.indent()}return {val}.to_string()"
            if (self.ret_elem_type is not None or self.ret_mojo_type == "String") and isinstance(node.value, ast.Name):
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
                expr_code = "String()"
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
                        expr_code = "String()"
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
                len_expr = self.active_ptr_lens.get(arr_name, f"len({arr_name})")
                tmp_idx = self._next_tmp("_hot_idx")
                lines = [f"{self.indent()}var {tmp_idx} = _checked_index({idx_code}, {len_expr})"]
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

            inbounds_entry = None
            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                range_args = [self.visit_expr(a) for a in node.iter.args]
                iter_code = f"range({', '.join(range_args)})"
                loop_var_type = "Int"

                lower = 0
                upper_node = None
                if len(node.iter.args) == 1:
                    lower = 0
                    upper_node = node.iter.args[0]
                elif len(node.iter.args) == 2:
                    if isinstance(node.iter.args[0], ast.Constant) and isinstance(node.iter.args[0].value, int):
                        lower = node.iter.args[0].value
                        upper_node = node.iter.args[1]

                if upper_node is not None:
                    upper_arrays = set()
                    if isinstance(upper_node, ast.Call) and isinstance(upper_node.func, ast.Name) and upper_node.func.id == "len":
                        if len(upper_node.args) == 1 and isinstance(upper_node.args[0], ast.Name):
                            upper_arrays.add(upper_node.args[0].id)
                    elif isinstance(upper_node, ast.Name):
                        if upper_node.id in self.length_aliases:
                            upper_arrays.update(self.length_aliases[upper_node.id])
                        if upper_node.id.startswith("_n_") and upper_node.id[3:] in self.active_ptr_lens:
                            upper_arrays.add(upper_node.id[3:])
                    if upper_arrays:
                        inbounds_entry = (var_name, {"arrays": upper_arrays, "lower": lower})
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

            lines = [f"{self.indent()}for {var_name} in {iter_code}:"]
            self.indent_level += 1
            self.scopes.append({var_name})
            prev_t = self.var_types.get(var_name)
            if loop_var_type:
                self.var_types[var_name] = loop_var_type
            if inbounds_entry:
                self.loop_inbounds.append({inbounds_entry[0]: inbounds_entry[1]})
            for s in node.body:
                lines.append(self.visit_stmt(s))
            if inbounds_entry:
                self.loop_inbounds.pop()
            if prev_t is not None:
                self.var_types[var_name] = prev_t
            else:
                self.var_types.pop(var_name, None)
            self.scopes.pop()
            self.indent_level -= 1
            return "\n".join(lines)

        elif isinstance(node, ast.While):
            test_code = self._emit_cond_expr(node.test)
            lines = [f"{self.indent()}while {test_code}:"]
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

                # Check for proven inbounds loop variable access
                is_proven = False
                if isinstance(node.value, ast.Name):
                    arr_name = node.value.id
                    for frame in reversed(self.loop_inbounds):
                        for lvar, info in frame.items():
                            if arr_name in info["arrays"]:
                                if isinstance(node.slice, ast.Name) and node.slice.id == lvar and info["lower"] >= 0:
                                    is_proven = True
                                    break
                                elif (
                                    isinstance(node.slice, ast.BinOp)
                                    and isinstance(node.slice.op, ast.Sub)
                                    and isinstance(node.slice.left, ast.Name)
                                    and node.slice.left.id == lvar
                                    and isinstance(node.slice.right, ast.Constant)
                                    and node.slice.right.value == 1
                                    and info["lower"] >= 1
                                ):
                                    is_proven = True
                                    break
                        if is_proven:
                            break

                if is_proven:
                    if isinstance(node.value, ast.Name) and node.value.id in self.active_ptr_lens:
                        return f"{val}[unsafe_offset={idx}]"
                    return f"{val}[{idx}]"

                if isinstance(node.value, ast.Name) and node.value.id in self.active_ptr_lens:
                    return f"{val}[unsafe_offset=_checked_index({idx}, {self.active_ptr_lens[node.value.id]})]"
                return f"{val}[_checked_index({idx}, len({val}))]"

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
                if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)) and node.right.value != 0:
                    left_type = self.var_types.get(node.left.id) if isinstance(node.left, ast.Name) else None
                    if left_type == "Float64":
                        return f"({left} / {right})"
                    return f"(Float64({left}) / Float64({right}))"
                return f"_checked_div({left}, {right})"
            elif isinstance(node.op, ast.FloorDiv):
                return f"_checked_floordiv({left}, {right})"
            elif isinstance(node.op, ast.Mod):
                return f"_checked_mod({left}, {right})"
            elif isinstance(node.op, ast.Pow):
                return f"_checked_pow({left}, {right})"
            elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)):
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
                    if (
                        len(node.args) == 1
                        and isinstance(node.args[0], ast.Name)
                        and node.args[0].id in self.active_ptr_lens
                    ):
                        return self.active_ptr_lens[node.args[0].id]
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
                elif isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
                    fn_name = node.func.attr
                    args = [self.visit_expr(a) for a in node.args]
                    return f"math.{fn_name}({', '.join(args)})"
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

    transpiler = MojoASTTranspiler(mod_name, known_funcs=all_func_names)
    export_regs = []
    wrappers = []
    native_funcs = []

    # First, transpile unexported helper functions as native functions
    for node in helper_nodes:
        _, _, nat = transpiler.transpile_function_components(node)
        native_funcs.append(nat)

    # Next, transpile @hotloop target functions with C-ABI wrappers and module export
    for node in target_nodes:
        reg, wrap, nat = transpiler.transpile_function_components(node)
        export_regs.append(reg)
        wrappers.append(wrap)
        native_funcs.append(nat)

    export_block = "\n".join(export_regs)
    wrappers_block = "\n\n".join(wrappers)
    native_block = "\n\n".join(native_funcs)

    mojo_source = f"""from std.python import Python, PythonObject
from std.python.bindings import PythonModuleBuilder
from std.collections import List
from std.memory import OpaquePointer
from std.os import abort
import std.math as math

{CHECKED_HELPERS_MOJO}

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
