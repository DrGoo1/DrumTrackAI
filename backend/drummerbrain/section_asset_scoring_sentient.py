from __future__ import annotations

from typing import Any, Dict, Mapping, Optional


def _clamp(value: Any, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        num = float(value)
    except Exception:
        num = 0.0
    return max(lo, min(hi, num))


def _norm_key(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _technique_map(profile: Optional[Mapping[str, Any]]) -> Dict[str, float]:
    profile = profile or {}
    raw = profile.get("technique_breakdown") or {}
    if not isinstance(raw, Mapping):
        return {}
    total = 0.0
    out: Dict[str, float] = {}
    for key, value in raw.items():
        try:
            out[_norm_key(key)] = float(value)
            total += float(value)
        except Exception:
            continue
    if total <= 0.0:
        return {k: 0.0 for k in out}
    return {k: v / total for k, v in out.items()}


def derive_section_asset_scoring(
    profile: Optional[Mapping[str, Any]],
    *,
    section_type: str,
    local_time_feel: str,
    timekeeper: str,
    energy: float,
    fill_aggression: float,
    ghost_target: float,
    syncopation_target: float,
) -> Dict[str, Any]:
    profile = profile or {}
    section_type = _norm_key(section_type)
    local_time_feel = _norm_key(local_time_feel)
    timekeeper = _norm_key(timekeeper)
    energy = _clamp(energy)
    fill_aggression = _clamp(fill_aggression)
    ghost_target = _clamp(ghost_target)
    syncopation_target = _clamp(syncopation_target)

    shares = profile.get("instrument_shares") or {}
    if not isinstance(shares, Mapping):
        shares = {}
    ride_share = _clamp(shares.get("ride", shares.get("ride_bow", 0.0)))
    hat_share = _clamp(shares.get("hihat", shares.get("hihat_closed", 0.0)))
    crash_share = _clamp(shares.get("crash", 0.0))
    kick_share = _clamp(shares.get("kick", 0.0))
    ghost_pref = _clamp(profile.get("ghost_note_frequency", profile.get("ghost_frequency", ghost_target)))
    fills_per_min = _clamp(profile.get("fills_per_min", 0.0) / 3.0)
    humanness = _clamp(profile.get("humanness", 0.5))
    pocket = _clamp(profile.get("pocket_tightness", 0.5))
    techniques = _technique_map(profile)

    groove_weights: Dict[str, float] = {
        "pocket_backbeat": 0.35 + pocket * 0.45 + (0.12 if section_type == "verse" else 0.0),
        "ride_lead": 0.20 + max(ride_share, 0.0) * 0.8 + (0.20 if timekeeper in {"ride", "mixed"} else 0.0),
        "open_hat_lift": 0.18 + hat_share * 0.35 + energy * 0.35 + crash_share * 0.15,
        "syncopated_kick": 0.12 + syncopation_target * 0.7 + kick_share * 0.15,
        "halftime_space": 0.08 + (0.30 if section_type in {"bridge", "breakdown", "outro"} else 0.0),
        "shuffle_pocket": 0.10 + (0.75 if local_time_feel in {"swing", "shuffle"} else 0.0),
        "linear_support": 0.08 + techniques.get("linear", 0.0) * 0.6 + syncopation_target * 0.2,
        "tom_color": 0.05 + techniques.get("tom", 0.0) * 0.5 + (0.18 if section_type in {"bridge", "solo"} else 0.0),
    }

    if section_type == "chorus":
        groove_weights["ride_lead"] += 0.18
        groove_weights["open_hat_lift"] += 0.14
    if section_type == "intro":
        groove_weights["pocket_backbeat"] += 0.10
        groove_weights["halftime_space"] += 0.10
    if local_time_feel == "laid_back":
        groove_weights["pocket_backbeat"] += 0.12
    if local_time_feel in {"swing", "shuffle"}:
        groove_weights["shuffle_pocket"] += 0.18
        groove_weights["ride_lead"] += 0.08

    fill_weights: Dict[str, float] = {
        "snare_pickup": 0.18 + fill_aggression * 0.20,
        "snare_roll": 0.12 + (0.12 if section_type in {"chorus", "outro"} else 0.0),
        "tom_lift": 0.14 + energy * 0.18 + techniques.get("tom", 0.0) * 0.20,
        "linear_burst": 0.10 + syncopation_target * 0.25 + techniques.get("linear", 0.0) * 0.40,
        "triplet_turnaround": 0.08 + (0.35 if local_time_feel in {"swing", "shuffle"} else 0.0),
        "flam_tom": 0.08 + techniques.get("flam", 0.0) * 0.45,
        "cymbal_wash": 0.06 + crash_share * 0.45 + (0.14 if section_type in {"chorus", "outro"} else 0.0),
        "none": 0.10 + (0.16 if fill_aggression < 0.35 and section_type in {"verse", "intro"} else 0.0),
    }

    if ghost_pref >= 0.55 or ghost_target >= 0.55:
        fill_weights["snare_pickup"] += 0.08
        groove_weights["pocket_backbeat"] += 0.06
    if fills_per_min >= 0.55:
        fill_weights["linear_burst"] += 0.10
        fill_weights["tom_lift"] += 0.08
    if humanness >= 0.65 and pocket <= 0.45:
        groove_weights["open_hat_lift"] += 0.06
    if pocket >= 0.75:
        groove_weights["pocket_backbeat"] += 0.10
        fill_weights["none"] += 0.04

    preferred_groove_families = [
        fam for fam, _ in sorted(groove_weights.items(), key=lambda kv: kv[1], reverse=True)[:4]
    ]
    preferred_fill_families = [
        fam for fam, _ in sorted(fill_weights.items(), key=lambda kv: kv[1], reverse=True)[:4]
    ]

    return {
        "preferredGrooveFamilies": preferred_groove_families,
        "preferredFillFamilies": preferred_fill_families,
        "grooveFamilyWeights": {k: round(float(v), 4) for k, v in groove_weights.items()},
        "fillFamilyWeights": {k: round(float(v), 4) for k, v in fill_weights.items()},
        "scoreInputs": {
            "sectionType": section_type,
            "timeFeel": local_time_feel,
            "timekeeper": timekeeper,
            "energy": round(energy, 4),
            "fillAggression": round(fill_aggression, 4),
            "ghostTarget": round(ghost_target, 4),
            "syncopationTarget": round(syncopation_target, 4),
        },
        "retrievalPolicy": {
            "preferTimekeeperMatch": True,
            "preferFeelMatch": local_time_feel in {"swing", "shuffle", "laid_back", "pushed"},
            "preferCrashEntries": bool(section_type in {"chorus", "bridge", "outro"} or crash_share >= 0.2),
            "preferGhostRichPatterns": bool(ghost_pref >= 0.5 or ghost_target >= 0.5),
            "maxCandidatePool": 12 if section_type in {"chorus", "bridge", "solo"} else 8,
        },
    }


__all__ = ["derive_section_asset_scoring"]
