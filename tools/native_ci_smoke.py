"""A correct fallback is a failure for this required-native smoke."""
import argparse
import importlib.util
from pathlib import Path
import sys
from hotloop.backends.mojo import MojoBackend

p=argparse.ArgumentParser();p.add_argument("--directory",type=Path,required=True);args=p.parse_args()
args.directory.mkdir()
source=args.directory/"native_smoke.py"
source.write_text("from hotloop import hotloop\n@hotloop\ndef sum_squares(n: int) -> int:\n    total: int = 0\n    for i in range(n):\n        total += i*i\n    return total\n")
ok,diagnostic,_=MojoBackend().build_ast(source);assert ok,diagnostic
spec=importlib.util.spec_from_file_location("native_smoke",source)
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
got=mod.sum_squares(50000)
assert type(got) is int and got==sum(i*i for i in range(50000))
assert mod.sum_squares._last_backend=="native"
assert mod.sum_squares._call_count_native==1 and mod.sum_squares._call_count_fallback==0
print("Verified automatically generated Mojo via public @hotloop")
