from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

try:  # pragma: no cover - optional repo dependency
    from backend.fill_library import get_fill_pattern
except Exception:  # pragma: no cover
    get_fill_pattern = None

try:  # pragma: no cover - optional repo dependency
    from backend.groove_catalog import GrooveCatalog
except Exception:  # pragma: no cover
    GrooveCatalog = None


_GROOVE_FAMILY_TAGS: Dict[str, List[str]] = {
    "ride_lead": ["ride", "ride_lead", "chorus"],
    "pocket_backbeat": ["pocket", "backbeat", "groove"],
    "syncopated_kick": ["syncopated", "kick", "groove"],
    "open_hat_lift": ["open_hat", "hihat", "lift"],
    "linear_support": ["linear", "groove"],
    "tom_color": ["tom", "groove"],
    "halftime_space": ["halftime", "space", "groove"],
    "shuffle_pocket": ["shuffle", "swing", "pocket"],
}

_FILL_FAMILY_IDS: Dict[str, str] = {
    "linear_burst": "Nasty-Lick-34",
    "triplet_turnaround": "Nasty-Lick-39",
    "tom_lift": "Nasty-Lick-24",
    "flam_tom": "rudiment_midi:flam_accent",
    "snare_roll": "rudiment_midi:single_stroke_roll",
    "cymbal_wash": "pattern:cymbal_wash",
    "snare_pickup": "rudiment_midi:drag_tap",
    "none": "fallback",
    "auto": "fallback",
}

_TIMEKEEPER_TAGS: Dict[str, List[str]] = {
    "ride": ["ride"],
    "mixed": ["ride", "hihat"],
    "hats": ["hihat", "hat"],
}

_STYLE_ALIASES: Dict[str, str] = {
    "live_recording": "rock",
    "blues": "shuffle",
}


_FALLBACK_FILL_STEPS: Dict[str, Dict[str, List[int]]] = {
    "Nasty-Lick-34": {
        "crash_1": [0],
        "kick": [0, 6, 10, 12],
        "snare_center": [2, 4, 6, 8, 10, 12, 14],
        "tom_high": [1, 3],
        "tom_mid": [9, 11],
        "tom_floor": [13, 15],
    },
    "Nasty-Lick-39": {
        "crash_1": [0],
        "kick": [0, 8, 12],
        "snare_center": [2, 4, 6, 10, 14],
        "tom_mid": [8, 9, 12, 13],
        "tom_floor": [15],
        "hihat_closed": [0, 4, 8, 12],
    },
    "Nasty-Lick-24": {
        "crash_1": [0],
        "kick": [0, 8],
        "snare_center": [1, 2, 4, 6, 8, 10, 12, 14],
        "tom_high": [3, 7, 11],
        "tom_floor": [15],
    },
    "rudiment_midi:flam_accent": {"snare_ghost": [0, 4, 8, 12], "snare_center": [1, 5, 9, 13]},
    "rudiment_midi:single_stroke_roll": {"snare_center": [0, 4, 8, 12], "snare_ghost": [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15]},
    "rudiment_midi:drag_tap": {"snare_ghost": [0, 1, 4, 5, 8, 9, 12, 13], "snare_center": [2, 6, 10, 14]},
    "pattern:cymbal_wash": {"crash_1": [0, 8], "ride_bow": [2, 6, 10, 14], "kick": [0, 8], "snare_center": [4, 12]},
    "fallback": {"crash_1": [0], "kick": [0, 8], "snare_center": [4, 12], "tom_mid": [13, 14], "tom_floor": [15]},
}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))



def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)



def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)



def _style_group(value: Any) -> str:
    raw = str(value or "rock").strip().lower()
    return _STYLE_ALIASES.get(raw, raw or "rock")



def _split_env_paths(raw: str) -> List[str]:
    if not raw:
        return []
    parts: List[str] = []
    for chunk in raw.replace(";", os.pathsep).replace(",", os.pathsep).split(os.pathsep):
        chunk = chunk.strip()
        if chunk:
            parts.append(chunk)
    return parts



