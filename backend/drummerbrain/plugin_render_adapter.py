from __future__ import annotations

from typing import Any, Dict, Mapping


def build_plugin_render_payload(drum_track: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "midi": list(drum_track.get("midi_notes", []) or []),
        "tempo": drum_track.get("tempo", 120),
        "ppq": drum_track.get("ppq", 480),
    }


__all__ = ["build_plugin_render_payload"]
