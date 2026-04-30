import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

from mido import Message, MidiFile, MidiTrack, MetaMessage

from .articulation_mapper import ArticulationMapper


def _load_mapper(plugin: str) -> ArticulationMapper:
    base = Path(__file__).resolve().parent.parent / "config" / "articulation_maps"
    # Simple mapping; can be extended with more aliases
    fname = {
        "jamstix": "jamstix.json",
        "sd3": "superior_drummer3.json",
        "ssd5": "ssd5.json",
    }.get(plugin, "jamstix.json")
    return ArticulationMapper(base / fname)


def render_articulated_notes_to_midi(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Render logical drum notes + articulationId to plugin-specific MIDI.

    Expected payload shape:
      {
        "plugin": "jamstix" | "sd3" | "ssd5" | ...,
        "advancedArticulations": bool,
        "ppq": 480,
        "notes": [
          {"t0": int, "t1": int, "pitch": int, "vel": int, "chan": int,
           "articulationId": str | None},
          ...
        ]
      }
    """
    plugin = str(payload.get("plugin", "jamstix"))
    ppq = int(payload.get("ppq", 480)) or 480
    tempo_bpm = float(payload.get("tempo_bpm", 120.0) or 120.0)
    advanced = bool(payload.get("advancedArticulations", False))
    notes_in: List[Dict[str, Any]] = list(payload.get("notes", []))

    mapper = _load_mapper(plugin)

    mid = MidiFile(type=1)
    mid.ticks_per_beat = ppq

    track = MidiTrack()
    mid.tracks.append(track)

    # Constant tempo (caller-provided). Tempo meta message uses microseconds per beat.
    try:
        tempo_bpm = max(1e-3, float(tempo_bpm))
    except Exception:
        tempo_bpm = 120.0
    tempo_us = int(round(60_000_000.0 / tempo_bpm))
    track.append(MetaMessage("set_tempo", tempo=tempo_us, time=0))

    # Sort by start tick
    events: List[Dict[str, Any]] = []
    for n in notes_in:
        t0 = int(n.get("t0", 0))
        t1 = int(n.get("t1", t0 + ppq // 4))
        vel = int(n.get("vel", 100))
        chan = int(n.get("chan", 9))
        art_id = n.get("articulationId")

        # Look up articulation mapping (note + optional CCs)
        art = mapper.get_articulation(art_id) if art_id else None
        note_num = int(art.get("note", n.get("pitch", 36))) if art else int(n.get("pitch", 36))
        ccs = list(art.get("cc", [])) if (advanced and art) else []
        aftertouch = int(art.get("aftertouch")) if (advanced and art and art.get("aftertouch") is not None) else None

        # Program any static CC state at note-on
        events.append({
            "tick": t0,
            "kind": "note_on",
            "note": note_num,
            "vel": vel,
            "chan": chan,
            "ccs": ccs,
            "aftertouch": aftertouch,
        })
        events.append({
            "tick": t1,
            "kind": "note_off",
            "note": note_num,
            "vel": 0,
            "chan": chan,
            "ccs": [],
            "aftertouch": None,
        })

    events.sort(key=lambda e: e["tick"])

    last_tick = 0
    for ev in events:
        dt = max(0, int(ev["tick"]) - last_tick)
        last_tick = int(ev["tick"])
        # Emit CCs first (delta time applied to first one)
        first_cc = True
        for cc_spec in ev.get("ccs", []):
            ctrl = int(cc_spec.get("controller", 0))
            val = int(cc_spec.get("value", 0))
            track.append(
                Message(
                    "control_change",
                    control=ctrl,
                    value=val,
                    channel=ev["chan"],
                    time=dt if first_cc else 0,
                )
            )
            first_cc = False
            dt = 0

        # Optional per-note aftertouch (polytouch) next
        at = ev.get("aftertouch")
        if at is not None:
            track.append(
                Message(
                    "polytouch",
                    note=int(ev["note"]),
                    value=int(at),
                    channel=ev["chan"],
                    time=dt if first_cc else 0,
                )
            )
            first_cc = False
            dt = 0

        # Then the note event
        msg_type = "note_on" if ev["kind"] == "note_on" else "note_off"
        track.append(
            Message(
                msg_type,
                note=int(ev["note"]),
                velocity=int(ev["vel"]),
                channel=ev["chan"],
                time=dt if first_cc else 0,
            )
        )

    # Ensure track ends cleanly
    track.append(MetaMessage("end_of_track", time=0))

    buf = BytesIO()
    mid.save(file=buf)
    midi_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return {
        "plugin": plugin,
        "midi_base64": midi_b64,
        "ticks_per_beat": ppq,
    }
