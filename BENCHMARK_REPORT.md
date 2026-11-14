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
| `quant_backtest` (100k ticks) | Hand-crafted (Stage 2) / AST | Numba @njit (672.2ms JIT) | 26.382 ms | 0.377 ms | 0.344 ms | **76.7x** |

### Detailed Notes on `quant_backtest`
- **Pure Python**: 26.382 ms (p95: 28.092 ms)
- **Numba @njit**: 0.377 ms (p95: 0.394 ms), with a initial cold-start compile delay of 672.2 ms.
- **Mojo .so (C-ABI)**: 0.344 ms (p95: 0.365 ms), zero runtime compilation lag, pure native execution.
- **Verification**: 1,109 tests (boundary, 1000 randomized, hypothesis) passed with 0 mismatches.
