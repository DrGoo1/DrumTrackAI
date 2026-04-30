
from backend.backend.drummerbrain.rudiment_library_extended import rudiment_event_map
from backend.backend.drummerbrain.rudiment_detector_extended import detect_extended_rudiments
from backend.backend.drummerbrain.rudiment_phrase_generator_extended import choose_extended_rudiment_phrase

def test_library_contains_expected_families():
    m = rudiment_event_map()
    assert "six_stroke_roll" in m
    assert "swiss_triplet" in m
    assert "linear_hybrid" in m

def test_choose_extended_phrase_prefers_chorus_six_stroke():
    section = {"sectionType": "chorus", "energy": 0.8}
    profile = {"usage_rate": {"six_stroke_roll": 0.7, "linear_hybrid": 0.3}}
    result = choose_extended_rudiment_phrase(section, profile)
    assert result["rudimentType"] == "six_stroke_roll"
    assert len(result["events"]) > 0

def test_extended_detector_finds_hybrid_like_pattern():
    events = [
        {"time": 0.0, "instrument": "kick", "hand": "R"},
        {"time": 0.1, "instrument": "snare", "hand": "L"},
        {"time": 0.2, "instrument": "hihat", "hand": "R"},
        {"time": 0.3, "instrument": "tom1", "hand": "L"},
    ]
    out = detect_extended_rudiments(events)
    assert len(out) >= 1
