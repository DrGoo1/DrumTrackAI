
from typing import Dict, List
from .rudiment_runtime_policy import should_inject_rudiment

def annotate_song_roadmap_with_rudiments(sections: List[Dict], rudiment_profile: Dict) -> List[Dict]:
    out = []
    for s in sections or []:
        s2 = dict(s)
        inject = should_inject_rudiment(s2, rudiment_profile or {}, {"restrained": s2.get("restrained", False)})
        s2["rudimentPlan"] = {
            "enabled": inject,
            "preferredFamilies": sorted((rudiment_profile or {}).get("usage_rate", {}).keys()),
            "sectionType": s2.get("sectionType") or s2.get("type") or "verse",
        }
        out.append(s2)
    return out
