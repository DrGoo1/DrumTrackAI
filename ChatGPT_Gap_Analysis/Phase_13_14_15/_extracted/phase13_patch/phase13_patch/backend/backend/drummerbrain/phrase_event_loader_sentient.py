from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

try:  # pragma: no cover - optional runtime dependency
    import mido  # type: ignore
except Exception:  # pragma: no cover
    mido = None

_STEPS_PER_BAR = 16

_PITCH_TO_INSTRUMENT: Dict[int, str] = {
    35: "kick", 36: "kick",
    37: "snare_ghost", 38: "snare_center", 40: "snare_center",
    42: "hihat_closed", 44: "hihat_pedal", 46: "hihat_open",
    41: "tom_floor", 43: "tom_floor", 45: "tom_mid", 47: "tom_mid", 48: "tom_high", 50: "tom_high",
    49: "crash_1", 51: "ride_bow", 52: "crash_2", 53: "ride_bell", 55: "crash_2", 57: "crash_1", 59: "ride_bow",
}

_GROOVE_FAMILY_PATTERNS: Dict[str, Dict[str, List[int]]] = {
    "ride_lead": {
        "ride_bow": [0, 2, 4, 6, 8, 10, 12, 14],
        "kick": [0, 6, 8, 12],
        "snare_center": [4, 12],
    },
    "pocket_backbeat": {
        "hihat_closed": list(range(0, 16, 2)),
        "kick": [0, 5, 8, 11],
        "snare_center": [4, 12],
    },
    "syncopated_kick": {
        "hihat_closed": list(range(0, 16, 2)),
        "kick": [0, 3, 6, 10, 13],
        "snare_center": [4, 12],
    },
    "open_hat_lift": {
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12],
        "hihat_open": [14],
        "kick": [0, 6, 8, 11],
        "snare_center": [4, 12],
    },
    "shuffle_pocket": {
        "ride_bow": [0, 3, 4, 7, 8, 11, 12, 15],
        "kick": [0, 6, 10],
        "snare_center": [4, 12],
    },
    "halftime_space": {
        "hihat_closed": list(range(0, 16, 2)),
        "kick": [0, 6, 10],
        "snare_center": [8],
    },
    "linear_support": {
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
        "kick": [0, 7, 10],
        "snare_center": [4, 12],
        "tom_mid": [15],
    },
}

_DEFAULT_GROOVE = _GROOVE_FAMILY_PATTERNS["pocket_backbeat"]

_VELOCITY_BY_INSTRUMENT: Dict[str, int] = {
    "kick": 104,
    "snare_center": 112,
    "snare_ghost": 52,
    "hihat_closed": 78,
    "hihat_open": 84,
    "hihat_pedal": 64,
    "ride_bow": 80,
    "ride_bell": 96,
    "tom_high": 94,
    "tom_mid": 98,
    "tom_floor": 102,
    "crash_1": 108,
    "crash_2": 108,
}


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return int(default)



def _family_from_assets(phrase_assets: Mapping[str, Any], phrase_selection: Mapping[str, Any]) -> str:
    groove = phrase_assets.get("selectedGrooveAsset") if isinstance(phrase_assets, Mapping) else None
    if isinstance(groove, Mapping):
        for key in ("matchedFamily", "family"):
            raw = groove.get(key)
            if raw:
                return str(raw).strip().lower()
        aid = str(groove.get("assetId") or "").strip().lower()
        if aid.startswith("family:"):
            return aid.split(":", 1)[1]
    fam = phrase_selection.get("grooveFamily") if isinstance(phrase_selection, Mapping) else None
    return str(fam or "pocket_backbeat").strip().lower()



def _fill_steps(phrase_assets: Mapping[str, Any]) -> Dict[str, List[int]]:
    fill = phrase_assets.get("selectedFillAsset") if isinstance(phrase_assets, Mapping) else None
    if not isinstance(fill, Mapping):
        return {}
    raw = fill.get("patternSteps")
    out: Dict[str, List[int]] = {}
    if isinstance(raw, Mapping):
        for inst, vals in raw.items():
            if isinstance(vals, list):
                out[str(inst)] = [int(v) for v in vals if isinstance(v, (int, float))]
    return out



def _normalize_step_events(step_map: Mapping[str, List[int]], *, bars: int, aspect: str, source: str, start_bar_offset: int = 0) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    bars = max(1, int(bars))
    for bar_offset in range(bars):
        for inst, steps in step_map.items():
            base_vel = _VELOCITY_BY_INSTRUMENT.get(str(inst), 88)
            for step in steps:
                step_i = int(step) % _STEPS_PER_BAR
                events.append({
                    "barOffset": start_bar_offset + bar_offset,
                    "stepIndex": step_i,
                    "instrumentId": str(inst),
                    "velocity": int(base_vel),
                    "source": source,
                    "aspect": aspect,
                })
    events.sort(key=lambda e: (int(e["barOffset"]), int(e["stepIndex"]), str(e["instrumentId"])))
    return events



