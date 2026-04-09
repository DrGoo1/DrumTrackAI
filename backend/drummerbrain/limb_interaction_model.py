
from typing import Dict, List

def analyze_limb_load(events: List[Dict]) -> Dict:
    load = {"RH": 0, "LH": 0, "RF": 0, "LF": 0, "unknown": 0}
    for e in events or []:
        limb = e.get("limb") or e.get("hand") or "unknown"
        limb = limb if limb in load else "unknown"
        load[limb] += 1
    total = sum(load.values()) or 1
    return {
        "counts": load,
        "shares": {k: v / total for k, v in load.items()},
        "dominant": max(load, key=load.get),
    }

def infer_interaction_bias(events: List[Dict]) -> Dict:
    hats = 0
    ride = 0
    ghosts = 0
    kicks = 0
    for e in events or []:
        inst = e.get("instrument")
        role = e.get("role")
        if inst in ("hihat", "hh"):
            hats += 1
        if inst == "ride":
            ride += 1
        if role == "ghost":
            ghosts += 1
        if inst == "kick":
            kicks += 1
    return {
        "timekeeper": "ride" if ride > hats else "hihat",
        "ghost_to_kick_ratio": ghosts / max(1, kicks),
        "busy_feet": kicks >= max(4, hats // 2),
    }

def build_limb_interaction_profile(phrases: List[Dict]) -> Dict:
    all_events = []
    for p in phrases or []:
        all_events.extend(p.get("events", []))
    load = analyze_limb_load(all_events)
    bias = infer_interaction_bias(all_events)
    return {
        "limbLoad": load,
        "interactionBias": bias,
    }