def _manifest_candidates() -> List[Path]:
    out: List[Path] = []
    for env_name in (
        "DTK_GROOVE_MANIFEST_PATHS",
        "DTK_GROOVE_MANIFEST_PATH",
        "GROOVE_CATALOG_MANIFESTS",
        "GROOVE_CATALOG_MANIFEST",
    ):
        for part in _split_env_paths(str(os.getenv(env_name, ""))):
            p = Path(part)
            if p.exists():
                out.append(p)
    return out


@lru_cache(maxsize=1)
def _get_catalog() -> Optional[Any]:
    if GrooveCatalog is None:
        return None
    paths = _manifest_candidates()
    if not paths:
        return None
    try:
        if len(paths) == 1:
            return GrooveCatalog(paths[0])
        return GrooveCatalog(paths)
    except Exception:
        return None



def _collect_tags(selection: Mapping[str, Any], groove_family: str, timekeeper: str) -> List[str]:
    tags: List[str] = []
    tags.extend(_GROOVE_FAMILY_TAGS.get(groove_family, []))
    tags.extend(_TIMEKEEPER_TAGS.get(str(timekeeper or "").strip().lower(), []))
    for key in ("grooveCandidates", "fillCandidates"):
        vals = selection.get(key)
        if isinstance(vals, list):
            for item in vals:
                if isinstance(item, str):
                    tags.extend(_GROOVE_FAMILY_TAGS.get(item, []))
                    tags.append(item)
    deduped: List[str] = []
    for tag in tags:
        t = str(tag).strip().lower()
        if t and t not in deduped:
            deduped.append(t)
    return deduped



def _card_tags(card_dict: Mapping[str, Any]) -> List[str]:
    out: List[str] = []
    for tag in card_dict.get("tags") or []:
        t = str(tag).strip().lower()
        if t:
            out.append(t)
    for extra in (
        card_dict.get("style_group"),
        card_dict.get("style_detail"),
        card_dict.get("default_role"),
        card_dict.get("source"),
    ):
        if extra:
            out.append(str(extra).strip().lower())
    return out



def _score_card(
    card_dict: Mapping[str, Any],
    *,
    style_group: str,
    groove_family: str,
    timekeeper: str,
    bars: int,
    energy: float,
) -> float:
    score = 0.0
    tags = set(_card_tags(card_dict))

    if str(card_dict.get("default_role") or "").strip().lower() == "groove":
        score += 1.0
    if style_group and str(card_dict.get("style_group") or "").strip().lower() == style_group:
        score += 3.0
    family_tags = _GROOVE_FAMILY_TAGS.get(groove_family, [])
    score += 1.2 * sum(1 for tag in family_tags if tag in tags)
    score += 0.8 * sum(1 for tag in _TIMEKEEPER_TAGS.get(timekeeper, []) if tag in tags)

    try:
        if bars > 0 and card_dict.get("bars") is not None:
            card_bars = int(card_dict.get("bars"))
            if card_bars == bars:
                score += 1.0
            elif abs(card_bars - bars) == 1:
                score += 0.5
    except Exception:
        pass

    ride_hits = _safe_float(card_dict.get("ride_tip_hits_per_bar"), 0.0) + _safe_float(card_dict.get("ride_bell_hits_per_bar"), 0.0)
    hat_hits = _safe_float(card_dict.get("hat_hits_per_bar"), 0.0)
    if timekeeper == "ride":
        score += min(2.0, ride_hits * 0.2)
    elif timekeeper == "hats":
        score += min(2.0, hat_hits * 0.15)
    else:
        score += min(1.5, (ride_hits + hat_hits) * 0.1)

    complexity_tier = str(card_dict.get("complexity_tier") or "").strip().lower()
    if groove_family in {"pocket_backbeat", "halftime_space"} and complexity_tier == "simple":
        score += 0.8
    if groove_family in {"syncopated_kick", "linear_support", "tom_color"} and complexity_tier in {"intermediate", "complex"}:
        score += 0.8
    score += _clamp(energy) * _safe_float(card_dict.get("complexity_score"), 0.0)
    return float(score)



