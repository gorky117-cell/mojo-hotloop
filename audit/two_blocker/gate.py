"""Bounded numeric-operand and predicate qualification; no application replay."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "math_correctness"))
from run_focused import invoke
from hotloop import hotloop
from hotloop.backends.mojo import MojoBackend

OPS = ("sin", "cos", "sqrt", "log", "exp", "atan2", "isnan", "isinf")


class FloatObject:
    def __float__(self):
        print("FLOAT")
        return 2.0


class IndexObject:
    def __index__(self):
        print("INDEX")
        return 2


class BrokenFloat:
    def __float__(self):
        print("BROKEN_FLOAT")
        raise RuntimeError("conversion failed")


class FloatSubclass(float):
    def __float__(self):
        print("SUBCLASS_FLOAT")
        return 3.0


class IntSubclass(int):
    def __float__(self):
        print("SUBCLASS_INT_FLOAT")
        return 3.0


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def observe(original, factory, mode, native):
    expected = invoke(original, [factory()])
    fn = hotloop(force_native=mode == "forced", strict=mode == "strict")(original)
    actual = invoke(fn, [factory()])
    route = fn._last_backend
    if actual == expected and route == "native":
        category = "A"
    elif actual == expected and route.startswith("python_fallback"):
        category = "B"
    elif (mode == "strict" and route == "native_error"
          and actual.get("exception") == "HotloopNativeExecutionError"
          and actual["stdout"] == "" and fn._call_count_native == 0
          and fn._call_count_fallback == 0):
        category = "C"
    else:
        category = "D"
    wanted = "A" if native else "C" if mode == "strict" else "B"
    return dict(mode=mode, expected=expected, actual=actual, backend=route,
                classification=category, expected_classification=wanted,
                correct=category == wanted, native_calls=fn._call_count_native,
                fallback_calls=fn._call_count_fallback)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir()
    rows, builds = [], []
    source = args.output / "subject.py"
    source.write_bytes(Path(__file__).with_name("operand_source.py").read_bytes())
    ok, diagnostic, _ = MojoBackend().build_ast(source)
    builds.append(dict(name="supported", ok=ok, diagnostic=diagnostic))
    assert ok, diagnostic
    module = load(source, "numeric_operand_gate")

    def check(name, original, factory, native):
        for mode in ("default", "forced", "strict"):
            rows.append(dict(function=name, **observe(original, factory, mode, native)))

    for kind, values in [
        ("float", [0.0, -0.0, 1.0, -1.0, float("nan"), float("inf"), -float("inf"), 1000.0]),
        ("int", [0, 1, -1, 3, (1 << 63) - 1]),
        ("bool", [False, True]),
    ]:
        for op in OPS:
            original = getattr(module, op + "_" + kind)._original
            for value in values:
                check(op + "_" + kind, original, lambda value=value: value, True)

    unusual = [
        ("integer", lambda: 2), ("bool", lambda: True),
        ("numeric_string", lambda: "2.0"), ("spaced_string", lambda: "  +2.0e0  "),
        ("underscore_string", lambda: "2_000.0"), ("hex_string", lambda: "0x1.0p1"),
        ("nan_string", lambda: "nan"), ("inf_string", lambda: "inf"),
        ("invalid_string", lambda: "not a number"), ("empty_string", lambda: ""),
        ("complex", lambda: 2 + 0j), ("none", lambda: None),
        ("float_object", FloatObject), ("index_object", IndexObject),
        ("broken_float", BrokenFloat), ("float_subclass", lambda: FloatSubclass(2.0)),
        ("int_subclass", lambda: IntSubclass(2)), ("huge_int", lambda: 10 ** 1000),
    ]
    import numpy as np
    unusual += [("numpy_float", lambda: np.float64(2.0)),
                ("numpy_int", lambda: np.int64(2)), ("numpy_bool", lambda: np.bool_(True))]
    for op in OPS:
        original = getattr(module, op + "_float")._original
        for label, factory in unusual:
            check(op + "_float/" + label, original, factory, False)
    # Annotation mismatches must not silently change the actual operand.
    for kind, factory in [("int", lambda: 2.5), ("bool", lambda: 2.5)]:
        for op in OPS:
            check(op + "_" + kind + "/float", getattr(module, op + "_" + kind)._original, factory, False)
    for name in ("helper_expression", "temporary_expression", "predicates"):
        for value in [0.0, -1.0, float("nan"), float("inf")]:
            check(name, getattr(module, name)._original, lambda value=value: value, True)
    check("effects", module.effects._original, lambda: -1.0, False)

    # Isolate unqualified String expressions: no numeric parser can be selected.
    invalid = {op: "math." + op + ("(x, x)" if op == "atan2" else "(x)") for op in OPS}
    invalid.update(
        helper="math.log(text(x))",
        local="math.log(y)",
        from_alias="log_alias(x)",
        module_alias="mathematics.log(x)",
    )
    for label, expression in invalid.items():
        folder = args.output / label
        folder.mkdir()
        source = folder / "subject.py"
        ret = "bool" if label in ("isnan", "isinf") else "float"
        text = ("import math\nimport math as mathematics\nfrom math import log as log_alias\n"
                "from hotloop import hotloop\ndef text(x: str) -> str:\n    return x\n"
                "@hotloop\ndef subject(x: str) -> " + ret + ":\n")
        if label == "local":
            text += "    y: float = x\n"
        text += "    return " + expression + "\n"
        source.write_text(text)
        ok, diagnostic, _ = MojoBackend().build_ast(source)
        builds.append(dict(name=label, ok=ok, diagnostic=diagnostic))
        item = load(source, "invalid_operand_" + label)
        for value in ("2.0", "  +2.0e0  ", "nan", "bad"):
            check("string_expression/" + label, item.subject._original, lambda value=value: value, False)

    result = dict(rows=rows, builds=builds, counts={k: sum(x["classification"] == k for x in rows) for k in "ABCD"},
                  failures=[x for x in rows if not x["correct"]])
    (args.output / "observations.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(dict(rows=len(rows), counts=result["counts"], failures=len(result["failures"]))))
    return bool(result["failures"])


if __name__ == "__main__":
    sys.exit(main())
