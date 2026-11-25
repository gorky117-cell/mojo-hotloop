"""Check return identity and caller-visible writes on a function from each tag's own test suite."""
import ast
import json
from pathlib import Path
import subprocess
import sys
import warnings
from hotloop import hotloop

suite = ast.parse(Path(sys.argv[1]).read_text())
source = next(n.value.value for n in suite.body if isinstance(n, ast.Assign) and
              isinstance(n.value, ast.Constant) and any(isinstance(t, ast.Name) and t.id == "MODULE_SOURCE" for t in n.targets))
fn = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "in_place_list_swap")
Path("identity_subject.py").write_text("from hotloop import hotloop\n@hotloop\n" + ast.get_source_segment(source, fn) + "\n")
subprocess.run([sys.executable, "-m", "hotloop.cli", "build", "identity_subject.py", "--no-verify"], check=True, capture_output=True)
sys.path.insert(0, str(Path.cwd()))
from identity_subject import in_place_list_swap as decorated

out = {}
for mode, call in [("python",decorated._original),("default",decorated),
                   ("forced",hotloop(force_native=True)(decorated._original)),("strict",hotloop(strict=True)(decorated._original))]:
    argument = [1, 2, 3, 4]
    with warnings.catch_warnings(record=True) as msgs:
        warnings.simplefilter("always")
        try:
            result = call(argument)
        except Exception as e:
            out[mode] = {"input_after": argument, "exception": type(e).__name__, "message": str(e), "route": getattr(call, "_last_backend", "original")}
            continue
    out[mode] = {"input_after":argument,"returned":result,"returned_input":result is argument,
                 "route":getattr(call,"_last_backend","original"),"warnings":[w.category.__name__ for w in msgs]}
print(json.dumps(out,indent=2))
