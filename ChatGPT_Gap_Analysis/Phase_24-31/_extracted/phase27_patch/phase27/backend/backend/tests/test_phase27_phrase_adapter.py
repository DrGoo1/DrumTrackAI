from backend.backend.drummerbrain.phrase_adapter import adapt_phrase_to_section

def test_adapter():
    phrase = {"events":[{"velocity":0.5}]}
    sec = {"energy":1.0}
    out = adapt_phrase_to_section(phrase, sec)
    assert out["events"][0]["velocity"] > 0.5
