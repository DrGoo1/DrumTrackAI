
from typing import Dict, List

def _make_event(step: int, instrument: str, velocity: float, hand: str | None = None, accent: bool = False) -> Dict:
    return {
        "step": step,
        "instrument": instrument,
        "velocity": velocity,
        "hand": hand,
        "accent": accent,
    }

def generate_flam_fill(start_step: int = 0, lead_instrument: str = "snare", accent_instrument: str = "snare") -> List[Dict]:
    return [
        _make_event(start_step + 0, lead_instrument, 0.35, "L", False),
        _make_event(start_step + 0, accent_instrument, 0.90, "R", True),
        _make_event(start_step + 2, "tom1", 0.72, "L", False),
        _make_event(start_step + 4, "tom2", 0.78, "R", True),
        _make_event(start_step + 6, "crash", 0.95, "R", True),
    ]

def generate_drag_pickup(start_step: int = 0, instrument: str = "snare") -> List[Dict]:
    return [
        _make_event(start_step + 0, instrument, 0.25, "L", False),
        _make_event(start_step + 1, instrument, 0.30, "R", False),
        _make_event(start_step + 2, instrument, 0.92, "L", True),
        _make_event(start_step + 4, "kick", 0.82, "R", False),
    ]

def generate_paradiddle_phrase(start_step: int = 0, orchestrated: bool = True) -> List[Dict]:
    seq = [("R", "snare"), ("L", "hihat"), ("R", "snare"), ("R", "tom1"),
           ("L", "snare"), ("R", "hihat"), ("L", "snare"), ("L", "tom2")]
    if not orchestrated:
        seq = [(hand, "snare") for hand, _ in seq]
    events = []
    for i, (hand, inst) in enumerate(seq):
        events.append(_make_event(start_step + i, inst, 0.62 if i % 4 else 0.88, hand, i % 4 == 0))
    return events

def choose_rudiment_phrase(section: Dict, rudiment_profile: Dict) -> Dict:
    usage = rudiment_profile.get("usage_rate", {}) if rudiment_profile else {}
    section_type = (section or {}).get("sectionType") or (section or {}).get("type") or "verse"
    energy = float((section or {}).get("energy", 0.5))

    ranked = sorted(usage.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[0][0] if ranked else "paradiddle"

    if section_type in ("intro", "verse") and "drag" in usage:
        top = "drag"
    elif section_type in ("chorus", "bridge") and "flam" in usage and energy >= 0.6:
        top = "flam"
    elif section_type in ("turnaround", "fill", "ending") and "paradiddle" in usage:
        top = "paradiddle"

    if top == "flam":
        events = generate_flam_fill()
    elif top == "drag":
        events = generate_drag_pickup()
    else:
        events = generate_paradiddle_phrase(orchestrated=energy >= 0.5)

    return {
        "rudimentType": top,
        "events": events,
        "orchestrated": energy >= 0.5,
        "sectionType": section_type,
    }
