from backend.backend.drummerbrain.microtiming_profile import build_microtiming_profile

def test_profile():
    events = [{"instrument":"snare","role":"backbeat","timing_offset_ms":10}]
    prof = build_microtiming_profile(events)
    assert "snare:backbeat" in prof["byInstrumentRole"]
