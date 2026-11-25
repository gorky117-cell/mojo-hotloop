"""Run real installed interpreters in isolated subprocesses; no platform emulation."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import warnings
import io

def child(source,out):
    sys.path.insert(0,str(source))
    from hotloop import hotloop,HotloopNativeExecutionError
    from hotloop.backends.mojo import MojoBackend
    out.mkdir()
    path=out/"compat_subject.py"
    path.write_text("from hotloop import hotloop\n@hotloop\ndef identity(x: float) -> float:\n    return x\n")
    ok,diagnostic,_=MojoBackend().build_ast(path)
    spec=importlib.util.spec_from_file_location("compat_subject",path)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    rows=[]
    for mode in ("default","forced","strict"):
        fn=hotloop(force_native=mode=="forced",strict=mode=="strict")(mod.identity._original)
        owner=float("123.5");entered=[]
        if sys.version_info[:3]!=(3,12,16) and fn._compiled is not None:
            def forbidden(*args):
                entered.append(True)
                raise AssertionError("unsupported user kernel entered")
            fn._compiled.raw=forbidden
        with warnings.catch_warnings(record=True) as notices:
            warnings.simplefilter("always")
            try:
                result=fn(owner)
                exception=None;identity=result is owner
            except Exception as error:
                exception=type(error).__name__;identity=None
        if sys.version_info[:3]==(3,12,16):
            assert exception is None and identity and fn._last_backend=="native"
        else:
            assert not entered and fn._call_count_native==0
            if mode=="strict":assert exception=="HotloopNativeExecutionError"
            else:assert exception is None and identity and fn._last_backend.startswith("python_fallback")
        rows.append(dict(mode=mode,backend=fn._last_backend,identity=identity,exception=exception,
             native_calls=fn._call_count_native,fallback_calls=fn._call_count_fallback,
             native_entry_available=fn._compiled is not None,native_body_spy_called=bool(entered),
             warnings=[type(x.message).__name__ for x in notices]))
    return dict(python=sys.version,executable=sys.executable,machine=platform.machine(),platform=sys.platform,
        source_import=str(source),build_ok=ok,build_diagnostic=diagnostic,rows=rows)

if __name__=="__main__":
    if sys.argv[1]=="--child":
        source,out=map(Path,sys.argv[2:])
        (out.parent/(out.name+".json")).write_text(json.dumps(child(source,out),indent=2)+"\n")
    else:
        interpreter,label,destination,revision=sys.argv[1:]
        root=Path(destination);root.mkdir()
        source=root/"source";source.mkdir()
        archive=subprocess.check_output(["git","archive",revision,"hotloop"])
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:tar.extractall(source,filter="data")
        env=os.environ.copy()
        for key in ("PYTHONPATH","HOTLOOP_STRICT","HOTLOOP_FORCE_NATIVE","HOTLOOP_STRICT_PERF"):env.pop(key,None)
        subprocess.run([interpreter,str(Path(__file__).resolve()),"--child",str(source),str(root/label)],env=env,check=True)
