from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _aggregate_timing_stats(timing_profiles: Mapping[str, Any]) -> Dict[str, Any]:
    """Aggregate instrument/subdivision timing stats into global mean/std.

    Expected shape (Phase 7):
        timing_profiles[instrument][subdivision] = {count, mean, std}
    """

    total_n = 0
    # compute weighted mean of means
    mean_acc = 0.0
    for inst, submap in (timing_profiles or {}).items():
        if not isinstance(submap, Mapping):
            continue
        for _, stats in submap.items():
            if not isinstance(stats, Mapping):
                continue
            n = _safe_int(stats.get("count"), 0)
            m = stats.get("mean")
            if n <= 0 or m is None:
                continue
            total_n += n
            mean_acc += float(m) * float(n)

    mean = (mean_acc / float(total_n)) if total_n > 0 else 0.0

    # approximate global std using per-bucket variance + bucket mean delta
    var_acc = 0.0
    for inst, submap in (timing_profiles or {}).items():
        if not isinstance(submap, Mapping):
            continue
        for _, stats in submap.items():
            if not isinstance(stats, Mapping):
                continue
            n = _safe_int(stats.get("count"), 0)
            m = stats.get("mean")
            s = stats.get("std")
            if n <= 0 or m is None:
                continue
            bucket_var = float(s) ** 2 if s is not None else 0.0
            var_acc += float(n) * (bucket_var + (float(m) - mean) ** 2)

    std = (var_acc / float(total_n)) ** 0.5 if total_n > 0 else 0.0

    return {
        "count": int(total_n),
        "mean_offset_ms": float(mean),
        "std_offset_ms": float(std),
        # Convenience alias used elsewhere
        "timing_std_ms": float(std),
    }


def _normalize_tightness_from_std(std_ms: float) -> float:
    # Loose heuristic mapping: 0–40ms -> 1..0
    return max(0.0, min(1.0, 1.0 - (float(std_ms) / 40.0)))


def _preferred_feel(global_timing: Mapping[str, Any]) -> str:
    dominant = str(global_timing.get("dominant_feel") or "").strip().lower()
    if dominant in {"straight", "laid_back", "pushed", "shuffle", "swing"}:
        return dominant

    swing = _safe_float(global_timing.get("swing_factor"), 0.0)
    if swing >= 0.58:
        return "swing"
    if swing >= 0.35:
        return "shuffle"

    mean_offset = _safe_float(global_timing.get("mean_offset_ms"), 0.0)
    if mean_offset >= 4.0:
        return "laid_back"
    if mean_offset <= -4.0:
        return "pushed"

    return "straight"


