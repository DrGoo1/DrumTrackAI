from fastapi.testclient import TestClient

from llm_service.app import app


def test_generate_drums_default_route_prefers_sentient(monkeypatch):
    client = TestClient(app)

    def fake_render(req):
        return {
            "ok": True,
            "spec": {"styleId": "rock"},
            "drum_track": {"notes": [{"barIndex": 0, "tickInBar": 0, "tickLength": 120}]},
            "midi_notes": [],
            "plugin_render": None,
            "metadata": {"render_source": "sentient"},
        }

    monkeypatch.setattr("llm_service.app.render_sentient_take", fake_render)
    response = client.post(
        "/api/generate-drums",
        json={
            "sectionId": "verse_1",
            "tempo": 112,
            "drummer_profile": {
                "timing_profiles": [{"instrument": "snare", "mean_offset_ms": 9.0}],
                "dynamic_profiles": [{"instrument": "kick", "role": "backbeat", "velocity_mean": 96.0}],
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["metadata"]["sentient_routed"] is True
    assert payload["metadata"]["preferred_endpoint"] == "/v1/render_sentient_take"
    assert payload["drum_track"]["notes"][0]["barIndex"] == 0
