from backend.drummerbrain.eval_reconstruction import reconstruction_score


def test_reconstruction_basic():
    ref = {"events": [{"instrument": "kick"}, {"instrument": "snare"}]}
    gen = {"events": [{"instrument": "kick"}, {"instrument": "snare"}]}
    assert reconstruction_score(ref, gen) == 1.0
