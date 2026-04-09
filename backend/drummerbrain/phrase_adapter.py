from __future__ import annotations

from typing import Any, Dict, Mapping


def adapt_phrase_to_section(phrase: Dict[str, Any], section: Mapping[str, Any]) -> Dict[str, Any]:
    factor = float(section.get("energy", 0.5) or 0.5)
    events = phrase.get("events", [])
    if isinstance(events, list):
        for e in events:
            if not isinstance(e, dict):
                continue
            base = float(e.get("velocity", 0.5) or 0.0)
            e["velocity"] = min(1.0, base * (0.5 + factor))
    return phrase


__all__ = ["adapt_phrase_to_section"]
