"""Record that all nine unchanged constant cases actually complete natively."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
from hotloop import hotloop
from hotloop.backends.mojo import MojoBackend

test,output=map(Path,sys.argv[1:])
output.mkdir()
tree=ast.parse(test.read_text())
source=next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="SOURCE" for t in n.targets))
path=output/"nine_subject.py"
path.write_text(source)
ok,diagnostic,_=MojoBackend().build_ast(path)
assert ok,diagnostic
spec=importlib.util.spec_from_file_location("nine_subject",path)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)
rows=[]
for mode in ("default","forced","strict"):
    for name in ("literal_default","local_constant","helper_default"):
        original=getattr(mod,name)._original
        owner=original.__defaults__[0]
        assert original() is owner
        fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(original)
        result=fn()
        assert result is owner and fn._last_backend=="native"
        rows.append(dict(function=name,mode=mode,identity=True,native=fn._call_count_native,
                         fallback=fn._call_count_fallback,backend=fn._last_backend))
(output/"nine.json").write_text(json.dumps(dict(native=9,fallback=0,cases=rows),indent=2)+"\n")
