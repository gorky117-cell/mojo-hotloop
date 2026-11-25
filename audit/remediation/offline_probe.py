"""Functional acceptance checks using only the installed wheel and a preinstalled Mojo."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings

import hotloop
from hotloop.backends.mojo import MojoBackend


def run(*args):
    return subprocess.run([sys.executable, "-m", "hotloop.cli", "build", *args],
                          text=True, capture_output=True)


def read_case():
    out = subprocess.check_output([sys.executable, "-c", """
import json, warnings
from hotloop import hotloop
from myapp import running_sum
with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    result = running_sum([1.,2.,3.,4.,5.])
route = running_sum._last_backend
strict = hotloop(strict=True)(running_sum._original)
try:
    strict_result = strict([1.,2.,3.,4.,5.])
except Exception as exc:
    strict_result = type(exc).__name__
print(json.dumps([result, route, strict_result, strict._last_backend, [w.category.__name__ for w in caught]]))
"""], text=True)
    return json.loads(out)


assert Path(hotloop.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
assert importlib.util.find_spec("numpy") is None
assert importlib.util.find_spec("google") is None
Path("myapp.py").write_text("""from hotloop import hotloop
@hotloop
def running_sum(values: list[float]) -> float:
    total: float = 0.0
    for i in range(len(values)):
        total += values[i]
    return total
""")
before = read_case()
assert before[:3] == [15.0, "python_fallback", "HotloopNativeExecutionError"]
summaries = {}
for opts in ((), ("--engine=ast",), ("--engine=auto",)):
    proc = run("myapp.py", *opts)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    summaries[" ".join(opts) or "default"] = hashlib.sha256(Path("fast.mojo").read_bytes()).hexdigest()
assert len(set(summaries.values())) == 1
after = read_case()
assert after[:4] == [15.0, "python_fallback_slower", 15.0, "native"]
Path("unsupported.py").write_text("from hotloop import hotloop\n@hotloop\ndef unknown(x):\n    return x\n")
rejected = run("unsupported.py", "--engine=auto")
assert rejected.returncode != 0 and "AST" in rejected.stdout + rejected.stderr
assert run("myapp.py", "--engine=gemini").returncode != 0
assert not MojoBackend().build("myapp.py", engine="gemini")[0]
print(json.dumps({"package":str(Path(hotloop.__file__)), "before":before,"after":after,
                  "generated_sha256":summaries,"unsupported_auto_exit":rejected.returncode,
                  "manifest_fields":sorted(json.loads(Path("fast.hotloop_manifest.json").read_text()))}))
