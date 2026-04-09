
from backend.backend.drummerbrain.limb_interaction_model import build_limb_interaction_profile
from backend.backend.drummerbrain.limb_interaction_runtime import apply_limb_interaction_runtime
from backend.backend.drummerbrain.limb_interaction_planner import plan_limb_interaction_for_sections

def test_build_limb_interaction_profile():
    phrases = [{
        "events": [
            {"instrument": "hihat", "hand": "RH"},
            {"instrument": "kick", "hand": "RF"},
            {"instrument": "snare", "hand": "LH", "role": "ghost"},
        ]
    }]
    profile = build_limb_interaction_profile(phrases)
    assert "limbLoad" in profile
    assert "interactionBias" in profile

def test_apply_limb_interaction_runtime():
    phrases = [{
        "events": [
            {"instrument": "hihat", "velocity": 0.6},
            {"instrument": "snare", "velocity": 0.5, "role": "ghost"},
        ]
    }]
    profile = {"interactionBias": {"timekeeper": "ride", "busy_feet": True, "ghost_to_kick_ratio": 0.6}}
    out = apply_limb_interaction_runtime(phrases, profile)
    assert out[0]["limbInteractionApplied"] is True
    assert out[0]["events"][0]["instrument"] == "ride"

def test_section_plan_added():
    sections = [{"sectionType": "verse"}, {"sectionType": "chorus"}]
    profile = {"interactionBias": {"timekeeper": "hihat", "busy_feet": False}}
    out = plan_limb_interaction_for_sections(sections, profile)
    assert "limbInteractionPlan" in out[0]
