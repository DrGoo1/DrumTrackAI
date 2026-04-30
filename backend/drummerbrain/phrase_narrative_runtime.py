from typing import Dict, List

def apply_phrase_narrative(phrases: List[Dict], sections: List[Dict]) -> List[Dict]:
    out = []
    sec_map = {}
    for s in sections or []:
        key = s.get("id") or s.get("sectionId") or s.get("sectionType") or s.get("type")
        if key:
            sec_map[key] = s

    for p in phrases or []:
        p2 = dict(p)
        sid = p2.get("sectionId") or p2.get("sectionType") or p2.get("type")
        section = sec_map.get(sid, {"sectionType": sid or "verse"})
        plan = section.get("narrativePlan", {})
        level = plan.get("intensityLevel", "medium")

        # Adjust fill density and embellishments
        if level in ("minimal",):
            p2["fillDensity"] = 0.0
        elif level in ("low",):
            p2["fillDensity"] = 0.2
        elif level in ("medium",):
            p2["fillDensity"] = 0.4
        elif level in ("high",):
            p2["fillDensity"] = 0.7
        else:  # very_high
            p2["fillDensity"] = 0.9

        # tag narrative metadata
        p2["narrativeApplied"] = True
        p2["narrativeMeta"] = {
            "level": level,
            "escalationIndex": plan.get("escalationIndex", 0)
        }
        out.append(p2)

    return out
