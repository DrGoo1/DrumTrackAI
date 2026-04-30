from backend.drummerbrain.song_roadmap_sentient import build_song_roadmap_section_overrides


def test_phase10_song_roadmap_prefers_ride_and_fill_for_fill_heavy_profile():
    drummer_profile = {
        "fills_per_min": 1.9,
        "humanness": 0.78,
        "pocket_tightness": 0.52,
        "instrument_shares": {"ride": 0.24, "hihat": 0.38},
        "technique_breakdown": {"flam": 12, "roll": 9},
        "transition_model": {
            "transitions": [
                {"from": "variation", "to": "fill", "probability": 0.71},
                {"from": "groove", "to": "variation", "probability": 0.58},
                {"from": "fill", "to": "groove", "probability": 0.84},
            ]
        },
    }

    out = build_song_roadmap_section_overrides(
        section_type="chorus",
        energy=0.84,
        variation=0.62,
        swing_amount=0.08,
        time_feel="straight",
        drummer_profile=drummer_profile,
        current_timekeeper="hats",
        current_fill_enabled=True,
    )

    assert out["orchestration"]["timekeeper"] in {"ride", "mixed"}
    assert out["transitions"]["fillOut"]["enabled"] is True
    assert out["transitions"]["fillOut"]["aggression"] > 0.6
    assert out["transitions"]["fillOut"]["family"] in {"flam_tom", "tom_lift", "snare_roll"}
    assert out["fillPolicy"]["frequency"] in {"all_transitions", "section_transitions"}


def test_phase10_song_roadmap_can_stay_conservative_for_tight_hat_player():
    drummer_profile = {
        "fills_per_min": 0.35,
        "humanness": 0.45,
        "pocket_tightness": 0.91,
        "instrument_shares": {"ride": 0.03, "hihat": 0.61},
        "transition_model": {
            "transitions": [
                {"from": "groove", "to": "fill", "probability": 0.12},
                {"from": "groove", "to": "variation", "probability": 0.22},
                {"from": "fill", "to": "groove", "probability": 0.95},
            ]
        },
    }

    out = build_song_roadmap_section_overrides(
        section_type="verse",
        energy=0.58,
        variation=0.35,
        swing_amount=0.0,
        time_feel="straight",
        drummer_profile=drummer_profile,
        current_timekeeper="hats",
        current_fill_enabled=True,
    )

    assert out["orchestration"]["timekeeper"] == "hats"
    assert out["transitions"]["fillOut"]["probability"] < 0.25
    assert out["fillPolicy"]["frequency"] == "conservative"
    assert out["transitions"]["fillOut"]["length"] in {"last_beat", "last_2_beats"}
