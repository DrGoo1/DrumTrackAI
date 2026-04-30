
from typing import Dict, List
from .rudiment_runtime_policy import should_inject_rudiment
from .rudiment_generation_integration import inject_rudiment_phrase

def apply_rudiments_to_phrases(phrases: List[Dict], sections: List[Dict], rudiment_profile: Dict) -> List[Dict]:
    out = []
    section_map = {}
    for s in sections or []:
        key = s.get("id") or s.get("sectionId") or s.get("sectionType") or s.get("type")
        if key:
            section_map[key] = s

    for phrase in phrases or []:
        p = dict(phrase)
        sid = p.get("sectionId") or p.get("sectionType") or p.get("type")
        section = section_map.get(sid, {"sectionType": sid or "verse", "energy": p.get("energy", 0.5)})
        if should_inject_rudiment(section, rudiment_profile or {}, {"restrained": p.get("restrained", False)}):
            p = inject_rudiment_phrase(p, section, rudiment_profile or {})
            p["rudimentApplied"] = True
        else:
            p["rudimentApplied"] = False
        out.append(p)
    return out
