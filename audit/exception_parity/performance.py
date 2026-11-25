"""Bounded matched-source regression, with public geographic dispatch explicit.

Run with the toolchain interpreter:
  python audit/exception_parity/performance.py OUT BASELINE_PY CANDIDATE_PY
Optional fourth argument: an earlier OUT directory, to reuse its verified first-trial artifacts without compilation.
Each interpreter must have its own wheel installed. No source-tree runtime import.
"""
import gc,hashlib,importlib.util,json,os
from pathlib import Path
import statistics,subprocess,sys,time,tracemalloc,warnings
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"release_acceptance"))
from measure_applications import payloads,qualify
from hotloop import hotloop
from hotloop.backends.mojo import MojoBackend

APPS={"geo_distance":"accumulate_haversine_distance","pii_scrubber":"scrub_pii",
      "pdf_cleaner":"clean_pdf_text","quant_backtest":"stateful_trailing_backtest"}

def timed(fn,args):
    start=time.perf_counter_ns();fn(*args)
    elapsed=max(1,time.perf_counter_ns()-start)
    count=max(1,min(2000,int(5_000_000/elapsed)))
    batches=[]
    for _ in range(9):
        start=time.perf_counter_ns()
        for __ in range(count):fn(*args)
        batches.append((time.perf_counter_ns()-start)/count/1000)
    gc.collect();tracemalloc.start();fn(*args)
    current,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
    return dict(batch_us=batches,p50_us=statistics.median(batches),iterations=count,
                python_visible_current_bytes=current,python_visible_peak_bytes=peak)

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def prepare_build(path):
    # Compilation is outside call timing. Let the SDK use available CPUs, then
    # restore the worker's fixed measurement affinity before any warm call.
    measurement_cpus = os.sched_getaffinity(0)
    try:
        build_cpus = set(range(os.cpu_count()))
        os.sched_setaffinity(0, build_cpus)
        return MojoBackend().build_ast(path)
    finally:
        os.sched_setaffinity(0, measurement_cpus)

def worker(label,folder,root):
    import hotloop as package
    from hotloop._native_cache import implementation_revision
    expected_install=Path(sys.executable).absolute().parent.parent.resolve()
    assert Path(package.__file__).resolve().is_relative_to(expected_install),package.__file__
    folder=Path(folder);folder.mkdir();root=Path(root);rows=[];builds=[]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for app,symbol in APPS.items():
            d=folder/app;d.mkdir()
            prebuilt=os.environ.get("HOTLOOP_BENCH_PREBUILT_ROOT")
            if prebuilt:
                p=Path(prebuilt)/(label+"-1")/app/"original.py"
                assert p.read_bytes()==(root/"examples"/app/"original.py").read_bytes()
                # The public loader independently verifies manifest, hashes,
                # compiler identity and ownership; route assertions below
                # reject fallback. No compiler runs in this timing worker.
                builds.append(dict(application=app,prebuilt_artifact_source=str(p),
                                   cold_build_seconds=None,cache_seconds=None))
            else:
                p=d/"original.py";p.write_bytes((root/"examples"/app/"original.py").read_bytes())
                start=time.perf_counter();ok,msg,_=prepare_build(p);cold=time.perf_counter()-start;assert ok,msg
                start=time.perf_counter();ok,msg,_=prepare_build(p);cache=time.perf_counter()-start;assert ok,msg
                builds.append(dict(application=app,cold_build_seconds=cold,cache_seconds=cache,build_cpus=list(range(os.cpu_count()))))
            m=load(p,"regression_"+app);public=getattr(m,symbol);original=public._original
            engines=[("cpython",original),("default_public",public)]
            if app=="geo_distance":
                engines += [("forced_public",hotloop(force_native=True)(original)),
                            ("strict_public",hotloop(strict=True)(original))]
            for size,args in payloads(root,app):
                expected=original(*args)
                for engine,fn in engines:
                    result=qualify(fn,args,expected,original)
                    assert result["strict_correct"],(app,size,engine,result)
                    before=(getattr(fn,"_call_count_native",0),getattr(fn,"_call_count_fallback",0))
                    record=dict(application=app,size=size,engine=engine,label=label,qualification=result,
                        source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                        input_sha256=hashlib.sha256(json.dumps(args,ensure_ascii=True).encode()).hexdigest())
                    record.update(timed(fn,args))
                    record["actual_backend"]=getattr(fn,"_last_backend","cpython")
                    record["native_counter_delta"]=getattr(fn,"_call_count_native",0)-before[0]
                    record["fallback_counter_delta"]=getattr(fn,"_call_count_fallback",0)-before[1]
                    expected_route="cpython" if engine=="cpython" else (
                        "python_fallback_slower" if app=="geo_distance" and engine=="default_public" else "native")
                    assert record["actual_backend"]==expected_route,record
                    rows.append(record)
    return dict(label=label,python=sys.version,package=package.__file__,implementation=implementation_revision(),
                cpu=sorted(os.sched_getaffinity(0)),rows=rows,builds=builds)

