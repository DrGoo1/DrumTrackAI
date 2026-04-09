from typing import Dict, List

def _section_params(section: Dict, profile: Dict):
    st = section.get("sectionType") or section.get("type") or "verse"
    by = (profile or {}).get("bySection", {})
    base = by.get(st, {"mean": 0.6, "peak": 0.9})
    energy = float(section.get("energy", 0.5))
    # scale targets with section energy
    target_mean = min(1.0, base["mean"] * (0.8 + 0.6 * energy))
    target_peak = min(1.0, base["peak"] * (0.85 + 0.5 * energy))
    return target_mean, target_peak

def apply_dynamic_contour(phrases: List[Dict], sections: List[Dict], profile: Dict) -> List[Dict]:
    out = []
    sec_map = {}
    for s in sections or []:
        key = s.get("id") or s.get("sectionId") or s.get("sectionType") or s.get("type")
        if key:
            sec_map[key] = s

    for p in phrases or []:
        p2 = dict(p)
        sid = p2.get("sectionId") or p2.get("sectionType") or p2.get("type")
        section = sec_map.get(sid, {"sectionType": sid or "verse", "energy": p2.get("energy", 0.5)})
        tgt_mean, tgt_peak = _section_params(section, profile or {})
        evs = []
        # ramp shape within phrase (swell toward end)
        N = max(1, len(p2.get("events", [])))
        for i, e in enumerate(p2.get("events", []) or []):
            e2 = dict(e)
            frac = (i + 1) / N
            # blend toward target peak near end
            base_v = float(e2.get("velocity", 0.6))
            desired = tgt_mean * (1 - frac) + tgt_peak * frac
            e2["velocity"] = max(0.0, min(1.0, 0.5 * base_v + 0.5 * desired))
            evs.append(e2)
        p2["events"] = evs
        p2["dynamicContourApplied"] = True
        p2["dynamicContourMeta"] = {"targetMean": tgt_mean, "targetPeak": tgt_peak}
        out.append(p2)
    return out
