"""Compare the same argument-origin cases in separate installed runtimes.

Usage: python identity.py NEW_DIRECTORY [--expect-fixed]
Also supports --reject-old DIRECTORY to test old-artifact rejection before loading.
"""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import warnings

SOURCE = """from hotloop import hotloop
DEFAULT = float("123.5")
@hotloop
def direct(x: float) -> float:
    return x
@hotloop
def direct_int(x: int) -> int:
    return x
@hotloop
def alias(x: float) -> float:
    a: float = x
    b: float = a
    return b
@hotloop
def choose(x: float, y: float, flag: bool) -> float:
    value: float = x
    if flag:
        value = y
    return value
@hotloop
def empty_loop(x: float, count: int) -> float:
    result: float = x
    for i in range(count):
        result += 0.0
    return result
@hotloop
def defaulted(x: float = DEFAULT) -> float:
    return x
@hotloop
def first(values: list[float]) -> float:
    return values[0]
@hotloop
def computed(x: float) -> float:
    return x + 0.0
"""

def load(path):
    spec = importlib.util.spec_from_file_location("return_identity_case", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod

def main():
    from hotloop import hotloop, HotloopNativeExecutionError
    if sys.argv[1] == "--reject-old":
        import hotloop.decorator as runtime
        def forbidden(*a, **kw):
            raise AssertionError("old binary reached native loader")
        runtime._load_native_module = forbidden
        mod = load(Path(sys.argv[2]) / "return_identity_case.py")
        x = float("123.5")
        assert mod.direct._compiled is None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            assert mod.direct(x) is x
        assert mod.direct._last_backend == "python_fallback_stale_cache"
        try:
            hotloop(strict=True)(mod.direct._original)(x)
        except HotloopNativeExecutionError:
            pass
        else:
            raise AssertionError("strict accepted an old artifact")
        print(json.dumps(dict(old_artifact_rejected_before_loader=True,
                              default_identity_correct=True, strict_rejected=True)))
        return
    from hotloop.backends.mojo import MojoBackend
    root = Path(sys.argv[1]).resolve()
    root.mkdir()
    path = root / "return_identity_case.py"
    path.write_text(SOURCE)
    ok, diagnostic, _ = MojoBackend().build_ast(path)
    assert ok, diagnostic
    mod = load(path)
    x, same = float("123.5"), float("123.5")
    assert x is not same
    cases = [
        ("direct", (x,), {}, x, True),
        ("direct", (), {"x": x}, x, True),
        ("direct", (float("-0.0"),), {}, None, True),
        ("direct", (float("nan"),), {}, None, True),
        ("direct", (float("inf"),), {}, None, True),
        ("direct_int", (int("1234567890123"),), {}, None, True),
        ("alias", (x,), {}, x, True),
        ("choose", (x,same,False), {}, x, True),
        ("choose", (x,same,True), {}, same, True),
        ("empty_loop", (x,0), {}, x, True),
        ("empty_loop", (x,2), {}, x, False),
        ("defaulted", (), {}, mod.DEFAULT, True),
        ("first", ([x],), {}, x, True),
        ("computed", (x,), {}, x, False),
    ]
    rows = []
    for mode in ("default","forced","strict"):
        for name,args,kwargs,owner,alias in cases:
            fn = hotloop(force_native=mode=="forced", strict=mode=="strict")(getattr(mod,name)._original)
            # List marshaling is intentionally disabled by default.
            if name=="first" and mode=="default":
                continue
            owner = owner if owner is not None else args[0]
            expected = fn._original(*args, **kwargs)
            actual = fn(*args, **kwargs)
            assert type(actual) is type(expected)
            equal = (struct.pack(">d",actual)==struct.pack(">d",expected)
                     if type(expected) is float else actual==expected)
            assert equal
            correct_identity = (actual is owner) == alias
            row = dict(name=name,mode=mode,route=fn._last_backend,
                       types_and_bits_equal=equal,identity_correct=correct_identity,
                       returned_owner=actual is owner,expected_owner=alias)
            if "--expect-fixed" in sys.argv:
                assert correct_identity and fn._last_backend=="native", row
            rows.append(row)
    print(json.dumps(dict(cases=len(rows),identity_correct=sum(r["identity_correct"] for r in rows),
                          rows=rows), indent=2))

if __name__ == "__main__":
    main()
