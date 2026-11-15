import math
import sys
import time
import numpy as np

from all7 import (
    stateful_trailing_backtest,
    find_closest_point_to_ray,
    accumulate_haversine_distance,
    clean_pdf_text,
    scrub_pii,
    find_closest_match,
    chunk_document,
)


def unescape_line(s: str) -> str:
    out: list[str] = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == "\\" and i + 1 < n:
            nxt = s[i + 1]
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            elif nxt == "r":
                out.append("\r")
                i += 2
                continue
            elif nxt == "f":
                out.append("\f")
                i += 2
                continue
            elif nxt == "t":
                out.append("\t")
                i += 2
                continue
            elif nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def load_fixtures(path: str):
    strs: dict[str, str] = {}
    flts: dict[str, list[float]] = {}
    lsts: dict[str, list[str]] = {}
    with open(path, "r") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            kind = parts[0]
            tag = parts[1]
            if kind == "STR":
                strs[tag] = unescape_line(parts[2])
            elif kind == "FLT":
                flts[tag] = [float(x) for x in parts[2].split(",")]
            elif kind == "LST":
                lsts[tag] = [unescape_line(x) for x in parts[2:]]
    return strs, flts, lsts


def measure_stats(samples_ms: list[float]) -> tuple[float, float, float, float]:
    s = sorted(samples_ms)
    n = len(s)
    mean = sum(s) / float(n)
    p50 = s[n // 2] if (n % 2 == 1) else 0.5 * (s[n // 2 - 1] + s[n // 2])
    p95_idx = int(math.ceil(0.95 * float(n))) - 1
    if p95_idx < 0:
        p95_idx = 0
    if p95_idx >= n:
        p95_idx = n - 1
    p95 = s[p95_idx]
    var = sum((x - mean) * (x - mean) for x in s) / float(max(1, n - 1))
    stdev = math.sqrt(var)
    return p50, p95, mean, stdev


def emit_row(app: str, tier: str, variant: str, samples: list[float]):
    p50, p95, mean, stdev = measure_stats(samples)
    print(f"ROW\t{app}\t{tier}\t{variant}\t{p50:.8f}\t{p95:.8f}\t{mean:.8f}\t{stdev:.8f}")


def main():
    fixture_path = sys.argv[1]
    strs, flts, lsts = load_fixtures(fixture_path)
    sink = 0.0

    # 1. quant_backtest (100k ticks)
    for _ in range(5):
        sink += stateful_trailing_backtest(100000, 100.0, 0.05, 0.001)
    q_samples: list[float] = []
    for _ in range(5):
        t0 = time.monotonic_ns()
        for _ in range(40):
            sink += stateful_trailing_backtest(100000, 100.0, 0.05, 0.001)
        t1 = time.monotonic_ns()
        q_samples.append(float(t1 - t0) / (40.0 * 1_000_000.0))
    emit_row("quant_backtest", "ticks_100k", "codon_native", q_samples)

    # 2. ar_spatial (list & numpy)
    ar_cfg = [("small", 1500), ("medium", 200), ("large", 20)]
    for tier, iters in ar_cfg:
        xs = flts[f"ar_{tier}_xs"]
        ys = flts[f"ar_{tier}_ys"]
        zs = flts[f"ar_{tier}_zs"]
        npx = np.array(xs)
        npy = np.array(ys)
        npz = np.array(zs)
        for _ in range(5):
            sink += float(find_closest_point_to_ray(xs, ys, zs, 0.0, 0.0, 0.0, 0.1, 0.2, 1.0))
            sink += float(find_closest_point_to_ray(npx, npy, npz, 0.0, 0.0, 0.0, 0.1, 0.2, 1.0))
        s_list: list[float] = []
        s_np: list[float] = []
        for _ in range(5):
            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += float(find_closest_point_to_ray(xs, ys, zs, 0.0, 0.0, 0.0, 0.1, 0.2, 1.0))
            t1 = time.monotonic_ns()
            s_list.append(float(t1 - t0) / (float(iters) * 1_000_000.0))

            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += float(find_closest_point_to_ray(npx, npy, npz, 0.0, 0.0, 0.0, 0.1, 0.2, 1.0))
            t1 = time.monotonic_ns()
            s_np.append(float(t1 - t0) / (float(iters) * 1_000_000.0))
        emit_row("ar_spatial", tier, "codon_native_list", s_list)
        emit_row("ar_spatial", tier, "codon_native_numpy", s_np)

    # 3. geo_distance (list & numpy)
    geo_cfg = [("short", 1500), ("medium", 200), ("large", 20)]
    for tier, iters in geo_cfg:
        lats = flts[f"geo_{tier}_lats"]
        lons = flts[f"geo_{tier}_lons"]
        nplat = np.array(lats)
        nplon = np.array(lons)
        for _ in range(5):
            sink += accumulate_haversine_distance(lats, lons)
            sink += accumulate_haversine_distance(nplat, nplon)
        s_list = []
        s_np = []
        for _ in range(5):
            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += accumulate_haversine_distance(lats, lons)
            t1 = time.monotonic_ns()
            s_list.append(float(t1 - t0) / (float(iters) * 1_000_000.0))

            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += accumulate_haversine_distance(nplat, nplon)
            t1 = time.monotonic_ns()
            s_np.append(float(t1 - t0) / (float(iters) * 1_000_000.0))
        emit_row("geo_distance", tier, "codon_native_list", s_list)
        emit_row("geo_distance", tier, "codon_native_numpy", s_np)

    # 4. pdf_cleaner
    for tier, iters in [("small", 800), ("medium", 150), ("large", 3)]:
        txt = strs[f"pdf_{tier}"]
        for _ in range(2):
            sink += float(len(clean_pdf_text(txt)))
        samples: list[float] = []
        for _ in range(5):
            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += float(len(clean_pdf_text(txt)))
            t1 = time.monotonic_ns()
            samples.append(float(t1 - t0) / (float(iters) * 1_000_000.0))
        emit_row("pdf_cleaner", tier, "codon_native", samples)

    # 5. pii_scrubber
    for tier, iters in [("short", 2000), ("medium", 200), ("large", 3)]:
        txt = strs[f"pii_{tier}"]
        for _ in range(3):
            sink += float(len(scrub_pii(txt)))
        samples = []
        for _ in range(5):
            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += float(len(scrub_pii(txt)))
            t1 = time.monotonic_ns()
            samples.append(float(t1 - t0) / (float(iters) * 1_000_000.0))
        emit_row("pii_scrubber", tier, "codon_native", samples)

    # 6. ocr_matcher
    for tier, iters in [("small", 400), ("medium", 40), ("large", 8)]:
        q = strs[f"ocr_{tier}_q"]
        c = lsts[f"ocr_{tier}_c"]
        for _ in range(3):
            sink += float(find_closest_match(q, c, 3))
        samples = []
        for _ in range(5):
            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += float(find_closest_match(q, c, 3))
            t1 = time.monotonic_ns()
            samples.append(float(t1 - t0) / (float(iters) * 1_000_000.0))
        emit_row("ocr_matcher", tier, "codon_native", samples)

    # 7. rag_chunker
    rag_cfg = [("small", 250, 50, 800), ("medium", 500, 100, 150), ("large", 1000, 200, 20)]
    for tier, csize, covlp, iters in rag_cfg:
        txt = strs[f"rag_{tier}"]
        for _ in range(3):
            sink += float(len(chunk_document(txt, csize, covlp)))
        samples = []
        for _ in range(5):
            t0 = time.monotonic_ns()
            for _ in range(iters):
                sink += float(len(chunk_document(txt, csize, covlp)))
            t1 = time.monotonic_ns()
            samples.append(float(t1 - t0) / (float(iters) * 1_000_000.0))
        emit_row("rag_chunker", tier, "codon_native", samples)

    print(f"SINK\t{sink:.3f}")


if __name__ == "__main__":
    main()
