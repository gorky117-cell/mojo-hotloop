"""Summarize all retained batches and routes for the five companion applications."""
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys
src,out=map(Path,sys.argv[1:])
data=json.loads(src.read_text());groups=defaultdict(list)
for trial in data["trials"]:
    for row in trial["rows"]:groups[(row["application"],row["size"],trial["label"],row["engine"])].append(row)
rows=[]
for (app,size,label,engine),items in sorted(groups.items()):
    assert len(items)==5
    samples=sorted(v for x in items for v in x["batch_us"])
    values=[x["p50_us"] for x in items]
    rows.append(dict(application=app,size=size,label=label,engine=engine,
        p50_us=statistics.median(values),process_p50_us=values,
        minimum_process_p50_us=min(values),maximum_process_p50_us=max(values),
        p95_batch_us=samples[math.ceil(.95*len(samples))-1],
        native_calls=sum(x["native_calls"] for x in items),fallback_calls=sum(x["fallback_calls"] for x in items),
        routes=sorted({x["route"] for x in items}),all_float_bits_equal=all(x["float_bits_equal"] for x in items)))
for app,size in {(x["application"],x["size"]) for x in rows}:
    items=[v for trial in data["trials"] for v in trial["rows"] if v["application"]==app and v["size"]==size]
    assert len({v["input_sha256"] for v in items})==1
    assert len({v["source_sha256"] for v in items})==1
out.write_text(json.dumps(dict(protocol=data["protocol"],rows=rows),indent=2)+"\n")
