from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence

from backend.dcsmpiano.drumtrack_builder_dcsmpiano import (
    build_drumtrack_for_dcsm,
    convert_dcsm_track_to_legacy_midi_notes,
)
from backend.dcsmpiano.drumtrack_schema import instrument_id_to_midi_pitch

_DEFAULT_STEPS_PER_BAR = 16
_DEFAULT_RESOLUTION_PPQ = 960
_DEFAULT_BEATS_PER_BAR = 4


@dataclass
class _SyntheticBar:
    start_time: float
    end_time: float
    meter: tuple[int, int]
    tempo_bpm: float


@dataclass
class _SyntheticSongMap:
    bars: List[_SyntheticBar]
    global_bpm_estimate: float


_INSTRUMENT_DURATION_SEC: Dict[str, float] = {
    "kick": 0.10,
    "snare_center": 0.12,
    "snare_ghost": 0.08,
    "snare_rim": 0.08,
    "hihat_closed": 0.06,
    "hihat_open": 0.20,
    "hihat_pedal": 0.05,
    "ride_bow": 0.12,
    "ride_bell": 0.12,
    "ride_edge": 0.12,
    "tom_high": 0.14,
    "tom_mid": 0.16,
    "tom_floor": 0.18,
    "crash_1": 0.30,
    "crash_2": 0.30,
}


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)


def _tempo_series(cfg: Mapping[str, Any], *, total_bars: int) -> List[float]:
    tempos = cfg.get("tempos") or [cfg.get("tempo", 120.0)]
    if not isinstance(tempos, Sequence) or not tempos:
        tempos = [120.0]
    clean = [max(30.0, min(320.0, _safe_float(t, 120.0))) for t in tempos]
    if len(clean) >= total_bars:
        return clean[:total_bars]
    out: List[float] = []
    while len(out) < total_bars:
        out.extend(clean)
    return out[:total_bars]


def build_synthetic_songmap_from_spec(spec: Mapping[str, Any], cfg: Mapping[str, Any]) -> _SyntheticSongMap:
    phrases = spec.get("phrases") if isinstance(spec.get("phrases"), list) else []
    max_bar = 0
    for phrase in phrases:
        if not isinstance(phrase, Mapping):
            continue
        max_bar = max(max_bar, _safe_int(phrase.get("barEnd"), 0))
    total_bars = max(1, max_bar + 1)
    tempos = _tempo_series(cfg, total_bars=total_bars)

    bars: List[_SyntheticBar] = []
    cursor = 0.0
    for idx in range(total_bars):
        bpm = tempos[idx]
        bar_len_sec = (_DEFAULT_BEATS_PER_BAR * 60.0) / max(1e-6, bpm)
        bars.append(
            _SyntheticBar(
                start_time=cursor,
                end_time=cursor + bar_len_sec,
                meter=(_DEFAULT_BEATS_PER_BAR, 4),
                tempo_bpm=bpm,
            )
        )
        cursor += bar_len_sec

    avg_bpm = sum(tempos) / max(1, len(tempos))
    return _SyntheticSongMap(bars=bars, global_bpm_estimate=avg_bpm)


def _event_flags(instrument_id: str, velocity: int, aspect: str, source: str) -> Dict[str, bool]:
    inst = str(instrument_id or "")
    aspect = str(aspect or "")
    source = str(source or "").lower()
    return {
        "isGhost": inst == "snare_ghost" or velocity <= 58,
        "isAccent": inst.startswith("crash") or inst == "ride_bell" or velocity >= 110,
        "isFlam": "flam" in source or "flam" in aspect,
        "isDrag": "drag" in source or "drag" in aspect,
    }


def phrase_pattern_events_to_internal_events(
    spec: Mapping[str, Any],
    cfg: Mapping[str, Any],
    *,
    steps_per_bar: int = _DEFAULT_STEPS_PER_BAR,
) -> List[Dict[str, Any]]:
    songmap = build_synthetic_songmap_from_spec(spec, cfg)
    phrases = spec.get("phrases") if isinstance(spec.get("phrases"), list) else []

    internal: List[Dict[str, Any]] = []
    for phrase in phrases:
        if not isinstance(phrase, Mapping):
            continue
        phrase_bar_start = _safe_int(phrase.get("barStart"), 0)
        pattern = phrase.get("phraseEventPattern") if isinstance(phrase.get("phraseEventPattern"), Mapping) else None
        if not isinstance(pattern, Mapping):
            continue
        events = pattern.get("events") if isinstance(pattern.get("events"), list) else []
        for ev in events:
            if not isinstance(ev, Mapping):
                continue
            rel_bar = _safe_int(ev.get("barOffset"), 0)
            abs_bar = max(0, phrase_bar_start + rel_bar)
            if abs_bar >= len(songmap.bars):
                continue
            bar = songmap.bars[abs_bar]
            step_index = max(0, min(steps_per_bar - 1, _safe_int(ev.get("stepIndex"), 0)))
            frac = step_index / float(steps_per_bar)
            t_sec = bar.start_time + (bar.end_time - bar.start_time) * frac
            instrument_id = str(ev.get("instrumentId") or "snare_center")
            velocity = max(1, min(127, _safe_int(ev.get("velocity"), 96)))
            duration = _INSTRUMENT_DURATION_SEC.get(instrument_id, 0.10)
            aspect = str(ev.get("aspect") or "groove")
            source = str(ev.get("source") or "pattern")
            flags = _event_flags(instrument_id, velocity, aspect, source)
            internal.append(
                {
                    "time_sec": float(t_sec),
                    "length_sec": float(duration),
                    "instrument_id": instrument_id,
                    "midi_pitch": int(instrument_id_to_midi_pitch(instrument_id)),
                    "velocity": velocity,
                    **flags,
                }
            )
    internal.sort(key=lambda e: (float(e["time_sec"]), str(e["instrument_id"]), int(e["midi_pitch"])))
    return internal


def build_dcsm_payload_from_sentient_spec(
    *,
    spec: Mapping[str, Any],
    cfg: Mapping[str, Any],
    style_id: Optional[str] = None,
    resolution_ppq: int = _DEFAULT_RESOLUTION_PPQ,
) -> Dict[str, Any]:
    songmap = build_synthetic_songmap_from_spec(spec, cfg)
    internal_events = phrase_pattern_events_to_internal_events(spec, cfg)
    style_id = str(style_id or spec.get("styleId") or cfg.get("style") or "rock")
    if not internal_events:
        return {
            "available": False,
            "reason": "no_phrase_event_patterns",
            "internalEventCount": 0,
            "resolution_ppq": int(resolution_ppq),
        }

    track = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id=style_id,
        performance_spec=dict(spec),
        resolution_ppq=int(resolution_ppq),
    )
    legacy_notes = convert_dcsm_track_to_legacy_midi_notes(track, resolution_ppq=int(resolution_ppq))
    drum_track = {
        "track_id": track.track_id,
        "style_id": track.style_id,
        "resolution_ppq": track.resolution_ppq,
        "notes": [n.__dict__.copy() for n in track.notes],
        "performance_spec": dict(spec),
    }
    return {
        "available": True,
        "resolution_ppq": int(resolution_ppq),
        "internalEventCount": len(internal_events),
        "drum_track": drum_track,
        "legacy_midi_notes": legacy_notes,
    }
