from backend.backend.drummerbrain.plugin_render_adapter import build_plugin_render_payload

def test_plugin_payload():
    dt = {"midi_notes":[1,2,3], "tempo":120}
    p = build_plugin_render_payload(dt)
    assert "midi" in p
