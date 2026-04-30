from __future__ import annotations

from typing import Dict, List


def compare_events(a: List[Dict], b: List[Dict]) -> float:
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    matches = 0
    for i in range(n):
        if (a[i] or {}).get("instrument") == (b[i] or {}).get("instrument"):
            matches += 1
    return matches / n if n else 0.0


def reconstruction_score(reference: Dict, generated: Dict) -> float:
    return compare_events(reference.get("events", []), generated.get("events", []))


__all__ = ["compare_events", "reconstruction_score"]
