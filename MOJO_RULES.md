# Mojo Rules and Numerical Tolerance Policy

## Reference Pattern (Mojo 1.2.0)
```mojo
from std.python import PythonObject
from std.python.bindings import PythonModuleBuilder
from std.os import abort

@export
def PyInit_<mod_name>() abi("C") -> PythonObject:
    try:
        var m = PythonModuleBuilder("<mod_name>")
        m.def_function[<fn_name>]("<fn_name>")
        return m.finalize()
    except e:
        abort(String("error creating Python Mojo module: ", e))

def <fn_name>(arg0: PythonObject, ...) raises -> PythonObject:
    # 1. Convert PythonObject arguments to native Mojo values ONCE,
    #    before any loop (e.g., var n = Int(py=arg0), var f = Float64(py=arg1)).
    # 2. Call a native Mojo function that does all the heavy work,
    #    with zero PythonObject operations inside loops.
    # 3. Return the result as a PythonObject.
```

## Syntax & Standard Library Rules
- Always use `def` and `var`.
- NEVER use obsolete constructs: `let`, `@value`, `DynamicVector`, `from python import ...`.
- Standard library modules must use the `std` prefix: `from std.python import ...`, `from std.python.bindings import ...`, `from std.os import ...`, `from std.math import ...`.
- Build command: `mojo build <mod>.mojo --emit shared-lib -o <mod>.so`.
- No `main()` function in any file built as a shared library.

## Semantic Truth
- **THE ORIGINAL PYTHON FUNCTION IS THE SOURCE OF TRUTH.** Never alter `original.py` to make Mojo conversion easier. Mojo must return exactly what the Python function returns for the exact same input.
- **Strings**: Python `str` counts Unicode codepoints; Mojo `String` stores UTF-8 bytes. Output must equal Python output for any input, including Hindi, CJK, and emoji. Any length, offset, or slicing logic must match Python codepoint semantics.
- **Integers**: Python ints never overflow; Mojo `Int` is signed 64-bit (-9223372036854775808 to 9223372036854775807). Never add artificial masks or limits unless the Python code explicitly uses them. If a function's integers can overflow 64 bits on valid inputs, `hotloop` must refuse to build it and explain why.

## Explicit Numerical Tolerance Policy
- **Exact types** (`int`, `str`, `bool`, `list`, `tuple`): Require 100% exact equality (`py_out == mojo_out`).
- **Floating-point** (`float` / IEEE-754 `Float64`): Require `math.isclose(py_out, mojo_out, rel_tol=1e-9, abs_tol=1e-12)`, plus identical `math.isnan()` and `math.isinf()` behavior.
- **Exceptions**: If Python raises an exception (e.g. `ValueError`, `ZeroDivisionError`) on an invalid boundary input, match safe error handling without native crashing or segfaults.
