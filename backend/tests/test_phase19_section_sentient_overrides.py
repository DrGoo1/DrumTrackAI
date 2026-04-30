from backend.drummerbrain.section_sentient_overrides import (
    build_section_profile_map,
    derive_orchestration_bias,
    derive_time_feel,
    derive_transition_bias,
    has_sentient_identity,
    resolve_section_profile,
)


def test_resolve_section_profile_prefers_sentient_override():
    base = {"feel": "straight", "humanness": 0.3}
    section = {
        "name": "chorus",
        "sentientProfile": {
            "feel": "laid_back",
            "transition_model": {"groove_to_fill": 0.8},
            "timing_profiles": [{"instrument": "snare"}],
        },
    }
    resolved = resolve_section_profile(section, base)
    assert resolved["feel"] == "laid_back"
    assert has_sentient_identity(resolved) is True
    assert resolved["humanness"] == 0.3


def test_build_section_profile_map_keys_by_index_and_type():
    sections = [
        {"name": "verse", "drummerProfile": {"feel": "straight"}},
        {"name": "chorus", "sentientProfile": {"profiles": [{"instrumentId": "ride_bow"}]}},
    ]
    mapping = build_section_profile_map(sections, {"feel": "straight"})
    assert "0:verse" in mapping
    assert "1:chorus" in mapping
    assert mapping["1:chorus"]["profiles"][0]["instrumentId"] == "ride_bow"


def test_transition_and_orchestration_biases_follow_profile_content():
    profile = {
        "fills_per_min": 2.4,
        "transition_model": {"groove_to_fill": 0.75, "fill_to_groove": 0.9},
        "humanness": 0.8,
        "pocket_tightness": 0.35,
        "instrument_shares": {"ride": 0.42, "hihat": 0.18, "crash": 0.20},
    }
    transition = derive_transition_bias(profile)
    orch = derive_orchestration_bias(profile)
    assert transition["fill_probability_bias"] > 0.7
    assert transition["recovery_confidence"] > 0.7
    assert orch["preferred_timekeeper"] == "ride"
    assert orch["ride_bell_probability"] > 0.2


def test_derive_time_feel_uses_valid_override_and_fallback():
    assert derive_time_feel({"feel": "shuffle"}, "straight") == "shuffle"
    assert derive_time_feel({"feel": "unknown"}, "laid_back") == "laid_back"
