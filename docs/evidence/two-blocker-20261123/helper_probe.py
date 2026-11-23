import importlib.util,json,struct,sys
from pathlib import Path
from hotloop import hotloop
from hotloop.backends.mojo import MojoBackend
p=Path(sys.argv[1]);ok,msg,_=MojoBackend().build_ast(p)
rows=[]
if True:
 spec=importlib.util.spec_from_file_location("helper_contract_probe",p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
 for mode in ["default","forced","strict"]:
  f=hotloop(force_native=mode=="forced",strict=mode=="strict")(m.helper_operand._original)
  x=9007199254740993;expected=m.helper_operand._original(x)
  try:got=f(x);row=dict(actual=got,expected=expected,equal=struct.pack(">d",got)==struct.pack(">d",expected))
  except Exception as e:row=dict(error=type(e).__name__,message=str(e),expected=expected)
  row.update(mode=mode,backend=f._last_backend,native_calls=f._call_count_native,fallback_calls=f._call_count_fallback);rows.append(row)
print(json.dumps(dict(build_ok=ok,diagnostic=msg,rows=rows),indent=2))
