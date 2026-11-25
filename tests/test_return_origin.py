"""Input object provenance, control flow, binding and single-execution regressions."""
import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest
from hotloop import hotloop, HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend

SOURCE = """
from hotloop import hotloop
DEFAULT = float("123.5")

@hotloop
def direct(x: float) -> float:
    return x

@hotloop
def direct_int(x: int) -> int:
    return x

@hotloop
def direct_text(x: str) -> str:
    return x

@hotloop
def alias(x: float) -> float:
    y: float = x
    z: float = y
    return z

@hotloop
def choose(x: float, y: float, flag: bool) -> float:
    result: float = x
    if flag:
        result = y
    return result

@hotloop
def computed(x: float) -> float:
    y: float = x
    y += 0.0
    return y

@hotloop
def conditional(x: float, n: int) -> float:
    if n <= 0:
        return x
    return x + 0.0

@hotloop
def empty_loop(x: float, n: int) -> float:
    value: float = x
    for i in range(n):
        value = value + 0.0
    return value

@hotloop
def while_alias(x: float, y: float, n: int) -> float:
    value: float = x
    i: int = 0
    while i < n:
        value = y
        i += 1
    return value

@hotloop
def defaulted(x: float = DEFAULT, n: int = 0) -> float:
    if n == 0:
        return x
    return x * 2.0

@hotloop
def selected(xs: list[float], index: int) -> float:
    return xs[index]

@hotloop
def selected_alias(xs: list[float], index: int, n: int) -> float:
    value: float = xs[index]
    for i in range(n):
        value += 0.0
    return value

@hotloop
def exception_before_return(x: float, d: float) -> float:
    value: float = 1.0 / d
    return x

@hotloop
def index_exception(xs: list[float], divisor: int) -> float:
    return xs[10 // divisor]

@hotloop
def mutable_alias(xs: list[int]) -> list[int]:
    alias: list[int] = xs
    alias[0] += 1
    return alias

@hotloop
def side_effect(x: float, log: list[int], divisor: int) -> float:
    log.append(1)
    value: int = 1 // divisor
    return x

def helper(x: float) -> float:
    return x

@hotloop
def through_helper(x: float) -> float:
    return helper(x)

@hotloop
def computed_helper(x: float) -> float:
    return helper(x) + 0.0

@hotloop
def selected_min(x: float, y: float) -> float:
    return min(x, y)

@hotloop
def unary_plus(x: float) -> float:
    return +x

@hotloop
def collision(_hotloop_origin: float) -> float:
    _hotloop_origin_result: float = _hotloop_origin
    return _hotloop_origin_result

@hotloop
def return_origin_collision(x: float) -> float:
    return x

@hotloop
def direct_bool(x: bool) -> bool:
    return x

@hotloop
def sliced(x: str) -> str:
    return x[:]

@hotloop
def string_update(x: str) -> str:
    result: str = ""
    result += x
    return result

@hotloop
def collision_pair(x: float) -> float:
    return x

@hotloop
def return_origin_collision_pair(x: float) -> float:
    return x

@hotloop
def loop_target(x: float, n: int) -> int:
    for n in range(n):
        x = x + 0.0
    return n

def bool_helper(x: float, y: float) -> float:
    return x or y

@hotloop
def computed_bool_helper(x: float, y: float) -> float:
    return bool_helper(x, y) + 2.0

@hotloop
def embedded(x: float) -> list[float]:
    result: list[float] = [x]
    return result
"""

@pytest.fixture(scope="module")
def subject(tmp_path_factory):
    path = tmp_path_factory.mktemp("return-origin") / "origin_subject.py"
    path.write_text(SOURCE)
    ok, diagnostic, _ = MojoBackend().build_ast(path)
    assert ok, diagnostic
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    try:
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop(path.stem, None)


@pytest.mark.parametrize("name,value", [
    ("direct", float("123.5")), ("direct_int", int("1234567890123")),
    ("direct_text", "not interned " * 30), ("alias", float("345.25")),
    ("unary_plus", float("234.5")), ("collision", float("834.5")),
    ("return_origin_collision", float("444.25")),
    ("direct_bool", True), ("collision_pair", float("234.5")),
    ("return_origin_collision_pair", float("534.5")),
])
@pytest.mark.parametrize("mode", ["default", "forced", "strict"])
def test_direct_alias(subject,name,value,mode):
    original = getattr(subject,name)._original
    fn = hotloop(strict=mode=="strict",force_native=mode=="forced")(original)
    assert fn(value) is value and fn._last_backend == "native"
    assert fn(**{original.__code__.co_varnames[0]:value}) is value


@pytest.mark.parametrize("n", [0,1,4])
def test_branch_and_loop_origin(subject,n):
    x,y = float("123.5"),float("345.5")
    for mode in ({},{"force_native":True},{"strict":True}):
        conditional=hotloop(**mode)(subject.conditional._original)
        loop=hotloop(**mode)(subject.empty_loop._original)
        for fn in (conditional,loop):
            value=fn(x,n)
            assert value==x
            assert (value is x)==(n==0)
            assert fn._last_backend=="native"
        fn=hotloop(**mode)(subject.while_alias._original)
        assert fn(x,y,n) is (x if n==0 else y)
    assert subject.choose(x,y,False) is x
    assert subject.choose(x,y,True) is y
    same = float("123.5")
    assert same == x and same is not x
    assert subject.choose(x,same,False) is x
    assert subject.choose(x,same,True) is same
    with pytest.raises(TypeError):
        subject.choose(x, same, False, x=same)


