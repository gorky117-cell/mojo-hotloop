"""Reproduce the fixed M0 corpus through installed public @hotloop calls.

Run outside any source PYTHONPATH. Latencies are observations, never CI thresholds.
"""
import argparse
from array import array
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import statistics
import struct
import sys
import time
import warnings

def decode(value):
    if type(value) is list:return [decode(x) for x in value]
    if type(value) is not dict:return value
    kind=value["kind"]
    if kind=="int":return int(value["value"])
    if kind=="float":return float(value["value"])
    if kind=="array":return array("d",value["values"])
    if kind=="memoryview":return memoryview(array("d",value["values"]))
    if kind=="numpy":
        import numpy as np
        return np.array(value["values"],dtype="float64")
    raise ValueError(kind)

def wire(value):
    kind=type(value).__module__+"."+type(value).__qualname__
    if isinstance(value,float):return dict(type=kind,bits=struct.pack(">d",value).hex())
    if type(value) in (int,str,bool) or value is None:return dict(type=kind,value=value)
    if isinstance(value,(list,tuple,array,memoryview)):
        return dict(type=kind,items=[wire(x) for x in value])
    if type(value).__module__=="numpy":
        return dict(type=kind,dtype=str(value.dtype),items=value.tolist())
    raise TypeError(kind)

def nodes(value):
    yield value
    if type(value) in (list,tuple):
        for x in value:yield from nodes(x)

def owners(args,mod):
    result=[]
    for arg in args:result.extend(nodes(arg))
    for item in vars(mod).values():
        original=getattr(item,"_original",item)
        if type(original).__name__=="function" and getattr(original,"__module__",None)==mod.__name__:
            result.extend(x for x in original.__code__.co_consts if type(x) in (float,int,str,bool))
    return result

def graph(values,pool):
    prior=[];result=[]
    for value in values:
        for item in nodes(value):
            owner=next((i for i,x in enumerate(pool) if item is x),None)
            alias=next((i for i,x in enumerate(prior) if item is x),None)
            result.append([owner,alias]);prior.append(item)
    return result

def invoke(fn,args):
    stream=io.StringIO()
    with warnings.catch_warnings(record=True) as notices,redirect_stdout(stream):
        warnings.simplefilter("always")
        start=time.perf_counter_ns()
        try:
            value=fn(*args);error=None
        except Exception as exception:
            value=None;error=type(exception).__name__
        elapsed=time.perf_counter_ns()-start
    return value,dict(result=wire(value),exception=error,stdout=stream.getvalue(),
        warnings=[type(x.message).__name__ for x in notices],elapsed_ns=elapsed)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,default=Path(__file__).resolve().parents[1]/"reference/m0-v1/manifest.json")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--no-build",action="store_true",help="Negative test: required-native cases must fail")
    parser.add_argument("--samples",type=int,default=7)
    args=parser.parse_args()
    from hotloop import hotloop
    import hotloop as package
    from hotloop.backends.mojo import MojoBackend
    manifest=json.loads(args.manifest.read_text())
    assert manifest["denominator"]==len(manifest["functions"])==25
    args.output.mkdir()
    rows=[];failures=[]
    for case in manifest["functions"]:
        raw=(args.manifest.parent/case["source"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==case["source_sha256"]
        folder=args.output/case["id"];folder.mkdir()
        path=folder/case["source"];path.write_bytes(raw)
        start=time.perf_counter()
        if args.no_build:built,message=False,"intentionally omitted for negative CI proof"
        else:built,message,_=MojoBackend().build_ast(path)
        cold=time.perf_counter()-start
        start=time.perf_counter()
        if built:cached,cache_message,_=MojoBackend().build_ast(path)
        else:cached,cache_message=False,"not built"
        cache=time.perf_counter()-start
        spec=importlib.util.spec_from_file_location("reference_"+case["id"].replace("-","_"),path)
        mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
        original=getattr(mod,case["function"])._original
        modes=[];default_expected=None
        for mode in ("default","forced","strict"):
            reference_args=decode(case["args"]);actual_args=decode(case["args"])
            pool_reference=owners(reference_args,mod);pool_actual=owners(actual_args,mod)
            reference,expected=invoke(original,reference_args)
            assert {k:expected[k] for k in ("result","exception","stdout")}==case["expected_cpython"]
            fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(original)
            actual,observed=invoke(fn,actual_args)
            backend=fn._last_backend;requirement=case["required_routes"][mode]
            if mode=="strict" and requirement=="refuse":
                correct=(observed["exception"]=="HotloopNativeExecutionError" and observed["stdout"]==""
                         and wire(actual_args)==wire(decode(case["args"])))
            else:
                correct=all(observed[k]==expected[k] for k in ("result","exception","stdout"))
                correct &= wire(actual_args)==wire(reference_args)
                if observed["exception"] is None:
                    correct &= graph([actual],pool_actual)==graph([reference],pool_reference)
                    # Hold both outputs: verify fresh values and shared owners across calls.
                    reference2,expected2=invoke(original,reference_args)
                    actual2,observed2=invoke(fn,actual_args)
                    correct &= graph([actual,actual2],pool_actual)==graph([reference,reference2],pool_reference)
                    correct &= all(observed2[k]==expected2[k] for k in ("result","exception","stdout"))
                if requirement=="native":correct &= backend=="native"
                if requirement=="python":correct &= backend.startswith("python_fallback")
            mode_record=dict(mode=mode,required_route=requirement,backend=backend,correct=bool(correct),
                expected=expected,observed=observed,
                native_calls=fn._call_count_native,fallback_calls=fn._call_count_fallback)
            modes.append(mode_record)
            if mode=="default":
                samples=[];python_samples=[]
                for _ in range(args.samples):
                    _,sample=invoke(fn,decode(case["args"]));samples.append(sample["elapsed_ns"])
                    _,sample=invoke(original,decode(case["args"]));python_samples.append(sample["elapsed_ns"])
                mode_record.update(warm_public_ns=samples,warm_cpython_ns=python_samples,
                    p50_public_ns=statistics.median(samples),p50_cpython_ns=statistics.median(python_samples))
                default_expected=expected
            if not correct:failures.append(case["id"]+"/"+mode)
        default=modes[0]
        classification=("slower-native" if default["p50_public_ns"]>default["p50_cpython_ns"] else "native-correct") if default["backend"]=="native" else "fallback-correct"
        if not all(x["correct"] for x in modes):classification="failure"
        rows.append(dict(id=case["id"],function=case["function"],source_sha256=case["source_sha256"],
             inputs=case["args"],expected_cpython=default_expected,build_ok=built,build_diagnostic=message,
             cold_compile_seconds=cold,cache_hit_ok=cached,cache_seconds=cache,
             classification=classification,modes=modes))
    report=dict(schema=1,manifest_sha256=hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
      denominator=25,python=sys.version,platform=platform.platform(),machine=platform.machine(),
      package=package.__file__,hosted_run_id=os.environ.get("GITHUB_RUN_ID"),
      runner_image=os.environ.get("ImageVersion"),rows=rows,failures=failures,
      build_success=sum(x["build_ok"] for x in rows),
      default_native=sum(x["modes"][0]["backend"]=="native" and x["modes"][0]["correct"] for x in rows),
      forced_native=sum(x["modes"][1]["backend"]=="native" and x["modes"][1]["correct"] for x in rows))
    (args.output/"observations.json").write_text(json.dumps(report,indent=2,ensure_ascii=True)+"\n")
    print(json.dumps({k:report[k] for k in ("denominator","build_success","default_native","forced_native","failures")}))
    return bool(failures)
if __name__=="__main__":sys.exit(main())
