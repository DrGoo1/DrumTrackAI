from __future__ import annotations

from typing import Any, Dict, List, Sequence


def rank_by_drummer_similarity(
    candidates: Sequence[Dict[str, Any]],
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    preferred = set(profile.get("preferredGrooveFamilies", []) or [])
    time_feel = profile.get("timeFeel")
    target_density = float(profile.get("targetDensity", 0.5) or 0.5)

    def score(c: Dict[str, Any]) -> float:
        s = 0.0
        fam = c.get("family")
        if fam in preferred:
            s += 0.4
        if time_feel and time_feel == c.get("feel"):
            s += 0.2
        density = float(c.get("density", 0.5) or 0.5)
        complexity = abs(density - target_density)
        s += 1.0 - complexity
        return s

    return sorted(list(candidates or []), key=score, reverse=True)


__all__ = ["rank_by_drummer_similarity"]
