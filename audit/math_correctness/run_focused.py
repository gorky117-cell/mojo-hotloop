"""Focused CPython-oracle matrix; classification never equates fallback with native."""
import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import struct
import sys
import time
import warnings
from hotloop import hotloop,HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend

def wire(value):
    kind=type(value).__module__+"."+type(value).__qualname__
    if type(value) is float:return dict(type=kind,bits=struct.pack(">d",value).hex())
    if type(value) in (int,bool,str) or value is None:return dict(type=kind,value=value)
    raise TypeError(kind)

def invoke(fn,args):
    output=io.StringIO()
    with warnings.catch_warnings(record=True) as notes,contextlib.redirect_stdout(output):
        warnings.simplefilter("always")
        try:value=fn(*args);result=dict(result=wire(value),exception=None)
        except Exception as error:result=dict(exception=type(error).__name__,message=str(error))
    result["stdout"]=output.getvalue()
    return result

def cases():
    nan=struct.unpack(">d",bytes.fromhex("7ff8000000000123"))[0]
    negnan=struct.unpack(">d",bytes.fromhex("fff8000000000123"))[0]
    values=[0.0,-0.0,1.0,-1.0,0.5,2.0,1e-300,1e300,float("inf"),-float("inf"),float("nan"),nan,negnan]
    result=[]
    for name in ("sine","cosine","square_root","logarithm","exponential","helper_flow"):
        xs=list(values)
        if name=="exponential":
            pivot=math.log(sys.float_info.max)
            xs += [math.nextafter(pivot,-math.inf),pivot,math.nextafter(pivot,math.inf),709.0,710.0,1000.0,-745.0,-746.0,-800.0]
        if name in ("logarithm","helper_flow"):
            xs += [math.ulp(0.0),sys.float_info.min,sys.float_info.max,math.nextafter(1.0,0.0),math.nextafter(1.0,math.inf)]
        for x in xs:result.append((name,[x],"qualified"))
    for y,x in [(0.0,0.0),(-0.0,0.0),(0.0,-0.0),(-0.0,-0.0),(1.0,-1.0),(-1.0,1.0),(float("inf"),float("inf")),(-math.inf,math.inf),(1.0,math.inf),(nan,1.0),(1.0,negnan),(nan,negnan)]:
        result.append(("angle",[y,x],"qualified"))
    result += [("overflow_first",[1000.0,-1.0],"qualified"),
               ("domain_first",[1000.0,-1.0],"qualified"),("nested",[1000.0],"qualified"),
               ("nested",[-800.0],"qualified"),("helper_flow",[0.0],"qualified")]
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();args.output.mkdir()
    source=args.output/"subject.py";raw=Path(__file__).with_name("focused_source.py").read_bytes();source.write_bytes(raw)
    start=time.perf_counter();built,message,_=MojoBackend().build_ast(source);cold=time.perf_counter()-start
    assert built,message
    spec=importlib.util.spec_from_file_location("focused_math",source)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    rows=[]
    for name,inputs,policy in cases():
        original=getattr(module,name)._original
        for mode in ("default","forced","strict"):
            expected=invoke(original,inputs)
            fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(original)
            actual=invoke(fn,inputs);same=actual==expected;route=fn._last_backend
            category="A" if same and route=="native" else "B" if same and route.startswith("python_fallback") else "C" if mode=="strict" and actual.get("exception")=="HotloopNativeExecutionError" and route=="native_error" else "D"
            rows.append(dict(function=name,inputs=[wire(x) for x in inputs],policy=policy,mode=mode,
                             expected=expected,actual=actual,backend=route,classification=category,
                             native_calls=fn._call_count_native,fallback_calls=fn._call_count_fallback))
    report=dict(python=sys.version,source_sha256=hashlib.sha256(raw).hexdigest(),build_ok=built,cold_seconds=cold,
                rows=rows,counts={k:sum(x["classification"]==k for x in rows) for k in "ABCD"})
    (args.output/"observations.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(rows=len(rows),counts=report["counts"])))
    return bool(report["counts"]["D"])
if __name__=="__main__":sys.exit(main())
