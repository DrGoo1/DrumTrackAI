
from typing import Dict, List

def orchestrate_rudiment_events(events: List[Dict], section: Dict) -> List[Dict]:
    section_type = (section or {}).get("sectionType") or (section or {}).get("type") or "verse"
    energy = float((section or {}).get("energy", 0.5))

    out = []
    for e in events:
        e = dict(e)
        if section_type == "chorus" and energy >= 0.7:
            if e["instrument"] == "snare" and e.get("accent"):
                e["instrument"] = "tom1"
            elif e["instrument"] == "hihat":
                e["instrument"] = "ride"
        elif section_type == "bridge":
            if e["instrument"] == "tom1":
                e["instrument"] = "tom2"
        elif section_type == "verse":
            if e["instrument"] == "crash":
                e["instrument"] = "hihat"
                e["velocity"] = min(e["velocity"], 0.72)
        out.append(e)
    return out
