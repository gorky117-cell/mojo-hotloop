> This guide describes AST lowering, not unconditional native qualification. The unreleased corrective candidate additionally enforces exact interpreter/platform, object provenance and input restrictions described in [README](../README.md). Unsupported calls may fall back even if syntax lowers.

# Supported Python Syntax — mojo-hotloop AST Transpiler

> **Version**: mojo-hotloop v0.2.1, Mojo 1.2.0 target
> **Transpiler**: `hotloop/ast_transpiler.py`, offline AST engine (`0.2.1-ast`)

This document describes exactly which Python constructs the AST transpiler
supports, and what must be rewritten for a function to be transpilable.

---

## Overview

The AST transpiler performs **ahead-of-time** (AOT) transpilation of annotated
Python functions into Mojo 1.2.0 source code. It supports a **strict subset**
of Python — not all Python programs can be transpiled.

If a function uses unsupported syntax, the transpiler raises `ASTTranspileError`
and the `@hotloop` decorator safely falls back to the original Python
implementation.

---

## Type Annotations (Required)

All function parameters and return types **must** be annotated.

| Python annotation | Mojo type |
|-------------------|-----------|
| `int`             | `Int`     |
| `float`           | `Float64` |
| `bool`            | `Bool`    |
| `str`             | `String`  |
| `list[int]`       | `List[Int]` |
| `list[float]`     | `List[Float64]` |
| `list[bool]`      | `List[Bool]` |
| `list[str]`       | `List[String]` |

**Not directly annotated yet**: `dict`, `set`, `tuple`, `Optional`, `Union`,
`Any`, generic type parameters.

**Collection boundary.** v0.2.1 copies qualified exact lists of builtin elements into native storage. Functions that can mutate, retain, alias or return a borrowed list use Python. NumPy values, memoryviews and other buffer exporters use Python in ordinary and forced modes. Strict mode rejects these calls. No native kernel borrows a buffer address. The preserved [NumPy example](../examples/numpy_vector/README.md) describes the old route; its native expectation is not valid for v0.2.1.

**Corrective native restrictions.** Prefix/suffix methods with start/end bounds or keywords use Python because bounded Unicode parity is unproven. Unbounded methods retain native qualification. Variadic signatures use semantic fallback even with keyword calls; strict mode rejects them before application effects.

**Keyword & default arguments**: Functions compiled by `@hotloop` support default
parameter values and keyword call-site arguments (bound via `inspect.signature`
when needed).

### Example — Correctly Annotated

```python
@hotloop
def dot_product(xs: list[float], ys: list[float]) -> float:
    total: float = 0.0
    for i in range(len(xs)):
        total += xs[i] * ys[i]
    return total
```

---

## Local Variable Declarations

Local variables **must** be declared with an explicit type annotation on first assignment:

```python
total: float = 0.0   # ✅ correct
total = 0.0          # ❌ rejected — missing type annotation
```

---

## Control Flow

| Construct | Supported | Notes |
|-----------|-----------|-------|
| `for i in range(n)` | ✅ | Single-argument range |
| `for i in range(start, stop)` | ✅ | Two-argument range |
| `for i in range(start, stop, step)` | ✅ | Three-argument range |
| `while <condition>:` | ✅ | |
| `if / elif / else` | ✅ | Arbitrarily nested |
| `return` (anywhere) | ✅ | Early return inside loops works |
| `break` | ❌ | Not supported — use `return` instead |
| `continue` | ❌ | Not supported |
| `for x in collection:` | ❌ | Only `range()` iteration supported |

---

## Expressions

### Arithmetic Operators

| Operator | Python | Supported |
|----------|--------|-----------|
| Add      | `a + b` | ✅ |
| Subtract | `a - b` | ✅ |
| Multiply | `a * b` | ✅ |
| Divide   | `a / b` | ✅ (raises `ZeroDivisionError` on zero divisor) |
| Floor div | `a // b` | ✅ |
| Modulo   | `a % b`  | ✅ |
| Power    | `a ** b` | ✅ |
| Bitwise AND | `a & b` | ✅ |
| Bitwise OR  | `a \| b` | ✅ |
| Bitwise XOR | `a ^ b` | ✅ |
| Left shift  | `a << b` | ✅ |
| Right shift | `a >> b` | ✅ |
| Unary negate | `-x` | ✅ |
| Unary not   | `not x` | ✅ |

### Comparison Operators

| Operator | Supported |
|----------|-----------|
| `==`, `!=`, `<`, `<=`, `>`, `>=` | ✅ |
| Chained comparisons (`a < b < c`) | ✅ Supported (`0 <= ord(ch) <= 127`, numeric chains, etc.; slice targets excluded) |

### Boolean Operators

| Operator | Supported |
|----------|-----------|
| `and`, `or` | ✅ |
| `not` | ✅ |

### Augmented Assignment

```python
x += 1    # ✅
x -= 1    # ✅
x *= 2    # ✅
x /= 2    # ✅
x //= 2   # ✅
x %= 2    # ✅
x **= 2   # ✅
```

---

## Built-in Functions

