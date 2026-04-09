from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _iter_transition_rows(model: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(model, Mapping):
        rows = model.get("transitions")
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, Mapping):
                    yield row
            return
        for src, dsts in model.items():
            if not isinstance(dsts, Mapping):
                continue
            for dst, prob in dsts.items():
                yield {"from": src, "to": dst, "probability": prob}


def transition_probability(drummer_profile: Mapping[str, Any], src: str, dst: str, default: float) -> float:
    model = drummer_profile.get("transition_model") or {}
    src = str(src or "").strip().lower()
    dst = str(dst or "").strip().lower()
    for row in _iter_transition_rows(model):
        if str(row.get("from") or "").strip().lower() == src and str(row.get("to") or "").strip().lower() == dst:
            return _clamp(_safe_float(row.get("probability"), default), 0.0, 1.0)
    return _clamp(default, 0.0, 1.0)


SECTION_TO_STATE = {
    "intro": "groove",
    "verse": "groove",
    "pre": "variation",
    "prechorus": "variation",
    "chorus": "variation",
    "bridge": "variation",
    "solo": "variation",
    "breakdown": "variation",
    "outro": "groove",
    "ending": "fill",
}


def _section_state(section_type: str) -> str:
    return SECTION_TO_STATE.get(str(section_type or "").strip().lower(), "groove")


def _lookup_metric(drummer_profile: Mapping[str, Any], *keys: str, default: float = 0.0) -> float:
    for key in keys:
        if key in drummer_profile:
            return _safe_float(drummer_profile.get(key), default)
    rollup = drummer_profile.get("rollup")
    if isinstance(rollup, Mapping):
        for key in keys:
            if key in rollup:
                return _safe_float(rollup.get(key), default)
    return float(default)


def _lookup_mapping(drummer_profile: Mapping[str, Any], *keys: str) -> Dict[str, Any]:
    for key in keys:
        value = drummer_profile.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    rollup = drummer_profile.get("rollup")
    if isinstance(rollup, Mapping):
        for key in keys:
            value = rollup.get(key)
            if isinstance(value, Mapping):
                return dict(value)
    return {}


def _fill_length(fill_drive: float, energy: float) -> str:
    score = max(fill_drive, energy)
    if score >= 0.72:
        return "last_bar"
    if score >= 0.48:
        return "last_2_beats"
    return "last_beat"


def _phrase_family(section_type: str, techniques: Mapping[str, Any], fill_drive: float, time_feel: str) -> str:
    st = str(section_type or "").strip().lower()
    tech_text = " ".join(str(k).lower() for k in techniques.keys())
    if time_feel in {"swing", "shuffle"}:
        return "snare_tom_turnaround" if fill_drive >= 0.55 else "snare_pickup"
    if "flam" in tech_text and fill_drive >= 0.5:
        return "flam_tom"
    if "roll" in tech_text and st in {"bridge", "outro", "ending"}:
        return "snare_roll"
    if st in {"chorus", "bridge", "solo"}:
        return "tom_lift"
    return "snare_pickup"


