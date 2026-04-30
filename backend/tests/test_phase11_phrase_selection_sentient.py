from backend.drummerbrain.phrase_selection_sentient import (
    choose_phrase_shape_from_family,
    select_phrase_families,
)


def test_phrase_selection_prefers_ride_and_linear_fill_for_busy_ride_player():
    profile = {
        "fills_per_min": 1.5,
        "humanness": 0.7,
        "pocket_tightness": 0.58,
        "instrument_shares": {"ride": 0.22, "hihat": 0.12, "kick": 0.15},
        "technique_breakdown": {"flam": 3, "linear": 8},
        "transition_model": {
            "transitions": [
                {"from": "groove", "to": "fill", "probability": 0.58},
                {"from": "groove", "to": "variation", "probability": 0.52},
            ]
        },
    }
    out = select_phrase_families(
        section_type="chorus",
        energy=0.84,
        variation=0.73,
        timekeeper="ride",
        fill_family="tom_lift",
        fill_enabled=True,
        time_feel="straight",
        drummer_profile=profile,
    )
    assert out["grooveFamily"] == "ride_lead"
    assert "linear_burst" in out["fillCandidates"]
    assert out["selectorWeights"]["fillBias"] > 0.45


def test_phrase_selection_prefers_pocket_for_tight_hat_player():
    profile = {
        "fills_per_min": 0.45,
        "humanness": 0.42,
        "pocket_tightness": 0.83,
        "instrument_shares": {"ride": 0.02, "hihat": 0.24, "kick": 0.10},
        "technique_breakdown": {},
        "transition_model": {"groove": {"fill": 0.16, "variation": 0.22}},
    }
    out = select_phrase_families(
        section_type="verse",
        energy=0.58,
        variation=0.42,
        timekeeper="hats",
        fill_family="snare_pickup",
        fill_enabled=True,
        time_feel="straight",
        drummer_profile=profile,
    )
    assert out["grooveFamily"] == "pocket_backbeat"
    assert out["fillFamily"] == "snare_pickup"
    assert out["selectorWeights"]["spacePreference"] > 0.5


def test_phrase_shape_from_family():
    assert choose_phrase_shape_from_family("ride_lead", "snare_pickup") == "swell"
    assert choose_phrase_shape_from_family("pocket_backbeat", "snare_pickup") == "flat"
    assert choose_phrase_shape_from_family("syncopated_kick", "linear_burst") == "push"
