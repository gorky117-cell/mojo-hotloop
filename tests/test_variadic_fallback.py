"""Unsupported signatures must fall back before observable Python effects."""
import importlib.util
import sys
import pytest
from hotloop import hotloop,HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend

SOURCE="""from hotloop import hotloop
@hotloop
def variadic(x: int = 7, *rest: int) -> int:
    print("BODY")
    return x
@hotloop
def keyword_variadic(x: int = 7, **options: int) -> int:
    print("BODY")
    return x
"""
@pytest.fixture(scope="module")
def subject(tmp_path_factory):
    folder=tmp_path_factory.mktemp("variadic_fallback")
    source=folder/"subject.py";source.write_text(SOURCE)
    ok,message,_=MojoBackend().build_ast(source);assert ok,message
    spec=importlib.util.spec_from_file_location("variadic_fallback_subject",source)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module

@pytest.mark.parametrize("mode",["default","forced","strict"])
@pytest.mark.parametrize("symbol",["variadic","keyword_variadic"])
def test_variadic_keyword_fallback(subject,symbol,mode,capsys):
    fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(getattr(subject,symbol)._original)
    owner=int("1000")
    if mode=="strict":
        with pytest.raises(HotloopNativeExecutionError):fn(x=owner)
        assert capsys.readouterr().out=="" and fn._call_count_fallback==0
    else:
        assert fn(x=owner) is owner
        assert capsys.readouterr().out=="BODY\n"
        assert fn._last_backend=="python_fallback_semantics" and fn._call_count_fallback==1
    assert fn._call_count_native==0
