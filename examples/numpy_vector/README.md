> **Historical v0.2.0 example.** The v0.2.1 corrective candidate withdraws ndarray native borrowing. Its original algorithm still runs through Python fallback; strict mode rejects unqualified ndarray calls. The original verification script below retains 30 native-route assertions that are intentionally incompatible with this candidate. It is preserved as historical evidence, not a current native quickstart or speedup claim. Use the scalar installed-package example in the [current README](../../README.md).

# NumPy ndarray Zero-Copy Acceleration Example

This example demonstrates how **Mojo Hotloop** automatically provides zero-copy C-pointer dispatch for 1-D C-contiguous `numpy.ndarray` (`float64` and `int64`) inputs.

---

## The Challenge

In scientific Python, recursive or autoregressive equations (such as exponential decay filters, IIR filters, cumulative momentum, and dynamic threshold state machines) cannot be vectorized cleanly with standard NumPy operations because step $i$ strictly depends on step $i - 1$:

$$s_i = s_{i-1} \cdot \alpha + x_i \cdot (1 - \alpha)$$

Writing this in a pure Python loop suffers from substantial interpreter overhead:
- Python integer and float boxing / unboxing on every iteration.
- Dynamic method dispatch and bytecode loop overhead.
- Inability to optimize or pipeline memory access.

---

## How Mojo Hotloop Solves This

When you annotate the function with `@hotloop`:

```python
from hotloop import hotloop

@hotloop
def exponential_decay_filter(signal: list[float], decay: float) -> float:
    n: int = len(signal)
    if n == 0:
        return 0.0

    state: float = signal[0]
    weight: float = 1.0 - decay
    for i in range(1, n):
        state = state * decay + signal[i] * weight
    return state
```

Mojo Hotloop’s AST compiler analyzes the function and detects that:
1. `signal` is only accessed via `len(signal)` and read subscripts `signal[i]`.
2. The parameter is pointer-safe (`elem_type == "float"`).

It automatically generates a **dual-path C-ABI wrapper**:
- **Zero-Copy Native Path**: If the passed array satisfies:
  - `ndim == 1`
  - `flags.c_contiguous == True`
  - `dtype == np.float64` (or `np.int64`)
  
  Mojo Hotloop directly extracts `signal.ctypes.data` and passes the raw memory pointer (`OpaquePointer[MutUntrackedOrigin]`) into Mojo! No array copies, no unboxing, and no PythonObject allocations.
- **Safe Fallback Path**: If non-contiguous slices or generic Python lists are passed, Hotloop safely unboxes elements without crashing or causing undefined memory reads.

---

## Running the Benchmark

```bash
# 1. Build the native shared library
hotloop build original.py --engine=ast

# 2. Run the end-to-end benchmark
python run.py
```

### Empirical Results (1,000,000 floats):

| Implementation | Latency (1M elements) | Speedup |
|:---|:---|:---|
| **Pure Python loop** | 48.52 ms | Baseline (1.0×) |
| **Mojo Hotloop (Zero-Copy)** | **1.21 ms** | **40.2× faster** |

---

## Running Verification

```bash
python verify.py
```

Verifies:
- Empty array edge case.
- Single element boundary.
- Multiple array sizes (5 to 100,000 elements) with diverse decay factors.
- Safe execution on strided / non-contiguous arrays.
- 100% numerical equality against CPython float calculations.
