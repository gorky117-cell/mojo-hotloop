"""A binary generated at the frozen baseline must not enter the corrected runtime."""
import importlib.util,json,shutil,sys,warnings
from pathlib import Path
from hotloop import hotloop
from hotloop._native_cache import implementation_revision
source,dest,output=map(Path,sys.argv[1:])
dest.mkdir()
for name in ("original.py","fast.mojo","fast.so","fast.hotloop_manifest.json"):
    shutil.copyfile(source/name,dest/name)
shutil.copytree(source/"__mojocache__",dest/"__mojocache__")
old=json.loads((dest/"fast.hotloop_manifest.json").read_text())
spec=importlib.util.spec_from_file_location("old_geographic_artifact",dest/"original.py")
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m
with warnings.catch_warnings():
    warnings.simplefilter("ignore");spec.loader.exec_module(m)
    rows=[]
    for mode in ("default","forced","strict"):
        f=hotloop(force_native=mode=="forced",strict=mode=="strict")(m.accumulate_haversine_distance._original)
        try:f([1.,2.],[1.]);actual=dict(exception=None)
        except Exception as e:actual=dict(exception=type(e).__name__,message=str(e))
        actual.update(mode=mode,backend=f._last_backend,native_calls=f._call_count_native,fallback_calls=f._call_count_fallback)
        assert f._call_count_native==0,actual
        if mode=="strict":
            assert actual["exception"]=="HotloopNativeExecutionError" and f._call_count_fallback==0,actual
        else:
            assert actual["exception"]=="IndexError" and actual["message"]=="list index out of range",actual
            assert f._last_backend=="python_fallback_stale_cache" and f._call_count_fallback==1,actual
        rows.append(actual)
new=implementation_revision();assert new!=old["context"]["implementation"]
output.write_text(json.dumps(dict(old_context=old["context"],current_implementation=new,rows=rows),indent=2)+"\n")
print(json.dumps(rows))
