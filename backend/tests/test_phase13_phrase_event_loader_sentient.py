from __future__ import annotations

from backend.drummerbrain.phrase_event_loader_sentient import build_phrase_event_pattern


def test_build_phrase_event_pattern_uses_family_fallback_and_fill_overlay():
    phrase_assets = {
        "selectedGrooveAsset": {"assetId": "family:ride_lead", "matchedFamily": "ride_lead"},
        "selectedFillAsset": {
            "assetId": "Nasty-Lick-34",
            "patternSteps": {"snare_center": [12, 14], "tom_floor": [15]},
        },
    }
    out = build_phrase_event_pattern(
        phrase_assets=phrase_assets,
        phrase_selection={"grooveFamily": "ride_lead"},
        bars=2,
    )
    assert out["sourceGrooveAssetId"] == "family:ride_lead"
    assert out["bars"] == 2
    assert out["eventSummary"]["fillEvents"] == 3
    assert any(e["instrumentId"] == "ride_bow" and e["barOffset"] == 0 for e in out["events"])
    assert any(e["instrumentId"] == "ride_bow" and e["barOffset"] == 1 for e in out["events"])
    assert any(
        e["instrumentId"] == "tom_floor" and e["barOffset"] == 1 and e["aspect"] == "fill" for e in out["events"]
    )


def test_inline_pattern_steps_take_priority_over_family_fallback():
    phrase_assets = {
        "selectedGrooveAsset": {
            "assetId": "egmd:test_inline",
            "matchedFamily": "pocket_backbeat",
            "patternSteps": {"kick": [0, 8], "snare_center": [4, 12]},
        }
    }
    out = build_phrase_event_pattern(
        phrase_assets=phrase_assets,
        phrase_selection={"grooveFamily": "ride_lead"},
        bars=1,
    )
    events = out["events"]
    assert out["sourceGrooveAssetId"] == "egmd:test_inline"
    assert len(events) == 4
    assert [e["instrumentId"] for e in events] == ["kick", "snare_center", "kick", "snare_center"]