def test_defaults_and_computed_returns(subject):
    assert subject.defaulted() is subject.DEFAULT
    assert subject.defaulted(n=0) is subject.DEFAULT
    x=float("123.5")
    assert subject.defaulted(n=0,x=x) is x
    assert subject.defaulted(n=2,x=x)==247.0
    assert subject.computed(x)==x and subject.computed(x) is not x
    assert subject.computed_helper(x)==x and subject.computed_helper(x) is not x


@pytest.mark.parametrize("index", [0,1,-1,-2])
def test_list_item_identity(subject,index):
    values=[float("123.5"),float("567.25")]
    for name in ("selected","selected_alias"):
        fn=hotloop(strict=True)(getattr(subject,name)._original)
        args=(values,index) if name=="selected" else (values,index,0)
        assert fn(*args) is values[index] and fn._last_backend=="native"
    fn=hotloop(strict=True)(subject.selected_alias._original)
    assert fn(values,index,1)==values[index]
    assert fn(values,index,1) is not values[index]
    assert values==[123.5,567.25]


def test_exceptions_and_side_effects(subject):
    x=float("123.5")
    with pytest.raises(ZeroDivisionError):
        subject.exception_before_return(x,0.0)
    assert subject.exception_before_return(x,2.0) is x
    for divisor,kind in ((0,ZeroDivisionError),(1,IndexError)):
        with pytest.raises(kind):
            hotloop(strict=True)(subject.index_exception._original)([x],divisor)
    log=[]
    with pytest.raises(ZeroDivisionError):
        subject.side_effect(x,log,0)
    assert log==[1]
    assert subject.side_effect(x,log,1) is x and log==[1,1]
    before=list(log)
    with pytest.raises(HotloopNativeExecutionError):
        hotloop(strict=True)(subject.side_effect._original)(x,log,1)
    assert log==before


def test_conservative_paths(subject):
    x,y=float("123.5"),float("345.5")
    for mode in ({},{"force_native":True}):
        fn=hotloop(**mode)(subject.through_helper._original)
        assert fn(x) is x and fn._last_backend=="native"
        assert hotloop(strict=True)(subject.through_helper._original)(x) is x
        assert hotloop(**mode)(subject.selected_min._original)(x,y) is x
        result=hotloop(**mode)(subject.embedded._original)(x)
        assert type(result) is list and result[0] is x
        values=[1000,2000]
        result=hotloop(**mode)(subject.mutable_alias._original)(values)
        assert result is values and values==[1001,2000]
    for name,args in (("selected_min",(x,y)),("embedded",(x,)),
                      ("mutable_alias",([1,2],))):
        with pytest.raises(HotloopNativeExecutionError):
            hotloop(strict=True)(getattr(subject,name)._original)(*args)


def test_ownership_in_child(subject):
    script = """
import gc
from hotloop import hotloop
from origin_subject import selected, direct_text
x=float("123.5")
values=[x]
f=hotloop(strict=True)(selected._original)
r=f(values,0)
del values
gc.collect()
assert r is x
text="immutable unicode 🚀 " * 100
f=hotloop(strict=True)(direct_text._original)
assert f(text) is text
"""
    subprocess.run([sys.executable,"-c",script],cwd=Path(subject.__file__).parent,
                   timeout=60,check=True)


def test_string_and_bool_provenance_fallback(subject):
    text = "retain original text " * 20
    for name in ("sliced", "string_update"):
        for mode in ({}, {"force_native": True}):
            fn = hotloop(**mode)(getattr(subject, name)._original)
            assert fn(text) is text
            assert fn._last_backend == "native"
        fn=hotloop(strict=True)(getattr(subject,name)._original)
        assert fn(text) is text and fn._last_backend=="native"


def test_loop_target_fallback(subject):
    fn = hotloop(subject.loop_target._original)
    assert fn(123.5, 0) == 0
    assert fn(123.5, 4) == 3
    assert fn._last_backend == "python_fallback_semantics"
    with pytest.raises(HotloopNativeExecutionError):
        hotloop(strict=True)(subject.loop_target._original)(123.5, 4)


def test_unary_bool_falls_back_without_wrong_identity(tmp_path):
    path = tmp_path / "unary_bool.py"
    path.write_text("from hotloop import hotloop\n@hotloop\ndef plus_bool(x: bool) -> int:\n    return +x\n")
    ok, diagnostic, _ = MojoBackend().build_ast(path)
    assert ok, diagnostic
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = mod
    try:
        spec.loader.exec_module(mod)
        result = mod.plus_bool(True)
        assert type(result) is int and result == 1
        with pytest.raises(HotloopNativeExecutionError):
            hotloop(strict=True)(mod.plus_bool._original)(True)
    finally:
        sys.modules.pop(path.stem, None)


def test_unproven_helper_propagation(subject):
    fn = subject.computed_bool_helper
    for x, y in ((0.0, 9.0), (3.0, 9.0)):
        assert fn(x, y) == fn._original(x, y)
        assert fn._last_backend == "python_fallback_semantics"
    with pytest.raises(HotloopNativeExecutionError):
        hotloop(strict=True)(fn._original)(0.0, 9.0)


@pytest.mark.parametrize("signature", ["x", "x: float"])
def test_unannotated_function_has_compiler_diagnostic(tmp_path, signature):
    path = tmp_path / "unsupported.py"
    path.write_text(f"from hotloop import hotloop\n@hotloop\ndef unknown({signature}):\n    return x\n")
    ok, diagnostic, _ = MojoBackend().build_ast(path)
    assert not ok and "AST" in diagnostic and "annotation" in diagnostic
