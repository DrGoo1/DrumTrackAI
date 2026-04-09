from __future__ import annotations

from typing import Dict


def style_consistency_score(profile: Dict, generated: Dict) -> float:
    fam = generated.get("family")
    prefs = profile.get("preferredGrooveFamilies", [])
    return 1.0 if fam in (prefs or []) else 0.0


__all__ = ["style_consistency_score"]
