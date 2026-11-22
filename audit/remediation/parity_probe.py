"""Compare ordinary scalar and array calls, and inspect unqualified layouts without dereferencing them."""

import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import struct
import subprocess
import sys
import warnings

import numpy as np

from hotloop import hotloop
import hotloop as package


def serialize(fn, args):
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        try:
            result = fn(*args)
            outcome = {"value": str(result), "type": type(result).__module__ + "." + type(result).__name__}
            if isinstance(result, float):
                outcome["bits"] = struct.pack(">d", result).hex()
        except Exception as error:
            outcome = {"exception": type(error).__name__}
    return outcome, [w.category.__name__ for w in captured]


def build(path):
    subprocess.run([sys.executable, "-m", "hotloop.cli", "build", path, "--engine=ast",
                    "--no-verify"], capture_output=True, text=True, check=True)


assert Path(package.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
source = """from hotloop import hotloop
@hotloop
def sum_squares(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i * i
    return total

@hotloop
def multiply(x: int, y: int) -> int:
    return x * y

@hotloop
def affine(x: float, y: float, z: float) -> float:
    return x * y + z

@hotloop
def decay_step(samples: list[float], decay: float) -> float:
    if len(samples) == 0:
        return 0.0
    state: float = samples[0]
    for index in range(1, len(samples)):
        state = state * decay + samples[index] * (1.0 - decay)
    return state

@hotloop
def first_value(xs: list[float]) -> float:
    return xs[0]

@hotloop
def accumulate(n: int, x: float, divisor: float) -> float:
    total: float = 0.0
    for i in range(n):
        total += x / divisor
    return total
"""
Path("numeric_case.py").write_text(source)
build("numeric_case.py")
sys.path.insert(0, str(Path.cwd()))
import numeric_case as mod

cases = [("readme_scalar", mod.sum_squares, (100_000,)),
         ("ordinary_product", mod.multiply, (-37, 53)),
         ("positive_overflow", mod.multiply, (2**62, 3)),
         ("signed_limit_product", mod.multiply, (-(2**63), -1)),
         ("signed_limit_times_one", mod.multiply, (-(2**63), 1)),
         ("float_rounding", mod.affine, (1+2**-27, 1-2**-27, -1.0)),
         ("signed_zero", mod.affine, (-0.0, 1.0, -0.0)),
         ("nan", mod.affine, (float("nan"), 1.0, 0.0)),
         ("infinity", mod.affine, (float("inf"), 1.0, 0.0)),
         ("zero_iterations", mod.accumulate, (0, 1.0, 0.0)),
         ("division_exception", mod.accumulate, (1, 1.0, 0.0)),
         ("numpy_scalar_contract", mod.first_value, (np.array([1.25]),)),
         ("strided_valid", mod.first_value, (np.arange(8,dtype=np.float64)[::2],)),
         ("float32_valid", mod.first_value, (np.array([1.25],dtype=np.float32),))]
# Well-conditioned scalar recurrence from the later development regression.
samples = list(map(float.fromhex, ("0x1.a1311af758d0bp-1", "0x1.e45af1f5c647dp-1")))
decay = float.fromhex("0x1.dca1021b09b10p-2")
forced_decay = hotloop(force_native=True)(mod.decay_step._original)
cases.append(("float_decay_list_forced", forced_decay, (samples, decay)))
rows = {}
for label, fn, args in cases:
    expected, _ = serialize(fn._original, args)
    native, emitted = serialize(fn, args)
    row = {"python":expected, "actual":native, "route":fn._last_backend,
           "warnings":emitted, "equal":expected == native}
    if label == "readme_scalar" and hasattr(package, "inspect_dispatch"):
        d = package.inspect_dispatch(fn)
        row["native_calls"], row["fallback_calls"] = d["call_count_native"], d["call_count_fallback"]
    if label in ("positive_overflow", "signed_limit_product"):
        strict = hotloop(strict=True)(fn._original)
        row["strict"], _ = serialize(strict, args)
        row["strict_route"] = strict._last_backend
    rows[label] = row

# Descriptor comparison only. Do not pass non-native-endian or unaligned storage to the native entry.
layouts = [np.ones(3,dtype=np.float64),np.ones(3,dtype=">f8"),
           np.ndarray(3,dtype=np.float64,buffer=bytearray(25),offset=1)]
descriptors = [{"name":a.dtype.name,"ndim":a.ndim,"contiguous":a.flags.c_contiguous,
                "aligned":a.flags.aligned,"native_endian":a.dtype.isnative} for a in layouts]
manifest = json.loads(Path("fast.hotloop_manifest.json").read_text())
assert manifest["so_sha256"] == hashlib.sha256(Path("fast.so").read_bytes()).hexdigest()
print(json.dumps({"version":metadata.version("mojo-hotloop"),"cases":rows,"descriptors":descriptors,
                  "manifest_keys":sorted(manifest)}, indent=2))
