
from backend.backend.drummerbrain.rudiment_phrase_generator import choose_rudiment_phrase
from backend.backend.drummerbrain.rudiment_generation_integration import inject_rudiment_phrase

def test_choose_drag_for_verse_when_drag_is_present():
    section = {"sectionType": "verse", "energy": 0.4}
    profile = {"usage_rate": {"drag": 0.6, "flam": 0.2, "paradiddle": 0.2}}
    result = choose_rudiment_phrase(section, profile)
    assert result["rudimentType"] == "drag"

def test_injects_rudiment_phrase_into_output():
    phrase = {"events": []}
    section = {"sectionType": "chorus", "energy": 0.8}
    profile = {"usage_rate": {"flam": 0.7, "paradiddle": 0.3}}
    out = inject_rudiment_phrase(phrase, section, profile)
    assert len(out["events"]) > 0
    assert out["generatedTechniques"][0]["type"] in ("flam", "paradiddle")
