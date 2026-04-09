from __future__ import annotations

from typing import Any, Dict, List, Mapping


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _mapping(profile: Mapping[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        value = profile.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    rollup = profile.get("rollup")
    if isinstance(rollup, Mapping):
        for key in keys:
            value = rollup.get(key)
            if isinstance(value, Mapping):
                return dict(value)
    return {}


def _metric(profile: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in profile:
            return _safe_float(profile.get(key), default)
    rollup = profile.get("rollup")
    if isinstance(rollup, Mapping):
        for key in keys:
            if key in rollup:
                return _safe_float(rollup.get(key), default)
    return float(default)


def _transition_probability(profile: Mapping[str, Any], src: str, dst: str, default: float) -> float:
    model = profile.get("transition_model") or {}
    if isinstance(model, Mapping):
        rows = model.get("transitions")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                if str(row.get("from") or "").strip().lower() == src and str(row.get("to") or "").strip().lower() == dst:
                    return _clamp(_safe_float(row.get("probability"), default), 0.0, 1.0)
        dsts = model.get(src)
        if isinstance(dsts, Mapping):
            return _clamp(_safe_float(dsts.get(dst), default), 0.0, 1.0)
    return _clamp(default, 0.0, 1.0)


def select_phrase_families(
    *,
    section_type: str,
    energy: float,
    variation: float,
    timekeeper: str,
    fill_family: str,
    fill_enabled: bool,
    time_feel: str,
    drummer_profile: Mapping[str, Any],
) -> Dict[str, Any]:
    st = str(section_type or "").strip().lower()
    fills_per_min = _metric(drummer_profile, "fills_per_min", default=0.75)
    humanness = _metric(drummer_profile, "humanness", default=0.5)
    pocket = _metric(drummer_profile, "pocket_tightness", default=0.65)
    ride_share = _metric(_mapping(drummer_profile, "instrument_shares", "instrument_counts"), "ride", default=0.0)
    hihat_share = _metric(_mapping(drummer_profile, "instrument_shares", "instrument_counts"), "hihat", "hat", default=0.0)
    kick_share = _metric(_mapping(drummer_profile, "instrument_shares", "instrument_counts"), "kick", default=0.0)
    techniques = _mapping(drummer_profile, "technique_breakdown")
    tech_text = " ".join(str(k).lower() for k in techniques.keys())

    groove_to_fill = _transition_probability(drummer_profile, "groove", "fill", 0.26 + variation * 0.18)
    groove_to_variation = _transition_probability(drummer_profile, "groove", "variation", 0.30 + energy * 0.18)

    groove_candidates: List[str] = []
    if time_feel in {"swing", "shuffle"}:
        groove_candidates.append("shuffle_pocket")
    if timekeeper == "ride" or ride_share >= max(0.10, hihat_share * 0.4):
        groove_candidates.append("ride_lead")
    if st in {"breakdown", "verse", "intro"} and pocket >= 0.72:
        groove_candidates.append("pocket_backbeat")
    if groove_to_variation >= 0.48 or (variation >= 0.62 and kick_share >= 0.12):
        groove_candidates.append("syncopated_kick")
    if humanness >= 0.62 and pocket < 0.72:
        groove_candidates.append("open_hat_lift")
    if "linear" in tech_text or (variation >= 0.72 and fills_per_min >= 1.1):
        groove_candidates.append("linear_support")
    if st in {"bridge", "solo", "outro"} and energy >= 0.74:
        groove_candidates.append("tom_color")
    if st in {"breakdown", "bridge"} and pocket >= 0.7 and energy < 0.72:
        groove_candidates.append("halftime_space")

    if not groove_candidates:
        groove_candidates = ["pocket_backbeat", "syncopated_kick"] if pocket >= 0.7 else ["open_hat_lift", "syncopated_kick"]

    deduped_grooves: List[str] = []
    for item in groove_candidates:
        if item not in deduped_grooves:
            deduped_grooves.append(item)
    groove_candidates = deduped_grooves[:4]

    fill_candidates: List[str] = []
    if fill_enabled:
        if fill_family and fill_family != "auto":
            fill_candidates.append(fill_family)
        if time_feel in {"swing", "shuffle"}:
            fill_candidates.append("triplet_turnaround")
        if "flam" in tech_text:
            fill_candidates.append("flam_tom")
        if "roll" in tech_text and st in {"bridge", "outro", "ending"}:
            fill_candidates.append("snare_roll")
        if fills_per_min >= 1.15 or groove_to_fill >= 0.5:
            fill_candidates.append("linear_burst")
        if st in {"chorus", "bridge", "solo"} and energy >= 0.74:
            fill_candidates.append("tom_lift")
        if humanness >= 0.68 and energy >= 0.68:
            fill_candidates.append("cymbal_wash")
        fill_candidates.append("snare_pickup")
    else:
        fill_candidates = ["none"]

    deduped_fills: List[str] = []
    for item in fill_candidates:
        if item not in deduped_fills:
            deduped_fills.append(item)
    fill_candidates = deduped_fills[:4]

    primary_groove = groove_candidates[0]
    primary_fill = fill_candidates[0]

    selector_weights = {
        "grooveDensity": _clamp(0.25 + energy * 0.45 + variation * 0.10, 0.0, 1.0),
        "spacePreference": _clamp(0.35 + pocket * 0.35 - energy * 0.15, 0.0, 1.0),
        "technicality": _clamp(0.20 + variation * 0.40 + max(0.0, fills_per_min - 0.8) * 0.20, 0.0, 1.0),
        "timekeeperBias": 1.0 if timekeeper == "ride" else (0.75 if timekeeper == "mixed" else 0.35),
        "fillBias": _clamp(groove_to_fill * 0.7 + max(0.0, fills_per_min - 0.6) * 0.2, 0.0, 1.0),
    }

    return {
        "grooveFamily": primary_groove,
        "fillFamily": primary_fill,
        "grooveCandidates": groove_candidates,
        "fillCandidates": fill_candidates,
        "selectorWeights": selector_weights,
    }


def choose_phrase_shape_from_family(groove_family: str, fill_family: str, default_shape: str = "flat") -> str:
    groove_family = str(groove_family or "").strip().lower()
    fill_family = str(fill_family or "").strip().lower()
    if groove_family in {"open_hat_lift", "ride_lead", "tom_color"}:
        return "swell"
    if groove_family in {"halftime_space", "pocket_backbeat"}:
        return "flat"
    if fill_family in {"linear_burst", "triplet_turnaround", "cymbal_wash"}:
        return "push"
    return default_shape
