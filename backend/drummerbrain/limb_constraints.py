from __future__ import annotations

from typing import Any, Dict, List


def enforce_limb_constraints(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    active = 0
    for e in events or []:
        if active < 2:
            cleaned.append(e)
            active += 1
    return cleaned


__all__ = ["enforce_limb_constraints"]
