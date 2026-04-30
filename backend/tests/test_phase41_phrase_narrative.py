from backend.backend.drummerbrain.phrase_narrative_planner import plan_phrase_narrative
from backend.backend.drummerbrain.phrase_narrative_runtime import apply_phrase_narrative

def test_planner_creates_levels():
    sections = [{"sectionType":"verse"}, {"sectionType":"chorus"}]
    out = plan_phrase_narrative(sections)
    assert "narrativePlan" in out[0]

def test_runtime_sets_fill_density():
    phrases = [{"sectionType":"chorus"}]
    sections = [{"sectionType":"chorus","narrativePlan":{"intensityLevel":"high"}}]
    out = apply_phrase_narrative(phrases, sections)
    assert out[0]["fillDensity"] >= 0.7
