from backend.backend.drummerbrain.drummer_personality_profile import build_drummer_personality_profile
from backend.backend.drummerbrain.drummer_personality_planner import plan_personality_for_sections
from backend.backend.drummerbrain.drummer_personality_runtime import apply_drummer_personality

def test_profile_builder():
    phrases = [{"events":[
        {"instrument":"crash","accent":True,"velocity":0.8},
        {"instrument":"kick","velocity":0.7},
        {"instrument":"snare","role":"ghost","velocity":0.3},
    ]}]
    profile = build_drummer_personality_profile(phrases, {"fills_per_min": 1.2, "humanness": 0.7, "pocket_tightness": 0.6})
    assert "aggressiveness" in profile
    assert "signatureHabits" in profile

def test_planner():
    sections = [{"sectionType":"verse"}, {"sectionType":"chorus"}]
    personality = {"aggressiveness":0.5, "restraint":0.6, "chaos":0.3, "signatureHabits":{"crashBias":0.7}}
    out = plan_personality_for_sections(sections, personality)
    assert "personalityPlan" in out[0]

def test_runtime():
    phrases = [{"sectionType":"chorus","events":[{"instrument":"crash","accent":True,"velocity":0.6}]}]
    sections = [{"sectionType":"chorus","personalityPlan":{"aggressiveness":0.8,"restraint":0.4,"chaos":0.2,"signatureHabits":{"crashBias":0.8}}}]
    out = apply_drummer_personality(phrases, sections)
    assert out[0]["personalityApplied"] is True
    assert out[0]["events"][0]["velocity"] >= 0.6
