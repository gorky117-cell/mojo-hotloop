"""Compare installed wheels in separate processes on identical Python arguments.

Run once with --build, then three times without it from a private empty directory,
using the chosen release's Python. Supply --directory for the generated module.
"""
import argparse
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
from statistics import median
import subprocess
import sys
from time import perf_counter_ns
import warnings

SOURCE = """from hotloop import hotloop

@hotloop
def sum_squares(n: int) -> int:
    total: int = 0
    for i in range(n):
        total += i * i
    return total

@hotloop
def sum_samples(samples: list[float]) -> float:
    total: float = 0.0
    for i in range(len(samples)):
        total += samples[i]
    return total
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--directory", required=True, type=Path)
    args = parser.parse_args()
    root = args.directory.resolve()
    root.mkdir(exist_ok=True)
    path = root / "timed_kernels.py"
    if args.build:
        path.write_text(SOURCE)
        subprocess.run(
            [sys.executable, "-m", "hotloop.cli", "build", str(path), "--no-verify"],
            cwd=root, check=True,
        )
        return
    import numpy as np
    from hotloop import hotloop
    sys.path.insert(0, str(root))
    kernels = importlib.import_module("timed_kernels")
    buffer = np.arange(8192, dtype=np.float64) * 0.25
    items = buffer.tolist()
    forced = hotloop(force_native=True)(kernels.sum_samples._original)
    rows = {}
    for name, fn, arg, calls in (
        ("scalar-1", kernels.sum_squares, 1, 4000),
        ("scalar-8192", kernels.sum_squares, 8192, 20),
        ("ndarray-8192", kernels.sum_samples, buffer, 15),
        ("list-8192-default", kernels.sum_samples, items, 20),
        ("list-8192-forced", forced, items, 20),
    ):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            expected = fn._original(arg)
            actual = fn(arg)
            assert actual == expected
            times = {"python": [], "decorated": []}
            for sample in range(5):
                order = [("python", fn._original), ("decorated", fn)]
                for label, target in order[::1 if sample % 2 == 0 else -1]:
                    start = perf_counter_ns()
                    for _ in range(calls):
                        target(arg)
                    times[label].append((perf_counter_ns() - start) / calls / 1000)
            rows[name] = {"route": fn._last_backend, "type_parity": type(actual) is type(expected),
                          "python_us": median(times["python"]), "decorated_us": median(times["decorated"])}
    print(json.dumps({"version": importlib.metadata.version("mojo-hotloop"), "pid": os.getpid(), "cases": rows}))


if __name__ == "__main__":
    main()
