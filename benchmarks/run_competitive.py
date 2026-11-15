"""Unified orchestrator running CPython/Mojo/Numba/NumPy/RapidFuzz/Regex + Codon JIT + Codon Native cleanly with zero CPU contention."""
import csv
import json
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from benchmarks.payload_gen import export_codon_fixture

HOTLOOP_PY = "/home/gaurav/mojo-hotloop/.venv/bin/python"
CODON_PY = "/home/gaurav/codon-bench/venv/bin/python"
CODON_DIR = "/home/gaurav/codon-bench/codon-0.20.6"
CODON_BIN = f"{CODON_DIR}/bin/codon"
CODON_PYLIB_DIR = "/home/gaurav/.local/share/uv/python/cpython-3.12.16-linux-x86_64-gnu/lib"
CODON_PYLIB = f"{CODON_PYLIB_DIR}/libpython3.12.so"


def run_all(tag: str = "baseline", skip_hotloop: bool = False) -> None:
    bench_dir = os.path.join(REPO_ROOT, "benchmarks")
    hotloop_json = os.path.join(bench_dir, f"_tmp_hotloop_{tag}.json")
    jit_json = os.path.join(bench_dir, f"_tmp_codon_jit_{tag}.json")
    fixture_path = "/home/gaurav/codon-bench/fixture.tsv"
    native_bin = "/home/gaurav/codon-bench/bench_native"

    print(f"[1/4] Exporting byte-identical fixture -> {fixture_path}")
    export_codon_fixture(fixture_path)

    if not skip_hotloop:
        print(f"[2/4] Running CPython / Mojo / Numba / NumPy / RapidFuzz / Regex suite...")
        env_hl = os.environ.copy()
        env_hl["VIRTUAL_ENV"] = "/home/gaurav/mojo-hotloop/.venv"
        env_hl["PATH"] = f"/home/gaurav/mojo-hotloop/.venv/bin:{env_hl.get('PATH', '')}"
        subprocess.run([HOTLOOP_PY, os.path.join(bench_dir, "run_hotloop_suite.py"), hotloop_json], env=env_hl, check=True)

    codon_env = os.environ.copy()
    codon_env["CODON_DIR"] = CODON_DIR
    codon_env["PATH"] = f"/usr/bin:/bin:/usr/local/bin:{CODON_DIR}/bin"
    codon_env["CODON_PYTHON"] = CODON_PYLIB
    codon_env["LD_LIBRARY_PATH"] = f"{CODON_PYLIB_DIR}:{CODON_DIR}/lib/codon"

    print(f"[3/4] Running @codon.jit suite...")
    subprocess.run([CODON_PY, os.path.join(bench_dir, "run_codon_jit_suite.py"), jit_json], env=codon_env, check=True)

    print(f"[4/4] Building and running Codon native (-release) suite...")
    t0 = time.perf_counter_ns()
    subprocess.run(
        [CODON_BIN, "build", "-release", os.path.join(bench_dir, "codon_kernels/bench_native.py"), "-o", native_bin],
        env=codon_env,
        check=True,
    )
    native_compile_ms = (time.perf_counter_ns() - t0) / 1_000_000.0
    t_run0 = time.perf_counter_ns()
    proc = subprocess.run([native_bin, fixture_path], env=codon_env, capture_output=True, text=True, check=True)
    native_wall_ms = (time.perf_counter_ns() - t_run0) / 1_000_000.0

    with open(hotloop_json, "r", encoding="utf-8") as f:
        merged = json.load(f)
    with open(jit_json, "r", encoding="utf-8") as f:
        jit_data = json.load(f)

    merged["compile_times_ms"]["codon_native_all7_ms"] = native_compile_ms
    merged["compile_times_ms"]["codon_jit_per_fn_ms"] = jit_data["jit_compile_times_ms"]
    merged["codon_native_total_wall_ms"] = native_wall_ms
    merged["rss_kb"] = {
        "hotloop_suite": merged.pop("peak_rss_kb"),
        "codon_jit_suite": jit_data["peak_rss_kb"],
    }

    for app, tiers in jit_data["workloads"].items():
        for tier, variants in tiers.items():
            for vname, stats in variants.items():
                merged["workloads"][app][tier][vname] = stats

    for line in proc.stdout.splitlines():
        if line.startswith("ROW\t"):
            _, app, tier, variant, p50, p95, mean, stdev = line.split("\t")
            merged["workloads"][app][tier][variant] = {
                "p50_ms": float(p50),
                "p95_ms": float(p95),
                "mean_ms": float(mean),
                "stdev_ms": float(stdev),
            }

    out_json = os.path.join(bench_dir, f"results_{tag}.json")
    out_csv = os.path.join(bench_dir, f"results_{tag}.csv")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["app", "tier", "variant", "p50_ms", "p95_ms", "mean_ms", "stdev_ms", "speedup_vs_cpython"])
        for app, tiers in merged["workloads"].items():
            for tier, variants in tiers.items():
                py_p50 = variants["cpython"]["p50_ms"]
                for vname, stats in variants.items():
                    if not isinstance(stats, dict) or "p50_ms" not in stats:
                        continue
                    sp = py_p50 / stats["p50_ms"] if stats["p50_ms"] > 0 else 0.0
                    w.writerow([app, tier, vname, f"{stats['p50_ms']:.6f}", f"{stats['p95_ms']:.6f}", f"{stats['mean_ms']:.6f}", f"{stats['stdev_ms']:.6f}", f"{sp:.2f}x"])

    print(f"[DONE] Saved {out_json} & {out_csv}")


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    skip_hl = "--skip-hotloop" in sys.argv
    run_all(tag, skip_hotloop=skip_hl)
