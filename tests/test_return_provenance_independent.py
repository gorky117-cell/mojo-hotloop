"""Independent owner, lifetime, string and pre-effect qualification cases."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import pytest
from hotloop import hotloop,HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend

SOURCE="""from hotloop import hotloop
@hotloop
def literal_value(x: float, choose: bool) -> float:
    if choose:
        return x
    return 19.75
@hotloop
def folded_value(x: float) -> float:
    result: float = 1.25 + 1.25
    return result
@hotloop
def signed_value(x: float) -> float:
    return -0.0
def helper_value() -> float:
    return 19.75
@hotloop
def choose_helper(x: float, choose: bool) -> float:
    if choose:
        return x
    return helper_value()
def helper_argument(x: float) -> float:
    return x
@hotloop
def helper_alias(x: float) -> float:
    return helper_argument(x)
def helper_text(x: str) -> str:
    return x
@hotloop
def helper_string(x: str) -> str:
    return helper_text(x)
@hotloop
def full_slice(text: str, start: int, end: int, step: int) -> str:
    value: str = text[start:end:step]
    return value
@hotloop
def concat_pair(left: str, right: str) -> str:
    return left + right
@hotloop
def append_pair(left: str, right: str) -> str:
    value: str = left
    value += right
    return value
@hotloop
def repeated_builder(text: str, count: int) -> str:
    value: str = ""
    for i in range(count):
        value += text[:]
    return value
@hotloop
def constant_builder(text: str) -> str:
    value: str = ""
    value += "constant owner text"
    return value
@hotloop
def constant_alias(text: str) -> str:
    value: str = "constant owner text"
    other: str = value
    return other[:]
@hotloop
def default_owner(x: float = 19.75, choose: bool = False) -> float:
    if choose:
        return x
    return 19.75
@hotloop
def first_owner(values: list[str], index: int) -> str:
    return values[index]
@hotloop
def ordered_print(x: float) -> float:
    print("effect")
    return helper_value()
@hotloop
def integer_remainder(x: int, y: int) -> int:
    return x % y
@hotloop
def inplace_remainder(x: int, y: int) -> int:
    value: int = x
    value %= y
    return value
@hotloop
def format_counter(x: int) -> str:
    return str(x)
@hotloop
def shared_output(x: int) -> list[int]:
    value: int = x + 0
    alias: int = int(value)
    result: list[int] = []
    result.append(value)
    result.append(alias)
    return result
@hotloop
def repeated_output(x: int, count: int) -> list[int]:
    value: int = x + 0
    result: list[int] = []
    for i in range(count):
        value = value
        result.append(value)
    return result
def fresh_character(code: int) -> str:
    return chr(code)
@hotloop
def helper_append_once(code: int) -> str:
    value: str = ""
    value += fresh_character(code)
    return value
@hotloop
def nested_container_sharing(x: int) -> list[int]:
    values: list[int] = [x + 0]
    result: list[int] = []
    result.append(helper_argument(values[0]))
    result.append(helper_argument(values[0]))
    return result
@hotloop
def conditional_expression(x: str, y: str, choose: bool) -> str:
    return x if choose else y
