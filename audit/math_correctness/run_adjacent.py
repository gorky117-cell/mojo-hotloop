"""Adjacent unsupported-call, side-effect and alias dispatch qualification."""
import argparse, hashlib, importlib.util, json
from pathlib import Path
import struct, sys
from hotloop import hotloop
from hotloop.backends.mojo import MojoBackend
from run_focused import invoke,wire

def cases():
    rows=[]
    for args in [(2.0,3.0),(0.0,-1.0),(-1.0,0.5),(float("nan"),0.0),(1.0,float("nan")),(0.0,-float("inf"))]:
        rows += [("power",list(args)),("power_parent",list(args))]
    for symbol in ["floor_value","ceil_value"]:
        rows += [(symbol,[x]) for x in [0.0,-0.0,1.5,-1.5,1e300,float("inf"),float("nan")]]
    rows += [("log_base",[8.0,2.0]),("log_base",[8.0,1.0]),("keyword_log",[2.0]),
             ("effect_first",[-1.0,1000.0]),("overflow_before_effect",[-1.0,1000.0]),
             ("constant_exp",[]),("constant_sin",[]),("integer_log",[3])]
    return rows

def load(source,name):
    spec=importlib.util.spec_from_file_location(name,source)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module);return module

def check(original,args,mode,policy):
    expected=invoke(original,args);fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(original)
    actual=invoke(fn,args);route=fn._last_backend
    same=expected==actual
    category="A" if same and route=="native" else "B" if same and route.startswith("python_fallback") else "C" if mode=="strict" and actual.get("exception")=="HotloopNativeExecutionError" and route=="native_error" and actual["stdout"]=="" and fn._call_count_fallback==0 else "D"
    correct=category==("A" if policy=="native" else "C" if mode=="strict" else "B")
    return dict(inputs=[wire(x) for x in args],mode=mode,policy=policy,expected=expected,actual=actual,
        backend=route,classification=category,correct=correct,native_calls=fn._call_count_native,fallback_calls=fn._call_count_fallback)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args();args.output.mkdir()
    source=args.output/"subject.py";source.write_bytes(Path(__file__).with_name("adjacent_source.py").read_bytes())
    built,diagnostic,_=MojoBackend().build_ast(source);assert built,diagnostic
    module=load(source,"adjacent_math");rows=[];builds=[dict(source="adjacent_source.py",ok=built,diagnostic=diagnostic)]
    for name,inputs in cases():
        policy="native" if name in ("constant_exp","constant_sin","integer_log") else "python"
        for mode in ("default","forced","strict"):
            rows.append(dict(function=name,**check(getattr(module,name)._original,inputs,mode,policy)))
    aliases=[("from_import","from math import log as logarithm","logarithm(x)"),
             ("module_alias","import math as mathematics","mathematics.log(x)"),
             ("string_argument","import math","math.log(x)")]
    for label,statement,expression in aliases:
        folder=args.output/label;folder.mkdir();path=folder/"subject.py"
        annotation="str" if label=="string_argument" else "float";values=["2.0"] if label=="string_argument" else [0.0]
        text=statement+"\nfrom hotloop import hotloop\n@hotloop\ndef alias_call(x: "+annotation+") -> float:\n    return "+expression+"\n"
        path.write_text(text);ok,message,_=MojoBackend().build_ast(path);builds.append(dict(source=label,ok=ok,diagnostic=message))
        mod=load(path,"alias_"+label)
        for mode in ("default","forced","strict"):
            rows.append(dict(function=label,**check(mod.alias_call._original,values,mode,"python")))
    result=dict(python=sys.version,builds=builds,rows=rows,counts={k:sum(x["classification"]==k for x in rows) for k in "ABCD"},failures=[x for x in rows if not x["correct"]])
    (args.output/"observations.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(dict(rows=len(rows),counts=result["counts"],failures=len(result["failures"]))))
    return bool(result["failures"])
if __name__=="__main__":sys.exit(main())
