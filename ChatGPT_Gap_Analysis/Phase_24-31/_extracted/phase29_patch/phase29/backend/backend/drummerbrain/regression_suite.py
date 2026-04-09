def basic_regression_check(output):
    assert "drum_track" in output
    assert len(output["drum_track"].get("events", [])) > 0
    return True