"""

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

@pytest.fixture(scope="module")
def subject(tmp_path_factory):
    path=tmp_path_factory.mktemp("independent-provenance")/"owners.py"
    path.write_text(SOURCE)
    # Keep unsupported ternary in a separate module: no change to its Python body.
    ternary=SOURCE[SOURCE.index("@hotloop\ndef conditional_expression"):]
    path.write_text(SOURCE[:SOURCE.index("@hotloop\ndef conditional_expression")])
    ok,diagnostic,_=MojoBackend().build_ast(path)
    assert ok,diagnostic
    mod=load(path,"owners")
    yield mod
    sys.modules.pop("owners",None)

@pytest.mark.parametrize("mode",["default","forced","strict"])
def test_actual_constant_sites(subject,mode):
    f=lambda name:hotloop(force_native=mode=="forced",strict=mode=="strict")(getattr(subject,name)._original)
    argument=float("19.75")
    for name,args in (("literal_value",(argument,False)),("folded_value",(argument,)),
                      ("signed_value",(argument,)),("choose_helper",(argument,False)),
                      ("constant_builder",("ignored",)),("constant_alias",("ignored",))):
        fn=f(name)
        owner=fn._original(*args)
        assert fn(*args) is owner
        assert fn._last_backend=="native"
    for name in ("literal_value","choose_helper"):
        assert f(name)(argument,True) is argument
    assert f("helper_alias")(argument) is argument
    text="helper keeps actual input 🚀"*10
    assert f("helper_string")(text) is text

@pytest.mark.parametrize("mode",["default","forced","strict"])
@pytest.mark.parametrize("left,right",[("",""),("","dynamic value"),("dynamic value",""),("left","right"),("नमस्ते","🚀")])
def test_concatenation(subject,mode,left,right):
    left=left.encode().decode()
    right=right.encode().decode()
    for name in ("concat_pair","append_pair"):
        fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(getattr(subject,name)._original)
        expected=fn._original(left,right)
        actual=fn(left,right)
        assert type(actual) is str and actual==expected and fn._last_backend=="native"
        for owner in (left,right):
            assert (actual is owner)==(expected is owner)

@pytest.mark.parametrize("text",["","a","abc","नमस्ते🚀","🚀"])
@pytest.mark.parametrize("bounds",[(0,1000,1),(-1000,1000,1),(0,2,1),(0,1000,2),(-1000,1000,-1)])
def test_slice_bounds(subject,text,bounds):
    fn=hotloop(strict=True)(subject.full_slice._original)
    expected=fn._original(text,*bounds)
    actual=fn(text,*bounds)
    assert type(actual) is str and actual==expected and fn._last_backend=="native"
    assert (actual is text)==(expected is text)
    with pytest.raises(ValueError):
        fn(text,0,1,0)

@pytest.mark.parametrize("count",[0,1,2,5])
def test_builder_loop(subject,count):
    text="owner string 🚀 "*10
    fn=hotloop(strict=True)(subject.repeated_builder._original)
    expected=fn._original(text,count)
    actual=fn(text,count)
    assert actual==expected and (actual is text)==(expected is text)
    assert fn._last_backend=="native"

def test_defaults_distinct_from_code_constant(subject):
    original=subject.default_owner._original
    old=original.__defaults__
    argument=float("19.75")
    original.__defaults__=(argument,False)
    try:
        fn=hotloop(strict=True)(original)
        owner=original()
        assert owner==argument and owner is not argument
        assert fn() is owner and fn(choose=True) is argument
    finally:
        original.__defaults__=old

def test_helper_actual_code_owner(subject):
    helper=subject.helper_value
    old=helper.__code__
    pool=list(old.co_consts)
    index=next(i for i,value in enumerate(pool) if type(value) is float)
    owner=float(str(pool[index]))
    assert owner is not pool[index]
    pool[index]=owner
    helper.__code__=old.replace(co_consts=tuple(pool))
    try:
        fn=hotloop(strict=True)(subject.choose_helper._original)
        assert fn(float("19.75"),False) is owner
        assert fn._last_backend=="native"
    finally:
        helper.__code__=old

def test_alternate_import_owners(subject):
    other=load(Path(subject.__file__),"alternate_owners")
    try:
        x=float("19.75")
        for module in (subject,other):
            fn=hotloop(strict=True)(module.literal_value._original)
            assert fn(x,False) is fn._original(x,False)
            assert fn._last_backend=="native"
    finally:
        sys.modules.pop("alternate_owners",None)

def test_helper_rebinding_before_effects(subject,capfd):
    fn=hotloop(subject.ordered_print._original)
    assert fn(1.0)==19.75
    assert capfd.readouterr().out=="effect\n"
    previous=subject.helper_value
    replacement=lambda: float("37.25")
    subject.helper_value=replacement
    try:
        assert fn(1.0)==37.25
        assert capfd.readouterr().out=="effect\n"
        assert fn._last_backend=="python_fallback_semantics"
        with pytest.raises(HotloopNativeExecutionError):
            hotloop(strict=True)(subject.ordered_print._original)(1.0)
        assert capfd.readouterr().out==""
    finally:
        subject.helper_value=previous

def test_root_default_change_refuses_before_effects(subject):
    fn=hotloop(subject.default_owner._original)
    assert fn()==19.75
    original=fn._original
    before=original.__defaults__
    owner=float("22.5")
    original.__defaults__=(owner,True)
    try:
        assert fn() is owner and fn._last_backend=="python_fallback_semantics"
        # A newly bound wrapper can safely establish the new defaults.
        assert hotloop(strict=True)(original)() is owner
    finally:
        original.__defaults__=before

def test_unknown_code_constants_do_not_call_repr(subject,capfd):
    class Opaque:
        def __repr__(self):
            print("repr effect")
            return "opaque"
    original=subject.ordered_print._original
    code=original.__code__
    original.__code__=code.replace(co_consts=(*code.co_consts,Opaque()))
    try:
        fn=hotloop(original)
        assert fn(1.0)==19.75
        assert capfd.readouterr().out=="effect\n"
        with pytest.raises(HotloopNativeExecutionError):
            hotloop(strict=True)(original)(1.0)
        assert capfd.readouterr().out==""
    finally:
        original.__code__=code

def test_list_element_and_lifetime(subject):
    fn=hotloop(strict=True)(subject.first_owner._original)
    owner="list object 🚀"*20
    values=[owner]
    result=fn(values,-1)
    del values
    assert result is owner and fn._last_backend=="native"
    with pytest.raises(IndexError):
        fn([],0)

def test_ternary_remains_safe_fallback(tmp_path):
    source=SOURCE[SOURCE.index("@hotloop\ndef conditional_expression"):]
    path=tmp_path/"conditional_owner.py"
    path.write_text("from hotloop import hotloop\n"+source)
    ok,_,_=MojoBackend().build_ast(path)
    assert not ok
    mod=load(path,path.stem)
    try:
        x,y="arg one "*10,"arg two "*10
        assert mod.conditional_expression(x,y,True) is x
        with pytest.raises(HotloopNativeExecutionError):
            hotloop(strict=True)(mod.conditional_expression._original)(x,y,False)
    finally:
        sys.modules.pop(path.stem,None)


@pytest.mark.parametrize("x,y",[(1000,2000),(1000,2**32),(2**40,2**41),(-1000,-2000),(-1000,-2**32),(-2**40,-2**41),(1000,-2**32),(-1000,2**32),(2**40+1,2**40+2),(-2**40-1,-2**40-2),(-(2**63),-1),(2**30,2**31),(2**60,2**61)])
@pytest.mark.parametrize("mode",["default","forced","strict"])
def test_integer_remainder_origin(subject,x,y,mode):
    # Construct independent non-cached int owners.
    x,y=int(str(x)),int(str(y))
    fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(subject.integer_remainder._original)
    expected=fn._original(x,y)
    actual=fn(x,y)
    assert actual==expected and (actual is x)==(expected is x)
    assert fn._last_backend=="native"

@pytest.mark.parametrize("number",[0,1,7,10,12345,-17])
def test_fresh_integer_formatting(subject,number):
    fn=hotloop(strict=True)(subject.format_counter._original)
    first=fn(number)
    second=fn(number)
    assert first==str(number) and first is not second
    assert fn._last_backend=="native"

@pytest.mark.parametrize("name,args",[("shared_output",(2**40,)),("repeated_output",(2**40,3))])
def test_unknown_container_sharing_falls_back(subject,name,args):
    original=getattr(subject,name)._original
    for mode in ({},{"force_native":True}):
        fn=hotloop(**mode)(original)
        result=fn(*args)
        assert result[0] is result[1]
        assert fn._last_backend.startswith("python")
    with pytest.raises(HotloopNativeExecutionError):
        hotloop(strict=True)(original)(*args)


def test_inplace_remainder_and_random_boundaries(subject):
    import random
    rng=random.Random(20261122)
    fn=hotloop(strict=True)(subject.inplace_remainder._original)
    for i in range(1200):
        x=rng.randrange(-(2**63),2**63)
        y=rng.randrange(-(2**63),2**63) or 1
        if i%4==0:
            x=rng.randrange(-2000,2000)
        if i%5==0:
            y=rng.choice((2**30,2**60,2**63-1,-2**63))
        original=fn._original(x,y)
        result=fn(x,y)
        assert result==original and (result is x)==(original is x),(x,y)
        assert fn._last_backend=="native"


def test_nested_definition_stays_python_without_preexecution(tmp_path):
    source="""from hotloop import hotloop
