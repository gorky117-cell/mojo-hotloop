"""Summarize frozen independent-process regression data; never rerun user code."""
import json
import math
from pathlib import Path
import statistics
import sys


def summarize(data):
    cases = list(dict.fromkeys((r["application"], r["size"])
                               for r in data["trials"][0]["rows"]))
    result = []
    for application, size in cases:
        row = {"application": application, "size": size}
        for label in ("baseline", "candidate"):
            trials = [t for t in data["trials"] if t["label"] == label]
            assert len(trials) == 5
            records = [r for t in trials for r in t["rows"]
                       if (r["application"], r["size"], r["engine"]) ==
                       (application, size, "public")]
            assert len(records) == 5
            cp = [r["p50_us"] for t in trials for r in t["rows"]
                  if (r["application"], r["size"], r["engine"]) ==
                  (application, size, "cpython")]
            batches = sorted(v for r in records for v in r["batch_us"])
            medians = [r["p50_us"] for r in records]
            row[label] = {
                "public_p50_us": statistics.median(medians),
                "public_p95_batch_us": batches[math.ceil(.95 * len(batches)) - 1],
                "process_median_range_us": [min(medians), max(medians)],
                "cpython_p50_us": statistics.median(cp),
                "correct": all(r["correct"] for r in records),
                "routes": sorted({r["actual_backend"] for r in records}),
            }
        b, a = row["baseline"], row["candidate"]
        row["diagnostic_latency_change_percent"] = 100 * (a["public_p50_us"] / b["public_p50_us"] - 1)
        row["comparable_correct_results"] = a["correct"] and b["correct"]
        row["regression_over_10_percent"] = row["comparable_correct_results"] and row["diagnostic_latency_change_percent"] > 10
        row["candidate_speedup_over_cpython"] = a["cpython_p50_us"] / a["public_p50_us"] if a["correct"] else None
        result.append(row)
    return {
        "units": "microseconds",
        "p50_definition": "median of five process medians, each from nine batch means",
        "p95_definition": "nearest-rank p95 of 45 batch means; not individual-call tail latency",
        "rows": result,
    }


if __name__ == "__main__":
    source, destination = map(Path, sys.argv[1:])
    destination.write_text(json.dumps(summarize(json.loads(source.read_text())), indent=2) + "\n")
