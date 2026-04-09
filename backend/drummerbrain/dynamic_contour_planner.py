from typing import Dict, List

def plan_dynamic_contour_for_sections(sections: List[Dict]) -> List[Dict]:
    out = []
    for s in sections or []:
        s2 = dict(s)
        t = s2.get("sectionType") or s2.get("type") or "verse"
        energy = float(s2.get("energy", 0.5))
        if t in ("chorus",):
            mode = "lift"
        elif t in ("bridge", "prechorus"):
            mode = "build"
        else:
            mode = "steady"
        s2["dynamicContourPlan"] = {"mode": mode, "energy": energy}
        out.append(s2)
    return out
