from typing import Dict, List

def build_dynamic_contour_profile(phrases: List[Dict]) -> Dict:
    # compute simple energy curves by section type
    curves = {}
    for p in phrases or []:
        st = p.get("sectionType") or p.get("type") or "verse"
        evs = p.get("events", [])
        if not evs: 
            continue
        v = [float(e.get("velocity", 0.6)) for e in evs]
        mean = sum(v)/len(v)
        peak = max(v)
        curves.setdefault(st, {"means": [], "peaks": []})
        curves[st]["means"].append(mean)
        curves[st]["peaks"].append(peak)

    out = {}
    for st, d in curves.items():
        m = sum(d["means"])/len(d["means"]) if d["means"] else 0.6
        p = sum(d["peaks"])/len(d["peaks"]) if d["peaks"] else 0.9
        out[st] = {"mean": m, "peak": p}
    return {"bySection": out}
