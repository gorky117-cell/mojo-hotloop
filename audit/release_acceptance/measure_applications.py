"""Five independent processes/runtime; original seven applications and inputs.

No result with a type/value/alias mismatch enters the strict ranking. Expert
references and tolerance-only NumPy results remain explicitly distinguished.
"""
import ast
from contextlib import redirect_stderr
import functools
import gc
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import random
import re
import statistics
import struct
import subprocess
import sys
import sysconfig
import time
import tracemalloc
import typing

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"return_provenance"))
from other_applications import data as other_data
from scanner import scanner
FUNCTIONS={"pii_scrubber":"scrub_pii","pdf_cleaner":"clean_pdf_text","quant_backtest":"stateful_trailing_backtest",
 "rag_chunker":"chunk_document","ocr_matcher":"find_closest_match","geo_distance":"accumulate_haversine_distance","ar_spatial":"find_closest_point_to_ray"}

def payloads(root,app):
    if app=="quant_backtest":
        return [(str(n),(n,float("123.5"),0.05,0.001)) for n in (0,100,10000,100000)]
    if app!="pii_scrubber":return list(other_data(root,app))
    ns=dict(vars(typing),random=random)
    for filename in ("verify.py","bench.py"):
        path=root/"examples"/app/filename
        tree=ast.parse(path.read_text())
        nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and (n.name.startswith("gen_synthetic_") or n.name=="generate_bench_payloads")]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),ns)
    return [(name,(item["text"],)) for name,item in ns["generate_bench_payloads"]().items()]

def references(root,app):
    import numpy as np
    path=root/"examples"/app/"verify.py"
    from rapidfuzz.distance import Levenshtein
    ns=dict(vars(typing),math=math,np=np,re=re,random=random,Levenshtein=Levenshtein)
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,(ast.Assign,ast.FunctionDef))]
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),ns)
    return ns

def objects(value):
    yield value
    if type(value) in (list,tuple):
        for item in value:yield from objects(item)
def signature(value,pool):
    seen=[];rows=[]
    for item in objects(value):
        owner=next((i for i,x in enumerate(pool) if item is x),None)
        alias=next((i for i,x in enumerate(seen) if item is x),None)
        rows.append([type(item).__module__+"."+type(item).__qualname__,owner,alias])
        seen.append(item)
    return rows

def qualify(fn,args,expected,original):
    try:
        result=fn(*args)
        same_type=type(result) is type(expected)
        value=result==expected
        bits=struct.pack(">d",result)==struct.pack(">d",expected) if type(expected) is float and same_type else bool(value)
        pool=[x for arg in args for x in objects(arg)]
        pool += [x for x in original.__code__.co_consts if type(x) in (float,int,str,bool)]
        aliases=signature(result,pool)==signature(expected,pool)
        close=(math.isclose(result,expected,rel_tol=1e-8,abs_tol=1e-8) if type(expected) is float else bool(value))
        return dict(type_correct=same_type,value_correct=bool(value),bits_correct=bits,aliases_correct=aliases,
          strict_correct=bool(same_type and value and bits and aliases),tolerance_correct=bool(same_type and close),
          result_sha256=hashlib.sha256(repr(result).encode("utf8","surrogatepass")).hexdigest())
    except Exception as error:
        return dict(strict_correct=False,tolerance_correct=False,exception=type(error).__name__,message=str(error))

def measure(fn,args):
    start=time.perf_counter();fn(*args)
    count=max(1,min(2000,int(.008/max(time.perf_counter()-start,1e-9))))
    batches=[]
    for _ in range(9):
        start=time.perf_counter_ns()
        for _ in range(count):fn(*args)
        batches.append((time.perf_counter_ns()-start)/count/1000)
    gc.collect();tracemalloc.start();fn(*args);current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    return dict(batch_us=batches,p50_us=statistics.median(batches),iterations=count,
        python_visible_current_bytes=current,python_visible_peak_bytes=peak)

