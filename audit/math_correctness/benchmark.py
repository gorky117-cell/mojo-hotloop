"""Bounded matched-input performance regression:five processes per runtime."""
import ast,gc,hashlib,importlib.util,json,math,os
from pathlib import Path
import statistics,struct,subprocess,sys,time,warnings
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"release_acceptance"))
from measure_applications import payloads,qualify
from hotloop import hotloop
from hotloop.backends.mojo import MojoBackend

APPS={"pii_scrubber":"scrub_pii","pdf_cleaner":"clean_pdf_text","quant_backtest":"stateful_trailing_backtest"}

def observe(fn,values):
    try:
        value=fn(*values)
        if type(value) is float:return dict(type="float",bits=struct.pack(">d",value).hex())
        return dict(type=type(value).__name__,value=value)
    except Exception as error:return dict(exception=type(error).__name__,message=str(error))

def timed(fn,values):
    start=time.perf_counter_ns()
    try:fn(*values)
    except Exception:pass
    elapsed=max(1,time.perf_counter_ns()-start)
    count=max(1,min(2000,int(5_000_000/elapsed)))
    batches=[]
    for _ in range(9):
        start=time.perf_counter_ns()
        for __ in range(count):
            try:fn(*values)
            except Exception:pass
        batches.append((time.perf_counter_ns()-start)/count/1000)
    return dict(batch_us=batches,p50_us=statistics.median(batches),iterations=count)

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module;spec.loader.exec_module(module);return module

def worker(label,folder,root):
    import hotloop as package
    folder=Path(folder);folder.mkdir();root=Path(root);rows=[];builds=[]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for app,symbol in APPS.items():
            d=folder/app;d.mkdir();source=d/"original.py";source.write_bytes((root/"examples"/app/"original.py").read_bytes())
            start=time.perf_counter();ok,message,_=MojoBackend().build_ast(source);cold=time.perf_counter()-start;assert ok,message
            module=load(source,"regression_"+app);public=getattr(module,symbol);original=public._original
            builds.append(dict(application=app,cold_seconds=cold))
            for size,values in payloads(root,app):
                expected=original(*values)
                for engine,fn in [("cpython",original),("public",public)]:
                    result=qualify(fn,values,expected,original)
                    assert result["strict_correct"],(app,size,engine,result)
                    record=dict(application=app,size=size,engine=engine,label=label,correct=True,qualification=result,
                        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                        input_sha256=hashlib.sha256(json.dumps(values,ensure_ascii=True).encode()).hexdigest(),
                        actual_backend="cpython" if engine=="cpython" else None)
                    record.update(timed(fn,values))
                    if engine=="public":
                        record["actual_backend"]=fn._last_backend
                        assert fn._last_backend=="native",(app,size,fn._last_backend)
                    rows.append(record)
        gate=ast.parse((root/"audit/math_correctness/original_gate.py").read_text())
        text=next(ast.literal_eval(n.value) for n in gate.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="SOURCE" for x in n.targets))
        d=folder/"math";d.mkdir();source=d/"subject.py";source.write_text(text)
        ok,message,_=MojoBackend().build_ast(source);assert ok,message;module=load(source,"regression_math")
        cases=[("sine","valid",0.5),("cosine","valid",0.5),("logarithm","valid",2.0),("exponential","valid",1.0),
               ("sine","inf",float("inf")),("cosine","inf",float("inf")),("logarithm","zero",0.0),
               ("logarithm","negative",-1.0),("exponential","overflow",1000.0)]
        for symbol,size,value in cases:
            public=getattr(module,symbol);original=public._original;expected=observe(original,(value,))
            for engine,fn in [("cpython",original),("public",public)]:
                got=observe(fn,(value,));correct=got==expected
                # Wrong pre-fix values are timed only as historical diagnostics;
                # they are never accepted as performance wins.
                record=dict(application="math_"+symbol,size=size,engine=engine,label=label,correct=correct,
                    expected=expected,actual=got,actual_backend="cpython" if engine=="cpython" else None,
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    input_sha256=hashlib.sha256(struct.pack(">d",value)).hexdigest())
                record.update(timed(fn,(value,)))
                if engine=="public":record["actual_backend"]=fn._last_backend
                if label=="candidate":assert correct,record
                rows.append(record)
    return dict(label=label,python=sys.version,package=package.__file__,rows=rows,builds=builds)

def main():
    if sys.argv[1]=="--worker":
        label,folder,root,destination=sys.argv[2:]
        Path(destination).write_text(json.dumps(worker(label,folder,root),indent=2)+"\n");return
    out,base,candidate=sys.argv[1:];out=Path(out).resolve();out.mkdir();root=Path(__file__).resolve().parents[2]
    cpu=max(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
    env=os.environ.copy()
    for key in ["PYTHONPATH","HOTLOOP_STRICT","HOTLOOP_FORCE_NATIVE","HOTLOOP_STRICT_PERF"]:env.pop(key,None)
    trials=[]
    for trial in range(5):
        order=[("baseline",base),("candidate",candidate)]
        if trial%2:order.reverse()
        for label,interpreter in order:
            name=label+"-"+str(trial+1);dest=out/(name+".json")
            subprocess.run([interpreter,str(Path(__file__).resolve()),"--worker",label,str(out/name),str(root),str(dest)],env=env,check=True)
            trials.append(json.loads(dest.read_text()));print(name+" completed",flush=True)
    # Inputs/source bytes must match in all ten independent processes.
    for key in {(x["application"],x["size"]) for t in trials for x in t["rows"]}:
        records=[x for t in trials for x in t["rows"] if (x["application"],x["size"])==key]
        assert len({x["input_sha256"] for x in records})==1,key
        assert len({x["source_sha256"] for x in records})==1,key
    (out/"results.json").write_text(json.dumps(dict(protocol="five independent processes/runtime; alternating order; nine batch means; matched original inputs; public includes conversions and exception handling",
        cpu=cpu,trials=trials),indent=2)+"\n")
if __name__=="__main__":main()
