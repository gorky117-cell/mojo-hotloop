import ast
import inspect
from typing import Dict, List, Optional, Set, Tuple

TYPE_MAP = {
    "int": "Int",
    "float": "Float64",
    "bool": "Bool",
}

PY_CONVERT_MAP = {
    "int": "Int(py={var})",
    "float": "Float64(py={var})",
    "bool": "Bool(py={var})",
}

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
"""

class ASTTranspileError(Exception):
    """Raised when an AST node cannot be deterministically transpiled to Mojo."""
    pass

class MojoASTTranspiler:
    def __init__(self, mod_name: str):
        self.mod_name = mod_name
        self.indent_level = 0
        self.declared_vars: Set[str] = set()
        self.var_types: Dict[str, str] = {}
        self.has_math = False

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
        self.declared_vars.clear()
        self.var_types.clear()

        # 1. Validate argument types
        args = []
        for arg in func_def.args.args:
            arg_name = arg.arg
            if not arg.annotation or not isinstance(arg.annotation, ast.Name):
                raise ASTTranspileError(f"Argument '{arg_name}' must have explicit type annotation (int, float, bool)")
            py_type = arg.annotation.id
            if py_type not in TYPE_MAP:
                raise ASTTranspileError(f"Unsupported argument type '{py_type}' for '{arg_name}'. Supported: int, float, bool")
            args.append((arg_name, py_type, TYPE_MAP[py_type]))
            self.declared_vars.add(arg_name)
            self.var_types[arg_name] = TYPE_MAP[py_type]

        # 2. Validate return type
        if not func_def.returns or not isinstance(func_def.returns, ast.Name):
            raise ASTTranspileError(f"Function '{func_def.name}' must have explicit return type annotation (int, float, bool)")
        ret_py_type = func_def.returns.id
        if ret_py_type not in TYPE_MAP:
            raise ASTTranspileError(f"Unsupported return type '{ret_py_type}'. Supported: int, float, bool")
        ret_mojo_type = TYPE_MAP[ret_py_type]

        # 3. Transpile body
        self.indent_level = 1
        body_lines = []
        for stmt in func_def.body:
            body_lines.append(self.visit_stmt(stmt))
        body_code = "\n".join(body_lines)

        # 4. Generate C-ABI wrapper
        wrapper_args_def = ", ".join([f"arg{i}: PythonObject" for i in range(len(args))])
        wrapper_conversions = []
        call_args = []
        for i, (name, py_type, mojo_type) in enumerate(args):
            conv = PY_CONVERT_MAP[py_type].format(var=f"arg{i}")
            wrapper_conversions.append(f"    var {name} = {conv}")
            call_args.append(name)

        conv_block = "\n".join(wrapper_conversions)
        call_block = f"    var res = _native_{func_def.name}({', '.join(call_args)})\n    return PythonObject(res)"

        wrapper_code = f"""def {func_def.name}({wrapper_args_def}) raises -> PythonObject:
{conv_block}
{call_block}"""

        native_code = f"""def _native_{func_def.name}({", ".join([f"{name}: {m_type}" for name, _, m_type in args])}) raises -> {ret_mojo_type}:
{body_code}"""

        export_reg = f'        m.def_function[{func_def.name}]("{func_def.name}")'

        return export_reg, wrapper_code, native_code

    def visit_stmt(self, node: ast.stmt) -> str:
        if isinstance(node, ast.Return):
            val = self.visit_expr(node.value) if node.value else ""
            return f"{self.indent()}return {val}"

        elif isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ASTTranspileError("Only single variable assignments are currently supported")
            var_name = node.targets[0].id
            expr_code = self.visit_expr(node.value)
            if var_name not in self.declared_vars:
                self.declared_vars.add(var_name)
                return f"{self.indent()}var {var_name} = {expr_code}"
            else:
                return f"{self.indent()}{var_name} = {expr_code}"

        elif isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name):
                raise ASTTranspileError("Only single variable augmented assignments are supported")
            var_name = node.target.id
            expr_code = self.visit_expr(node.value)
            if isinstance(node.op, ast.Add):
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
            if not isinstance(node.iter, ast.Call) or not isinstance(node.iter.func, ast.Name) or node.iter.func.id != "range":
                raise ASTTranspileError("Only 'for ... in range(...)' loops are supported in AST transpiler")
            range_args = [self.visit_expr(a) for a in node.iter.args]
            iter_code = f"range({', '.join(range_args)})"
            lines = [f"{self.indent()}for {var_name} in {iter_code}:"]
            self.indent_level += 1
            for s in node.body:
                lines.append(self.visit_stmt(s))
            self.indent_level -= 1
            return "\n".join(lines)

        elif isinstance(node, ast.While):
            test_code = self.visit_expr(node.test)
            lines = [f"{self.indent()}while {test_code}:"]
            self.indent_level += 1
            for s in node.body:
                lines.append(self.visit_stmt(s))
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
            left = self.visit_expr(node.left)
            parts = [left]
            for op, comparator in zip(node.ops, node.comparators):
                comp_op = self.visit_cmp_op(op)
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
                if fn_name in ("abs", "min", "max", "int", "float"):
                    if fn_name == "int":
                        return f"Int({', '.join(args)})"
                    if fn_name == "float":
                        return f"Float64({', '.join(args)})"
                    return f"{fn_name}({', '.join(args)})"
                elif fn_name == "range":
                    return f"range({', '.join(args)})"
                else:
                    return f"{fn_name}({', '.join(args)})"
            elif isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "math":
                    fn_name = node.func.attr
                    args = [self.visit_expr(a) for a in node.args]
                    return f"math.{fn_name}({', '.join(args)})"
                else:
                    raise ASTTranspileError(f"Unsupported method call: {ast.dump(node.func)}")
            else:
                raise ASTTranspileError(f"Unsupported function call expression: {type(node.func).__name__}")

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
    """Parses Python source, finds ALL @hotloop functions, and transpiles them into a unified Mojo module."""
    tree = ast.parse(source_code)
    hotloop_nodes = []
    all_funcs = []

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            all_funcs.append(node)
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

    # If no explicit @hotloop decorator, default to all functions if only 1 exists
    target_nodes = hotloop_nodes if hotloop_nodes else (all_funcs if len(all_funcs) == 1 else [])
    if not target_nodes:
        raise ASTTranspileError("No @hotloop-decorated function found in source file.")

    transpiler = MojoASTTranspiler(mod_name)
    export_regs = []
    wrappers = []
    native_funcs = []

    for node in target_nodes:
        reg, wrap, nat = transpiler.transpile_function_components(node)
        export_regs.append(reg)
        wrappers.append(wrap)
        native_funcs.append(nat)

    export_block = "\n".join(export_regs)
    wrappers_block = "\n\n".join(wrappers)
    native_block = "\n\n".join(native_funcs)

    mojo_source = f"""from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder
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
