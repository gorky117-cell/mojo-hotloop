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
| `quant_backtest` (100k ticks) | Hand-crafted (Stage 2) / AST | Numba @njit (2375.5ms JIT) | 25.934 ms | 0.353 ms | 0.322 ms | **80.5x** |

### Detailed Notes on `quant_backtest`
- **Pure Python**: 25.934 ms (p95: 32.263 ms)
- **Numba @njit**: 0.353 ms (p95: 0.456 ms), with a initial cold-start compile delay of 2375.5 ms.
- **Mojo .so (C-ABI)**: 0.322 ms (p95: 0.464 ms), zero runtime compilation lag, pure native execution.
- **Verification**: 1,109 tests (boundary, 1000 randomized, hypothesis) passed with 0 mismatches.
