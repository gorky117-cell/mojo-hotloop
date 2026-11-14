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

    def transpile_function(self, func_def: ast.FunctionDef) -> str:
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

        mojo_source = f"""from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort
import std.math as math

@export
def PyInit_{self.mod_name}() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("{self.mod_name}")
        m.def_function[{func_def.name}]("{func_def.name}")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def {func_def.name}({wrapper_args_def}) raises -> PythonObject:
{conv_block}
{call_block}

def _native_{func_def.name}({", ".join([f"{name}: {m_type}" for name, _, m_type in args])}) -> {ret_mojo_type}:
{body_code}
"""
        return mojo_source

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
            op = self.visit_op(node.op)
            expr_code = self.visit_expr(node.value)
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
            # range call check
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
            op = self.visit_op(node.op)
            # Check for float division or integer overflow
            if isinstance(node.op, ast.Pow):
                if isinstance(node.right, ast.Constant) and isinstance(node.right.value, (int, float)) and node.right.value > 62:
                    raise ASTTranspileError(f"Power exponent {node.right.value} exceeds 64-bit integer capacity")
                return f"({left} ** {right})"
            if isinstance(node.op, ast.Div):
                # Ensure float representation and Float64 division
                return f"(Float64({left}) / Float64({right}))"
            return f"({left} {op} {right})"

        elif isinstance(node, ast.UnaryOp):
            operand = self.visit_expr(node.operand)
            if isinstance(node.op, ast.Not):
                return f"(not {operand})"
            elif isinstance(node.op, ast.USub):
                return f"(-{operand})"
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
    """Parses Python source, finds the @hotloop function, and transpiles it to Mojo 1.2.0."""
    tree = ast.parse(source_code)
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            # Check if decorated with hotloop or target function
            is_hotloop = any(
                (isinstance(d, ast.Name) and d.id == "hotloop") or
                (isinstance(d, ast.Attribute) and d.attr == "hotloop")
                for d in node.decorator_list
            )
            if is_hotloop or len(tree.body) == 1:
                transpiler = MojoASTTranspiler(mod_name)
                return transpiler.transpile_function(node)
    raise ASTTranspileError("No @hotloop-decorated function found in source file.")
