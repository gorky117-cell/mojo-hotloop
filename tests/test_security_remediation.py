"""Public-contract regression tests for the 0.2.1 maintenance branch."""
import importlib.util
import math
from pathlib import Path
import struct
import subprocess
import sys
import textwrap

import numpy as np
import pytest

from hotloop import HotloopNativeExecutionError, hotloop
from hotloop.backends.mojo import MojoBackend


SOURCE = """
import math
from hotloop import hotloop

@hotloop
def sqrt_value(x: float) -> float:
    return math.sqrt(x)

@hotloop
def real_power(x: float, y: float) -> float:
    return x ** y

@hotloop
def float_floor(x: float, y: float) -> float:
    return x // y

@hotloop
def int_ratio(x: int, y: int) -> float:
    return x / y

@hotloop
def product(a: int, b: int) -> int:
    return a * b

@hotloop
def accumulate(n: int, d: float) -> float:
    total: float = 0.0
    for i in range(n):
        for j in range(i):
            if j == 1:
                break
            total += 1.0 / d
    return total

@hotloop
def skip_division(stop: bool, d: float) -> float:
    total: float = 0.0
    while True:
        if stop:
            break
        total += 1.0 / d
        break
    return total

@hotloop
def loop_else(n: int) -> int:
    for i in range(n):
        if i == 1:
            break
    else:
        return -1
    return i

@hotloop
def first(xs: list[float]) -> float:
    return xs[0]

@hotloop
def decay_step(samples: list[float], decay: float) -> float:
    state: float = samples[0]
    for i in range(1, len(samples)):
        state = state * decay + samples[i] * (1.0 - decay)
    return state

def mutate(xs: list[int]) -> list[int]:
    xs[0] = 8
    return xs

@hotloop
def through_helper(xs: list[int]) -> list[int]:
    return mutate(xs)

@hotloop
def return_alias(xs: list[int]) -> list[int]:
    alias: list[int] = xs
    return alias
"""
OPS = {"plus": "+", "minus": "-", "quotient": "//", "remainder": "%", "power": "**",
       "left_shift": "<<", "right_shift": ">>"}
for name, op in OPS.items():
    SOURCE += f"\n@hotloop\ndef {name}(a: int, b: int) -> int:\n    return a {op} b\n"


@pytest.fixture(scope="module")
def subject(tmp_path_factory):
    path = tmp_path_factory.mktemp("patch-subject") / "patch_subject.py"
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


@pytest.mark.parametrize("a,b", [
    (-(2**63), -1), (-1, -(2**63)), (-(2**63), 0), (-(2**63), 1),
    (2**63-1, 1), (2**63-1, 2), (3037000500, 3037000500), (2**70, 1),
])
def test_signed_product(subject, a, b):
    fn = subject.product
    assert fn(a, b) == a * b
    strict = hotloop(strict=True)(fn._original)
    if -(2**63) <= a * b < 2**63 and -(2**63) <= a < 2**63:
        assert fn._last_backend == "native"
        assert strict(a, b) == a * b
    else:
        assert fn._last_backend == "python_fallback_overflow"
        with pytest.raises(HotloopNativeExecutionError):
            strict(a, b)


@pytest.mark.parametrize("name,a,b,route", [
    ("plus", 2**63 - 1, 1, "python_fallback_overflow"),
    ("minus", -(2**63), 1, "python_fallback_overflow"),
    ("quotient", -(2**63), -1, "python_fallback_overflow"),
    ("remainder", -(2**63), -1, "native"),
    ("power", 3037000500, 2, "python_fallback_overflow"),
    ("power", 2, -1, "python_fallback_semantics"),
    ("left_shift", 1, 64, "python_fallback_overflow"),
    ("left_shift", -1, 63, "native"),
    ("right_shift", -1, 900, "native"),
])
def test_related_integer_operations(subject, name, a, b, route):
    fn = getattr(subject, name)
    assert fn(a,b) == fn._original(a,b)
    assert fn._last_backend == route


def test_exceptions_and_control_flow(subject):
    assert subject.accumulate(1, 0.0) == 0.0
    assert subject.accumulate._last_backend == "native"
    assert subject.skip_division(True, 0.0) == 0.0
    assert subject.skip_division._last_backend == "native"
    with pytest.raises(ZeroDivisionError):
        subject.accumulate(2, 0.0)
    with pytest.raises(ValueError):
        subject.left_shift(1, -1)
    for n in (0, 1, 2):
        assert subject.loop_else(n) == subject.loop_else._original(n)
        assert subject.loop_else._last_backend == "python_fallback"
    with pytest.raises(HotloopNativeExecutionError):
        hotloop(strict=True)(subject.loop_else._original)(0)


