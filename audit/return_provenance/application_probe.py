"""Run an unchanged verifier in its isolated process; observe actual wrappers."""
import importlib
import json
from pathlib import Path
import runpy
import sys

app,output=sys.argv[1:]
factory=importlib.import_module("hotloop.decorator")._create_hotloop_wrapper
wrappers=[]
def observe(frame,event,value):
    if event=="return" and frame.f_code is factory.__code__:
        if callable(value) and hasattr(value,"_call_count_native"):
            wrappers.append(value)
# Observe factory returns without replacing functions or changing verifier bodies.
sys.setprofile(observe)
if app=="quant_backtest":
    # This process is already isolated. Execute the original worker body, including
    # all original cases, instead of launching an unobserved second interpreter.
    sys.argv.append("--worker")
try:
    runpy.run_path("examples/"+app+"/verify.py",run_name="__main__")
except SystemExit as error:
    if error.code not in (None,0):
        raise
finally:
    sys.setprofile(None)
rows=[]
for fn in wrappers:
    rows.append(dict(function=fn.__qualname__,native_calls=fn._call_count_native,
                     fallback_calls=fn._call_count_fallback,last_backend=fn._last_backend))
assert rows,app
Path(output).write_text(json.dumps(dict(application=app,public_wrappers=rows),indent=2)+"\n")
