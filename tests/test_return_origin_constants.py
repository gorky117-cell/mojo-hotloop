"""Release-blocking constant identity cases. These must not be marked xfail.

CPython shares each default float with the function/module's returned constant.
Returning an argument is not the only way a return can alias that argument.
"""
import importlib.util
import sys
import pytest
from hotloop import hotloop, HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend

SOURCE = """from hotloop import hotloop
@hotloop
def literal_default(x: float = 1.25) -> float:
    return 1.25
@hotloop
def local_constant(x: float = 1.25) -> float:
    value: float = 1.25
    return value
def helper_constant() -> float:
    return 1.25
@hotloop
def helper_default(x: float = 1.25) -> float:
    return helper_constant()
"""

@pytest.fixture(scope="module")
def subject(tmp_path_factory):
    path = tmp_path_factory.mktemp("return-constant") / "constant_subject.py"
    path.write_text(SOURCE)
    ok, diagnostic, _ = MojoBackend().build_ast(path)
    assert ok, diagnostic
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
        yield mod
    finally:
        sys.modules.pop(spec.name, None)

@pytest.mark.parametrize("name", ["literal_default","local_constant","helper_default"])
@pytest.mark.parametrize("mode", ["default","forced","strict"])
def test_shared_default_constant_identity(subject, name, mode):
    original = getattr(subject,name)._original
    owner = original.__defaults__[0]
    assert original() is owner
    fn = hotloop(force_native=mode=="forced", strict=mode=="strict")(original)
    try:
        result = fn()
    except HotloopNativeExecutionError:
        # Conservative qualification is acceptable; strict must not run Python.
        assert mode == "strict"
        return
    assert type(result) is float and result == owner
    assert result is owner, (
        f"{name}: {mode} returned a new float through {fn._last_backend}; "
        "the original returns the exact default argument object")
