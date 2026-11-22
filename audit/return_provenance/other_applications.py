"""Regression check of the other five original application payload families.

Usage: python other_applications.py OUT SECURITY_PY ORIGIN_PY PROPOSED_PY
The numerical/spatial comparison retains the original verifier tolerances and
reports bit equality separately. Forced routes never become default coverage.
"""
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import random
import statistics
import struct
import subprocess
import sys
import time
import typing

FUNCTIONS={"pdf_cleaner":"clean_pdf_text","rag_chunker":"chunk_document",
 "ocr_matcher":"find_closest_match","geo_distance":"accumulate_haversine_distance",
 "ar_spatial":"find_closest_point_to_ray"}
def definitions(path,names):
    import numpy as np
    ns=dict(vars(typing),random=random,math=math,np=np)
    tree=ast.parse(path.read_text())
    nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert len(nodes)==len(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),ns)
    return ns
def data(root,app):
    path=root/"examples"/app/"bench.py"
    if app in ("pdf_cleaner","rag_chunker","ocr_matcher"):
        values=definitions(path,["generate_bench_payloads"])["generate_bench_payloads"]()
        for size,x in values.items():
            if app=="rag_chunker":args=(x["text"],x["size"],x["overlap"])
            elif app=="ocr_matcher":args=(x["query"],x["candidates"],x["max_d"])
            else:args=(x["text"],)
            yield size,args
    else:
        name="generate_trail" if app=="geo_distance" else "generate_cloud"
        gen=definitions(path,[name])[name]
        for size in (100,1000,10000):
            x=gen(size)
            args=tuple(x[:2]) if app=="geo_distance" else tuple(x[:3])+tuple(x[-1])
            yield str(size),args
def same(actual,expected):
    assert type(actual) is type(expected)
    if type(expected) is float:
        assert math.isclose(actual,expected,rel_tol=1e-8,abs_tol=1e-8)
        return struct.pack(">d",actual)==struct.pack(">d",expected)
    assert actual==expected
    if type(expected) is list:
        assert all(type(a) is type(b) for a,b in zip(actual,expected))
    return True
def measure(fn,args,expected):
    result=fn(*args);bits=same(result,expected)
    start=time.perf_counter();fn(*args);elapsed=time.perf_counter()-start
    count=max(1,min(2000,int(.005/max(elapsed,1e-9))))
    samples=[]
    for _ in range(9):
        start=time.perf_counter_ns()
        for _ in range(count):fn(*args)
        samples.append((time.perf_counter_ns()-start)/count/1000)
    return dict(p50_us=statistics.median(samples),batch_us=samples,iterations=count,
                result_type=type(result).__name__,float_bits_equal=bits)
def worker(label,out,root):
    from hotloop import hotloop
    import hotloop as package
    from hotloop.backends.mojo import MojoBackend
    folder=Path(out);folder.mkdir()
    root=Path(root);rows=[]
    for app,name in FUNCTIONS.items():
        d=folder/app;d.mkdir()
        source=d/"original.py";source.write_bytes((root/"examples"/app/"original.py").read_bytes())
        start=time.perf_counter()
        ok,diagnostic,_=MojoBackend().build_ast(source)
        build_seconds=time.perf_counter()-start
        assert ok,diagnostic
        spec=importlib.util.spec_from_file_location("original",source)
        module=importlib.util.module_from_spec(spec);sys.modules["original"]=module;spec.loader.exec_module(module)
        public=getattr(module,name);original=public._original
        engines={"cpython":original,"default_public":public}
        if app in ("ocr_matcher","geo_distance","ar_spatial"):
            engines["forced_public"]=hotloop(force_native=True)(original)
        for size,args in data(root,app):
            expected=original(*args)
            digest=hashlib.sha256(json.dumps(args,ensure_ascii=True).encode()).hexdigest()
            for engine,fn in engines.items():
                before=(getattr(fn,"_call_count_native",0),getattr(fn,"_call_count_fallback",0))
                row=measure(fn,args,expected)
                row.update(application=app,size=size,label=label,engine=engine,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),input_sha256=digest,
                  native_calls=getattr(fn,"_call_count_native",0)-before[0],
                  fallback_calls=getattr(fn,"_call_count_fallback",0)-before[1],
                  route=getattr(fn,"_last_backend","cpython"),build_seconds=build_seconds)
                if engine=="forced_public":assert row["route"]=="native",row
                rows.append(row)
    return dict(label=label,package=package.__file__,rows=rows)
def main():
    if sys.argv[1]=="--worker":
        label,out,root,dest=sys.argv[2:]
        Path(dest).write_text(json.dumps(worker(label,out,root),indent=2)+"\n");return
    out,security,origin,proposed=sys.argv[1:]
    out=Path(out).resolve();out.mkdir()
    cpu=max(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
    root=Path(__file__).resolve().parents[2]
    env=os.environ.copy()
    for name in ("PYTHONPATH","HOTLOOP_STRICT","HOTLOOP_FORCE_NATIVE","HOTLOOP_STRICT_PERF"):env.pop(name,None)
    rows=[]
    for trial in range(5):
        order=[("baseline",security),("origin",origin),("candidate",proposed)]
        order=order[trial%3:]+order[:trial%3]
        if trial%2:order.reverse()
        for label,python in order:
            name=label+"-"+str(trial+1);dest=out/(name+".json")
            subprocess.run([python,str(Path(__file__).resolve()),"--worker",label,str(out/name),str(root),str(dest)],env=env,check=True)
            rows.append(json.loads(dest.read_text()));print(name,"completed",flush=True)
    (out/"results.json").write_text(json.dumps(dict(protocol="5 processes/runtime; original payloads; 9 batches; CPU affinity",cpu=cpu,trials=rows),indent=2)+"\n")
if __name__=="__main__":main()
