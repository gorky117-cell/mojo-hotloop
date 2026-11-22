"""Public admission checks; injected profiles are not real cross-platform runs."""
from contextlib import contextmanager
import importlib.util
import sys
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from hotloop import hotloop,HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend
import hotloop._provenance as provenance

@pytest.fixture(scope="module")
def subject(tmp_path_factory):
    path=tmp_path_factory.mktemp("runtime-profile")/"profile_subject.py"
    path.write_text("from hotloop import hotloop\n@hotloop\ndef identity(x: float) -> float:\n    return x\n")
    ok,message,_=MojoBackend().build_ast(path)
    assert ok,message
    spec=importlib.util.spec_from_file_location("profile_subject",path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    try:yield module
    finally:sys.modules.pop(spec.name,None)

@contextmanager
def unsupported(profile):
    if profile=="architecture":
        target=patch.object(provenance.platform,"machine",return_value="aarch64")
    elif profile=="platform":
        target=patch.object(sys,"platform","darwin")
    elif profile=="pointers":
        target=patch.object(provenance.struct,"calcsize",return_value=4)
    elif profile=="byteorder":
        target=patch.object(sys,"byteorder","big")
    elif profile=="free-threaded":
        target=patch.object(provenance.sysconfig,"get_config_var",return_value=1)
    elif profile=="gil-disabled":
        target=patch.object(sys,"_is_gil_enabled",lambda:False,create=True)
    elif profile=="python":
        target=patch.object(sys,"version_info",(3,12,3))
    elif profile=="implementation":
        target=patch.object(sys,"implementation",SimpleNamespace(name="pypy",cache_tag="pypy"))
    else:
        target=patch.object(sys,"int_info",SimpleNamespace(bits_per_digit=15))
    with target:yield

@pytest.mark.parametrize("profile",["architecture","platform","pointers","byteorder","free-threaded","gil-disabled","python","implementation","pylong"])
@pytest.mark.parametrize("mode",["default","forced","strict"])
def test_unqualified_runtime_refuses_before_native_body(subject,profile,mode):
    fn=hotloop(force_native=mode=="forced",strict=mode=="strict",cache_check="import")(subject.identity._original)
    assert fn._compiled is not None
    entered=[]
    def forbidden(*args):
        entered.append(True)
        raise AssertionError("unqualified native body")
    fn._compiled.raw=forbidden
    owner=float("123.5")
    with unsupported(profile):
        if mode=="strict":
            with pytest.raises(HotloopNativeExecutionError):fn(owner)
        else:
            assert fn(owner) is owner
    assert not entered
    assert fn._call_count_native==0
    assert fn._call_count_fallback==(0 if mode=="strict" else 1)
    assert fn._last_backend==("native_error" if mode=="strict" else "python_fallback_semantics")

def test_qualified_host_executes_real_native(subject):
    fn=hotloop(strict=True)(subject.identity._original)
    owner=float("123.5")
    assert fn(owner) is owner
    assert fn._last_backend=="native" and fn._call_count_native==1
