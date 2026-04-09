from backend.drummerbrain.render_take_sentient import build_sentient_take_bundle


def test_uses_existing_dcsm_payload_without_rebuild():
    spec = {
        "styleId": "rock",
        "dcsmRenderPayload": {
            "available": True,
            "resolution_ppq": 960,
            "drum_track": {
                "track_id": "t1",
                "style_id": "rock",
                "resolution_ppq": 960,
                "notes": [{"barIndex": 0, "tickInBar": 0, "tickLength": 120}],
                "performance_spec": {"quantizationBase": "16th"},
            },
            "legacy_midi_notes": [{"time": 0.0, "note": 36, "velocity": 100, "drum": "kick", "length": 0.1}],
        },
    }

    out = build_sentient_take_bundle(spec=spec, cfg={})
    assert out["available"] is True
    assert out["source"] == "existing_dcsm_payload"
    assert out["drum_track"]["track_id"] == "t1"
    assert len(out["midi_notes"]) == 1


def test_builds_plugin_render_when_plugin_requested(monkeypatch):
    import backend.drummerbrain.render_take_sentient as mod

    captured = {}

    def fake_renderer(payload):
        captured.update(payload)
        return {"plugin": payload["plugin"], "midi_base64": "ZmFrZQ==", "ticks_per_beat": payload["ppq"]}

    monkeypatch.setattr(mod, "render_articulated_notes_to_midi", fake_renderer)

    spec = {
        "styleId": "rock",
        "dcsmRenderPayload": {
            "available": True,
            "resolution_ppq": 960,
            "drum_track": {"track_id": "t1", "notes": [], "performance_spec": {}},
            "legacy_midi_notes": [
                {"time": 0.5, "note": 38, "velocity": 96, "drum": "snare_center", "length": 0.2}
            ],
        },
    }

    out = build_sentient_take_bundle(spec=spec, cfg={"pluginTarget": "jamstix", "tempo": 120})
    assert out["plugin_render"]["plugin"] == "jamstix"
    assert captured["plugin"] == "jamstix"
    assert len(captured["notes"]) == 1
    assert captured["notes"][0]["articulationId"] == "snare_center"