| Function | Supported | Notes |
|----------|-----------|-------|
| `len(xs)` | ✅ | Works on `list[*]` and `str` |
| `range(n)` | ✅ | |
| `range(start, stop)` | ✅ | |
| `range(start, stop, step)` | ✅ | |
| `ord(c)` | ✅ | Returns Unicode codepoint of single-char string |
| `chr(code)` | ✅ | Returns single-character string (`ValueError` if outside `0..0x10FFFF`) |
| `abs(x)` | ✅ | Scalar only (checks `INT64_MIN` overflow) |
| `int(x)`, `float(x)`, `str(x)` | ✅ | Type conversion |
| `bool(x)` | ✅ | |
| `min(a, b)`, `max(a, b)` | ✅ | Two scalars only; list form not supported |
| `print(...)` | ❌ | Not supported inside transpiled functions |
| `enumerate()`, `zip()` | ❌ | Not supported |

---

## Standard Library (`math` module)

Import with `import math`, then use `math.<function>`:

In `v0.2.1`, unary `sin`/`cos`/`sqrt`/`log`/`exp`, binary `atan2`, and predicates `isnan`/`isinf` qualify **exact numeric operands only** (`int`, `float`, `bool`) via overloaded `_math_operand` helpers preserving CPython `ValueError`/`OverflowError` domain/range semantics. Strings, complex numbers, custom `__float__`/`__index__` objects, NumPy scalars, other `math.*` signatures (`math.pow`, two-argument `log`), and aliased imports fall back to Python (or raise `HotloopNativeExecutionError` in `strict=True`).

| Function | Supported |
|----------|-----------|
| `math.sin(x)` | ✅ |
| `math.cos(x)` | ✅ |
| `math.sqrt(x)` | ✅ |
| `math.atan2(y, x)` | ✅ |
| `math.log(x)` | ✅ |
| `math.exp(x)` | ✅ |
| `math.floor(x)` | Python fallback; native integer/type contract unqualified |
| `math.ceil(x)` | Python fallback; native integer/type contract unqualified |
| `math.pi` | ✅ |
| `math.e` | ✅ |
| `math.inf` | ❌ |
| `math.nan` | ❌ |
| `math.isnan(x)` | ✅ (`int` / `float` / `bool` numeric operands only) |
| `math.isinf(x)` | ✅ (`int` / `float` / `bool` numeric operands only) |

---

## List Operations

```python
result: list[float] = []        # ✅ Empty list initialization
result.append(value)            # ✅ Append element
result[i]                       # ✅ Positive & negative index read (IndexError on OOB)
result[-1]                      # ✅ Negative index read
result[i] = value               # ✅ Index write (including negative indices & AugAssign)
result.clear()                  # ✅ Clear list
len(result)                     # ✅ Length
```

---

## String Operations

```python
s: str = ""                     # ✅ Empty string (also supports unannotated s = "")
s += "text"                     # ✅ String concatenation
s += s[i]                       # ✅ Direct single-character write without temp allocation
len(s)                          # ✅ Length in Unicode codepoints
ord(s[i])                       # ✅ Character access + codepoint
s[i]                            # ✅ Positive & negative indexing (IndexError on OOB)
s[start:stop]                   # ✅ String slicing
s[start:stop:step]              # ✅ Stepped slicing (ValueError if step == 0)
s.startswith(prefix)            # ✅ Unbounded prefix check (str, literal, or tuple of prefixes)
s.endswith(suffix)              # ✅ Unbounded suffix check (str, literal, or tuple of suffixes)
s.startswith(prefix, start, stop) # Python fallback (bounded Unicode/keyword parity excluded from native)
s.endswith(suffix, start, stop)   # Python fallback (bounded Unicode/keyword parity excluded from native)
```

---

## Numeric Semantics

- **Integer arithmetic**: 64-bit checked arithmetic. Overflow raises `HotloopFallbackWarning`
  and falls back to arbitrary-precision Python (unless `strict=True`).
- **Float arithmetic**: IEEE 754 double precision. NaN comparisons (`x != x`) work correctly.
- **Division by zero**: Exact Python `ZeroDivisionError` semantics preserved across FFI boundary.

---

## Not Supported (Will Raise ASTTranspileError)

- `lambda` expressions
- List comprehensions (`[x*x for x in xs]`)
- Generator expressions
- `*args`, `**kwargs`
- `yield` / generators
- `class` definitions
- `import` statements inside function body
- `try` / `except` / `finally`
- `with` / context managers
- `global` / `nonlocal`
- `del`
- Walrus operator (`:=`)
- f-strings
- List slice notation (`xs[1:3]`) — note: string slices `s[1:3]` *are* supported
- `dict`, `set`, `tuple`, `frozenset`
- Mojo hard keywords (`fn`, `var`, `struct`, `ref`, `trait`, `comptime`, `Self`) used as variable/parameter names, or argument-convention keywords (`out`, `mut`, `owned`, `borrowed`, `inout`, `read`) used as parameter names (rejected with `ASTTranspileError`)

---

## Full Working Example

```python
import math
from hotloop import hotloop

@hotloop
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R: float = 6371.0
    dlat: float = (lat2 - lat1) * math.pi / 180.0
    dlon: float = (lon2 - lon1) * math.pi / 180.0
    a: float = math.sin(dlat / 2.0) * math.sin(dlat / 2.0) + \
               math.cos(lat1 * math.pi / 180.0) * math.cos(lat2 * math.pi / 180.0) * \
               math.sin(dlon / 2.0) * math.sin(dlon / 2.0)
    c: float = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c
```

Build with:
```bash
hotloop build myfile.py --engine=ast
```
