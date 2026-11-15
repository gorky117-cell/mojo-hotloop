# Supported Python Syntax — mojo-hotloop AST Transpiler

> **Version**: mojo-hotloop v0.1.0, Mojo 1.2.0 target  
> **Transpiler**: `hotloop/ast_transpiler.py`, version `1.2.0-phaseD`

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

**Not supported**: `numpy.ndarray`, `dict`, `set`, `tuple`, `Optional`, `Union`,
`Any`, generic type parameters.

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
| Chained: `a < b < c` | ⚠️ **Known limitation** — accepted but may compile incorrectly. Rewrite as `a < b and b < c` |

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
| `abs(x)` | ✅ | Scalar only |
| `int(x)`, `float(x)`, `str(x)` | ✅ | Type conversion |
| `bool(x)` | ✅ | |
| `min(a, b)`, `max(a, b)` | ✅ | Two scalars only; list form not supported |
| `print(...)` | ❌ | Not supported inside transpiled functions |
| `enumerate()`, `zip()` | ❌ | Not supported |

---

## Standard Library (`math` module)

Import with `import math`, then use `math.<function>`:

| Function | Supported |
|----------|-----------|
| `math.sin(x)` | ✅ |
| `math.cos(x)` | ✅ |
| `math.sqrt(x)` | ✅ |
| `math.atan2(y, x)` | ✅ |
| `math.log(x)` | ✅ |
| `math.exp(x)` | ✅ |
| `math.floor(x)` | ✅ |
| `math.ceil(x)` | ✅ |
| `math.pi` | ✅ |
| `math.e` | ✅ |
| `math.inf` | ❌ |
| `math.nan` | ❌ |
| `math.isnan(x)` | ❌ |
| `math.isinf(x)` | ❌ |

---

## List Operations

```python
result: list[float] = []        # ✅ Empty list initialization
result.append(value)            # ✅ Append element
result[i]                       # ✅ Positive index access
result[i] = value               # ✅ Positive index write
result[-1]                      # ⚠️ KNOWN BUG — accepted but generates wrong code
                                #   Workaround: result[len(result) - 1]
result.clear()                  # ✅ Clear list
len(result)                     # ✅ Length
```

---

## String Operations

```python
s: str = ""                     # ✅
s += "text"                     # ✅ String concatenation
s += other_str                  # ✅
len(s)                          # ✅
ord(s[i])                       # ✅ Character access + codepoint
s[i]                            # ✅ Single-character access by index
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
- Slice notation (`xs[1:3]`)
- `dict`, `set`, `tuple`, `frozenset`
- `numpy` / any third-party types

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
