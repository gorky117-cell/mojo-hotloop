"""CPython-oracle public list-index gate, retaining strict refusals separately."""
import argparse,contextlib,hashlib,importlib.util,io,json,struct,sys,warnings
from pathlib import Path
import hotloop as package
from hotloop import hotloop
from hotloop._native_cache import implementation_revision
from hotloop.backends.mojo import MojoBackend

class CustomIndex:
    def __init__(self,value):self.value=value
    def __index__(self):
        print("CUSTOM_INDEX")
        return self.value

def wire(value):
    if type(value) is float:return dict(type="float",bits=struct.pack(">d",value).hex())
    if type(value) in (int,bool,str) or value is None:return dict(type=type(value).__name__,value=value)
    return dict(type=type(value).__module__+"."+type(value).__qualname__)

def invoke(fn,args):
    stdout=io.StringIO()
    with contextlib.redirect_stdout(stdout),warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            result=fn(*args)
            outcome=dict(result=wire(result),exception=None)
            outcome["return_input_owner"]=[i for i,x in enumerate(args) if result is x]
            outcome["return_element_owner"]=[[i,j] for i,x in enumerate(args) if type(x) is list for j,v in enumerate(x) if result is v]
        except Exception as e:outcome=dict(exception=type(e).__name__,message=str(e),args=[wire(x) for x in e.args])
    outcome["stdout"]=stdout.getvalue()
    return outcome

def load(source,name):
    spec=importlib.util.spec_from_file_location(name,source);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def cases():
    rows=[]
    for name,values in [("get_int",[1000,2000]),("get_float",[1.25,-0.0]),("get_bool",[True,False]),("get_str",["alpha","🚀"])]:
        for i in [0,1,-1,-2,2,-3,sys.maxsize,-sys.maxsize-1]:rows.append((name,lambda values=values,i=i:[list(values),i],"list"))
        for i in [0,-1]:rows.append((name,lambda i=i:[[],i],"list"))
    for name in ["compute","nested_index"]:
        for i in [0,1,-1,-2,2,-3]:rows.append((name,lambda i=i:[[1000,2000],i],"list"))
    for name in ["local_read","literal_read","helper_list"]:
        for i in [0,1,-1,-2,2,-3]:rows.append((name,lambda i=i:[i],"python" if name=="helper_list" else "native"))
    for name in ["read_before_div","div_before_read"]:
        for i,den in [(0,2),(2,0),(2,1),(0,0),(-3,0)]:rows.append((name,lambda i=i,den=den:[[1,2],i,den],"list"))
    for name in ["local_store","local_aug"]:
        for i in [0,1,-1,-2,2,-3]:rows.append((name,lambda i=i:[i,7],"native"))
    for name in ["store_rhs_first","aug_read_first"]:
        for i,den in [(0,2),(2,0),(2,1),(0,0),(-3,0)]:rows.append((name,lambda i=i,den=den:[i,den],"native"))
    for name in ["effect_read","effect_store"]:
        for i in [0,-1,2,-3]:
            rows.append((name,(lambda i=i:[[1,2],i]) if name=="effect_read" else (lambda i=i:[i]),"python"))
    for i in [0,-1,2]:
        rows.append(("get_int",lambda i=i:[[1000,2000],CustomIndex(i)],"python"))
    for i in [1.5,"1",True,10**100]:
        rows.append(("get_int",lambda i=i:[[1000,2000],i],"python"))
    return rows

def check(name,fn,factory,mode,policy):
    expected=invoke(fn,factory());public=hotloop(force_native=mode=="forced",strict=mode=="strict")(fn)
    actual=invoke(public,factory());route=public._last_backend
    same=expected==actual
    category=("A" if same and route=="native" else "B" if same and route.startswith("python_fallback")
              else "C" if mode=="strict" and actual.get("exception")=="HotloopNativeExecutionError" and route=="native_error"
                   and actual["stdout"]=="" and public._call_count_native==0 and public._call_count_fallback==0 else "D")
    target=("C" if mode=="strict" else "B") if policy=="python" else "B" if policy=="list" and mode=="default" else "A"
    return dict(function=name,mode=mode,policy=policy,expected_classification=target,classification=category,
                correct=category==target,expected=expected,actual=actual,backend=route,
                native_calls=public._call_count_native,fallback_calls=public._call_count_fallback)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True);args=parser.parse_args();args.output.mkdir()
    source=args.output/"subject.py";source.write_bytes(Path(__file__).with_name("subject.py").read_bytes())
    ok,msg,_=MojoBackend().build_ast(source);assert ok,msg
    m=load(source,"list_exception_subject");rows=[];builds=[dict(source="subject.py",ok=ok,diagnostic=msg)]
    for name,factory,policy in cases():
        for mode in ("default","forced","strict"):rows.append(check(name,getattr(m,name)._original,factory,mode,policy))
    # Original application is copied without source changes.
    geo=args.output/"geo";geo.mkdir();p=geo/"original.py"
    p.write_bytes((Path(__file__).resolve().parents[2]/"examples/geo_distance/original.py").read_bytes())
    ok,msg,_=MojoBackend().build_ast(p);assert ok,msg;gm=load(p,"geographic_exception_gate")
    builds.append(dict(source="geo",ok=ok,diagnostic=msg))
    for lats,lons in [([1.,2.],[1.]),([],[]),([1.],[1.]),([1.,2.],[1.,2.]),([1.,2.],[1.,2.,3.])]:
        for mode in ("default","forced","strict"):
            rows.append(check("geographic",gm.accumulate_haversine_distance._original,lambda lats=lats,lons=lons:[list(lats),list(lons)],mode,"list"))
    # Explicit Python raises are outside the supported AST and must stay Python.
    for label,text in [("direct",'from hotloop import hotloop\n@hotloop\ndef raised(message: str) -> int:\n    raise IndexError(message)\n'),
                       ("helper",'from hotloop import hotloop\ndef fail(message: str) -> int:\n    print("HELPER")\n    raise IndexError(message)\n@hotloop\ndef raised(message: str) -> int:\n    return fail(message)\n')]:
        folder=args.output/label;folder.mkdir();p=folder/"subject.py";p.write_text(text)
        ok,msg,_=MojoBackend().build_ast(p);builds.append(dict(source=label,ok=ok,diagnostic=msg))
        mod=load(p,"explicit_raise_"+label)
        for message in ["user chosen","index out of range","list assignment index out of range","HOTLOOP_INDEX_ERROR: user chosen"]:
            for mode in ("default","forced","strict"):
                rows.append(check("explicit_"+label,mod.raised._original,lambda message=message:[message],mode,"python"))
    result=dict(python=sys.version,package=package.__file__,implementation=implementation_revision(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),builds=builds,rows=rows,
                counts={k:sum(r["classification"]==k for r in rows) for k in "ABCD"},failures=[r for r in rows if not r["correct"]])
    (args.output/"observations.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(rows=len(rows),counts=result["counts"],failures=len(result["failures"]))))
    return bool(result["failures"])
if __name__=="__main__":sys.exit(main())
