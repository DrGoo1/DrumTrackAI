from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

try:
    from backend.drummerbrain.performance_to_dcsm_sentient import build_dcsm_payload_from_sentient_spec
except Exception:  # pragma: no cover - optional dependency from Phase 14
    build_dcsm_payload_from_sentient_spec = None

try:
    from backend.render_to_plugin_midi import render_articulated_notes_to_midi
except Exception:  # pragma: no cover - optional in lightweight envs
    render_articulated_notes_to_midi = None


_DEF_PPQ = 960


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)



def _extract_existing_dcsm_payload(spec: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    payload = spec.get("dcsmRenderPayload")
    if isinstance(payload, dict) and payload.get("available"):
        return dict(payload)
    return None



def _legacy_notes_to_plugin_notes(
    legacy_notes: List[Dict[str, Any]],
    *,
    ppq: int,
    tempo_bpm: float,
) -> List[Dict[str, Any]]:
    ticks_per_second = (ppq * tempo_bpm) / 60.0
    out: List[Dict[str, Any]] = []
    for note in legacy_notes:
        if not isinstance(note, dict):
            continue
        t_sec = _safe_float(note.get("time"), 0.0)
        length_sec = max(0.01, _safe_float(note.get("length"), 0.10))
        t0 = int(round(t_sec * ticks_per_second))
        t1 = max(t0 + 1, int(round((t_sec + length_sec) * ticks_per_second)))
        pitch = int(note.get("note") or 38)
        vel = int(note.get("velocity") or 96)
        drum = str(note.get("drum") or "")
        out.append(
            {
                "t0": t0,
                "t1": t1,
                "pitch": pitch,
                "vel": vel,
                "chan": 9,
                "articulationId": drum or None,
            }
        )
    return out



def build_sentient_take_bundle(
    *,
    spec: Mapping[str, Any],
    cfg: Mapping[str, Any],
) -> Dict[str, Any]:
    """Resolve the renderable sentient take for frontend + plugin paths.

    Output keys:
      - available
      - source: existing_dcsm_payload | rebuilt_from_phrase_patterns | unavailable
      - drum_track
      - midi_notes
      - plugin_render
      - resolution_ppq
    """

    spec_dict = dict(spec or {})
    cfg_dict = dict(cfg or {})

    payload = _extract_existing_dcsm_payload(spec_dict)
    source = "existing_dcsm_payload"

    if payload is None and callable(build_dcsm_payload_from_sentient_spec):
        payload = build_dcsm_payload_from_sentient_spec(
            spec=spec_dict,
            cfg=cfg_dict,
            style_id=str(spec_dict.get("styleId") or cfg_dict.get("style") or "rock"),
            resolution_ppq=int(cfg_dict.get("resolutionPpq") or _DEF_PPQ),
        )
        source = "rebuilt_from_phrase_patterns"

    if not isinstance(payload, dict) or not payload.get("available"):
        return {
            "available": False,
            "source": "unavailable",
            "reason": (payload or {}).get("reason", "no_dcsm_payload"),
            "resolution_ppq": int(cfg_dict.get("resolutionPpq") or _DEF_PPQ),
            "drum_track": None,
            "midi_notes": [],
            "plugin_render": None,
        }

    drum_track = payload.get("drum_track") if isinstance(payload.get("drum_track"), dict) else None
    midi_notes = payload.get("legacy_midi_notes") if isinstance(payload.get("legacy_midi_notes"), list) else []
    resolution_ppq = int(payload.get("resolution_ppq") or cfg_dict.get("resolutionPpq") or _DEF_PPQ)

    plugin_name = str(
        cfg_dict.get("pluginTarget")
        or cfg_dict.get("plugin")
        or cfg_dict.get("pluginName")
        or ""
    ).strip().lower()
    plugin_render = None

    if plugin_name and callable(render_articulated_notes_to_midi):
        tempo_bpm = _safe_float(cfg_dict.get("tempo"), 120.0)
        notes = _legacy_notes_to_plugin_notes(midi_notes, ppq=resolution_ppq, tempo_bpm=tempo_bpm)
        plugin_render = render_articulated_notes_to_midi(
            {
                "plugin": plugin_name,
                "advancedArticulations": bool(cfg_dict.get("advancedArticulations", False)),
                "ppq": resolution_ppq,
                "tempo_bpm": tempo_bpm,
                "notes": notes,
            }
        )

    return {
        "available": True,
        "source": source,
        "resolution_ppq": resolution_ppq,
        "drum_track": drum_track,
        "midi_notes": midi_notes,
        "plugin_render": plugin_render,
    }
