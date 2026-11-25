"""Refuse unqualified pre-import bindings before any native user-body call."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
from hotloop.backends.mojo import MojoBackend

SOURCE = """import math
from hotloop import hotloop
@hotloop
def square_root(x: float) -> float:
    return math.sqrt(x) + 1.0
@hotloop
def absolute(x: float) -> float:
    return abs(x) + 1.0
@hotloop
def pi_scale(x: float) -> float:
    return math.pi * x
"""
PATCHES = [
    ("sqrt_lambda", "math.sqrt = lambda x: 123.0", "square_root"),
    ("sqrt_alias", "math.sqrt = math.sin", "square_root"),
    ("sqrt_spoofed_function", "def replacement(x): return 123.0\nreplacement.__name__ = 'sqrt'\nreplacement.__module__ = 'math'\nmath.sqrt = replacement", "square_root"),
    ("abs_lambda", "builtins.abs = lambda x: 123.0", "absolute"),
    ("abs_alias", "builtins.abs = builtins.round", "absolute"),
    ("pi_replaced", "math.pi = 123.0", "pi_scale"),
]
DRIVER = r"""import builtins, importlib.util, json, math, pathlib, sys, types
patch, symbol, mode, source = sys.argv[1:]
exec(patch)
# No Hotloop/provenance import precedes the replacement in this subprocess.
from hotloop import hotloop, HotloopNativeExecutionError
spec = importlib.util.spec_from_file_location("preimport_subject", source)
module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module; spec.loader.exec_module(module)
original = getattr(module, symbol)._original
fn = hotloop(force_native=mode=="forced", strict=mode=="strict")(original)
assert fn._compiled is not None, fn._fallback_reason
entries = []
raw = fn._compiled.raw
def forbidden(*args):
    entries.append("native-body")
    return raw(*args)
fn._compiled.raw = forbidden
expected = original(-9.0)
error = None
try:
    got = fn(-9.0)
except Exception as exception:
    got = None; error = type(exception).__name__
record = dict(expected=expected, got=got, error=error, backend=fn._last_backend,
              entered=len(entries), native_calls=fn._call_count_native, fallback_calls=fn._call_count_fallback)
print(json.dumps(record))
assert not entries, record
if mode == "strict":
    assert error == "HotloopNativeExecutionError" and fn._call_count_fallback == 0, record
else:
    assert error is None and type(got) is type(expected) and got == expected, record
    assert fn._last_backend == "python_fallback_semantics" and fn._call_count_fallback == 1, record
"""
@pytest.fixture(scope="module")
def compiled_subject(tmp_path_factory):
    folder = tmp_path_factory.mktemp("preimport_bindings")
    source = folder / "subject.py"; source.write_text(SOURCE)
    ok, message, _ = MojoBackend().build_ast(source)
    assert ok, message
    driver = folder / "driver.py"; driver.write_text(DRIVER)
    return source, driver

@pytest.mark.parametrize("mode", ["default", "forced", "strict"])
@pytest.mark.parametrize("name,patch,symbol", PATCHES, ids=[x[0] for x in PATCHES])
def test_preimport_replacements_refuse_native(compiled_subject, name, patch, symbol, mode):
    source, driver = compiled_subject
    process = subprocess.run([sys.executable, str(driver), patch, symbol, mode, str(source)],
                             capture_output=True, text=True, timeout=60)
    assert process.returncode == 0, process.stdout + process.stderr

def test_authentic_bindings_still_run_native(compiled_subject):
    source, _ = compiled_subject
    code = """import importlib.util, pathlib, sys
p = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('canonical_subject', p)
m = importlib.util.module_from_spec(spec); sys.modules[spec.name] = m; spec.loader.exec_module(m)
for symbol in ('square_root', 'absolute', 'pi_scale'):
    f = getattr(m, symbol); x = 9.0
    assert f(x) == f._original(x) and f._last_backend == 'native'
"""
    process = subprocess.run([sys.executable, "-c", code, str(source)],capture_output=True,text=True,timeout=60)
    assert process.returncode == 0, process.stdout + process.stderr
