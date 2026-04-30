
from typing import Dict, List
from .rudiment_runtime_policy_extended import should_use_extended_rudiments

def annotate_song_roadmap_with_extended_rudiments(sections: List[Dict], rudiment_profile: Dict) -> List[Dict]:
    out = []
    usage = (rudiment_profile or {}).get("usage_rate", {})
    advanced = list((rudiment_profile or {}).get("advancedFamilies", []))
    preferred = sorted(usage.keys(), key=lambda k: usage.get(k, 0), reverse=True)

    for s in sections or []:
        s2 = dict(s)
        enabled = should_use_extended_rudiments(s2, rudiment_profile or {})
        s2["extendedRudimentPlan"] = {
            "enabled": enabled,
            "preferredFamilies": preferred,
            "advancedFamilies": advanced,
            "sectionType": s2.get("sectionType") or s2.get("type") or "verse",
        }
        out.append(s2)
    return out
