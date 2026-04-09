
from typing import Dict, List

def vary_phrase_events(events: List[Dict], intensity: float = 0.25) -> List[Dict]:
    out = []
    for idx, e in enumerate(events or []):
        e2 = dict(e)
        if "velocity" in e2:
            if idx % 4 == 0:
                e2["velocity"] = min(1.0, float(e2["velocity"]) + 0.10 * intensity)
            elif idx % 3 == 0:
                e2["velocity"] = max(0.0, float(e2["velocity"]) - 0.06 * intensity)
        if idx % 5 == 0 and e2.get("instrument") == "hihat":
            e2["instrument"] = "ride" if intensity >= 0.6 else "hihat"
        out.append(e2)
    return out

def apply_phrase_variation(phrase: Dict, mode: str = "light", continuity_score: float = 0.0) -> Dict:
    out = dict(phrase or {})
    events = list(out.get("events") or [])

    if not events:
        out["variationApplied"] = False
        return out

    intensity = 0.20
    if mode == "light":
        intensity = 0.20
    elif mode == "medium":
        intensity = 0.45
    elif mode == "strong":
        intensity = 0.70

    # If continuity is already very high, encourage subtle differentiation.
    if continuity_score >= 0.75:
        intensity = max(intensity, 0.35)
    elif continuity_score <= 0.25:
        intensity = min(intensity, 0.20)

    out["events"] = vary_phrase_events(events, intensity=intensity)
    out["variationApplied"] = True
    out["variationMeta"] = {
        "mode": mode,
        "intensity": intensity,
        "continuityScore": continuity_score,
    }
    return out
