
from typing import Dict, List

def _evt(step: int, instrument: str, velocity: float, hand: str | None = None, accent: bool = False) -> Dict:
    return {
        "step": step,
        "instrument": instrument,
        "velocity": velocity,
        "hand": hand,
        "accent": accent,
    }

def six_stroke_roll(start_step: int = 0) -> List[Dict]:
    # RllrrL-inspired drumset phrasing
    seq = [
        _evt(start_step + 0, "snare", 0.90, "R", True),
        _evt(start_step + 1, "snare", 0.45, "L", False),
        _evt(start_step + 2, "snare", 0.48, "L", False),
        _evt(start_step + 3, "tom1", 0.78, "R", True),
        _evt(start_step + 4, "tom2", 0.74, "R", False),
        _evt(start_step + 5, "kick", 0.82, "L", False),
    ]
    return seq

def swiss_triplet(start_step: int = 0) -> List[Dict]:
    return [
        _evt(start_step + 0, "snare", 0.32, "L", False),
        _evt(start_step + 0, "snare", 0.88, "R", True),
        _evt(start_step + 2, "tom1", 0.80, "L", True),
        _evt(start_step + 3, "snare", 0.30, "R", False),
        _evt(start_step + 3, "snare", 0.84, "L", True),
        _evt(start_step + 5, "tom2", 0.82, "R", True),
    ]

def ratamacue(start_step: int = 0) -> List[Dict]:
    return [
        _evt(start_step + 0, "snare", 0.25, "L", False),
        _evt(start_step + 1, "snare", 0.28, "R", False),
        _evt(start_step + 2, "snare", 0.92, "L", True),
        _evt(start_step + 4, "tom1", 0.72, "R", False),
        _evt(start_step + 6, "crash", 0.96, "R", True),
    ]

def herta(start_step: int = 0) -> List[Dict]:
    # 3+1 grouping feel
    return [
        _evt(start_step + 0, "kick", 0.84, "R", True),
        _evt(start_step + 1, "snare", 0.62, "L", False),
        _evt(start_step + 2, "hihat", 0.58, "R", False),
        _evt(start_step + 4, "snare", 0.91, "L", True),
    ]

def inverted_herta(start_step: int = 0) -> List[Dict]:
    # 1+3 grouping feel
    return [
        _evt(start_step + 0, "snare", 0.92, "R", True),
        _evt(start_step + 2, "kick", 0.76, "L", False),
        _evt(start_step + 3, "hihat", 0.55, "R", False),
        _evt(start_step + 4, "snare", 0.60, "L", False),
    ]

def linear_hybrid(start_step: int = 0) -> List[Dict]:
    # Drumset hybrid phrase, non-overlapping limbs feel
    return [
        _evt(start_step + 0, "kick", 0.84, "R", True),
        _evt(start_step + 1, "snare", 0.66, "L", False),
        _evt(start_step + 2, "hihat", 0.52, "R", False),
        _evt(start_step + 3, "tom1", 0.72, "L", True),
        _evt(start_step + 4, "kick", 0.80, "R", False),
        _evt(start_step + 5, "snare", 0.88, "L", True),
    ]

def rudiment_event_map() -> Dict[str, callable]:
    return {
        "six_stroke_roll": six_stroke_roll,
        "swiss_triplet": swiss_triplet,
        "ratamacue": ratamacue,
        "herta": herta,
        "inverted_herta": inverted_herta,
        "linear_hybrid": linear_hybrid,
    }
