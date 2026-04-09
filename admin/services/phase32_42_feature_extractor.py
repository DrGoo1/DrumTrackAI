from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple


def rows_to_events(rows: List[Tuple[Any, ...]]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    for t, inst, offset_ms, vel, strength, is_ghost, is_accent, component in rows:
        e: Dict[str, Any] = {"time": float(t or 0.0), "instrument": str(inst or "unknown")}
        if offset_ms is not None:
            try:
                e["timing_offset_ms"] = float(offset_ms)
            except Exception:
                pass
        if vel is not None:
            try:
                e["velocity"] = float(vel)
            except Exception:
                pass
        elif strength is not None:
            try:
                e["velocity"] = max(0.0, min(1.0, float(strength)))
            except Exception:
                pass
        try:
            if is_ghost is not None and int(is_ghost) == 1:
                e["role"] = "ghost"
        except Exception:
            pass
        try:
            if is_accent is not None and int(is_accent) == 1:
                e["accent"] = True
        except Exception:
            pass
        if component:
            c = str(component)
            if c in ("R", "L"):
                e["hand"] = c
            elif c in ("RH", "LH", "RF", "LF"):
                e["limb"] = c
        events.append(e)
    return events


def compute_phase37_42_features(*, events: List[Dict[str, Any]], rollup: Dict[str, Any] | None = None) -> Dict[str, Any]:
    # Minimal phrase wrapper (these phase modules expect phrases -> events)
    phrases = [{"sectionType": "verse", "events": list(events or [])}]

    from backend.drummerbrain.microtiming_profile import build_microtiming_profile
    from backend.drummerbrain.limb_interaction_model import build_limb_interaction_profile
    from backend.drummerbrain.dynamic_contour_profile import build_dynamic_contour_profile
    from backend.drummerbrain.phrase_continuity_memory import build_continuity_memory
    from backend.drummerbrain.drummer_personality_profile import build_drummer_personality_profile

    rollup = rollup or {}

    return {
        "microtiming_profile": build_microtiming_profile(events),
        "limb_interaction_profile": build_limb_interaction_profile(phrases),
        "dynamic_contour_profile": build_dynamic_contour_profile(phrases),
        "phrase_continuity_memory": build_continuity_memory(phrases, window=4),
        "drummer_personality_profile": build_drummer_personality_profile(phrases, rollup),
    }


def build_phase32_42_features_json(*, event_rows: List[Tuple[Any, ...]], rollup: Dict[str, Any] | None = None) -> str:
    events = rows_to_events(event_rows)
    payload = {"phase37_42": compute_phase37_42_features(events=events, rollup=rollup)}
    return json.dumps(payload, default=str)
