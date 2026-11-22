"""Private, verified Python owners for native return metadata. Never executes source."""
import ast
import builtins
import math
import dis
import hashlib
import json
import struct
import sys
import types
import platform
import sysconfig

PROFILE = "cpython-3.12.16-pylong30-linux-x86_64-gil"

ERROR = "HOTLOOP_PYTHON_SEMANTICS: return owner cannot be proven"
INTRINSICS={name:getattr(builtins,name) for name in ("len","range","ord","chr","abs","min","max","int","float","str","bool")}
MATH={name:value for name,value in vars(math).items() if not name.startswith("_")}

# A snapshot taken after application monkeypatching is not proof of a stdlib
# operation. Qualify only referenced bindings, without executing the callable.
_LITERAL_TYPES = {"int": (0).__class__, "float": (0.0).__class__,
                  "str": "".__class__, "bool": True.__class__}
_MATH_CONSTANT_BITS = {
    "pi": "400921fb54442d18", "e": "4005bf0a8b145769",
    "tau": "401921fb54442d18", "inf": "7ff0000000000000",
    "nan": "7ff8000000000000",
}

def _canonical_intrinsic(name, value):
    if name in _LITERAL_TYPES:
        return value is _LITERAL_TYPES[name]
    if name == "range":
        # Exact CPython profile: heap-type flag is Py_TPFLAGS_HEAPTYPE (1 << 9).
        # Python classes can spoof module/name; static builtin types cannot.
        return (type(value) is type and value.__module__ == "builtins"
                and value.__name__ == "range" and not value.__flags__ & (1 << 9))
    return (type(value) is types.BuiltinFunctionType and value.__self__ is builtins
            and value.__module__ == "builtins" and value.__name__ == name)

def _canonical_math(name, value):
    if type(value) is types.BuiltinFunctionType:
        return (value.__self__ is math and value.__module__ == "math"
                and value.__name__ == name)
    return (type(value) is _LITERAL_TYPES["float"]
            and struct.pack(">d", value).hex() == _MATH_CONSTANT_BITS.get(name))

def _value(value):
    if isinstance(value, types.CodeType):
        return _code(value)
    if type(value) is float:
        return ["float", struct.pack(">d", value).hex()]
    if type(value) is complex:
        return ["complex", _value(value.real), _value(value.imag)]
    if type(value) in (tuple, frozenset):
        items = [_value(x) for x in value]
        if type(value) is frozenset:
            items.sort(key=repr)
        return [type(value).__name__, items]
    if type(value) is bytes:
        return ["bytes", value.hex()]
    if value is None or type(value) in (str,int,bool):
        return [type(value).__name__,value]
    if value is Ellipsis:
        return ["ellipsis"]
    raise ValueError(ERROR)

def _code(code):
    return [code.co_code.hex(), code.co_exceptiontable.hex(), code.co_linetable.hex(),
            code.co_firstlineno, code.co_flags, code.co_argcount, code.co_posonlyargcount,
            code.co_kwonlyargcount, code.co_names, code.co_varnames, code.co_freevars,
            code.co_cellvars, [_value(x) for x in code.co_consts]]

def fingerprint(code):
    return hashlib.sha256(json.dumps(_code(code),ensure_ascii=True,separators=(",",":")).encode()).hexdigest()

def span(node):
    return (node.lineno, node.end_lineno, node.col_offset, node.end_col_offset)

class Layout:
    def __init__(self, source, functions):
        module = compile(source, "<hotloop-source>", "exec", dont_inherit=True)
        self.function_nodes={fn.name:fn for fn in functions}
        self.constants = []
        self.maps = {}
        self.codes = {}
        self.canonical_tokens = set()
        self.canonical = []
        self.calls = {}
        self.builtins = {}
        self.math = {}
        for fn in functions:
            first = min([fn.lineno, *(n.lineno for n in fn.decorator_list)])
            found = [c for c in module.co_consts if isinstance(c,types.CodeType)
                     and c.co_name==fn.name and c.co_firstlineno==first]
            if len(found)!=1:
                raise ValueError("ambiguous function code mapping")
            code = found[0]
            self.codes[fn.name] = fingerprint(code)
            mapping = {}
            for ins in dis.get_instructions(code):
                if ins.opname not in {"LOAD_CONST","RETURN_CONST"} or type(ins.argval) not in (float,int,str,bool):
                    continue
                p = ins.positions
                key = (p.lineno,p.end_lineno,p.col_offset,p.end_col_offset)
                # Multiple instructions at one source span must agree on slot.
                previous = mapping.get(key)
                if previous is not None and self.constants[previous][1]!=ins.arg:
                    mapping[key] = -1
                    continue
                if previous is None:
                    mapping[key] = len(self.constants)
                    self.constants.append([fn.name,ins.arg])
                    if type(ins.argval) is bool or (type(ins.argval) is int and -5<=ins.argval<=256):
                        self.canonical_tokens.add(-(mapping[key]+2))
                        self.canonical.append(mapping[key])
            self.maps[fn.name] = mapping
            self.builtins[fn.name]=sorted({n.func.id for n in ast.walk(fn) if isinstance(n,ast.Call)
                and isinstance(n.func,ast.Name) and n.func.id in INTRINSICS})
            self.math[fn.name]=sorted({n.attr for n in ast.walk(fn) if isinstance(n,ast.Attribute)
                and isinstance(n.value,ast.Name) and n.value.id=="math"})
            self.calls[fn.name] = sorted({n.func.id for n in ast.walk(fn)
                if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                and any(other.name==n.func.id for other in functions)})
    def constant(self, owner, node):
        if not isinstance(node,ast.expr):
            return None
        index = self.maps[owner].get(span(node))
        return index if index is not None and index>=0 else None
    def spec(self):
        return dict(version=1,profile=PROFILE, codes=self.codes,calls=self.calls,constants=self.constants,canonical=self.canonical,builtins=self.builtins,math=self.math)

