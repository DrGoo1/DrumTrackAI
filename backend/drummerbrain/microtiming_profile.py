from typing import Dict, List
from collections import defaultdict

def build_microtiming_profile(events: List[Dict]) -> Dict:
    buckets = defaultdict(list)
    for e in events or []:
        inst = e.get("instrument") or "unknown"
        role = e.get("role") or "default"
        if "timing_offset_ms" in e:
            buckets[(inst, role)].append(float(e["timing_offset_ms"]))

    profile = {"byInstrumentRole": {}, "global": {}}

    for (inst, role), arr in buckets.items():
        if not arr: continue
        n = len(arr)
        mean = sum(arr)/n
        var = sum((x-mean)**2 for x in arr)/max(1,n)
        profile["byInstrumentRole"][f"{inst}:{role}"] = {
            "mean_ms": mean,
            "std_ms": var**0.5
        }

    all_vals = [x for arr in buckets.values() for x in arr]
    if all_vals:
        n = len(all_vals)
        mean = sum(all_vals)/n
        var = sum((x-mean)**2 for x in all_vals)/max(1,n)
        profile["global"] = {"mean_ms": mean, "std_ms": var**0.5}

    return profile
