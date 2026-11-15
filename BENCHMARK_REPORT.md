# mojo-hotloop Benchmark Report

## System Environment
- **CPU**: Intel(R) Core(TM) i5-8265U CPU @ 1.60GHz
- **Cores**: 8
- **RAM**: 7.6 GB
- **OS**: Linux (WSL2 x86_64)
- **Mojo Version**: Mojo 1.2.0
- **Python Version**: 3.12.16

## Results Table
| Benchmark Workload | Engine | Comparison Tool | Pure Python p50 (ms) | Comparison Tool p50 (ms) | Mojo .so p50 (ms) | Speedup vs Python |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `quant_backtest` (100k ticks) | AST-auto (`--engine=ast`, `-O3`) | Numba `@njit` (1810.4ms JIT) | 43.780 ms | 0.604 ms | 0.531 ms | **82.4x** |

### Detailed Notes on `quant_backtest`
- **Pure Python**: 43.780 ms (p95: 62.290 ms, mean: 46.258 ms)
- **Numba `@njit`**: 0.604 ms (p95: 0.828 ms, mean: 0.637 ms), with an initial cold-start compile delay of 1810.4 ms.
- **Mojo `.so` (C-ABI, AST-generated)**: 0.531 ms (p95: 0.764 ms, mean: 0.570 ms), zero runtime JIT lag.
- **Verification**: 1,117 tests verified with 0 mismatches (`examples/quant_backtest/verify.py`). See [`docs/BENCHMARKS.md`](docs/BENCHMARKS.md) for all 7 application benchmarks.