@hotloop
def outer(events: list[int]) -> float:
    events.append(1)
    def nested() -> float:
        return 19.75
    return nested()
"""
    path=tmp_path/"nested_scope.py"
    path.write_text(source)
    ok,diagnostic,_=MojoBackend().build_ast(path)
    assert not ok and "AST" in diagnostic
    mod=load(path,path.stem)
    try:
        events=[]
        expected=mod.outer._original([])
        assert mod.outer(events) is expected and events==[1]
        with pytest.raises(HotloopNativeExecutionError):
            hotloop(strict=True)(mod.outer._original)(events)
        assert events==[1]
    finally:
        sys.modules.pop(path.stem,None)


def test_augmented_helper_rhs_executes_once(subject):
    path=Path(subject.__file__).with_name("fast.mojo")
    generated=path.read_text()
    header="def _native_return_origin_helper_append_once("
    body=generated.split(header,1)[1].split("\ndef ",1)[0]
    assert body.count("_native_fresh_character(")==1
    fn=hotloop(strict=True)(subject.helper_append_once._original)
    for code in (97,233,0x1f680):
        assert fn(code)==chr(code) and fn._last_backend=="native"


def test_indirect_container_sharing_is_not_boxed_twice(subject):
    fn=hotloop(force_native=True)(subject.nested_container_sharing._original)
    value=fn(int("1234567890123"))
    assert value[0] is value[1] and fn._last_backend=="python_fallback_semantics"
    with pytest.raises(HotloopNativeExecutionError):
        hotloop(strict=True)(fn._original)(int("1234567890123"))


@pytest.mark.parametrize("signature,call",[
    ("x: float, /",lambda fn,x:fn(x)),
    ("x: float, *, flag: bool = True",lambda fn,x:fn(x,flag=False)),
])
def test_unsupported_signature_refuses_before_stream_effects(tmp_path,capfd,signature,call):
    path=tmp_path/"signature_owner.py"
    path.write_text(f'from hotloop import hotloop\n@hotloop\ndef f({signature}) -> float:\n    print("effect")\n    return x\n')
    ok,diagnostic,_=MojoBackend().build_ast(path)
    assert ok,diagnostic
    mod=load(path,path.stem)
    try:
        owner=float("123.5")
        assert call(mod.f,owner) is owner
        assert capfd.readouterr().out=="effect\n"
        with pytest.raises(HotloopNativeExecutionError):
            call(hotloop(strict=True)(mod.f._original),owner)
        assert capfd.readouterr().out==""
    finally:
        sys.modules.pop(path.stem,None)

@pytest.fixture(scope="module")
def helper_imported_before_build(tmp_path_factory):
    path=tmp_path_factory.mktemp("helper-before-build")/"helper_subject.py"
    path.write_text("from hotloop import hotloop\n@hotloop(strict=True)\ndef strict_helper(x: float) -> float:\n    return x\n@hotloop\ndef parent(x: float) -> float:\n    return strict_helper(x)\n")
    spec=importlib.util.spec_from_file_location("helper_subject",path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    assert module.strict_helper._compiled is None
    ok,diagnostic,_=MojoBackend().build_ast(path)
    assert ok,diagnostic
    try:
        yield module
    finally:
        sys.modules.pop(spec.name,None)

@pytest.mark.parametrize("mode",["default","forced","strict"])
def test_decorated_helper_policy_is_preserved(helper_imported_before_build,mode):
    module=helper_imported_before_build
    with pytest.raises(HotloopNativeExecutionError):
        module.parent._original(2.5)
    fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(module.parent._original)
    assert fn._compiled is not None
    with pytest.raises(HotloopNativeExecutionError):
        fn(2.5)
    assert fn._call_count_native==0
    assert fn._call_count_fallback==(0 if mode=="strict" else 1)
    assert fn._last_backend==("native_error" if mode=="strict" else "python_fallback_semantics")
