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
"""

class ASTTranspileError(Exception):
    """Raised when an AST node cannot be deterministically transpiled to Mojo."""
    pass

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

    def indent(self) -> str:
        return "    " * self.indent_level

    def transpile_function_components(self, func_def: ast.FunctionDef) -> Tuple[str, str, str]:
        """
        Transpiles a single FunctionDef.
        Returns:
            export_registration: e.g. 'm.def_function[name]("name")'
            c_abi_wrapper: wrapper function callable from Python
            native_function: native compiled implementation
        """
        self.scopes = [set()]
        self.var_types.clear()

        # 1. Validate argument types
        args = []
        for arg in func_def.args.args:
            arg_name = arg.arg
            if not arg.annotation:
                raise ASTTranspileError(f"Argument '{arg_name}' must have explicit type annotation (e.g. int, float, list[float])")
            py_type, mojo_type, elem_type = parse_type_annotation(arg.annotation)
            args.append((arg_name, py_type, mojo_type, elem_type))
            self.scopes[0].add(arg_name)
            self.var_types[arg_name] = mojo_type

        # 2. Validate return type
        if not func_def.returns:
            raise ASTTranspileError(f"Function '{func_def.name}' must have explicit return type annotation")
        ret_py_type, ret_mojo_type, ret_elem_type = parse_type_annotation(func_def.returns)
        self.ret_mojo_type = ret_mojo_type
        self.ret_elem_type = ret_elem_type

        # 2b. Check which String arguments are subscripted/sliced
        subscripted_args = set()
        for arg in func_def.args.args:
            arg_name = arg.arg
            if any(isinstance(n, ast.Subscript) and isinstance(n.value, ast.Name) and n.value.id == arg_name for n in ast.walk(func_def)):
                subscripted_args.add(arg_name)

        native_args = []
        body_prep = []
        for name, py_type, mojo_type, elem_type in args:
            if name in subscripted_args and mojo_type == "String":
                native_args.append(f"_arg_{name}: String")
                body_prep.append(f"    var {name}: _PyStr = _PyStr(_arg_{name})")
                self.var_types[name] = "_PyStr"
            else:
                native_args.append(f"{name}: {mojo_type}")

        # 3. Transpile body
        self.indent_level = 1
        body_lines = list(body_prep)
        for stmt in func_def.body:
            body_lines.append(self.visit_stmt(stmt))
        body_code = "\n".join(body_lines)

        # 4. Check for typed array collections to generate pointer fast-path
        coll_args = [
            (name, py_type, mojo_type, elem_type, i)
            for i, (name, py_type, mojo_type, elem_type) in enumerate(args)
            if elem_type in ("float", "int")
        ]

        ptr_native_code = ""
        if coll_args:
            ptr_args_def = []
            ptr_body_lines = []
            for name, py_type, mojo_type, elem_type in args:
                if elem_type in ("float", "int"):
                    inner_m = "Float64" if elem_type == "float" else "Int"
                    ptr_args_def.append(f"{name}_ptr: OpaquePointer[MutUntrackedOrigin]")
                    ptr_args_def.append(f"_n_{name}: Int")
                    ptr_body_lines.append(f"    var {name} = {name}_ptr.unsafe_bitcast[{inner_m}]()")
                elif name in subscripted_args and mojo_type == "String":
                    ptr_args_def.append(f"_arg_{name}: String")
                    ptr_body_lines.append(f"    var {name}: _PyStr = _PyStr(_arg_{name})")
                else:
                    ptr_args_def.append(f"{name}: {mojo_type}")

            for line in body_lines:
                mod_line = line
                for name, _, _, elem_type, _ in coll_args:
                    mod_line = mod_line.replace(f"_len({name})", f"_n_{name}")
                ptr_body_lines.append(mod_line)
            ptr_body_code = "\n".join(ptr_body_lines)
            ptr_native_code = f"""@always_inline\ndef _ptr_{func_def.name}({", ".join(ptr_args_def)}) raises -> {ret_mojo_type}:\n{ptr_body_code}"""

        # 5. Generate C-ABI wrapper
        wrapper_args_def = ", ".join([f"arg{i}: PythonObject" for i in range(len(args))])
        wrapper_conversions = []
        call_args = []
        for i, (name, py_type, mojo_type, elem_type) in enumerate(args):
            if elem_type is not None:
                inner_mojo = "Float64" if elem_type == "float" else ("Int" if elem_type == "int" else ("String" if elem_type == "str" else "Bool"))
                conv = (
                    f"    var {name} = {mojo_type}()\n"
                    f"    var _n_{name} = Int(py=arg{i}.__len__())\n"
                    f"    for _i in range(_n_{name}):\n"
                    f"        {name}.append({inner_mojo}(py=arg{i}[_i]))"
                )
            else:
                conv = f"    var {name} = {mojo_type}(py=arg{i})"
            wrapper_conversions.append(conv)
            call_args.append(name)

        if ret_elem_type is not None:
            call_block = (
                f"    var _res = _native_{func_def.name}({', '.join(call_args)})\n"
                f"    var _builtins = Python.import_module(\"builtins\")\n"
                f"    var _py_res = _builtins.list()\n"
                f"    for _i in range(len(_res)):\n"
                f"        _py_res.append(_res[_i])\n"
                f"    return _py_res"
            )
        else:
            call_block = f"    var _res = _native_{func_def.name}({', '.join(call_args)})\n    return PythonObject(_res)"

        if coll_args:
            ctypes_cond = " and ".join([f'Bool(py=_builtins.hasattr(arg{i}, "ctypes"))' for _, _, _, _, i in coll_args])
            ptr_calls = []
            for i, (name, py_type, mojo_type, elem_type) in enumerate(args):
                if elem_type in ("float", "int"):
                    ptr_calls.append(f"_{name}_op")
                    ptr_calls.append(f"_n_{name}")
                else:
                    ptr_calls.append(f"{mojo_type}(py=arg{i})")

            len_checks = "\n".join([f"        var _n_{name} = Int(py=arg{i}.__len__())" for name, _, _, _, i in coll_args])
            addr_fetches = "\n".join([f"        var _{name}_addr = Int(py=arg{i}.ctypes.data)" for name, _, _, _, i in coll_args])
            op_wraps = "\n".join([f"        var _{name}_op = OpaquePointer[MutUntrackedOrigin](unsafe_from_address=_{name}_addr)" for name, _, _, _, i in coll_args])

            conv_block_8 = "\n".join(["    " + l if l.strip() else "" for l in "\n".join(wrapper_conversions).splitlines()])
            call_block_8 = "\n".join(["    " + l if l.strip() else "" for l in call_block.splitlines()])

            wrapper_code = f"""def {func_def.name}({wrapper_args_def}) raises -> PythonObject:
    var _builtins = Python.import_module("builtins")
    var _has_ctypes = {ctypes_cond}
    if _has_ctypes:
{len_checks}
{addr_fetches}
{op_wraps}
        var _res = _ptr_{func_def.name}({', '.join(ptr_calls)})
        return PythonObject(_res)
    else:
{conv_block_8}
{call_block_8}"""
        else:
            conv_block_4 = "\n".join(wrapper_conversions)
            wrapper_code = f"""def {func_def.name}({wrapper_args_def}) raises -> PythonObject:
{conv_block_4}
{call_block}"""

        native_code = f"""def _native_{func_def.name}({", ".join(native_args)}) raises -> {ret_mojo_type}:
{body_code}"""
        if ptr_native_code:
            native_code = f"{ptr_native_code}\n\n{native_code}"

        export_reg = f'        m.def_function[{func_def.name}]("{func_def.name}")'

        return export_reg, wrapper_code, native_code

    def visit_stmt(self, node: ast.stmt) -> str:
        if isinstance(node, ast.Return):
            if node.value is None:
                return f"{self.indent()}return"
            if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                return f"{self.indent()}return {self.ret_mojo_type}()"
            val = self.visit_expr(node.value)
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

            if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                expr_code = f"{mojo_type}()"
            elif mojo_type == "String" and isinstance(node.value, ast.Constant) and node.value.value == "":
                expr_code = "String()"
            else:
                expr_code = self.visit_expr(node.value)

            if var_name not in self.scopes[-1]:
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
                if isinstance(node.value, ast.List) and len(node.value.elts) == 0:
                    inferred_type = self.var_types.get(var_name, self.ret_mojo_type)
                    expr_code = f"{inferred_type}()"
                elif isinstance(node.value, ast.Constant) and node.value.value == "" and self.var_types.get(var_name) == "String":
                    expr_code = "String()"
                else:
                    expr_code = self.visit_expr(node.value)

                is_declared = any(var_name in s for s in self.scopes)
                if not is_declared:
                    self.scopes[-1].add(var_name)
                    return f"{self.indent()}var {var_name} = {expr_code}"
                else:
                    return f"{self.indent()}{var_name} = {expr_code}"
            else:
                raise ASTTranspileError(f"Unsupported assignment target: {type(target).__name__}")

        elif isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name):
                raise ASTTranspileError("Only single variable augmented assignments are supported")
            var_name = node.target.id
            expr_code = self.visit_expr(node.value)
            if self.var_types.get(var_name) == "String" and isinstance(node.op, ast.Add):
                return f"{self.indent()}{var_name}.write({expr_code})"
            elif isinstance(node.op, ast.Add):
                return f"{self.indent()}{var_name} = _checked_add({var_name}, {expr_code})"
            elif isinstance(node.op, ast.Sub):
                return f"{self.indent()}{var_name} = _checked_sub({var_name}, {expr_code})"
            elif isinstance(node.op, ast.Mult):
                return f"{self.indent()}{var_name} = _checked_mul({var_name}, {expr_code})"
            elif isinstance(node.op, ast.Div):
                return f"{self.indent()}{var_name} = _checked_div({var_name}, {expr_code})"
            elif isinstance(node.op, ast.FloorDiv):
                return f"{self.indent()}{var_name} = _checked_floordiv({var_name}, {expr_code})"
            elif isinstance(node.op, ast.Mod):
                return f"{self.indent()}{var_name} = _checked_mod({var_name}, {expr_code})"
            elif isinstance(node.op, ast.Pow):
                return f"{self.indent()}{var_name} = _checked_pow({var_name}, {expr_code})"
            else:
                op = self.visit_op(node.op)
                return f"{self.indent()}{var_name} {op}= {expr_code}"

        elif isinstance(node, ast.If):
            test_code = self.visit_expr(node.test)
            lines = [f"{self.indent()}if {test_code}:"]
            self.indent_level += 1
            for s in node.body:
                lines.append(self.visit_stmt(s))
            self.indent_level -= 1
            if node.orelse:
                if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                    # elif
                    elif_stmt = node.orelse[0]
                    lines.append(f"{self.indent()}elif {self.visit_expr(elif_stmt.test)}:")
                    self.indent_level += 1
                    for s in elif_stmt.body:
                        lines.append(self.visit_stmt(s))
                    self.indent_level -= 1
                    if elif_stmt.orelse:
                        lines.append(f"{self.indent()}else:")
                        self.indent_level += 1
                        for s in elif_stmt.orelse:
                            lines.append(self.visit_stmt(s))
                        self.indent_level -= 1
                else:
                    lines.append(f"{self.indent()}else:")
                    self.indent_level += 1
                    for s in node.orelse:
                        lines.append(self.visit_stmt(s))
                    self.indent_level -= 1
            return "\n".join(lines)

        elif isinstance(node, ast.For):
            if not isinstance(node.target, ast.Name):
                raise ASTTranspileError("Only simple variable loop targets are supported")
            var_name = node.target.id
            self.scopes[-1].add(var_name)

            if isinstance(node.iter, ast.Call) and isinstance(node.iter.func, ast.Name) and node.iter.func.id == "range":
                range_args = [self.visit_expr(a) for a in node.iter.args]
                iter_code = f"range({', '.join(range_args)})"
                self.var_types[var_name] = "Int"
            else:
                iter_expr = self.visit_expr(node.iter)
                if self.var_types.get(iter_expr) == "String":
                    iter_code = f"{iter_expr}.codepoints()"
                    self.var_types[var_name] = "Codepoint"
                else:
                    iter_code = iter_expr
                    if self.var_types.get(iter_expr) == "List[Int]":
                        self.var_types[var_name] = "Int"
                    elif self.var_types.get(iter_expr) == "List[Float64]":
                        self.var_types[var_name] = "Float64"

            lines = [f"{self.indent()}for {var_name} in {iter_code}:"]
            self.indent_level += 1
            self.scopes.append(set())
            for s in node.body:
                lines.append(self.visit_stmt(s))
            self.scopes.pop()
            self.indent_level -= 1
            return "\n".join(lines)

        elif isinstance(node, ast.While):
            test_code = self.visit_expr(node.test)
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
                    start = self.visit_expr(node.slice.lower) if node.slice.lower else "0"
                    end = self.visit_expr(node.slice.upper) if node.slice.upper else f"_len({val})"
                    return f"{val}[{start}:{end}]"
                else:
                    idx = self.visit_expr(node.slice)
                    return f"{val}[{idx}]"
            elif val_type == "String":
                if isinstance(node.slice, ast.Slice):
                    start = self.visit_expr(node.slice.lower) if node.slice.lower else "0"
                    end = self.visit_expr(node.slice.upper) if node.slice.upper else f"_len({val})"
                    return f"String({val}[codepoint={start}:{end}])"
                else:
                    idx = self.visit_expr(node.slice)
                    return f"String({val}[codepoint={idx}])"
            else:
                idx = self.visit_expr(node.slice)
                return f"{val}[{idx}]"

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
            elif isinstance(node.op, (ast.BitAnd, ast.BitOr, ast.BitXor, ast.LShift, ast.RShift)):
                op = self.visit_op(node.op)
                return f"({left} {op} {right})"
            else:
                op = self.visit_op(node.op)
                return f"({left} {op} {right})"

        elif isinstance(node, ast.UnaryOp):
            operand = self.visit_expr(node.operand)
            if isinstance(node.op, ast.Not):
                return f"(not {operand})"
            elif isinstance(node.op, ast.USub):
                return f"_checked_neg({operand})"
            elif isinstance(node.op, ast.UAdd):
                return f"(+{operand})"
            elif isinstance(node.op, ast.Invert):
                return f"(~{operand})"
            else:
                raise ASTTranspileError(f"Unsupported unary operator: {type(node.op).__name__}")

        elif isinstance(node, ast.Compare):
            def _is_pystr_sub(n):
                return (
                    isinstance(n, ast.Subscript) and
                    isinstance(n.value, ast.Name) and
                    self.var_types.get(n.value.id) == "_PyStr"
                )

            left_is_cp = (isinstance(node.left, ast.Name) and self.var_types.get(node.left.id) == "Codepoint")
            left_is_sub = _is_pystr_sub(node.left)
            left = self.visit_expr(node.left)
            parts = [left]
            for op, comparator in zip(node.ops, node.comparators):
                comp_op = self.visit_cmp_op(op)
                comp_is_cp = (isinstance(comparator, ast.Name) and self.var_types.get(comparator.id) == "Codepoint")
                comp_is_sub = _is_pystr_sub(comparator)
                if left_is_sub and isinstance(comparator, ast.Constant) and isinstance(comparator.value, str) and len(comparator.value) == 1:
                    vname = node.left.value.id
                    slice_code = self.visit_expr(node.left.slice)
                    parts[0] = f"{vname}.get_ord({slice_code})"
                    comp_val = str(ord(comparator.value))
                elif comp_is_sub and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str) and len(node.left.value) == 1:
                    cname = comparator.value.id
                    slice_code = self.visit_expr(comparator.slice)
                    parts[0] = str(ord(node.left.value))
                    comp_val = f"{cname}.get_ord({slice_code})"
                elif left_is_cp and isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                    comp_val = f'Codepoint({repr(comparator.value)})'
                elif comp_is_cp and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
                    parts[0] = f'Codepoint({repr(node.left.value)})'
                    comp_val = self.visit_expr(comparator)
                else:
                    comp_val = self.visit_expr(comparator)
                parts.append(f"{comp_op} {comp_val}")
            return f"({' '.join(parts)})"

        elif isinstance(node, ast.BoolOp):
            op = "and" if isinstance(node.op, ast.And) else "or"
            values = [self.visit_expr(v) for v in node.values]
            return f"({(' ' + op + ' ').join(values)})"

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                fn_name = node.func.id
                args = [self.visit_expr(a) for a in node.args]
                if fn_name == "len":
                    return f"_len({', '.join(args)})"
                elif fn_name == "ord":
                    return f"Int({args[0]})"
                elif fn_name == "chr":
                    return f"String(Codepoint({args[0]}))"
                elif fn_name in ("abs", "min", "max", "int", "float"):
                    if fn_name == "int":
                        return f"Int({', '.join(args)})"
                    if fn_name == "float":
                        return f"Float64({', '.join(args)})"
                    return f"{fn_name}({', '.join(args)})"
                elif fn_name == "range":
                    return f"range({', '.join(args)})"
                elif fn_name in self.known_funcs:
                    return f"_native_{fn_name}({', '.join(args)})"
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