def _to_groove_asset(card: Any, groove_family: str, score: float) -> Dict[str, Any]:
    card_dict = card.to_dict() if hasattr(card, "to_dict") else dict(card)
    return {
        "assetId": card_dict.get("id"),
        "source": card_dict.get("source"),
        "title": card_dict.get("title"),
        "styleGroup": card_dict.get("style_group"),
        "bars": card_dict.get("bars"),
        "tempoBpm": card_dict.get("tempo_bpm"),
        "midiPath": card_dict.get("midi_path"),
        "audioPath": card_dict.get("audio_path"),
        "complexityTier": card_dict.get("complexity_tier"),
        "defaultRole": card_dict.get("default_role"),
        "matchedFamily": groove_family,
        "selectionScore": round(float(score), 4),
    }



def _fallback_groove_asset(groove_family: str, style_group: str, bars: int) -> Dict[str, Any]:
    return {
        "assetId": f"family:{groove_family or 'groove'}",
        "source": "sentient_family_fallback",
        "title": groove_family or "groove",
        "styleGroup": style_group,
        "bars": max(1, int(bars or 1)),
        "matchedFamily": groove_family,
        "selectionScore": 0.0,
    }



def _fill_asset(fill_family: str) -> Dict[str, Any]:
    fill_id = _FILL_FAMILY_IDS.get(fill_family, _FILL_FAMILY_IDS.get("auto", "fallback"))
    pattern_steps: Dict[str, List[int]] = {}
    resolved_id = fill_id
    if callable(get_fill_pattern):
        try:
            pattern, resolved_id = get_fill_pattern(fill_id)
            pattern_steps = dict(getattr(pattern, "steps", {}) or {})
        except Exception:
            pattern_steps = {}
    if not pattern_steps:
        pattern_steps = dict(_FALLBACK_FILL_STEPS.get(fill_id) or _FALLBACK_FILL_STEPS.get(resolved_id) or _FALLBACK_FILL_STEPS.get("fallback") or {})
    return {
        "assetId": fill_id,
        "resolvedId": resolved_id,
        "source": "fill_library",
        "matchedFamily": fill_family,
        "patternSteps": pattern_steps,
    }



def retrieve_phrase_assets(
    *,
    phrase_selection: Mapping[str, Any],
    section_type: str,
    style_group: str,
    timekeeper: str,
    bars: int,
    energy: float,
    groove_catalog: Optional[Any] = None,
    groove_limit: int = 5,
) -> Dict[str, Any]:
    groove_family = str(phrase_selection.get("grooveFamily") or "").strip().lower() or "pocket_backbeat"
    fill_family = str(phrase_selection.get("fillFamily") or "").strip().lower() or "auto"
    style_group = _style_group(style_group)
    timekeeper = str(timekeeper or "hats").strip().lower() or "hats"
    bars = max(1, _safe_int(bars, 1))

    tags = _collect_tags(phrase_selection, groove_family, timekeeper)
    query = groove_family.replace("_", " ")
    catalog = groove_catalog if groove_catalog is not None else _get_catalog()

    groove_candidates: List[Dict[str, Any]] = []
    if catalog is not None:
        try:
            cards = catalog.search(
                query=query,
                tags=tags,
                style_group=style_group,
                limit=max(3, int(groove_limit)),
            )
        except Exception:
            cards = []
        scored: List[tuple[float, Dict[str, Any]]] = []
        for card in cards:
            card_dict = card.to_dict() if hasattr(card, "to_dict") else dict(card)
            score = _score_card(card_dict, style_group=style_group, groove_family=groove_family, timekeeper=timekeeper, bars=bars, energy=energy)
            scored.append((score, _to_groove_asset(card, groove_family, score)))
        scored.sort(key=lambda item: item[0], reverse=True)
        groove_candidates = [item[1] for item in scored[: max(1, int(groove_limit))]]

    selected_groove = groove_candidates[0] if groove_candidates else _fallback_groove_asset(groove_family, style_group, bars)
    selected_fill = _fill_asset(fill_family)

    return {
        "sectionType": str(section_type or "section"),
        "selectedGrooveAsset": selected_groove,
        "grooveAssetCandidates": groove_candidates,
        "selectedFillAsset": selected_fill,
        "retrievalHints": {
            "styleGroup": style_group,
            "grooveFamily": groove_family,
            "fillFamily": fill_family,
            "timekeeper": timekeeper,
            "bars": bars,
            "tags": tags,
        },
    }
