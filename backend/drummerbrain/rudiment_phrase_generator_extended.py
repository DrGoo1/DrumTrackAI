
from typing import Dict, List
from .rudiment_library_extended import rudiment_event_map

def choose_extended_rudiment_phrase(section: Dict, rudiment_profile: Dict) -> Dict:
    usage = dict((rudiment_profile or {}).get("usage_rate", {}))
    section_type = (section or {}).get("sectionType") or (section or {}).get("type") or "verse"
    energy = float((section or {}).get("energy", 0.5))

    ranked = sorted(usage.items(), key=lambda kv: kv[1], reverse=True)
    selected = ranked[0][0] if ranked else "linear_hybrid"

    if section_type in ("chorus", "ending") and energy >= 0.7 and "six_stroke_roll" in usage:
        selected = "six_stroke_roll"
    elif section_type == "bridge" and "swiss_triplet" in usage:
        selected = "swiss_triplet"
    elif section_type in ("verse", "intro") and "linear_hybrid" in usage:
        selected = "linear_hybrid"
    elif section_type in ("turnaround", "fill") and "ratamacue" in usage:
        selected = "ratamacue"

    factory = rudiment_event_map().get(selected)
    events = factory() if factory else rudiment_event_map()["linear_hybrid"]()

    return {
        "rudimentType": selected,
        "events": events,
        "sectionType": section_type,
        "energy": energy,
    }
