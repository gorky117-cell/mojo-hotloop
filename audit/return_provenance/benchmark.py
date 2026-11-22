"""Offline five-process backtest comparison. Zero-tick competitors may be value-only.

Usage: python audit/return_provenance/benchmark.py OUT SECURITY_PY ORIGIN_PY CANDIDATE_PY
Requires the provisioned local Mojo, Numba and C++ toolchains, without downloads.
"""
import ast
import gc
import functools
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from scanner import scanner
import platform
import random
import typing
import statistics
import struct
import subprocess
import sys
import sysconfig
import time
import tracemalloc

SIZES = (0, 100, 10_000, 100_000)

def measure(fn, args, expected):
    result = fn(*args)
    assert type(result) is type(expected)
    assert struct.pack(">d", result) == struct.pack(">d", expected)
    start = time.perf_counter()
    for _ in range(3):
        fn(*args)
    elapsed = (time.perf_counter() - start) / 3
    count = max(2, min(10_000, int(.015 / max(elapsed, 1e-9))))
    samples = []
    for _ in range(15):
        start = time.perf_counter_ns()
        for _ in range(count):
            fn(*args)
        samples.append((time.perf_counter_ns() - start) / count / 1000)
    gc.collect()
    tracemalloc.start()
    fn(*args)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(batch_us=samples, iterations=count, p50_us=statistics.median(samples),
                p95_us=sorted(samples)[-1], python_visible_current_bytes=current,
                python_visible_peak_bytes=peak, result_bits=struct.pack(">d", result).hex(),
                result_type=type(result).__name__, input_identity=result is args[1])

def measure_text(fn, text, expected, owners):
    result = fn(text)
    assert type(result) is str and result == expected
    aliases=[result is owner for owner in owners]
    expected_aliases=[expected is owner for owner in owners]
    assert aliases==expected_aliases
    start = time.perf_counter()
    fn(text)
    elapsed = time.perf_counter() - start
    count = max(2, min(5000, int(.015 / max(elapsed, 1e-9))))
    samples = []
    for _ in range(15):
        start = time.perf_counter_ns()
        for _ in range(count):
            fn(text)
        samples.append((time.perf_counter_ns() - start) / count / 1000)
    gc.collect()
    tracemalloc.start()
    fn(text)
    current,peak=tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(batch_us=samples, iterations=count, p50_us=statistics.median(samples),
                p95_us=max(samples), identity_correct=True, result_sha256=hashlib.sha256(result.encode()).hexdigest(),
                python_visible_current_bytes=current,python_visible_peak_bytes=peak)


def pii_qualification(folder, source_root, label):
    from hotloop.backends.mojo import MojoBackend
    directory = folder / "pii"
    directory.mkdir()
    source = source_root / "pii_scrubber/original.py"
    path = directory / "pii_case.py"
    path.write_bytes(source.read_bytes())
    backend=MojoBackend()
    start=time.perf_counter()
    ok, diagnostic, _ = backend.build_ast(path)
    build_seconds=time.perf_counter()-start
    assert ok, diagnostic
    start=time.perf_counter()
    ok, diagnostic, _ = backend.build_ast(path)
    cache_seconds=time.perf_counter()-start
    assert ok, diagnostic
    spec = importlib.util.spec_from_file_location("pii_case", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    start=time.perf_counter()
    spec.loader.exec_module(mod)
    import_seconds=time.perf_counter()-start
    public = mod.scrub_pii
    probe = str(123)
    expected = public._original(probe)
    start=time.perf_counter()
    actual = public(probe)
    first_public_us=(time.perf_counter()-start)*1e6
    assert expected is probe and actual == expected
    identity = actual is probe
    if label=="candidate":
        assert identity and public._last_backend=="native"
    elif label=="origin":
        assert identity and public._last_backend=="python_fallback_semantics"
    else:
        assert not identity and public._last_backend=="native"
    ns = dict(random=random, Dict=typing.Dict)
    app = source.parent
    for name in ("verify.py", "bench.py"):
        tree = ast.parse((app / name).read_text())
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and
                 (node.name.startswith("gen_synthetic_") or node.name=="generate_bench_payloads")]
        exec(compile(ast.Module(body=nodes,type_ignores=[]), str(app / name), "exec"), ns)
    rows = []
    regex=scanner(mod)
    for size, item in ns["generate_bench_payloads"]().items():
        text = item["text"]
        expected = public._original(text)
        for engine, fn in (("cpython",public._original),("hotloop_public",public),("strict_regex",regex)):
            before_native=public._call_count_native
            before_fallback=public._call_count_fallback
            owners=[text,*[c for c in public._original.__code__.co_consts if type(c) is str]]
            row = measure_text(fn, text, expected, owners)
            row.update(native_calls=public._call_count_native-before_native,
                       fallback_calls=public._call_count_fallback-before_fallback)
            row.update(engine=engine, size=size, characters=len(text), label=label,
                       route=public._last_backend if engine=="hotloop_public" else engine,
                       payload_sha256=hashlib.sha256(text.encode()).hexdigest())
            rows.append(row)
    return dict(input_identity_correct=identity, probe_route=public._last_backend,
                build_seconds=build_seconds,cache_build_seconds=cache_seconds,
                import_seconds=import_seconds,first_public_us=first_public_us,
                source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(), rows=rows)


