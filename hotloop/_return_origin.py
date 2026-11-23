"""Conservative input-object provenance for generated native return metadata."""
import ast
from ._provenance import INTRINSICS

UNKNOWN = -(1 << 62)

# This release qualifies only these Python math call shapes. The table is also
# consumed by code generation; other operations keep Python semantics.
NATIVE_MATH_ARITIES = {"sin": 1, "cos": 1, "sqrt": 1, "log": 1, "exp": 1, "atan2": 2,
                       "isnan": 1, "isinf": 1}

def native_math_call(node):
    return (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name) and node.func.value.id == "math"
            and node.func.attr in NATIVE_MATH_ARITIES
            and len(node.args) == NATIVE_MATH_ARITIES[node.func.attr]
            and not node.keywords)


def _targets(node):
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, (ast.AnnAssign, ast.AugAssign)) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


class ReturnOrigin:
    def __init__(self, fn, summaries, layout):
        self.fn = fn
        self.layout = layout
        self.arguments = {a.arg: i for i, a in enumerate(fn.args.args)}
        self.types = {a.arg: ast.unparse(a.annotation) for a in fn.args.args if a.annotation}
        self.types.update({n.target.id: ast.unparse(n.annotation) for n in ast.walk(fn)
                           if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)})
        self.sources = {name: {index} for name, index in self.arguments.items()}
        self.summaries = summaries
        self.assignments = [n for n in ast.walk(fn) if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))]
        changed = True
        while changed:
            previous = {name: set(items) for name, items in self.sources.items()}
            for node in self.assignments:
                for name in _targets(node):
                    if not isinstance(node,ast.AugAssign) or self.types.get(name)=="str":
                        self.sources.setdefault(name, set()).update(self.origins(node.value))
                    inferred=self.expression_type(node.value)
                    if inferred and name not in self.types:
                        self.types[name]=inferred
                    if isinstance(node.value, ast.Name) and name not in self.types:
                        if node.value.id in self.types:
                            self.types[name] = self.types[node.value.id]
            for node in ast.walk(fn):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "append" and isinstance(node.func.value, ast.Name)):
                    self.sources.setdefault(node.func.value.id, set()).update(
                        set().union(*(self.origins(arg) for arg in node.args)))
                if (isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name)
                        and self.types.get(node.target.id) == "str"):
                    self.sources.setdefault(node.target.id, set()).update(self.origins(node.value))
                if isinstance(node, ast.For) and isinstance(node.target, ast.Name):
                    self.sources.setdefault(node.target.id, set()).update(self.origins(node.iter))
            changed = self.sources != previous
        self.returns = [n.value for n in ast.walk(fn) if isinstance(n, ast.Return) and n.value is not None]
        self.returned = set().union(*(self.origins(n) for n in self.returns))
        self.needed = {n.id for value in self.returns for n in self._alias_names(value)}
        changed = True
        while changed:
            previous = set(self.needed)
            for node in self.assignments:
                if set(_targets(node)) & self.needed:
                    self.needed.update(n.id for n in self._alias_names(node.value))
            changed = previous != self.needed
        self.needed = {name for name in self.needed if self.sources.get(name)}
        self.assigned = {name for node in ast.walk(fn) for name in _targets(node)}
        self.reason = self._restriction()
        self.scalar = self.fn.returns is not None and not ast.unparse(self.fn.returns).startswith("list[")
        occupied = {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)} | set(self.arguments)
        prefix = "_hotloop_origin"
        while any(name.startswith(prefix) for name in occupied):
            prefix += "_"
        self.prefix = prefix
        self.counter = 0
        self.tags = {name: f"{prefix}_{i}" for i, name in enumerate(sorted(self.needed & self.assigned))}
        self.slots = {name: tag + "_item" for name, tag in self.tags.items()}

    def expression_type(self,node):
        if isinstance(node,ast.Name):
            return self.types.get(node.id)
        if isinstance(node,ast.Constant) and type(node.value) in (str,float,int,bool):
            return type(node.value).__name__
        if isinstance(node,ast.UnaryOp):
            return self.expression_type(node.operand)
        if isinstance(node,ast.BinOp):
            left,right=self.expression_type(node.left),self.expression_type(node.right)
            if left==right=="str": return "str"
            if left in ("int","float") and right in ("int","float"):
                return "float" if "float" in (left,right) or isinstance(node.op,ast.Div) else "int"
        if isinstance(node,ast.Subscript):
            value=self.expression_type(node.value)
            if value=="str": return "str"
            if value and value.startswith("list["): return value[5:-1]
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
            if node.func.id in ("str","int","float","bool"): return node.func.id
            if node.func.id in ("len","ord"): return "int"
            if node.func.id=="chr": return "str"
            fn=self.layout.function_nodes.get(node.func.id)
            if fn and fn.returns: return ast.unparse(fn.returns)
        return None

    def origins(self, node):
        if node is None:
            return set()
        constant=self.layout.constant(self.fn.name,node)
        if constant is not None:
            return {-(constant+2)}
        if isinstance(node,ast.Constant):
            return {UNKNOWN}
        if isinstance(node,ast.Attribute):
            return {UNKNOWN}
        if isinstance(node, ast.Name):
            return self.sources.get(node.id, set())
        if isinstance(node, ast.UnaryOp):
            return self.origins(node.operand) if isinstance(node.op, ast.UAdd) else set()
        if isinstance(node, ast.Subscript):
            # A list lookup retains the element. A full string slice may
            # retain its source; without a slice identity proof, fall back.
            value_type = self.types.get(node.value.id) if isinstance(node.value, ast.Name) else None
            if value_type and (value_type.startswith("list[") or
                               (value_type == "str" and isinstance(node.slice, ast.Slice))):
                return self.origins(node.value)
            return set()
        if isinstance(node, (ast.BoolOp, ast.List, ast.Tuple)):
            children = node.values if isinstance(node, ast.BoolOp) else node.elts
            return set().union(*(self.origins(n) for n in children))
        if isinstance(node, ast.IfExp):
            return self.origins(node.body) | self.origins(node.orelse)
        if isinstance(node, ast.BinOp):
            if isinstance(node.op,ast.Mod) and self.expression_type(node)=="int":
                return self.origins(node.left)
            left,right=self.expression_type(node.left),self.expression_type(node.right)
            if left=="str" or right=="str":
                return self.origins(node.left) | self.origins(node.right) | ({UNKNOWN} if self.expression_type(node)!="str" else set())
            return set()
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name=="str" and len(node.args)==1 and self.expression_type(node.args[0])!="str":
                    return {UNKNOWN}
                if name in {"len", "range", "ord", "chr", "bool"}:
                    return set()
                if name in self.summaries:
                    values=self.summaries[name]
                    constants={x for x in values if x<0}
                    if any(x>=0 for x in values):
                        constants.update(set().union(*(self.origins(n) for n in node.args)))
                    return constants
                return set().union(*(self.origins(n) for n in
                                         [*node.args, *(kw.value for kw in node.keywords)]))
            return set()
        return set()

    def _alias_names(self, node):
        if isinstance(node, ast.Name):
            return [node]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            return self._alias_names(node.operand)
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="str" and node.args and self.expression_type(node.args[0])!="str":
            return []
        if self.origins(node):
            if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Mod) and self.expression_type(node)=="int":
                return self._alias_names(node.left)
            if isinstance(node,ast.Subscript):
                return self._alias_names(node.value)
            if isinstance(node,ast.BinOp):
                return self._alias_names(node.left)+self._alias_names(node.right)
            if isinstance(node,ast.Call):
                return [name for arg in node.args for name in self._alias_names(arg)]
        return []

    def descriptor(self, node):
        constant=self.layout.constant(self.fn.name,node)
        if constant is not None:
            return "constant",constant
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="str":
            if len(node.args)==1 and not node.keywords:
                kind=self.expression_type(node.args[0])
                if kind=="int": return "format_int",node.args[0]
                if kind=="str": return "string_identity",node.args[0]
            return "unknown",None
        if not self.origins(node):
            return "value", None
        if isinstance(node, ast.BinOp) and isinstance(node.op,ast.Mod) and self.expression_type(node)=="int":
            return "int_mod",node
        if isinstance(node, ast.Name):
            return "name", node.id
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
            if any(self.types.get(name) in {"bool", "list[bool]"}
                   for name in self.arguments if self.arguments[name] in self.origins(node)):
                return "unknown", None
            return self.descriptor(node.operand)
        if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name)
                and node.value.id in self.arguments and not isinstance(node.slice, ast.Slice)
                and self.types.get(node.value.id, "").startswith("list[")):
            return "item", node
        if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and self.types.get(node.value.id)=="str" and isinstance(node.slice,ast.Slice):
            return "slice",node
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Add):
            if self.expression_type(node)=="str":
                return "concat",node
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in self.summaries:
            return "helper",node
        return "unknown", None

    def _container_aliases_safe(self):
        parents={}
        for parent in ast.walk(self.fn):
            for child in ast.iter_child_nodes(parent): parents[child]=parent
        groups={}
        def root(name):
            while groups.get(name,name)!=name: name=groups[name]
            return name
        for node in self.assignments:
            aliases=[]
            if isinstance(node.value,ast.Name): aliases=[node.value.id]
            if isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name):
                if node.value.func.id in {"int","float","str","abs","min","max"} or any(v>=0 for v in self.summaries.get(node.value.func.id,())):
                    aliases=[arg.id for arg in node.value.args if isinstance(arg,ast.Name)]
            if isinstance(node.value,ast.BinOp) and isinstance(node.value.op,ast.Mod) and isinstance(node.value.left,ast.Name):
                aliases=[node.value.left.id]
            for alias in aliases:
                for name in _targets(node): groups[root(name)]=root(alias)
        def escaped(value):
            if isinstance(value,ast.Subscript): return [None]
            if isinstance(value,ast.Name): return [value.id]
            if isinstance(value,ast.UnaryOp) and isinstance(value.op,ast.UAdd): return escaped(value.operand)
            if isinstance(value,ast.BinOp) and isinstance(value.op,ast.Mod): return escaped(value.left)
            if isinstance(value,ast.Call) and isinstance(value.func,ast.Name):
                if value.func.id in {"int","float","str","abs","min","max"} or any(v>=0 for v in self.summaries.get(value.func.id,())):
                    return [name for arg in value.args for name in escaped(arg)]
            return []
        uses=[]
        for node in ast.walk(self.fn):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="append" and node.args:
                if isinstance(node.args[0],ast.Subscript):
                    return False
                uses.extend((node,name) for name in escaped(node.args[0]))
            if isinstance(node,ast.List):
                for value in node.elts:
                    if isinstance(value,ast.Subscript):
                        return False
                    uses.extend((value,name) for name in escaped(value))
        def lineage(node):
            result=[]
            while node in parents:
                node=parents[node]; result.append(node)
            return result
        def terminal(node,loop):
            # Only a guaranteed break in this exact statement block qualifies.
            stmt=node
            while stmt in parents and not isinstance(stmt,ast.stmt): stmt=parents[stmt]
            parent=parents.get(stmt)
            for field in ("body","orelse"):
                block=getattr(parent,field,())
                if stmt in block:
                    if any(isinstance(n,ast.Break) for n in block[block.index(stmt)+1:]):
                        nearest=next((n for n in lineage(stmt) if isinstance(n,(ast.For,ast.While))),None)
                        return nearest is loop
            return False
        def exclusive(a,b):
            for loop in (x for x in lineage(a) if isinstance(x,(ast.For,ast.While)) and x in lineage(b)):
                for first,last in ((a,b),(b,a)):
                    if not terminal(first,loop): continue
                    branch=first
                    while parents.get(branch) is not loop and branch in parents: branch=parents[branch]
                    other=last
                    while parents.get(other) is not loop and other in parents: other=parents[other]
                    if branch is not other and branch in loop.body and other in loop.body and loop.body.index(branch)<loop.body.index(other):
                        return True
            return False
        def fresh(value,seen=()):
            if isinstance(value,ast.Constant):
                token=self.layout.constant(self.fn.name,value)
                return token is not None and -(token+2) in self.layout.canonical_tokens
            if isinstance(value,ast.BinOp):
                return self.expression_type(value) in ("int","float") and not isinstance(value.op,ast.Mod)
            if isinstance(value,ast.UnaryOp) and not isinstance(value.op,ast.UAdd):
                return self.expression_type(value) in ("int","float")
            if isinstance(value,ast.Call) and isinstance(value.func,ast.Name) and value.func.id in {"len","ord","bool"}:
                return True
            if isinstance(value,ast.Name) and value.id not in seen:
                values=[n for n in self.assignments if value.id in _targets(n)]
                return bool(values) and all(
                    (isinstance(n,ast.AugAssign) and not isinstance(n.op,ast.Mod) and self.types.get(value.id) in ("int","float"))
                    or (not isinstance(n,ast.AugAssign) and fresh(n.value,(*seen,value.id))) for n in values)
            return False
        for i,(node,name) in enumerate(uses):
            if name is None: return False
            for other,alias in uses[:i]:
                if root(name)==root(alias) and not exclusive(node,other): return False
            for loop in (n for n in lineage(node) if isinstance(n,(ast.For,ast.While))):
                if terminal(node,loop): continue
                if isinstance(loop,ast.For) and isinstance(loop.target,ast.Name) and loop.target.id==name:
                    continue
                assigns=[n for n in loop.body if name in _targets(n) and
                    ((isinstance(n,ast.AugAssign) and not isinstance(n.op,ast.Mod) and self.types.get(name) in ("int","float")) or
                     (not isinstance(n,ast.AugAssign) and fresh(n.value,(name,))))]
                if not fresh(ast.Name(id=name,ctx=ast.Load())):
                    return False
                if not assigns or any(isinstance(n,ast.Continue) for n in ast.walk(loop)):
                    return False
        return True

    def _restriction(self):
        if self.fn.returns is None:
            return "return annotation is required"
        bound=set(self.arguments)|self.assigned
        for call in ast.walk(self.fn):
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=="print":
                return "Python stream effects require Python execution"
            if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                    and isinstance(call.func.value, ast.Name) and call.func.value.id == "math"
                    and not native_math_call(call)):
                return "unqualified math operation or signature requires Python"
            if (isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute)
                    and call.func.attr in {"startswith","endswith"}
                    and (len(call.args)>1 or call.keywords)):
                return "bounded or keyword string-prefix comparisons require Python"
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id in INTRINSICS and (call.func.id in bound or call.func.id in self.layout.function_nodes):
                return "shadowed Python intrinsic requires Python"
            if isinstance(call,ast.Call) and isinstance(call.func,ast.Attribute) and call.func.attr in {"write","clear"} and self.expression_type(call.func.value)=="str":
                return "Python strings do not support native builder methods"
        if self.fn.args.posonlyargs or self.fn.args.kwonlyargs or self.fn.args.vararg or self.fn.args.kwarg:
            return "return provenance for this signature is unproven"
        if ast.unparse(self.fn.returns).startswith("list["):
            canonical = self.layout.canonical_tokens
            if any(token not in canonical for token in self.returned):
                return "container return may retain Python objects"
            if not self._container_aliases_safe():
                return "container element sharing is unproven"
        if any(self.descriptor(node)[0] == "unknown" for node in self.returns):
            return "return expression has unproven object provenance"
        for node in self.assignments:
            if set(_targets(node)) & self.needed:
                if isinstance(node, ast.AnnAssign) and node.value is None:
                    return "annotation-only alias binding is unproven"
                if (not isinstance(node,ast.AugAssign) or self.types.get(_targets(node)[0])=="str") and self.descriptor(node.value)[0] == "unknown":
                    return "local alias has unproven object provenance"
                if isinstance(node.value, ast.Name):
                    target = _targets(node)[0]
                    if (self.types.get(target) and self.types.get(node.value.id)
                            and self.types[target] != self.types[node.value.id]):
                        return "alias annotation changes the native representation"
        for node in ast.walk(self.fn):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id in self.needed:
                return "loop target return provenance is unproven"
        return None

    def temporary(self):
        self.counter += 1
        return f"{self.prefix}_index_{self.counter}"

    def reference(self, name):
        if name in self.tags:
            return self.tags[name], self.slots[name]
        if name in self.arguments:
            return str(self.arguments[name]), "-1"
        return "-1", "-1"


def analyze(functions,layout):
    summaries = {fn.name: set() for fn in functions}
    while True:
        plans = {fn.name: ReturnOrigin(fn, summaries,layout) for fn in functions}
        updated = {name: plan.returned for name, plan in plans.items()}
        if updated == summaries:
            return plans
        summaries = updated