def _events_from_midi_path(midi_path: str, *, target_bars: int, source: str) -> List[Dict[str, Any]]:
    if not midi_path or mido is None:
        return []
    try:
        mid = mido.MidiFile(midi_path)
    except Exception:
        return []

    tpb = int(getattr(mid, "ticks_per_beat", 480) or 480)
    step_ticks = max(1, int(round(tpb / 4)))
    raw_events: List[Dict[str, Any]] = []
    max_bar = 0
    for track in mid.tracks:
        abs_ticks = 0
        for msg in track:
            abs_ticks += int(getattr(msg, "time", 0) or 0)
            if getattr(msg, "type", None) != "note_on" or not getattr(msg, "velocity", 0):
                continue
            if getattr(msg, "channel", None) not in (None, 9):
                continue
            note = int(getattr(msg, "note", 0) or 0)
            inst = _PITCH_TO_INSTRUMENT.get(note)
            if not inst:
                continue
            total_steps = int(round(abs_ticks / float(step_ticks)))
            bar_offset = max(0, total_steps // _STEPS_PER_BAR)
            step_index = total_steps % _STEPS_PER_BAR
            max_bar = max(max_bar, bar_offset)
            raw_events.append({
                "barOffset": bar_offset,
                "stepIndex": step_index,
                "instrumentId": inst,
                "velocity": int(getattr(msg, "velocity", 96) or 96),
                "source": source,
                "aspect": "groove",
            })
    if not raw_events:
        return []
    source_bars = max(1, max_bar + 1)
    target_bars = max(1, int(target_bars))
    if source_bars == target_bars:
        return sorted(raw_events, key=lambda e: (e["barOffset"], e["stepIndex"], e["instrumentId"]))
    out: List[Dict[str, Any]] = []
    for bar in range(target_bars):
        src_bar = bar % source_bars
        for ev in raw_events:
            if int(ev["barOffset"]) != src_bar:
                continue
            e2 = dict(ev)
            e2["barOffset"] = bar
            out.append(e2)
    out.sort(key=lambda e: (e["barOffset"], e["stepIndex"], e["instrumentId"]))
    return out



def build_phrase_event_pattern(
    *,
    phrase_assets: Optional[Mapping[str, Any]],
    phrase_selection: Optional[Mapping[str, Any]] = None,
    bars: int = 1,
) -> Dict[str, Any]:
    phrase_assets = dict(phrase_assets or {})
    phrase_selection = dict(phrase_selection or {})
    bars = max(1, _safe_int(bars, 1))

    groove = phrase_assets.get("selectedGrooveAsset") if isinstance(phrase_assets, Mapping) else None
    groove_events: List[Dict[str, Any]] = []
    groove_asset_id = None
    if isinstance(groove, Mapping):
        groove_asset_id = groove.get("assetId")
        inline_steps = groove.get("patternSteps")
        if isinstance(inline_steps, Mapping):
            groove_events = _normalize_step_events(inline_steps, bars=bars, aspect="groove", source=str(groove_asset_id or "inline"))
        else:
            groove_events = _events_from_midi_path(str(groove.get("midiPath") or ""), target_bars=bars, source=str(groove_asset_id or "midi"))

    if not groove_events:
        family = _family_from_assets(phrase_assets, phrase_selection)
        base_steps = _GROOVE_FAMILY_PATTERNS.get(family, _DEFAULT_GROOVE)
        groove_asset_id = groove_asset_id or f"family:{family}"
        groove_events = _normalize_step_events(base_steps, bars=bars, aspect="groove", source=str(groove_asset_id))

    fill_steps = _fill_steps(phrase_assets)
    fill_asset = phrase_assets.get("selectedFillAsset") if isinstance(phrase_assets, Mapping) else None
    fill_asset_id = fill_asset.get("assetId") if isinstance(fill_asset, Mapping) else None
    fill_events: List[Dict[str, Any]] = []
    if fill_steps:
        fill_events = _normalize_step_events(fill_steps, bars=1, aspect="fill", source=str(fill_asset_id or "fill"), start_bar_offset=max(0, bars - 1))

    events = groove_events + fill_events
    events.sort(key=lambda e: (int(e["barOffset"]), int(e["stepIndex"]), str(e["instrumentId"]), str(e["aspect"])))

    instrument_counts: Dict[str, int] = {}
    for ev in events:
        inst = str(ev.get("instrumentId") or "")
        instrument_counts[inst] = instrument_counts.get(inst, 0) + 1

    return {
        "sourceGrooveAssetId": groove_asset_id,
        "sourceFillAssetId": fill_asset_id,
        "resolution": "16th",
        "bars": bars,
        "events": events,
        "eventSummary": {
            "totalEvents": len(events),
            "grooveEvents": len(groove_events),
            "fillEvents": len(fill_events),
            "instrumentCounts": instrument_counts,
        },
    }
