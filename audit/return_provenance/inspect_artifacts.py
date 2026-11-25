"""Check installed runtime bytes and inspect generated backtest code; no execution."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

bench,security,origin,candidate,output=sys.argv[1:]
environment=os.environ.copy()
environment.pop("PYTHONPATH",None)
revisions={"baseline":"c2aebd78be8aebb325c94976dbc20462ad350948",
           "origin":"1a59efd4c2d6917fb6c1af06a15e7a403ae57e61",
           "candidate":os.environ.get("HOTLOOP_AUDIT_CANDIDATE_REV",subprocess.check_output(["git","rev-parse","HEAD"]).decode().strip())}
probe="""
import hashlib,json,platform,sys,sysconfig
from pathlib import Path
import hotloop,importlib.metadata
root=Path(hotloop.__file__).parent
print(json.dumps(dict(package=str(root),python=sys.version,abi=sysconfig.get_config_var("SOABI"),
 files={"hotloop/"+str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*.py")},versions={name:importlib.metadata.version(name)
        for name in ("numpy","numba","pytest","setuptools","rapidfuzz")})))
"""
records={}
bodies={}
for label,python in (("baseline",security),("origin",origin),("candidate",candidate)):
    row=json.loads(subprocess.check_output([python,"-c",probe],env=environment,cwd=Path(bench).resolve()))
    revision=revisions[label]
    files=subprocess.check_output(["git","ls-tree","-r","--name-only",revision,"hotloop"]).decode().splitlines()
    expected={p:hashlib.sha256(subprocess.check_output(["git","show",revision+":"+p])).hexdigest() for p in files}
    assert expected==row["files"],label
    row["revision"]=revision
    folder=Path(bench)/(label+"-1")
    text=(folder/"fast.mojo").read_text()
    def body(name):
        match=re.search(r"^def "+name+r"\([^\n]*\n([\s\S]*?)(?=^def |\Z)",text,re.M)
        assert match,name
        return match.group(1).strip()
    bodies[label]=body("_native_stateful_trailing_backtest")
    stem="_native_stateful_trailing_backtest" if label=="baseline" else "_native_return_origin_stateful_trailing_backtest"
    native=folder/"fast.so"
    symbols=subprocess.check_output(["nm","-S","-C",str(native)]).decode()
    matches=[line for line in symbols.splitlines() if "fast::"+stem+"(" in line]
    assert len(matches)==1,matches
    parts=matches[0].split()
    address,size=int(parts[0],16),int(parts[1],16)
    assembly=subprocess.check_output(["objdump","-d","-C","--no-show-raw-insn",
       "--start-address="+hex(address),"--stop-address="+hex(address+size),str(native)]).decode()
    (folder/"kernel.s").write_text(assembly)
    instructions=[m.group(1) for line in assembly.splitlines()
                  if (m:=re.match(r"\s*[0-9a-f]+:\s+([a-z0-9]+)",line))]
    row.update(native_binary_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
               binary_bytes=native.stat().st_size,kernel_bytes=size,
               kernel_instruction_count=len(instructions),
               kernel_fp_instructions={op:instructions.count(op) for op in sorted(set(instructions))
                   if op.endswith(("sd","ss","pd","ps"))},
               generated_sha256=hashlib.sha256(text.encode()).hexdigest())
    records[label]=row
assert bodies["baseline"]==bodies["origin"]==bodies["candidate"]
records["plain_numerical_Mojo_body_identical"]=True
records["cpu"]=subprocess.check_output(["lscpu"]).decode()
records["mojo"]=subprocess.check_output([os.environ["MOJO_BIN"],"--version"]).decode()
records["compiler"]=subprocess.check_output(["c++","--version"]).decode()
records["platform"]=platform.platform()
Path(output).write_text(json.dumps(records,indent=2)+"\n")
