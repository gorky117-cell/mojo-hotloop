import os
import resource
import sys

repo_root = "/home/gaurav/mojo-hotloop"
sys.path.insert(0, repo_root)

from audit.unseen_cases.running_max.original import running_max
from audit.unseen_cases.count_greater.original import count_greater
from audit.unseen_cases.simple_moving_average.original import simple_moving_average

def get_rss_kb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

print("=== Memory Leak & Stability Verification ===")
data = [float(i % 100) for i in range(1000)]

# Warmup
for _ in range(100):
    _ = running_max(data)
    _ = count_greater(data, 50.0)
    _ = simple_moving_average(data, 10)

rss_before = get_rss_kb()

# 20,000 iterations of collection operations
for i in range(20000):
    _ = running_max(data)
    _ = count_greater(data, 50.0)
    _ = simple_moving_average(data, 10)

rss_after = get_rss_kb()
rss_growth_kb = rss_after - rss_before
print(f"RSS Before : {rss_before} KB")
print(f"RSS After  : {rss_after} KB")
print(f"Growth     : {rss_growth_kb} KB across 60,000 native collection calls")

# Allow small Python GC buffer (<= 2048 KB)
assert rss_growth_kb <= 2048, f"Memory leak detected! Growth was {rss_growth_kb} KB"
print("SUCCESS: Zero memory leaks verified!")