@pytest.mark.parametrize("name", ["through_helper", "return_alias"])
def test_borrowed_identity_and_mutation(subject, name):
    fn = getattr(subject, name)
    for forced in (False, True):
        wrapped = hotloop(force_native=forced)(fn._original)
        value = [1, 2]
        assert wrapped(value) is value
        assert value == ([8, 2] if name == "through_helper" else [1, 2])
        assert wrapped._last_backend == "python_fallback"
    value = [1, 2]
    strict = hotloop(strict=True)(fn._original)
    with pytest.raises(HotloopNativeExecutionError):
        strict(value)
    assert strict._last_backend == "native_error"
    assert strict._call_count_fallback == strict._call_count_native == 0
    assert value == [1, 2]


@pytest.mark.parametrize("values", [
    [float.fromhex("0x1.a1311af758d0bp-1"), float.fromhex("0x1.e45af1f5c647dp-1")],
    [-0.0, -0.0], [float("inf"), 1.0], [float("nan"), 1.0],
])
def test_separate_float_rounding(subject, values):
    f = hotloop(strict=True)(subject.decay_step._original)
    decay = float.fromhex("0x1.dca1021b09b10p-2")
    expected = f._original(values, decay)
    actual = f(values, decay)
    assert math.isnan(actual) if math.isnan(expected) else struct.pack(">d",actual) == struct.pack(">d",expected)
    assert f._last_backend == "native"


def test_buffer_boundary_in_child(subject):
    # All exports below are valid Python buffers. Assert route as well as value/type.
    work = Path(subject.__file__).parent
    child = """
import array, threading
import numpy as np
from patch_subject import first
from hotloop import hotloop, HotloopNativeExecutionError
strict = hotloop(strict=True)(first._original)
forced = hotloop(force_native=True)(first._original)
storage = array.array('d', [1.25, 3.5])
readonly = memoryview(storage).toreadonly()
unaligned = np.ndarray(2, dtype='float64', buffer=bytearray(17), offset=1)
for obj in (storage, readonly, memoryview(storage), np.ones(2), np.arange(6.)[::2],
            np.ones(3, dtype='>f8'), unaligned, np.ones(3,dtype='f4'), np.ones((2,2))):
    expected = first._original(obj)
    for fn in (first, forced):
        result = fn(obj)
        assert type(result) is type(expected) and np.array_equal(result,expected)
        assert fn._last_backend == 'python_fallback_semantics'
    with_rejected = False
    try:
        strict(obj)
    except HotloopNativeExecutionError:
        with_rejected = True
    assert with_rejected
try:
    first(np.array([]))
except IndexError:
    pass
else:
    raise AssertionError("empty input lost its Python exception")
readonly.release()
storage.append(8.)
view = memoryview(storage)
view.release()
try:
    first(view)
except ValueError:
    pass
else:
    raise AssertionError("released view was accepted")
thread = threading.Thread(target=lambda: storage.__setitem__(0, 3.0))
thread.start()
assert first(storage) in (1.25, 3.0)
thread.join()
assert first._last_backend == 'python_fallback_semantics'
"""
    subprocess.run([sys.executable, "-c", textwrap.dedent(child)], cwd=work, check=True, timeout=60)


def test_generated_bounds_and_buffer_contract(subject):
    source = Path(subject.__file__).with_name("fast.mojo").read_text()
    assert "unsafe_from_address" not in source and "ctypes.data" not in source
    assert "_safe_array_index" not in source and "get_cp_fast" not in source
    assert "_checked_index(" in source
    assert "_pywrap_through_helper" not in source


def test_exception_and_rounding_edges(subject):
    assert subject.float_floor(1.0, 0.1) == 9.0
    assert subject.float_floor._last_backend == "python_fallback_semantics"
    assert subject.real_power(-1.0, 0.5) == (-1.0) ** 0.5
    assert subject.real_power._last_backend == "python_fallback_semantics"
    with pytest.raises(OverflowError):
        subject.real_power(1e200, 2.0)
    assert subject.int_ratio(2**60 + 123, 17) == (2**60 + 123) / 17
    assert subject.int_ratio._last_backend == "python_fallback_semantics"
    with pytest.raises(ValueError):
        subject.sqrt_value(-1.0)
    assert subject.sqrt_value(-0.0).hex() == (-0.0).hex()
