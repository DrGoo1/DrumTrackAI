from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

_SENTIENT_RICH_KEYS = {
    "profiles",
    "timing_profiles",
    "dynamic_profiles",
    "transition_model",
    "instrument_timing_profiles",
    "instrument_dynamic_profiles",
    "phrase_memory",
    "phrase_library",
    "sentient_profile_id",
    "export_path",
}

_PROFILE_CONTAINER_KEYS = (
    "drummer_profile",
    "drummerProfile",
    "sentient_profile",
    "sentientProfile",
    "profile",
)

_CFG_EXCLUDE_KEYS = set(_PROFILE_CONTAINER_KEYS) | {
    "songmap_summary",
    "songmapSummary",
    "cfg",
    "metadata",
}


def _as_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def extract_drummer_profile(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}

    for key in _PROFILE_CONTAINER_KEYS:
        value = payload.get(key)
        if isinstance(value, Mapping):
            return dict(value)

    cfg = payload.get("cfg")
    if isinstance(cfg, Mapping):
        for key in _PROFILE_CONTAINER_KEYS:
            value = cfg.get(key)
            if isinstance(value, Mapping):
                return dict(value)

    return {}


def has_sentient_profile(payload: Mapping[str, Any]) -> bool:
    if not isinstance(payload, Mapping):
        return False

    if bool(payload.get("sentientEnabled") or payload.get("useSentientTake")):
        return True

    profile = extract_drummer_profile(payload)
    if not profile:
        return False

    if any(key in profile for key in _SENTIENT_RICH_KEYS):
        return True

    if isinstance(profile.get("profiles"), list) and profile.get("profiles"):
        return True

    if isinstance(profile.get("persona"), Mapping) and profile.get("persona"):
        return True

    return False


def normalize_generate_drums_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"cfg": {}, "songmap_summary": {}, "drummer_profile": {}}

    incoming_cfg = payload.get("cfg")
    cfg: Dict[str, Any] = _as_dict(incoming_cfg)
    if not cfg:
        cfg = {k: v for k, v in payload.items() if k not in _CFG_EXCLUDE_KEYS}

    tempos = cfg.get("tempos") or payload.get("tempos")
    if isinstance(tempos, list) and tempos and "tempo" not in cfg:
        cfg["tempo"] = tempos[0]
    elif "tempo" not in cfg and payload.get("tempo") is not None:
        cfg["tempo"] = payload.get("tempo")

    section_id = cfg.get("sectionId") or payload.get("sectionId")
    section_name = cfg.get("sectionName") or payload.get("sectionName") or section_id or "section"
    start_measure = cfg.get("startMeasure") if cfg.get("startMeasure") is not None else payload.get("startMeasure")
    end_measure = cfg.get("endMeasure") if cfg.get("endMeasure") is not None else payload.get("endMeasure")
    measure_count = cfg.get("measureCount") if cfg.get("measureCount") is not None else payload.get("measureCount")

    bars = None
    try:
        if measure_count is not None:
            bars = max(1, int(measure_count))
        elif start_measure is not None and end_measure is not None:
            bars = max(1, int(end_measure) - int(start_measure) + 1)
    except Exception:
        bars = None

    if section_id and not isinstance(cfg.get("songSections"), list):
        cfg["songSections"] = [{
            "id": str(section_id),
            "name": str(section_name),
            "bars": int(bars or 1),
        }]

    songmap_summary = _as_dict(payload.get("songmap_summary") or payload.get("songmapSummary"))
    if not songmap_summary and isinstance(cfg.get("songSections"), list):
        songmap_summary = {
            "sections": [
                {
                    "sectionId": str(sec.get("id") or sec.get("sectionId") or f"section_{idx+1}"),
                    "name": str(sec.get("name") or sec.get("label") or sec.get("sectionType") or f"section_{idx+1}"),
                    "bars": int(sec.get("bars") or 1),
                }
                for idx, sec in enumerate(cfg.get("songSections") or [])
                if isinstance(sec, Mapping)
            ]
        }

    drummer_profile = extract_drummer_profile(payload)

    return {
        "cfg": cfg,
        "songmap_summary": songmap_summary,
        "drummer_profile": drummer_profile,
    }
