from __future__ import annotations

import json
from pathlib import Path

from backend.backend.drummerbrain.sentient_profile_registry import build_sentient_profile_response, load_sentient_profile


def test_load_sentient_profile_from_export_root(tmp_path, monkeypatch):
    root = tmp_path / "database" / "drummer_profiles_generated" / "bonham_like"
    root.mkdir(parents=True)
    payload = {
        "drummer_id": "bonham_like",
        "profiles": [{"instrumentId": "kick", "microTiming": {"subdivisionOffsetsMs": [4, 1, -2, 0]}}],
        "transition_model": {"groove_to_fill": 0.4},
    }
    (root / "drummer_profile.json").write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setenv("SENTIENT_PROFILE_ROOTS", str(tmp_path / "database" / "drummer_profiles_generated"))

    loaded = load_sentient_profile("bonham_like")
    assert loaded is not None
    assert loaded["publicDrummerId"] == "bonham_like"
    assert loaded["transition_model"]["groove_to_fill"] == 0.4


def test_build_sentient_profile_response_not_found(tmp_path, monkeypatch):
    monkeypatch.setenv("SENTIENT_PROFILE_ROOTS", str(tmp_path / "missing"))
    resp = build_sentient_profile_response("nobody")
    assert resp["ok"] is True
    assert resp["found"] is False
    assert resp["profile"] is None