def worker(label,folder,root,reference):
    import hotloop as package
    from hotloop import hotloop
    from hotloop.backends.mojo import MojoBackend
    folder=Path(folder);folder.mkdir();root=Path(root)
    sys.path.insert(0,reference)
    import native_reference
    rows=[];costs=[]
    for app,name in FUNCTIONS.items():
        directory=folder/app;directory.mkdir()
        path=directory/"original.py";path.write_bytes((root/"examples"/app/"original.py").read_bytes())
        backend=MojoBackend()
        start=time.perf_counter();ok,message,_=backend.build_ast(path);cold=time.perf_counter()-start
        assert ok,message
        start=time.perf_counter();ok,message,_=backend.build_ast(path);cache=time.perf_counter()-start
        assert ok,message
        spec=importlib.util.spec_from_file_location("original",path)
        module=importlib.util.module_from_spec(spec);sys.modules["original"]=module
        start=time.perf_counter();spec.loader.exec_module(module);loaded=time.perf_counter()-start
        public=getattr(module,name);original=public._original
        cases=payloads(root,app)
        start=time.perf_counter();public(*cases[0][1]);first=(time.perf_counter()-start)*1e6
        engines={"cpython":original,"hotloop_public":public}
        if app in ("ocr_matcher","geo_distance","ar_spatial"):engines["forced_public"]=hotloop(force_native=True)(original)
        if public._compiled is not None:engines["private_entry"]=public._compiled
        jit=None
        if app in ("quant_backtest","geo_distance","ar_spatial"):
            import numba
            start=time.perf_counter()
            numba_fn=numba.njit(fastmath=False,cache=False)(original)
            numba_fn(*cases[-1][1]);jit=time.perf_counter()-start
            engines["numba"]=numba_fn
            engines["manual_cpp"]=getattr(native_reference,{"quant_backtest":"quant","geo_distance":"geo","ar_spatial":"ar"}[app])
        if app=="pii_scrubber":engines["expert_regex"]=scanner(module)
        elif app in ("pdf_cleaner","ocr_matcher","geo_distance","ar_spatial"):
            ns=references(root,app)
            engine={"pdf_cleaner":("compiled_regex","regex_clean_pdf"),"ocr_matcher":("rapidfuzz","rapidfuzz_find_closest"),
                    "geo_distance":("numpy","numpy_haversine"),"ar_spatial":("numpy","numpy_closest_point_to_ray")}[app]
            engines[engine[0]]=ns[engine[1]]
        for size,values in cases:
            expected=original(*values)
            for engine,fn in engines.items():
                qualification=qualify(fn,values,expected,original)
                before=(getattr(fn,"_call_count_native",0),getattr(fn,"_call_count_fallback",0))
                timed=None
                if qualification["strict_correct"] or qualification["tolerance_correct"]:
                    timed=measure(fn,values)
                if label=="candidate" and engine in ("cpython","hotloop_public","forced_public"):
                    assert qualification["strict_correct"],(app,size,engine,qualification)
                rows.append(dict(application=app,size=size,label=label,engine=engine,qualification=qualification,timing=timed,
                    actual_backend=getattr(fn,"_last_backend","private_entry" if engine=="private_entry" else engine),
                    native_counter_delta=getattr(fn,"_call_count_native",0)-before[0],
                    fallback_counter_delta=getattr(fn,"_call_count_fallback",0)-before[1],
                    input_sha256=hashlib.sha256(json.dumps(values,ensure_ascii=True).encode()).hexdigest(),
                    source_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        costs.append(dict(application=app,cold_build_seconds=cold,cache_hit_seconds=cache,
            import_after_build_seconds=loaded,first_public_us=first,numba_jit_seconds=jit))
    return dict(label=label,package=package.__file__,python=sys.version,costs=costs,rows=rows)

def main():
    if sys.argv[1]=="--worker":
        label,folder,root,reference,destination=sys.argv[2:]
        Path(destination).write_text(json.dumps(worker(label,folder,root,reference),indent=2)+"\n");return
    out,baseline,candidate=sys.argv[1:]
    out=Path(out).resolve();out.mkdir()
    cpu=max(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
    root=Path(__file__).resolve().parents[2]
    cpp=root/"audit/return_provenance/native_reference.cpp"
    flags=["c++","-O3","-shared","-fPIC","-std=c++17","-fno-fast-math","-ffp-contract=off",
           "-I"+sysconfig.get_path("include"),str(cpp),"-o",str(out/("native_reference"+sysconfig.get_config_var("EXT_SUFFIX")))]
    subprocess.run(flags,check=True)
    env=os.environ.copy()
    for key in ("PYTHONPATH","HOTLOOP_STRICT","HOTLOOP_FORCE_NATIVE","HOTLOOP_STRICT_PERF"):env.pop(key,None)
    trials=[]
    for trial in range(5):
        order=[("security",baseline),("candidate",candidate)]
        if trial%2:order.reverse()
        for label,python in order:
            name=label+"-"+str(trial+1);destination=out/(name+".json")
            subprocess.run([python,str(Path(__file__).resolve()),"--worker",label,str(out/name),str(root),str(out),str(destination)],env=env,check=True)
            trials.append(json.loads(destination.read_text()));print(name,"completed",flush=True)
    (out/"results.json").write_text(json.dumps(dict(protocol="5 processes/runtime; 9 batch means; original inputs; CPU affinity",cpu=cpu,cpp_flags=flags,
            expert_roles=["expert_regex","compiled_regex","manual_cpp","numpy","rapidfuzz"],trials=trials),indent=2)+"\n")
if __name__=="__main__":main()
