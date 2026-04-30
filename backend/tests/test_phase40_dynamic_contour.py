from backend.backend.drummerbrain.dynamic_contour_profile import build_dynamic_contour_profile
from backend.backend.drummerbrain.dynamic_contour_runtime import apply_dynamic_contour
from backend.backend.drummerbrain.dynamic_contour_planner import plan_dynamic_contour_for_sections

def test_profile_build():
    phrases = [{"sectionType":"verse","events":[{"velocity":0.5},{"velocity":0.7}]}]
    prof = build_dynamic_contour_profile(phrases)
    assert "bySection" in prof

def test_runtime_apply():
    phrases = [{"sectionType":"chorus","events":[{"velocity":0.5},{"velocity":0.5}]}]
    sections = [{"sectionType":"chorus","energy":0.8}]
    out = apply_dynamic_contour(phrases, sections, {"bySection":{"chorus":{"mean":0.6,"peak":0.9}}})
    assert out[0]["dynamicContourApplied"] is True

def test_planner():
    sections = [{"sectionType":"bridge","energy":0.6}]
    out = plan_dynamic_contour_for_sections(sections)
    assert "dynamicContourPlan" in out[0]
