import random

def apply_directional_microtiming(phrases, profile, strength=1.0):
    out = []
    for p in phrases or []:
        p2 = dict(p)
        evs = []
        for e in p2.get("events", []):
            e2 = dict(e)
            key = f"{e2.get('instrument')}:{e2.get('role','default')}"
            stats = profile.get("byInstrumentRole", {}).get(key, profile.get("global", {"mean_ms":0,"std_ms":0}))
            delta = (stats["mean_ms"] + random.gauss(0, stats["std_ms"])) * strength
            e2["timing_offset_ms"] = e2.get("timing_offset_ms",0) + delta
            evs.append(e2)
        p2["events"] = evs
        p2["microtimingApplied"] = True
        out.append(p2)
    return out
