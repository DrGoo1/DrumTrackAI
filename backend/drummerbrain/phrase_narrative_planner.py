from typing import Dict, List

def plan_phrase_narrative(sections: List[Dict]) -> List[Dict]:
    out = []
    total = len(sections or [])
    for idx, s in enumerate(sections or []):
        s2 = dict(s)
        t = s2.get("sectionType") or s2.get("type") or "verse"

        if t in ("intro",):
            level = "minimal"
        elif t in ("verse",):
            level = "low"
        elif t in ("prechorus", "bridge"):
            level = "medium"
        elif t in ("chorus",):
            level = "high"
        else:
            level = "medium"

        # escalate later repetitions
        if t == "chorus" and idx >= total // 2:
            level = "very_high"

        s2["narrativePlan"] = {
            "intensityLevel": level,
            "escalationIndex": idx,
            "totalSections": total,
            "strategy": "escalate_then_resolve"
        }
        out.append(s2)
    return out