def main():
    if sys.argv[1]=="--worker":
        label,folder,root,dest=sys.argv[2:]
        Path(dest).write_text(json.dumps(worker(label,folder,root),indent=2)+"\n");return
    out,base,candidate=sys.argv[1:4];out=Path(out).resolve();out.mkdir()
    prebuilt=sys.argv[4] if len(sys.argv)>4 else None
    root=Path(__file__).resolve().parents[2]
    cpu=max(os.sched_getaffinity(0));os.sched_setaffinity(0,{cpu})
    env=os.environ.copy()
    for key in ("PYTHONPATH","HOTLOOP_STRICT","HOTLOOP_FORCE_NATIVE","HOTLOOP_STRICT_PERF"):env.pop(key,None)
    if prebuilt:env["HOTLOOP_BENCH_PREBUILT_ROOT"]=str(Path(prebuilt).resolve())
    else:env.pop("HOTLOOP_BENCH_PREBUILT_ROOT",None)
    trials=[]
    for trial in range(5):
        order=[("baseline",base),("candidate",candidate)]
        if trial%2:order.reverse()
        for label,interpreter in order:
            name=label+"-"+str(trial+1);dest=out/(name+".json")
            subprocess.run([interpreter,str(Path(__file__).resolve()),"--worker",label,str(out/name),str(root),str(dest)],
                           env=env,check=True)
            result=json.loads(dest.read_text());result["trial"]=trial+1;trials.append(result)
            print(name+" completed",flush=True)
    keys=sorted({(r["application"],r["size"],r["engine"]) for t in trials for r in t["rows"]})
    summary=[]
    def percentile(xs,q):
        ys=sorted(xs);pos=(len(ys)-1)*q;i=int(pos);fraction=pos-i
        return ys[i]*(1-fraction)+ys[min(i+1,len(ys)-1)]*fraction
    for key in keys:
        records=[r for t in trials for r in t["rows"] if (r["application"],r["size"],r["engine"])==key]
        assert len(records)==10
        assert len({r["input_sha256"] for r in records})==len({r["source_sha256"] for r in records})==1
        row=dict(application=key[0],size=key[1],engine=key[2],backend=records[0]["actual_backend"])
        for label in ("baseline","candidate"):
            rec=[r for r in records if r["label"]==label]
            batches=[b for r in rec for b in r["batch_us"]]
            row[label]=dict(p50_us=statistics.median(batches),p95_batch_mean_us=percentile(batches,.95),
                process_median_min_us=min(r["p50_us"] for r in rec),process_median_max_us=max(r["p50_us"] for r in rec),
                process_medians_us=[r["p50_us"] for r in rec],
                peak_python_bytes=[r["python_visible_peak_bytes"] for r in rec])
        ratios=[row["candidate"]["process_medians_us"][i]/row["baseline"]["process_medians_us"][i] for i in range(5)]
        row["change_percent"]=(row["candidate"]["p50_us"]/row["baseline"]["p50_us"]-1)*100
        row["paired_changes_percent"]=[(r-1)*100 for r in ratios]
        row["slower_over_10_percent_pairs"]=sum(r>1.1 for r in ratios)
        row["repeatable_slowdown_over_10_percent"] = row["change_percent"]>10 and sum(r>1.1 for r in ratios)>=4
        summary.append(row)
    output=dict(protocol="five independent processes/runtime; alternating order; fixed CPU; nine batch means per row; all original payloads; identical source and input hashes; strict value/type/bits/alias qualification before timing; gc enabled; timings exclude tracemalloc; p95 is of batch means, not individual-call tail",
                baseline=base,candidate=candidate,cpu=cpu,prebuilt_root=prebuilt,trials=trials,summary=summary)
    (out/"results.json").write_text(json.dumps(output,indent=2)+"\n")
if __name__=="__main__":main()