def _phrase_type_counts_from_profile(sentient_profile: Mapping[str, Any]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in (sentient_profile.get("phrase_library") or []):
        if not isinstance(p, Mapping):
            continue
        t = str(p.get("type") or "").strip().lower()
        if not t:
            continue
        counts[t] = int(counts.get(t, 0)) + 1
    return counts


def _ghost_pref_from_phase7(sentient_profile: Mapping[str, Any]) -> float:
    """Return 0..1 preference estimate for ghost notes.

    Uses Phase 7 `dynamics_profiles['snare']['ghost']` when available.
    """

    dyn = sentient_profile.get("dynamics_profiles") or {}
    sn = dyn.get("snare") if isinstance(dyn, Mapping) else None
    ghost = sn.get("ghost") if isinstance(sn, Mapping) else None
    if not isinstance(ghost, Mapping):
        return 0.4

    vel_mean = ghost.get("mean")
    density = _safe_float(ghost.get("count"), 0.0) / max(1.0, _safe_float((sentient_profile.get("counts") or {}).get("hits"), 1.0))

    # Heuristic: more ghost events + lower ghost velocity mean -> higher ghost preference
    base = 0.35
    if vel_mean is not None:
        base += max(0.0, min(1.0, (60.0 - float(vel_mean)) / 100.0))
    base += min(1.0, density * 3.0)
    return max(0.0, min(1.0, base))


def to_runtime_drummer_profile(sentient_profile: Mapping[str, Any]) -> Dict[str, Any]:
    """Convert a Phase 7 sentient profile into the lightweight runtime drummer_profile shape.

    This keeps current runtime expectations stable while exposing richer per-instrument timing and
    dynamics maps for future use.
    """

    schema_version = str(sentient_profile.get("schema_version") or "")

    # Phase 7 shape
    timing_profiles = sentient_profile.get("timing_profiles") or {}
    dynamics_profiles = sentient_profile.get("dynamics_profiles") or {}
    persona = sentient_profile.get("persona") or {}

    global_timing = _aggregate_timing_stats(timing_profiles if isinstance(timing_profiles, Mapping) else {})
    feel = _preferred_feel(global_timing)

    tightness = _normalize_tightness_from_std(_safe_float(global_timing.get("timing_std_ms"), 12.0))

    phrase_type_counts = _phrase_type_counts_from_profile(sentient_profile)

    # Bridge limb_summary -> limb_profile
    limb_profile = sentient_profile.get("limb_profile")
    if limb_profile is None:
        limb_profile = sentient_profile.get("limb_summary") or {}

    # Bridge phrase_transition -> transition_model
    transition_model = sentient_profile.get("transition_model")
    if transition_model is None:
        pt = sentient_profile.get("phrase_transition") or {}
        if isinstance(pt, Mapping):
            transition_model = (pt.get("global") or {})
        else:
            transition_model = {}

    # Determine drummer_id/display_name
    drummer_id = sentient_profile.get("drummer_id")
    if drummer_id is None:
        src = sentient_profile.get("source") or {}
        if isinstance(src, Mapping):
            drummer_id = src.get("drummer_slug")

    out: Dict[str, Any] = {
        "drummer_id": drummer_id,
        "display_name": sentient_profile.get("display_name") or drummer_id,
        "timing_tightness": tightness,
        "timing_precision": tightness,
        "ghost_note_frequency": _ghost_pref_from_phase7(sentient_profile),
        "preferred_feel": feel,
        "feel": feel,
        "swing_factor": _safe_float(global_timing.get("swing_factor"), 0.0),
        "signature_techniques": [feel],
        "persona": persona,
        "instrument_timing_profiles": timing_profiles,
        "instrument_dynamic_profiles": dynamics_profiles,
        "transition_model": transition_model,
        "phrase_type_counts": phrase_type_counts,
        "limb_profile": limb_profile,
        "source": {
            "type": "sentient_profile",
            "schema_version": schema_version,
        },
    }

    tags = persona.get("tags") if isinstance(persona, Mapping) else None
    if isinstance(tags, list) and tags:
        out["style_tags"] = [str(t) for t in tags]

    return out


def load_runtime_drummer_profile(path: str | Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("Profile JSON must be an object")
    return to_runtime_drummer_profile(data)


def _agg_inst_timing(inst_map: Mapping[str, Any]) -> Tuple[float, float]:
    # Aggregate per-subdivision stats into mean/std
    means: List[float] = []
    stds: List[float] = []
    for _, s in inst_map.items():
        if not isinstance(s, Mapping):
            continue
        m = s.get("mean")
        if m is not None:
            means.append(float(m))
        sd = s.get("std")
        if sd is not None:
            stds.append(float(sd))
    mean = sum(means) / float(len(means)) if means else 0.0
    std = sum(stds) / float(len(stds)) if stds else 4.0
    return mean, std


def build_instrument_phrase_profiles(
    sentient_profile: Mapping[str, Any],
    base_velocity: int,
    humanize_amount: float,
) -> List[Dict[str, Any]]:
    """Build per-instrument phrase profiles compatible with the frontend/midi generator utilities.

    This function is intentionally conservative: it takes the Phase 7 summary stats and produces
    simple per-instrument microtiming/velocity parameterizations.
    """

    timing_profiles = sentient_profile.get("timing_profiles") or {}
    dynamics_profiles = sentient_profile.get("dynamics_profiles") or {}

    instruments = ["kick", "snare", "hihat", "ride", "tom"]
    out: List[Dict[str, Any]] = []

    swing = 0.0
    if isinstance(sentient_profile.get("phrase_transition"), Mapping):
        # no swing in Phase 7 yet; keep placeholder
        swing = 0.0

    for inst in instruments:
        t_inst = timing_profiles.get(inst) if isinstance(timing_profiles, Mapping) else None
        if not isinstance(t_inst, Mapping):
            t_inst = {}
        mean_offset, std_offset = _agg_inst_timing(t_inst)

        d_inst = dynamics_profiles.get(inst) if isinstance(dynamics_profiles, Mapping) else None
        if isinstance(d_inst, Mapping):
            d_role = d_inst.get("normal") if isinstance(d_inst.get("normal"), Mapping) else d_inst.get("accent")
            if not isinstance(d_role, Mapping):
                d_role = None
        else:
            d_role = None

        vel_mean = base_velocity
        vel_std = 10.0
        if isinstance(d_role, Mapping):
            if d_role.get("mean") is not None:
                vel_mean = int(max(1, min(127, round(float(d_role.get("mean"))))))
            if d_role.get("std") is not None:
                vel_std = float(d_role.get("std"))

        profile = {
            "instrumentId": "snare_center"
            if inst == "snare"
            else ("hihat_closed" if inst == "hihat" else ("ride_bow" if inst == "ride" else inst)),
            "microTiming": {
                "subdivisionOffsetsMs": [float(mean_offset)] * 16,
                "swingAmount": float(swing),
                "laidBackAmount": max(-1.0, min(1.0, float(mean_offset) / 12.0)),
                "randomStdMs": max(0.0, float(std_offset) * max(0.25, float(humanize_amount))),
            },
            "velocityProfile": {
                "base": int(max(1, min(127, int(vel_mean)))),
                "accentBoost": int(max(0, min(40, round(float(vel_std) * 1.2)))),
                "ghostReduction": 0.55 if inst == "snare" else 0.75,
                "randomRange": int(max(0, min(24, round(float(vel_std) * max(0.4, float(humanize_amount)))))),
                "phraseShape": "flat",
            },
            "ghostDensity": _ghost_pref_from_phase7(sentient_profile) if inst == "snare" else 0.0,
        }
        out.append(profile)

    return out
