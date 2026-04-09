from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional


_SENTIENT_KEYS = {
    "profiles",
    "timing_profiles",
    "dynamic_profiles",
    "transition_model",
    "instrument_timing_profiles",
    "instrument_dynamic_profiles",
    "phrase_library",
    "phrase_memory",
}


def has_sentient_identity(profile: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(profile, dict):
        return False
    return any(k in profile for k in _SENTIENT_KEYS)


def _section_profile_candidates(section: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    for key in (
        "sentientProfile",
        "drummer_profile",
        "drummerProfile",
        "sectionDrummerProfile",
        "profile",
    ):
        value = section.get(key)
        if isinstance(value, dict) and value:
            yield value


def resolve_section_profile(
    section: Optional[Dict[str, Any]],
    default_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    default_profile = deepcopy(default_profile or {})
    if not isinstance(section, dict):
        return default_profile

    for candidate in _section_profile_candidates(section):
        if has_sentient_identity(candidate):
            merged = deepcopy(default_profile)
            merged.update(deepcopy(candidate))
            return merged

    # still allow non-sentient per-section overrides for feel/ghost/etc.
    for candidate in _section_profile_candidates(section):
        merged = deepcopy(default_profile)
        merged.update(deepcopy(candidate))
        return merged

    return default_profile


def build_section_profile_map(
    sections: Optional[List[Dict[str, Any]]],
    default_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    if not isinstance(sections, list):
        return result
    for idx, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        section_type = str(section.get("type") or section.get("sectionType") or section.get("name") or section.get("label") or "section").strip().lower()
        key = f"{idx}:{section_type}"
        result[key] = resolve_section_profile(section, default_profile)
    return result


def derive_time_feel(profile: Optional[Dict[str, Any]], fallback: str = "straight") -> str:
    profile = profile or {}
    preferred_feel = str(profile.get("preferred_feel") or profile.get("feel") or fallback or "straight").strip().lower()
    if preferred_feel in {"straight", "swing", "shuffle", "laid_back", "pushed"}:
        return preferred_feel
    return str(fallback or "straight")


def derive_transition_bias(profile: Optional[Dict[str, Any]]) -> Dict[str, float]:
    profile = profile or {}
    transition = profile.get("transition_model") or {}
    if not isinstance(transition, dict):
        transition = {}

    fills_per_min = profile.get("fills_per_min")
    try:
        fills_per_min = float(fills_per_min) if fills_per_min is not None else None
    except Exception:
        fills_per_min = None

    fill_heavy = 0.0
    if fills_per_min is not None:
        fill_heavy = max(0.0, min(1.0, fills_per_min / 3.0))

    groove_to_fill = transition.get("groove_to_fill") or transition.get("groove->fill") or transition.get("groove_fill") or 0.0
    fill_to_groove = transition.get("fill_to_groove") or transition.get("fill->groove") or transition.get("fill_groove") or 0.0
    try:
        groove_to_fill = float(groove_to_fill)
    except Exception:
        groove_to_fill = 0.0
    try:
        fill_to_groove = float(fill_to_groove)
    except Exception:
        fill_to_groove = 0.0

    humanness = profile.get("humanness")
    try:
        humanness = float(humanness) if humanness is not None else 0.5
    except Exception:
        humanness = 0.5

    pocket = profile.get("pocket_tightness")
    try:
        pocket = float(pocket) if pocket is not None else 0.5
    except Exception:
        pocket = 0.5

    return {
        "fill_probability_bias": max(0.0, min(1.0, 0.45 * fill_heavy + 0.55 * max(0.0, groove_to_fill))),
        "recovery_confidence": max(0.0, min(1.0, 0.5 * max(0.0, fill_to_groove) + 0.25 * humanness + 0.25 * pocket)),
        "humanize_bias": max(0.0, min(1.0, 0.6 * humanness + 0.4 * (1.0 - pocket))),
    }


def derive_orchestration_bias(profile: Optional[Dict[str, Any]]) -> Dict[str, float | str]:
    profile = profile or {}
    shares = profile.get("instrument_shares") or {}
    if not isinstance(shares, dict):
        shares = {}
    ride = float(shares.get("ride", shares.get("ride_bow", 0.0)) or 0.0)
    hats = float(shares.get("hihat", shares.get("hihat_closed", 0.0)) or 0.0)
    crashes = float(shares.get("crash", 0.0) or 0.0)

    timekeeper = "hats"
    if ride >= max(hats, 0.2):
        timekeeper = "ride"
    elif ride >= 0.12 and hats >= 0.12:
        timekeeper = "mixed"

    return {
        "preferred_timekeeper": timekeeper,
        "hat_open_bias": max(0.0, min(1.0, 0.12 + hats * 0.55 + crashes * 0.15)),
        "ride_bell_probability": max(0.0, min(1.0, 0.05 + ride * 0.45)),
        "crash_downbeat_probability": max(0.0, min(1.0, 0.2 + crashes * 0.8)),
    }
