"""Aggregate all trials, retaining unqualified results and exact route counters."""
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys
src,out=map(Path,sys.argv[1:]);raw=json.loads(src.read_text())
groups=defaultdict(list);costs=defaultdict(list)
for trial in raw["trials"]:
    for r in trial["rows"]:groups[(r["application"],r["size"],trial["label"],r["engine"])].append(r)
    for c in trial["costs"]:costs[(c["application"],trial["label"])].append(c)
rows=[]
for (app,size,label,engine),items in sorted(groups.items()):
    assert len(items)==5
    timing=[i["timing"] for i in items if i["timing"] is not None]
    samples=sorted(v for t in timing for v in t["batch_us"])
    values=[t["p50_us"] for t in timing]
    rows.append(dict(application=app,size=size,label=label,engine=engine,
       strict_correct=all(i["qualification"]["strict_correct"] for i in items),
       tolerance_correct=all(i["qualification"]["tolerance_correct"] for i in items),
       routes=sorted({i["actual_backend"] for i in items}),
       p50_us=statistics.median(values) if values else None,
       p95_batch_us=samples[math.ceil(.95*len(samples))-1] if samples else None,
       process_p50_us=values,
       min_process_p50_us=min(values) if values else None,max_process_p50_us=max(values) if values else None,
       python_visible_peak_bytes=[t["python_visible_peak_bytes"] for t in timing],
       native_calls=sum(i["native_counter_delta"] for i in items),fallback_calls=sum(i["fallback_counter_delta"] for i in items)))
for app,size in {(r["application"],r["size"]) for r in rows}:
    items=[i for t in raw["trials"] for i in t["rows"] if i["application"]==app and i["size"]==size]
    assert len({i["input_sha256"] for i in items})==1
    assert len({i["source_sha256"] for i in items})==1
summary=dict(protocol=raw["protocol"],p95_definition="nearest-rank p95 of 45 batch means; not individual-call p95",rows=rows,
 costs=[dict(application=app,label=label,values={name:dict(p50=statistics.median(v),minimum=min(v),maximum=max(v))
       for name in ("cold_build_seconds","cache_hit_seconds","import_after_build_seconds","first_public_us","numba_jit_seconds")
       if (v:=[i[name] for i in items if i[name] is not None])}) for (app,label),items in sorted(costs.items())])
out.write_text(json.dumps(summary,indent=2)+"\n")
