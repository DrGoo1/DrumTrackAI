from backend.drummerbrain.sentient_request_routing import has_sentient_profile, normalize_generate_drums_payload


def test_has_sentient_profile_detects_rich_profile():
    payload = {
        "sectionId": "verse_a",
        "tempo": 118,
        "drummer_profile": {
            "timing_profiles": [{"instrument": "snare", "mean_offset_ms": 12.0}],
            "transition_model": {"groove_to_fill": 0.44},
        },
    }
    assert has_sentient_profile(payload) is True


def test_normalize_generate_drums_payload_builds_cfg_and_songmap():
    payload = {
        "sectionId": "chorus_1",
        "sectionName": "chorus",
        "tempo": 124,
        "startMeasure": 8,
        "endMeasure": 11,
        "drummer_profile": {"profiles": [{"instrument": "kick"}]},
    }
    normalized = normalize_generate_drums_payload(payload)
    assert normalized["cfg"]["tempo"] == 124
    assert normalized["cfg"]["songSections"][0]["bars"] == 4
    assert normalized["songmap_summary"]["sections"][0]["sectionId"] == "chorus_1"
