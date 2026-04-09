
from collections import Counter
from typing import Dict, List

def build_extended_rudiment_profile(rudiment_events: List[Dict]) -> Dict:
    counts = Counter([r["type"] for r in rudiment_events])
    total = sum(counts.values()) or 1
    profile = {
        "usage_rate": {k: v / total for k, v in counts.items()},
        "counts": dict(counts),
        "total_events": total,
        "advancedFamilies": [k for k in counts.keys() if k in (
            "six_stroke_roll", "swiss_triplet", "ratamacue", "herta", "inverted_herta", "linear_hybrid"
        )],
    }
    return profile
