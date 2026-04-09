from backend.drummerbrain.catalog_scoring_sentient import (
    rerank_fill_candidates,
    rerank_groove_candidates,
)


RIDE_HINTS = {
    "preferredGrooveFamilies": ["ride_lead", "open_hat_lift", "pocket_backbeat"],
    "preferredFillFamilies": ["tom_lift", "cymbal_wash", "snare_roll"],
    "grooveFamilyWeights": {"ride_lead": 0.95, "open_hat_lift": 0.72, "pocket_backbeat": 0.44},
    "fillFamilyWeights": {"tom_lift": 0.82, "cymbal_wash": 0.61, "snare_roll": 0.31},
    "scoreInputs": {"timekeeper": "ride", "timeFeel": "straight", "energy": 0.86, "fillAggression": 0.68},
    "retrievalPolicy": {"preferTimekeeperMatch": True},
}


SHUFFLE_HINTS = {
    "preferredGrooveFamilies": ["shuffle_pocket", "ride_lead"],
    "preferredFillFamilies": ["triplet_turnaround", "snare_roll"],
    "grooveFamilyWeights": {"shuffle_pocket": 1.0, "ride_lead": 0.4},
    "fillFamilyWeights": {"triplet_turnaround": 1.0, "snare_roll": 0.3},
    "scoreInputs": {"timekeeper": "mixed", "timeFeel": "shuffle", "energy": 0.64, "fillAggression": 0.57},
    "retrievalPolicy": {"preferTimekeeperMatch": True, "preferFeelMatch": True},
}


def test_rerank_grooves_prefers_ride_phrase_for_ride_chorus():
    candidates = [
        {
            "id": "groove:pocket_verse",
            "title": "Pocket Verse",
            "tags": ["pocket", "backbeat", "verse"],
            "hat_hits_per_bar": 8,
            "ride_tip_hits_per_bar": 0,
            "complexity_score": 0.44,
            "snare_backbeat_ratio": 0.92,
        },
        {
            "id": "groove:ride_chorus",
            "title": "Ride Lead Chorus",
            "tags": ["ride", "ride_lead", "chorus", "open_hat"],
            "hat_hits_per_bar": 2,
            "ride_tip_hits_per_bar": 8,
            "ride_bell_hits_per_bar": 1,
            "complexity_score": 0.73,
            "snare_backbeat_ratio": 0.76,
        },
    ]
    ranked = rerank_groove_candidates(candidates, RIDE_HINTS)
    assert ranked[0]["candidate"]["id"] == "groove:ride_chorus"
    assert ranked[0]["scoreBreakdown"]["timekeeper"] > 0
    assert any(name == "ride_lead" for name, _ in ranked[0]["scoreBreakdown"]["matchedFamilies"])



def test_rerank_fills_prefers_triplet_fill_for_shuffle_section():
    candidates = [
        {"id": "fill:snare_roll", "title": "Snare Roll", "tags": ["snare", "roll"], "complexity_score": 0.50},
        {"id": "fill:triplet_turnaround", "title": "Triplet Turnaround", "tags": ["triplet", "turnaround", "shuffle"], "complexity_score": 0.58},
    ]
    ranked = rerank_fill_candidates(candidates, SHUFFLE_HINTS)
    assert ranked[0]["candidate"]["id"] == "fill:triplet_turnaround"
    assert any(name == "triplet_turnaround" for name, _ in ranked[0]["scoreBreakdown"]["matchedFamilies"])



def test_limit_is_applied_after_sorting():
    candidates = [
        {"id": "a", "title": "Ride A", "tags": ["ride", "ride_lead"], "ride_tip_hits_per_bar": 8},
        {"id": "b", "title": "Ride B", "tags": ["ride", "ride_lead", "open_hat"], "ride_tip_hits_per_bar": 8, "complexity_score": 0.7},
        {"id": "c", "title": "Pocket C", "tags": ["pocket"], "hat_hits_per_bar": 8},
    ]
    ranked = rerank_groove_candidates(candidates, RIDE_HINTS, limit=2)
    assert len(ranked) == 2
    assert ranked[0]["score"] >= ranked[1]["score"]