def worker(label, folder, reference, source):
    import hotloop
    from hotloop.backends.mojo import MojoBackend
    folder = Path(folder)
    folder.mkdir()
    path = folder / "original.py"
    path.write_bytes(Path(source).read_bytes())
    backend = MojoBackend()
    start = time.perf_counter()
    ok, diagnostic, _ = backend.build_ast(path)
    build_seconds = time.perf_counter() - start
    assert ok, diagnostic
    start = time.perf_counter()
    ok, diagnostic, _ = backend.build_ast(path)
    cache_seconds = time.perf_counter() - start
    assert ok, diagnostic
    spec = importlib.util.spec_from_file_location("original", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["original"] = mod
    start = time.perf_counter()
    spec.loader.exec_module(mod)
    import_seconds = time.perf_counter() - start
    public = mod.stateful_trailing_backtest
    original = public._original
    args0 = (0, float("123.5"), float(".05"), float(".001"))
    start = time.perf_counter()
    first = public(*args0)
    first_us = (time.perf_counter() - start) * 1e6
    engines = {"hotloop_public": public, "private_generated_entry": public._compiled}
    jit_seconds = None
    # Identical competitor/JIT setup for both runtimes.
    import numba
    start = time.perf_counter()
    compiled = numba.njit(fastmath=False, cache=False)(original)
    compiled(*args0)
    jit_seconds = time.perf_counter() - start
    sys.path.insert(0, reference)
    import native_reference
    engines.update(cpython=original, numba=compiled, cpp=native_reference.quant)
    if label=="candidate":
        # Diagnostic: only after the real public call established all owner proofs.
        # Context and callable bindings remain unchanged throughout this workload.
        entry=public._compiled
        engines["prepared_generated_entry"]=functools.partial(entry.raw,entry.context)
    rows = []
    for size in SIZES:
        args = (size, float("123.5"), float(".05"), float(".001"))
        expected = original(*args)
        for name, fn in engines.items():
            before_native=public._call_count_native
            before_fallback=public._call_count_fallback
            row = measure(fn, args, expected)
            row.update(native_calls=public._call_count_native-before_native,
                       fallback_calls=public._call_count_fallback-before_fallback)
            row.update(engine=name, ticks=size, label=label,
                       route=public._last_backend if name == "hotloop_public" else name,
                       strict_correct=(row["input_identity"] if size == 0 else not row["input_identity"]))
            if name == "hotloop_public":
                assert row["route"] == "native"
                if label != "baseline":
                    assert row["strict_correct"]
            rows.append(row)
    pii = pii_qualification(folder, Path(source).parents[1], label)
    return dict(pii=pii, label=label, pid=os.getpid(), python=sys.version, package=hotloop.__file__,
                build_seconds=build_seconds, cache_build_seconds=cache_seconds,
                import_seconds=import_seconds, first_public_us=first_us,
                first_identity=first is args0[1], numba_jit_seconds=jit_seconds,
                binary_bytes=(folder / "fast.so").stat().st_size, rows=rows)

def main():
    if sys.argv[1] == "--worker":
        label, folder, reference, source, output = sys.argv[2:]
        result = worker(label, folder, reference, source)
        Path(output).write_text(json.dumps(result, indent=2) + "\n")
        return
    output, baseline, origin, candidate = sys.argv[1:]
    output = Path(output).resolve()
    output.mkdir()
    # Process-local affinity is inherited by workers; no machine settings change.
    pinned_cpu = max(os.sched_getaffinity(0))
    os.sched_setaffinity(0, {pinned_cpu})
    root = Path(__file__).resolve().parents[2]
    script = Path(__file__).resolve()
    cpp = script.with_name("native_reference.cpp")
    command = ["c++", "-O3", "-shared", "-fPIC", "-std=c++17", "-fno-fast-math",
               "-ffp-contract=off", "-I" + sysconfig.get_path("include"), str(cpp),
               "-o", str(output / ("native_reference" + sysconfig.get_config_var("EXT_SUFFIX")))]
    start = time.perf_counter()
    subprocess.run(command, check=True)
    cpp_seconds = time.perf_counter() - start
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    for key in ("HOTLOOP_STRICT", "HOTLOOP_FORCE_NATIVE", "HOTLOOP_STRICT_PERF"):
        environment.pop(key, None)
    trials = []
    for trial in range(5):
        labels = [("baseline", baseline), ("origin",origin), ("candidate", candidate)]
        labels=labels[trial%3:]+labels[:trial%3]
        if trial%2: labels.reverse()
        for label, python in labels:
            name = f"{label}-{trial + 1}"
            result_path = output / (name + ".json")
            subprocess.run([python, str(script), "--worker", label, str(output / name),
                            str(output), str(root / "examples/quant_backtest/original.py"),
                            str(result_path)], env=environment, check=True)
            trials.append(json.loads(result_path.read_text()))
            print(name, "completed", flush=True)
    (output / "results.json").write_text(json.dumps(dict(
        protocol="5 independent processes per runtime; 15 timed batches; identical JIT/engine setup; pinned CPU",
        pinned_cpu=pinned_cpu,
        source_sha256=hashlib.sha256((root / "examples/quant_backtest/original.py").read_bytes()).hexdigest(),
        cpp_origin="581a29ee6ab0d99ba4370e006e4f3edfa3b258c0:audit/seven_application/native_reference.cpp",
        cpp_sha256=hashlib.sha256(cpp.read_bytes()).hexdigest(), cpp_command=command,
        cpp_build_seconds=cpp_seconds, cpu=platform.processor(), platform=platform.platform(),
        trials=trials), indent=2) + "\n")

if __name__ == "__main__":
    main()
