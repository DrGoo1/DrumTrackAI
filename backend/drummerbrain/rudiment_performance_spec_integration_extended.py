
from typing import Dict, List
from .rudiment_runtime_policy_extended import should_use_extended_rudiments
from .rudiment_phrase_generator_extended import choose_extended_rudiment_phrase
from .rudiment_orchestration import orchestrate_rudiment_events

def apply_extended_rudiments_to_phrases(phrases: List[Dict], sections: List[Dict], rudiment_profile: Dict) -> List[Dict]:
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

        if should_use_extended_rudiments(section, rudiment_profile or {}):
            chosen = choose_extended_rudiment_phrase(section, rudiment_profile or {})
            events = orchestrate_rudiment_events(chosen["events"], section)
            p.setdefault("events", [])
            p["events"].extend(events)
            p["extendedRudimentApplied"] = True
            p["extendedRudimentMeta"] = {
                "type": chosen["rudimentType"],
                "eventCount": len(events),
                "sectionType": chosen["sectionType"],
            }
        else:
            p["extendedRudimentApplied"] = False
        out.append(p)

    return out
