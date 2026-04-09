from backend.backend.drummerbrain.regression_suite import basic_regression_check

def test_regression():
    out = {"drum_track":{"events":[1,2,3]}}
    assert basic_regression_check(out)
