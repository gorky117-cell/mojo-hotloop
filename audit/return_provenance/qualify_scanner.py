"""Qualify the expert scanner against all original PII fixtures and owner edges."""
import ast
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import re
import sys
from hotloop.backends.mojo import MojoBackend
from scanner import scanner

root,out=map(Path,sys.argv[1:])
out.mkdir()
path=out/"pii_subject.py"
path.write_bytes((root/"examples/pii_scrubber/original.py").read_bytes())
ok,diagnostic,_=MojoBackend().build_ast(path)
assert ok,diagnostic
spec=importlib.util.spec_from_file_location("pii_subject",path)
mod=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=mod
spec.loader.exec_module(mod)
public=mod.scrub_pii
original=public._original
reference=scanner(mod)
owners=[v for v in original.__code__.co_consts if type(v) is str]
records=[]
def check(text):
    expected=original(text)
    native=public(text)
    candidate=reference(text)
    assert type(native) is type(expected) is type(candidate) is str
    assert native==expected==candidate
    pool=[text,*owners]
    actual_alias=[native is owner for owner in pool]
    ref_alias=[candidate is owner for owner in pool]
    correct_alias=[expected is owner for owner in pool]
    assert actual_alias==correct_alias,(repr(text),public._last_backend)
    assert ref_alias==correct_alias,repr(text)
    records.append(dict(chars=len(text),input_sha256=hashlib.sha256(text.encode("utf8","surrogatepass")).hexdigest(),
                        backend=public._last_backend,identity_correct=True,scanner_correct=True))
    check._last_backend=public._last_backend
    return native
check._original=original
ns=dict(vars(mod),random=random,re=re,os=os,sys=sys,Path=Path,scrub_pii=check)
tree=ast.parse((root/"examples/pii_scrubber/verify.py").read_text())
# Reuse the original verifier's functions, generators and fixture body unchanged.
selected=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.Assign))]
exec(compile(ast.Module(body=selected,type_ignores=[]),str(root/"examples/pii_scrubber/verify.py"),"exec"),ns)
stream=io.StringIO()
with redirect_stdout(stream):
    ns["run_tests"]()
original_count=len(records)
extras=["","a","é","🚀","plain unmodified text",str(123),"ABCDE1234F","6011111111111117",
        "12A","A+123","+123","123-4","123 ","x\x00y","\ud800","नमस्ते १२३ 🚀","aABCDE1234Fz",
        "[REDACTED_PAN]",("aa")[::2]]
for text in extras:
    check(text)
summary=dict(original_fixture_cases=original_count,extra_cases=len(extras),cases=records,
             native_calls=sum(r["backend"]=="native" for r in records),
             fallback_calls=sum(r["backend"]!="native" for r in records),
             source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
             verifier_stdout=stream.getvalue())
(out/"qualification.json").write_text(json.dumps(summary,indent=2)+"\n")
print(json.dumps({k:v for k,v in summary.items() if k not in ("cases","verifier_stdout")}))
