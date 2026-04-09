from typing import Dict, List


def _safe_float(value, default: float) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)

def build_drummer_personality_profile(phrases: List[Dict], rollup: Dict | None = None) -> Dict:
    rollup = rollup or {}
    all_events = []
    for p in phrases or []:
        all_events.extend(p.get("events", []))

    total = max(1, len(all_events))
    accents = sum(1 for e in all_events if e.get("accent"))
    ghosts = sum(1 for e in all_events if e.get("role") == "ghost")
    kicks = sum(1 for e in all_events if e.get("instrument") == "kick")
    crashes = sum(1 for e in all_events if e.get("instrument") == "crash")

    fills_per_min = _safe_float(rollup.get("fills_per_min"), 0.0)
    humanness = _safe_float(rollup.get("humanness"), 0.5)
    pocket = _safe_float(rollup.get("pocket_tightness"), 0.5)

    aggressiveness = min(1.0, 0.35 * (accents / total * 4.0) + 0.25 * (crashes / total * 6.0) + 0.40 * min(1.0, fills_per_min / 2.0))
    restraint = min(1.0, 0.45 * pocket + 0.35 * humanness + 0.20 * max(0.0, 1.0 - aggressiveness))
    consistency = min(1.0, 0.55 * pocket + 0.45 * humanness)
    chaos = max(0.0, min(1.0, 1.0 - consistency + 0.25 * min(1.0, fills_per_min / 2.0)))
    ghost_style = min(1.0, ghosts / total * 5.0)
    kick_drive = min(1.0, kicks / total * 3.0)

    return {
        "aggressiveness": aggressiveness,
        "restraint": restraint,
        "consistency": consistency,
        "chaos": chaos,
        "ghostStyle": ghost_style,
        "kickDrive": kick_drive,
        "signatureHabits": {
            "crashBias": min(1.0, crashes / total * 6.0),
            "accentBias": min(1.0, accents / total * 4.0),
        },
    }