def _unwrap(fn):
    if type(fn) is not types.FunctionType:
        raise ValueError(ERROR)
    if type(fn.__dict__) is not dict:
        raise ValueError(ERROR)
    original = fn.__dict__.get("_original",fn)
    if original is not fn:
        # A decorated helper has observable policy (including strict-mode
        # exceptions) beyond its underlying code. Native inlining cannot prove
        # that policy, so refuse the parent before any native body executes.
        raise ValueError(ERROR)
    if type(original) is not types.FunctionType:
        raise ValueError(ERROR)
    return original

class Entry:
    """All owner proof precedes the native body, including private direct calls."""
    def __init__(self, fn, raw, spec):
        self.fn,self.raw,self.spec = fn,raw,spec
        self.code,self.defaults,self.kwdefaults = fn.__code__,fn.__defaults__,fn.__kwdefaults__
        self.context = None
        self.guards = ()
        self.builtin_guards=()
        self.math_guards=()
    def root_valid(self):
        fn=self.fn
        return (fn.__code__ is self.code and fn.__defaults__ is self.defaults
                and fn.__kwdefaults__ is self.kwdefaults)
    def _prepare(self):
        if not self.root_valid():
            raise ValueError(ERROR)
        code=self.fn.__code__
        if code.co_posonlyargcount or code.co_kwonlyargcount or code.co_flags & 12:
            raise ValueError(ERROR)
        spec=self.spec
        if (spec.get("version")!=1 or spec.get("profile")!=PROFILE
            or sys.implementation.name!="cpython" or sys.version_info[:3]!=(3,12,16)
            or sys.int_info.bits_per_digit!=30
            or sys.platform!="linux" or platform.machine()!="x86_64"
            or sys.byteorder!="little" or struct.calcsize("P")!=8
            or bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
            or not getattr(sys,"_is_gil_enabled",lambda:True)()):
            raise ValueError(ERROR)
        owners={}
        guards=[]
        def visit(name, actual):
            if type(actual.__globals__) is not dict or type(actual.__builtins__) is not dict:
                raise ValueError(ERROR)
            if name in owners:
                if owners[name] is not actual:
                    raise ValueError(ERROR)
                return
            if fingerprint(actual.__code__)!=spec["codes"].get(name):
                raise ValueError(ERROR)
            owners[name]=actual
            for callee in spec["calls"].get(name,()):
                bound=actual.__globals__.get(callee)
                inner=_unwrap(bound)
                guards.append((actual.__globals__,callee,bound,inner,bound.__code__,
                               inner.__code__,inner.__defaults__,inner.__kwdefaults__))
                visit(callee,inner)
        visit(self.fn.__name__,self.fn)
        pool=[]
        for name,index in spec["constants"]:
            owner=owners.get(name)
            pool.append(owner.__code__.co_consts[index] if owner is not None else None)
        # Concrete CPython/SDK ABI qualification, not an interning assumption.
        for index in spec.get("canonical",()):
            owner=spec["constants"][index][0]
            if owner not in owners:
                continue
            value=pool[index]
            if type(value) is bool:
                if value is not bool(int(value)):
                    raise ValueError(ERROR)
            elif type(value) is not int or value is not int(str(value)):
                raise ValueError(ERROR)
        builtin_guards={}
        math_guards={}
        for name,actual in owners.items():
            namespace=actual.__globals__
            for item in spec.get("builtins",{}).get(name,()):
                if item not in INTRINSICS or not _canonical_intrinsic(item, INTRINSICS[item]):
                    raise ValueError(ERROR)
                builtin_guards[(id(namespace),id(actual.__builtins__),item)]=(namespace,actual.__builtins__,item,INTRINSICS[item])
            for item in spec.get("math",{}).get(name,()):
                if item not in MATH or not _canonical_math(item, MATH[item]):
                    raise ValueError(ERROR)
                math_guards[(id(namespace),item)]=(namespace,item,MATH[item])
        self.builtin_guards=tuple(builtin_guards.values())
        self.math_guards=tuple(math_guards.values())
        # Keep actual owners/code and constants alive; never retain just object ids.
        self.owners=owners
        self.guards=tuple(guards)
        self.context=tuple(pool)
    def __call__(self,*args):
        if not self.root_valid():
            raise ValueError(ERROR)
        if self.context is None:
            self._prepare()
        for namespace,name,bound,inner,bcode,code,defaults,kwdefaults in self.guards:
            if (namespace.get(name) is not bound or _unwrap(bound) is not inner
                or bound.__code__ is not bcode or inner.__code__ is not code
                or inner.__defaults__ is not defaults or inner.__kwdefaults__ is not kwdefaults):
                raise ValueError(ERROR)
        for namespace,source,name,expected in self.builtin_guards:
            if namespace.get(name,source.get(name)) is not expected:
                raise ValueError(ERROR)
        for namespace,name,expected in self.math_guards:
            if namespace.get("math") is not math or math.__dict__.get(name) is not expected:
                raise ValueError(ERROR)
        return self.raw(self.context,*args)

def bind(fn,raw,module):
    """Called only after existing artifact/ABI/inode verification and loading."""
    spec=json.loads(module._hotloop_provenance_v1())
    return Entry(fn,raw,spec)


def fresh_string(value):
    # CPython's extended slice / integer formatting allocate even one-character
    # strings. SDK UTF-8 boxing may instead return a cached Latin-1 character.
    # A two-item join forces the equivalent allocation; empty remains canonical.
    if type(value) is not str:
        raise ValueError(ERROR)
    return "".join((value,""))
