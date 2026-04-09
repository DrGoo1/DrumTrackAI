
from backend.backend.drummerbrain.rudiment_detector import detect_rudiments

def test_detect():
    events = [
        {"time":0.0,"hand":"R"},
        {"time":0.01,"hand":"L"},
        {"time":0.5,"hand":"R"},
        {"time":0.6,"hand":"R"}
    ]
    r = detect_rudiments(events)
    assert len(r) >= 1
