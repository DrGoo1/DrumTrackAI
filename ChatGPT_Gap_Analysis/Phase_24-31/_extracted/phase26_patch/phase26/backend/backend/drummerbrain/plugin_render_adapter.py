def build_plugin_render_payload(drum_track):
    return {
        "midi": drum_track.get("midi_notes", []),
        "tempo": drum_track.get("tempo", 120),
        "ppq": drum_track.get("ppq", 480)
    }
