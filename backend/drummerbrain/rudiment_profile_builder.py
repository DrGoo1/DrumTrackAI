
from collections import Counter

def build_rudiment_profile(rudiment_events):
    counts = Counter([r["type"] for r in rudiment_events])
    total = sum(counts.values()) or 1

    return {
        "usage_rate": {k: v/total for k,v in counts.items()},
        "total_events": total
    }
