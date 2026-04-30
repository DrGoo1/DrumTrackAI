from backend.drummerbrain.drummer_similarity_ranker import rank_by_drummer_similarity


def test_ranker():
    candidates = [
        {"family": "ride_lead", "density": 0.5},
        {"family": "pocket", "density": 0.2},
    ]

    profile = {"preferredGrooveFamilies": ["ride_lead"], "targetDensity": 0.5}

    ranked = rank_by_drummer_similarity(candidates, profile)

    assert ranked[0]["family"] == "ride_lead"
