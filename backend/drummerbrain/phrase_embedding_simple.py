from __future__ import annotations

from typing import Any, Dict, List, Mapping


def build_simple_embedding(phrase: Mapping[str, Any]) -> List[float]:
    events = phrase.get("events", [])
    if not isinstance(events, list) or not events:
        return [0.0, 0.0, 0.0, 0.0, 0.0]

    density = len(events)

    vel_sum = 0.0
    kick = 0
    snare = 0
    sync = 0

    for e in events:
        if not isinstance(e, dict):
            continue
        vel_sum += float(e.get("velocity", 0.5) or 0.0)
        inst = e.get("instrument")
        if inst == "kick":
            kick += 1
        if inst == "snare":
            snare += 1
        try:
            subdiv = int(e.get("subdivision", 0) or 0)
        except Exception:
            subdiv = 0
        if subdiv % 2 != 0:
            sync += 1

    denom = max(1, len([e for e in events if isinstance(e, dict)]))
    vel = vel_sum / denom

    return [
        float(density) / 32.0,
        float(sync) / float(denom),
        float(vel),
        float(kick) / float(denom),
        float(snare) / float(denom),
    ]


__all__ = ["build_simple_embedding"]
