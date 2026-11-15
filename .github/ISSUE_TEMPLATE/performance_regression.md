---
name: Performance Regression
about: A function is slower than expected, or slower than a previous version
labels: performance
---

## Performance Regression Report

### Summary

<!-- One-line description: "haversine_km is 3x slower than v0.0.9" -->

### Environment

- **mojo-hotloop version** (current): <!-- git rev-parse HEAD -->
- **mojo-hotloop version** (last known good): <!-- if known -->
- **Python version**: <!-- python3 --version -->
- **Mojo version**: <!-- mojo --version -->
- **Hardware**: <!-- CPU model, RAM, OS -->

### Function

```python
from hotloop import hotloop

@hotloop
def affected_function(...) -> ...:
    # Paste the function here
    ...
```

### Benchmark Results

| Version | p50 (ms) | p5 (ms) | p95 (ms) | Backend |
|---------|----------|---------|----------|---------|
| Previous (working) | | | | native |
| Current (regressed) | | | | |

**How you measured**:
```python
import time
times = []
for _ in range(100):
    t0 = time.perf_counter()
    affected_function(...)
    times.append(time.perf_counter() - t0)
times.sort()
print(f"p50: {times[50]*1000:.3f} ms")
print(f"backend: {affected_function._last_backend}")
```

### Expected Performance

<!-- e.g., "Should be ~0.5 ms (66x over Python baseline of 32 ms)" -->

### Actual Performance

<!-- e.g., "Currently 5 ms (6x over Python)" -->

### Notes

- Is `_last_backend == "native"` confirmed?
- Has the input data size changed?
- Did you rebuild after source changes? (`hotloop build myfile.py --engine=ast`)