def build_song_roadmap_section_overrides(
    *,
    section_type: str,
    energy: float,
    variation: float,
    swing_amount: float,
    time_feel: str,
    drummer_profile: Mapping[str, Any],
    current_timekeeper: str,
    current_fill_enabled: bool,
) -> Dict[str, Any]:
    st = str(section_type or "").strip().lower()
    fills_per_min = _lookup_metric(drummer_profile, "fills_per_min", default=0.75)
    humanness = _lookup_metric(drummer_profile, "humanness", default=0.5)
    pocket = _lookup_metric(drummer_profile, "pocket_tightness", default=0.65)
    ride_share = _lookup_metric(_lookup_mapping(drummer_profile, "instrument_shares", "instrument_counts"), "ride", default=0.0)
    hihat_share = _lookup_metric(
        _lookup_mapping(drummer_profile, "instrument_shares", "instrument_counts"), "hihat", "hat", default=0.0
    )
    techniques = _lookup_mapping(drummer_profile, "technique_breakdown")

    current_state = _section_state(st)
    groove_to_fill = transition_probability(drummer_profile, current_state, "fill", 0.28 + variation * 0.18)
    variation_to_fill = transition_probability(drummer_profile, "variation", "fill", groove_to_fill)
    fill_to_groove = transition_probability(drummer_profile, "fill", "groove", 0.82)
    groove_to_variation = transition_probability(drummer_profile, "groove", "variation", 0.34 + energy * 0.18)

    fill_drive = _clamp((fills_per_min / 2.0) * 0.45 + groove_to_fill * 0.40 + variation * 0.15, 0.0, 1.0)
    aggression = _clamp(
        0.2 + energy * 0.35 + groove_to_fill * 0.30 + (1.0 - pocket) * 0.10 + humanness * 0.05, 0.0, 1.0
    )

    timekeeper = current_timekeeper
    if st == "chorus":
        if ride_share >= max(0.12, hihat_share * 0.45) or groove_to_variation >= 0.48:
            timekeeper = "ride"
    elif st in {"bridge", "solo"}:
        if ride_share >= 0.08 or groove_to_fill >= 0.42:
            timekeeper = "mixed"
    elif st in {"breakdown", "verse", "intro"} and hihat_share >= max(0.08, ride_share):
        timekeeper = "hats"

    hat_open_bias = _clamp(0.10 + energy * 0.28 + (1.0 - pocket) * 0.15 + swing_amount * 0.18, 0.0, 1.0)
    if timekeeper == "ride":
        hat_open_bias *= 0.7
    ride_bell_probability = _clamp(
        (0.03 if timekeeper not in {"ride", "mixed"} else 0.10) + groove_to_fill * 0.12 + max(0.0, energy - 0.7) * 0.18,
        0.0,
        1.0,
    )
    crash_downbeat_probability = _clamp(
        0.25 + energy * 0.35 + groove_to_fill * 0.20 + (0.08 if st in {"chorus", "bridge", "outro", "ending"} else 0.0),
        0.0,
        1.0,
    )

    fill_enabled = bool(current_fill_enabled and (st != "intro" or groove_to_fill >= 0.5))
    pickup_enabled = bool((variation_to_fill >= 0.42 or groove_to_variation >= 0.5) and st not in {"intro", "ending"})
    repetition_fills = bool(fill_drive >= 0.72 or groove_to_fill >= 0.58)

    return {
        "orchestration": {
            "timekeeper": timekeeper,
            "hatOpenBias": hat_open_bias,
            "rideBellProbability": ride_bell_probability,
            "crashDownbeatProbability": crash_downbeat_probability,
        },
        "grooveIntent": {
            "syncopation": _clamp(0.22 + variation * 0.28 + groove_to_variation * 0.28 + (1.0 - pocket) * 0.10, 0.0, 1.0),
            "snareGhostTarget": _clamp(0.18 + humanness * 0.32 + (techniques.get("ghost") and 0.06 or 0.0), 0.0, 1.0),
        },
        "transitions": {
            "fillOut": {
                "enabled": fill_enabled,
                "length": _fill_length(fill_drive, energy),
                "family": _phrase_family(st, techniques, fill_drive, time_feel),
                "aggression": aggression,
                "probability": groove_to_fill,
                "resolutionStrength": fill_to_groove,
            },
            "pickupIntoNext": {
                "enabled": pickup_enabled,
                "type": "snare_pickup" if time_feel not in {"swing", "shuffle"} else "triplet_pickup",
                "probability": max(groove_to_variation, variation_to_fill),
            },
        },
        "timing": {
            "timeFeel": time_feel,
            "shuffleMode": "swing_8th" if time_feel in {"swing", "shuffle"} else "straight",
            "humanizeAmount": _clamp(0.45 + (1.0 - pocket) * 0.30 + humanness * 0.15, 0.0, 1.0),
        },
        "globalHints": {
            "fillDrive": fill_drive,
            "grooveToFill": groove_to_fill,
            "grooveToVariation": groove_to_variation,
        },
        "fillPolicy": {
            "defaultLength": _fill_length(fill_drive, energy),
            "frequency": "all_transitions"
            if groove_to_fill >= 0.5
            else ("section_transitions" if groove_to_fill >= 0.28 else "conservative"),
            "transitionFills": groove_to_fill >= 0.22,
            "repetitionFills": repetition_fills,
        },
    }
