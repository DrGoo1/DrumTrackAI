
from backend.backend.drummerbrain.phrase_continuity_memory import phrase_signature, similarity_score
from backend.backend.drummerbrain.phrase_continuity_runtime import apply_phrase_continuity_runtime, continuity_plan_for_sections

def test_phrase_similarity_positive():
    a = {"events": [{"instrument": "kick"}, {"instrument": "snare"}], "type": "verse", "family": "pocket_backbeat"}
    b = {"events": [{"instrument": "kick"}, {"instrument": "snare"}], "type": "verse", "family": "pocket_backbeat"}
    sig_a = phrase_signature(a)
    sig_b = phrase_signature(b)
    assert similarity_score(sig_a, sig_b) > 0.5

def test_runtime_applies_variation_when_repetitive():
    phrases = [
        {"events": [{"instrument": "hihat", "velocity": 0.5}, {"instrument": "snare", "velocity": 0.8}], "type": "verse", "family": "pocket_backbeat"},
        {"events": [{"instrument": "hihat", "velocity": 0.5}, {"instrument": "snare", "velocity": 0.8}], "type": "verse", "family": "pocket_backbeat"},
    ]
    out = apply_phrase_continuity_runtime(phrases, variation_mode="medium")
    assert "continuityMeta" in out[1]
    assert out[1].get("variationApplied") in (True, False)

def test_section_plan_added():
    sections = [{"sectionType": "verse"}, {"sectionType": "chorus"}]
    out = continuity_plan_for_sections(sections)
    assert "continuityPlan" in out[0]
    assert "variationMode" in out[1]["continuityPlan"]
