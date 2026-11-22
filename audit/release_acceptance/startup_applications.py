"""Five fresh interpreters per candidate application; warm OS caches."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from measure_applications import FUNCTIONS,payloads
root=Path(__file__).resolve().parents[2]
bench,python,out=sys.argv[1:]
bench=Path(bench);out=Path(out)
env=os.environ.copy();env.pop("PYTHONPATH",None)
program="""
import importlib,json,sys,time
from pathlib import Path
start=time.perf_counter()
module=importlib.import_module("original")
loaded=time.perf_counter()
args=json.loads(Path("startup-input.json").read_text())
prepared=time.perf_counter()
fn=getattr(module,sys.argv[1]);actual=fn(*args)
called=time.perf_counter()
expected=fn._original(*args)
assert type(actual) is type(expected) and actual==expected
if sys.argv[1]=="stateful_trailing_backtest":assert actual is args[1]
print(json.dumps(dict(import_seconds=loaded-start,input_seconds=prepared-loaded,
 call_seconds=called-prepared,backend=fn._last_backend,result_type=type(actual).__name__)))
"""
rows=[]
for trial in range(1,6):
 for app,name in FUNCTIONS.items():
  folder=bench/("candidate-"+str(trial))/app
  args=payloads(root,app)[0][1]
  (folder/"startup-input.json").write_text(json.dumps(args))
  start=time.perf_counter()
  row=json.loads(subprocess.check_output([python,"-c",program,name],cwd=folder,env=env))
  row.update(application=app,trial=trial,launch_import_input_call_and_oracle_seconds=time.perf_counter()-start)
  rows.append(row)
out.write_text(json.dumps(dict(protocol="5 fresh processes/application; original smallest inputs; OS caches stay warm",rows=rows),indent=2)+"\n")
