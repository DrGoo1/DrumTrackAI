
from typing import Dict, List

def apply_limb_interaction_to_phrase(phrase: Dict, profile: Dict) -> Dict:
    out = dict(phrase or {})
    events = []
    interaction = (profile or {}).get("interactionBias", {})
    timekeeper = interaction.get("timekeeper", "hihat")
    busy_feet = bool(interaction.get("busy_feet", False))
    ghost_ratio = float(interaction.get("ghost_to_kick_ratio", 0.0))

    for idx, e in enumerate(out.get("events", []) or []):
        e2 = dict(e)
        inst = e2.get("instrument")

        # Timekeeper preference
        if inst in ("hihat", "ride"):
            e2["instrument"] = "ride" if timekeeper == "ride" else "hihat"

        # Busy feet simplify hand embellishment slightly
        if busy_feet and e2.get("role") == "ghost":
            e2["velocity"] = max(0.0, float(e2.get("velocity", 0.4)) - 0.08)

        # High ghost-note tendency adds slight ghost reinforcement on offbeats
        if ghost_ratio >= 0.5 and inst == "snare" and idx % 2 == 1:
            e2.setdefault("role", "ghost")
            e2["velocity"] = min(float(e2.get("velocity", 0.35)), 0.42)

        events.append(e2)

    out["events"] = events
    out["limbInteractionApplied"] = True
    out["limbInteractionMeta"] = {
        "timekeeper": timekeeper,
        "busyFeet": busy_feet,
        "ghostToKickRatio": ghost_ratio,
    }
    return out

def apply_limb_interaction_runtime(phrases: List[Dict], profile: Dict) -> List[Dict]:
    return [apply_limb_interaction_to_phrase(p, profile or {}) for p in (phrases or [])]
