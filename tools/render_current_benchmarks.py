"""Generate current public tables only; never rewrite historical measurements."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"benchmarks/current_public_v0_2_1_20261122.json"
def table(rows):
    lines=["| Application / case | Backend | CPython p50 us | Public p50 / p95 us | Fastest measured strict competitor p50 us |",
           "|---|---|---:|---:|---|"]
    for r in rows:
        lines.append(f'| {r["application"]} / {r["size"]} | {r["backend"]} | {r["cpython_p50_us"]:.3f} | {r["public_p50_us"]:.3f} / {r["public_p95_batch_us"]:.3f} | {r["best_measured_strict_competitor"]}: {r["competitor_p50_us"]:.3f} |')
    return "\n".join(lines)
def generate(check):
    d=json.loads(DATA.read_text())
    desired={"pii_scrubber":"large","pdf_cleaner":"large","quant_backtest":"100000","rag_chunker":"large","ocr_matcher":"large","geo_distance":"10000","ar_spatial":"10000"}
    selected=[r for app,size in desired.items() for r in d["rows"] if r["application"]==app and r["size"]==size]
    assert len(selected)==7
    text=table(selected)
    readme=ROOT/"README.md";content=readme.read_text()
    start="<!-- CURRENT_BENCHMARKS_START -->";end="<!-- CURRENT_BENCHMARKS_END -->"
    a=content.index(start)+len(start);b=content.index(end)
    updated=content[:a]+"\n"+text+"\n"+content[b:]
    document=("# Current candidate benchmark observations\n\n"
      +"Dataset: "+d["dataset_id"]+". Runtime: "+d["candidate_revision"]+". Status: "+d["release_status"]+".\n\n"
      +"Raw evidence: local review commit "+d["raw_evidence_commit"]+", "+d["raw_evidence_path"]+". This unpushed commit is not claimed publicly accessible.\n\n"
      +"Environment: "+d["environment"]+". Protocol: "+d["protocol"]+". These p95s describe batch means, not individual-call tails.\n\n"
      +table(d["rows"])+"\n\n"
      +"Input contracts: text/document fixtures are original strings and Python containers; spatial fixtures are Python lists. NumPy adapters include conversion and Numba list results include reflection. Equivalent ndarray-only timings cannot be substituted.\n\n"
      +"The [versioned data artifact](../benchmarks/current_public_v0_2_1_20261122.json) includes every engine, process p50 range, qualification status, Python-visible allocation peaks, AOT/cache/import/first-call/JIT costs and losing cases. No incorrect result enters the strict ranking. Tolerance-only NumPy and the disqualified PDF regex remain visible in data. Public fallback is not native acceleration; forced paths and private entries are separate. Private entry timing includes conversion/validation.\n\n"
      +"tracemalloc excludes Mojo/native allocation and total RSS. After-build import/first call and fresh-process startup are different scopes. Source/inputs and raw trial hashes are in the owner R1 evidence package. This workstation study makes no shared-runner performance guarantee.\n\n"
      +"[Historical claims and provenance](PRE_M0_CREDIBILITY_REVIEW.md) are separate. No v0.2.1 publication or universal speedup is implied.\n")
    path=ROOT/"docs/CURRENT_BENCHMARKS.md"
    if check:
        assert updated==content,"README current table drift"
        assert path.read_text()==document,"Current benchmark document drift"
    else:
        readme.write_text(updated);path.write_text(document)
def main():
    p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");p.add_argument("--update",action="store_true");a=p.parse_args()
    if not (a.check or a.update):p.error("choose --check or --update")
    generate(a.check);print("Current benchmark tables match their versioned dataset.")
if __name__=="__main__":main()
