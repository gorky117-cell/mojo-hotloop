---
name: Performance Regression Report
about: Report a function running slower than expected, or a regression versus earlier versions
labels: performance, bug
---

## Performance Regression Report

### Summary
<!-- 1-sentence description of the workload and observed slowdown -->

### Benchmark Environment
- **CPU / Hardware**: <!-- e.g., Intel Core i5-8265U, 4 cores / 8 threads -->
- **RAM**: <!-- e.g., 16 GB -->
- **Operating System**: <!-- e.g., Ubuntu 24.04 LTS / WSL2 -->
- **Python Version**: <!-- python3 --version -->
- **Mojo Version**: <!-- mojo --version -->
- **mojo-hotloop Version / Commit**: <!-- git rev-parse HEAD -->

### Workload & Data Scale
- **Function under test**: <!-- e.g., quantitative moving average, ray caster -->
- **Input scale & data type**: <!-- e.g., 10,000 float64 numpy array, 100k char string -->
- **Number of trials**: <!-- minimum 100 trials recommended -->

### Measured Timings (Median $p_{50}$)
| Implementation | Median ($p_{50}$) | Min ($p_5$) | Max ($p_{95}$) |
| :--- | :--- | :--- | :--- |
| Pure CPython 3.12 | | | |
| mojo-hotloop (Current) | | | |
| mojo-hotloop (Prior / Expected) | | | |
| Alternative (e.g. Numba/Codon/NumPy) | | | |

### Execution Mode
- [ ] Verified native execution (`fn._last_backend == 'native'`)
- [ ] Fallback execution occurred (`fn._last_backend == 'python_fallback'`)
- [ ] Tested with `HOTLOOP_STRICT_NATIVE=1`

### Minimal Benchmark Script
```python
# Provide a minimal reproduction script using time.perf_counter()
```
