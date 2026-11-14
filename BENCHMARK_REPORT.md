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
| `quant_backtest` (100k ticks) | Hand-crafted (Stage 2) / AST | Numba @njit (1573.5ms JIT) | 32.638 ms | 0.522 ms | 0.493 ms | **66.1x** |

### Detailed Notes on `quant_backtest`
- **Pure Python**: 32.638 ms (p95: 39.834 ms)
- **Numba @njit**: 0.522 ms (p95: 0.640 ms), with a initial cold-start compile delay of 1573.5 ms.
- **Mojo .so (C-ABI)**: 0.493 ms (p95: 0.658 ms), zero runtime compilation lag, pure native execution.
- **Verification**: 1,109 tests (boundary, 1000 randomized, hypothesis) passed with 0 mismatches.
