
from backend.backend.drummerbrain.rudiment_runtime_policy import should_inject_rudiment
from backend.backend.drummerbrain.rudiment_roadmap_integration import annotate_song_roadmap_with_rudiments
from backend.backend.drummerbrain.rudiment_performance_spec_integration import apply_rudiments_to_phrases

def test_runtime_policy_enables_chorus():
    section = {"sectionType": "chorus", "energy": 0.8, "fillProbability": 0.4}
    profile = {"usage_rate": {"flam": 0.5, "drag": 0.5}}
    assert should_inject_rudiment(section, profile) is True

def test_roadmap_annotation_adds_rudiment_plan():
    sections = [{"sectionType": "verse", "energy": 0.6, "fillProbability": 0.5}]
    profile = {"usage_rate": {"drag": 1.0}}
    out = annotate_song_roadmap_with_rudiments(sections, profile)
    assert "rudimentPlan" in out[0]

def test_phrase_integration_injects_events():
    phrases = [{"sectionType": "chorus", "events": []}]
    sections = [{"sectionType": "chorus", "energy": 0.8, "fillProbability": 0.6}]
    profile = {"usage_rate": {"flam": 0.8, "paradiddle": 0.2}}
    out = apply_rudiments_to_phrases(phrases, sections, profile)
    assert out[0]["rudimentApplied"] is True
    assert len(out[0]["events"]) > 0
