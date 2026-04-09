from backend.backend.drummerbrain.adaptive_feedback_sentient import adapt_profile_from_feedback

def test_feedback_reduces_fill_density():
    profile = {"fills_per_min": 2.0, "humanizeAmount": 0.4}
    edits = [{"type": "delete_fill"}, {"type": "timing_loosen"}]
    out = adapt_profile_from_feedback(profile, edits)
    assert out["fills_per_min"] < 2.0
    assert out["humanizeAmount"] > 0.4
