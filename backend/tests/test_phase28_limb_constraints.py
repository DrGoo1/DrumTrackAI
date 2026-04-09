from backend.drummerbrain.limb_constraints import enforce_limb_constraints


def test_constraints():
    events = [{"instrument": "kick"} for _ in range(5)]
    out = enforce_limb_constraints(events)
    assert len(out) <= 2
