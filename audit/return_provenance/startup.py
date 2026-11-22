"""Five fresh interpreter loads of already-built artifacts (OS caches stay warm).

Usage: python startup.py BENCH_DIR SECURITY_PY ORIGIN_PY CANDIDATE_PY OUT_JSON
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root,security,origin,candidate,output=sys.argv[1:]
environment=os.environ.copy()
environment.pop("PYTHONPATH",None)
probe="""
import json,time,hotloop
start=time.perf_counter()
from original import stateful_trailing_backtest as fn
loaded=time.perf_counter()
owner=float("123.5")
result=fn(0,owner,0.05,0.001)
called=time.perf_counter()
assert type(result) is float and result==owner
print(json.dumps(dict(package=hotloop.__file__,load_seconds=loaded-start,
                      call_seconds=called-loaded,identity=result is owner,backend=fn._last_backend)))
"""
rows=[]
for trial in range(5):
    order=[("baseline",security),("origin",origin),("candidate",candidate)]
    order=order[trial%3:]+order[:trial%3]
    if trial%2:
        order.reverse()
    for label,python in order:
        folder=Path(root)/(label+"-"+str(trial+1))
        start=time.perf_counter()
        row=json.loads(subprocess.check_output([python,"-c",probe],cwd=folder,env=environment))
        row.update(process_seconds=time.perf_counter()-start,label=label,trial=trial+1)
        assert row["backend"]=="native"
        assert row["identity"]==(label!="baseline")
        rows.append(row)
Path(output).write_text(json.dumps(dict(protocol="5 fresh processes per runtime; launch/load/first call; warm OS caches",rows=rows),indent=2)+"\n")
