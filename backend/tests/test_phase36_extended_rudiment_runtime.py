
from backend.backend.drummerbrain.rudiment_runtime_policy_extended import should_use_extended_rudiments
from backend.backend.drummerbrain.rudiment_roadmap_integration_extended import annotate_song_roadmap_with_extended_rudiments
from backend.backend.drummerbrain.rudiment_performance_spec_integration_extended import apply_extended_rudiments_to_phrases

def test_extended_policy_enables_chorus_for_advanced_profile():
    section = {"sectionType": "chorus", "energy": 0.8, "fillProbability": 0.4}
    profile = {
        "usage_rate": {"six_stroke_roll": 0.6, "linear_hybrid": 0.4},
        "advancedFamilies": ["six_stroke_roll", "linear_hybrid"]
    }
    assert should_use_extended_rudiments(section, profile) is True

def test_extended_roadmap_adds_plan():
    sections = [{"sectionType": "bridge", "energy": 0.7, "fillProbability": 0.5}]
    profile = {
        "usage_rate": {"swiss_triplet": 0.7, "linear_hybrid": 0.3},
        "advancedFamilies": ["swiss_triplet", "linear_hybrid"]
    }
    out = annotate_song_roadmap_with_extended_rudiments(sections, profile)
    assert "extendedRudimentPlan" in out[0]
    assert out[0]["extendedRudimentPlan"]["enabled"] is True

def test_extended_phrase_integration_injects_events():
    phrases = [{"sectionType": "chorus", "events": []}]
    sections = [{"sectionType": "chorus", "energy": 0.9, "fillProbability": 0.6}]
    profile = {
        "usage_rate": {"six_stroke_roll": 0.8, "linear_hybrid": 0.2},
        "advancedFamilies": ["six_stroke_roll", "linear_hybrid"]
    }
    out = apply_extended_rudiments_to_phrases(phrases, sections, profile)
    assert out[0]["extendedRudimentApplied"] is True
    assert len(out[0]["events"]) > 0
