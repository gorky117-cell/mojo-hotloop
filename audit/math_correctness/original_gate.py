"""Independent release gate: Python math exceptions must not become native NaN/inf.

A strict refusal is safe. Ordinary/forced calls must preserve the CPython result
or exception. This is separate from the unchanged frozen 25-function M0 corpus.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import struct
import sys
import warnings
from hotloop import hotloop, HotloopNativeExecutionError
from hotloop.backends.mojo import MojoBackend

SOURCE="""import math
from hotloop import hotloop
@hotloop
def sine(x: float) -> float:
    return math.sin(x)
@hotloop
def cosine(x: float) -> float:
    return math.cos(x)
@hotloop
def logarithm(x: float) -> float:
    return math.log(x)
@hotloop
def exponential(x: float) -> float:
    return math.exp(x)
"""
CASES=[("sine","inf"),("cosine","inf"),("logarithm","0.0"),
       ("logarithm","-1.0"),("exponential","1000.0")]

def invoke(fn,x):
    try:
        value=fn(x)
        return dict(type=type(value).__name__,bits=struct.pack(">d",value).hex())
    except Exception as error:
        return dict(exception=type(error).__name__,message=str(error))

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();args.output.mkdir()
    source=args.output/"subject.py";source.write_text(SOURCE)
    built,message,_=MojoBackend().build_ast(source)
    assert built,message
    spec=importlib.util.spec_from_file_location("math_release_gate",source)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    rows=[]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for symbol,text in CASES:
            original=getattr(module,symbol)._original
            for mode in ("default","forced","strict"):
                fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(original)
                expected=invoke(original,float(text));observed=invoke(fn,float(text))
                strict_refusal=(mode=="strict" and observed.get("exception")=="HotloopNativeExecutionError"
                                and fn._last_backend=="native_error" and fn._call_count_native==0)
                rows.append(dict(function=symbol,input=text,mode=mode,expected=expected,actual=observed,
                                 backend=fn._last_backend,native_calls=fn._call_count_native,
                                 fallback_calls=fn._call_count_fallback,equal=expected==observed or strict_refusal))
    failures=[row for row in rows if not row["equal"]]
    result=dict(python=sys.version,source=SOURCE,build_ok=built,rows=rows,failures=failures,
                expected_cases=15,denominator=len(rows),release_blocked=bool(failures))
    (args.output/"observations.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(cases=len(rows),mismatches=len(failures),release_blocked=bool(failures))))
    return bool(failures)
if __name__=="__main__":sys.exit(main())
