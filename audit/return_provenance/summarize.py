"""Summarize recorded batches without discarding slow processes or fallbacks."""
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys

source,out=map(Path,sys.argv[1:])
data=json.loads(source.read_text())
groups=defaultdict(list)
costs=defaultdict(lambda:defaultdict(list))
for trial in data["trials"]:
    label=trial["label"]
    for app,rows in (("backtest",trial["rows"]),("pii",trial["pii"]["rows"])):
        for row in rows:
            size=row["ticks"] if app=="backtest" else row["characters"]
            groups[(app,size,label,row["engine"])].append(row)
    for app,obj in (("backtest",trial),("pii",trial["pii"])):
        for name in ("build_seconds","cache_build_seconds","import_seconds","first_public_us"):
            costs[(app,label)][name].append(obj[name])
    costs[("backtest",label)]["numba_jit_seconds"].append(trial["numba_jit_seconds"])
def stat(values):
    return dict(p50=statistics.median(values),minimum=min(values),maximum=max(values))
rows=[]
for (app,size,label,engine),items in sorted(groups.items()):
    assert len(items)==5,(app,size,label,engine,len(items))
    samples=sorted(x for item in items for x in item["batch_us"])
    row=dict(application=app,size=size,label=label,engine=engine,
             process_p50_us=[x["p50_us"] for x in items],
             latency_us=stat([x["p50_us"] for x in items]),
             pooled_batch_p95_us=samples[math.ceil(.95*len(samples))-1],
             native_calls=sum(x["native_calls"] for x in items),
             fallback_calls=sum(x["fallback_calls"] for x in items),
             routes=sorted(set(x["route"] for x in items)),
             python_visible_peak_bytes=stat([x["python_visible_peak_bytes"] for x in items]))
    if app=="backtest":
        row["all_strict_correct"]=all(x["strict_correct"] for x in items)
    rows.append(row)
changes=[]
for app,size in sorted({(key[0],key[1]) for key in groups}):
    current=groups[(app,size,"candidate","hotloop_public")]
    for old in ("baseline","origin"):
        previous=groups[(app,size,old,"hotloop_public")]
        ratios=[a["p50_us"]/b["p50_us"] for a,b in zip(current,previous)]
        changes.append(dict(application=app,size=size,comparison=old,
            public_latency_ratio=statistics.median(x["p50_us"] for x in current)/statistics.median(x["p50_us"] for x in previous),
            per_trial_ratios=ratios,slower_by_over_10pct_trials=sum(x>1.1 for x in ratios)))
public=[r for r in rows if r["engine"]=="hotloop_public" and r["label"]=="candidate"]
summary=dict(protocol=data["protocol"],pinned_cpu=data["pinned_cpu"],
             latency_definition="median of five process p50s; p95 of 75 batch means, not individual-call p95",
             rows=rows,changes=changes,
             costs=[dict(application=app,label=label,values={k:stat(v) for k,v in vals.items()})
                    for (app,label),vals in sorted(costs.items())],
             measured_candidate_public_calls=dict(native=sum(r["native_calls"] for r in public),
                                                  fallback=sum(r["fallback_calls"] for r in public)))
out.write_text(json.dumps(summary,indent=2)+"\n")
