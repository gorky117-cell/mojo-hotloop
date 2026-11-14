import time
import sys

repo_root = "/home/gaurav/mojo-hotloop"
sys.path.insert(0, repo_root)

from audit.unseen_cases.running_max.original import running_max
from audit.unseen_cases.count_greater.original import count_greater

# Benchmark conversion for 50,000 floats
data = [float(i) for i in range(50000)]

# 1. Total decorated time
t0 = time.perf_counter_ns()
for _ in range(10):
    _ = running_max(data)
t1 = time.perf_counter_ns()
total_rm_ms = (t1 - t0) / 10 / 1_000_000.0

# 2. Count greater (input conversion only, scalar return)
t0 = time.perf_counter_ns()
for _ in range(10):
    _ = count_greater(data, 25000.0)
t1 = time.perf_counter_ns()
total_cg_ms = (t1 - t0) / 10 / 1_000_000.0

print(f"50,000 elements count_greater (Input unboxing + Mojo loop): {total_cg_ms:.2f} ms")
print(f"50,000 elements running_max   (Input unbox + Mojo loop + Output box): {total_rm_ms:.2f} ms")
input_unbox_ms = total_cg_ms
output_box_ms = total_rm_ms - total_cg_ms
print(f"-> Input unboxing overhead : ~{input_unbox_ms:.2f} ms (~{input_unbox_ms*1e6/50000:.1f} ns per element)")
print(f"-> Output boxing overhead  : ~{output_box_ms:.2f} ms (~{output_box_ms*1e6/50000:.1f} ns per element)")
print(f"-> Combined FFI overhead   : ~{input_unbox_ms + output_box_ms:.2f} ms")
