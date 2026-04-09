
from typing import Dict, List

def plan_limb_interaction_for_sections(sections: List[Dict], profile: Dict) -> List[Dict]:
    out = []
    interaction = (profile or {}).get("interactionBias", {})
    timekeeper = interaction.get("timekeeper", "hihat")
    busy_feet = bool(interaction.get("busy_feet", False))

    for s in sections or []:
        s2 = dict(s)
        section_type = s2.get("sectionType") or s2.get("type") or "verse"

        preferred = timekeeper
        if section_type == "chorus" and timekeeper == "hihat":
            preferred = "ride" if not busy_feet else "hihat"
        elif section_type in ("intro", "verse"):
            preferred = "hihat"

        s2["limbInteractionPlan"] = {
            "preferredTimekeeper": preferred,
            "simplifyGhostsWhenFeetBusy": busy_feet,
            "sectionType": section_type,
        }
        out.append(s2)
    return out
