
from typing import Dict

def should_use_extended_rudiments(section: Dict, rudiment_profile: Dict) -> bool:
    section = section or {}
    profile = rudiment_profile or {}
    advanced = set(profile.get("advancedFamilies", []))
    usage = profile.get("usage_rate", {})

    section_type = section.get("sectionType") or section.get("type") or "verse"
    energy = float(section.get("energy", 0.5))
    fill_prob = float(section.get("fillProbability", section.get("fill_bias", 0.35)))

    if not usage:
        return False
    if not advanced:
        return False
    if section_type in ("turnaround", "fill", "ending"):
        return True
    if section_type == "chorus" and energy >= 0.65:
        return True
    if section_type == "bridge" and energy >= 0.55 and fill_prob >= 0.4:
        return True
    return False
