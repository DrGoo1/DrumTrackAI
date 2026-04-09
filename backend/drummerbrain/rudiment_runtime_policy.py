
from typing import Dict

def should_inject_rudiment(section: Dict, rudiment_profile: Dict, phrase_meta: Dict | None = None) -> bool:
    section = section or {}
    phrase_meta = phrase_meta or {}
    usage = (rudiment_profile or {}).get("usage_rate", {})
    section_type = section.get("sectionType") or section.get("type") or "verse"
    energy = float(section.get("energy", 0.5))
    fill_bias = float(section.get("fillProbability", section.get("fill_bias", 0.35)))
    restrained = bool(phrase_meta.get("restrained", False))

    if not usage:
        return False
    if restrained and section_type in ("verse", "intro"):
        return False
    if section_type in ("turnaround", "fill", "ending"):
        return True
    if section_type == "chorus" and energy >= 0.65:
        return True
    if section_type == "bridge" and energy >= 0.55:
        return True
    if section_type == "verse":
        return fill_bias >= 0.45 and energy >= 0.45
    return fill_bias >= 0.5
