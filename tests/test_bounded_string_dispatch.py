"""Keep bounded Unicode prefix/suffix calls in Python until parity is proven."""
import importlib.util
from pathlib import Path
import sys
import pytest
from hotloop import hotloop, HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend

SOURCE = 'from hotloop import hotloop\n@hotloop(force_native=True)\ndef prefix(s: str, p: str, start: int, end: int) -> bool:\n    return s.startswith(p, start, end)\n@hotloop(force_native=True)\ndef subprefix(s: str, p: str, start: int, end: int) -> bool:\n    if len(s) > 0:\n        c: str = s[0]\n    return s.startswith(p, start, end)\n@hotloop(force_native=True)\ndef suffix(s: str, p: str, start: int, end: int) -> bool:\n    return s.endswith(p, start, end)\n@hotloop(force_native=True)\ndef subsuffix(s: str, p: str, start: int, end: int) -> bool:\n    if len(s) > 0:\n        c: str = s[0]\n    return s.endswith(p, start, end)\n\n@hotloop\ndef keyword_prefix(s: str) -> bool:\n    return s.startswith("a", start=1)\n'
@pytest.fixture(scope="module")
def subject(tmp_path_factory):
    folder=tmp_path_factory.mktemp("bounded_strings")
    source=folder/"subject.py";source.write_text(SOURCE)
    ok,message,_=MojoBackend().build_ast(source);assert ok,message
    spec=importlib.util.spec_from_file_location("bounded_string_subject",source)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module

@pytest.mark.parametrize("mode",["default","forced","strict"])
@pytest.mark.parametrize("symbol",["prefix","subprefix","suffix","subsuffix"])
def test_bounded_string_calls_use_semantic_policy(subject,symbol,mode):
    original=getattr(subject,symbol)._original
    fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(original)
    for s in ("","abc","नमस्ते","é🚀","aé🚀z"):
        for prefix in ("","a","é","🚀","न"):
            for start,end in ((0,99),(1,99),(2,99),(3,99),(99,99),(-1,99),(-99,99),(0,0),(0,1),(1,2)):
                args=(s,prefix,start,end)
                if mode=="strict":
                    with pytest.raises(HotloopNativeExecutionError):fn(*args)
                    assert fn._call_count_fallback==0
                else:
                    expected=original(*args);got=fn(*args)
                    assert type(got) is type(expected) and got is expected
                    assert fn._last_backend=="python_fallback_semantics"
                assert fn._call_count_native==0

@pytest.mark.parametrize("mode",["default","forced","strict"])
def test_prefix_keyword_exception_policy(subject,mode):
    fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(subject.keyword_prefix._original)
    error=HotloopNativeExecutionError if mode=="strict" else TypeError
    with pytest.raises(error):fn("abc")
    assert fn._call_count_native==0
