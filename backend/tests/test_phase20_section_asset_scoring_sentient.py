from backend.drummerbrain.section_asset_scoring_sentient import derive_section_asset_scoring


def test_chorus_ride_player_prefers_ride_and_open_hat_families():
    profile = {
        "instrument_shares": {"ride": 0.42, "hihat": 0.16, "crash": 0.22, "kick": 0.20},
        "pocket_tightness": 0.56,
        "humanness": 0.72,
        "fills_per_min": 2.1,
        "technique_breakdown": {"linear": 4, "flam": 1},
    }
    hints = derive_section_asset_scoring(
        profile,
        section_type="chorus",
        local_time_feel="straight",
        timekeeper="ride",
        energy=0.88,
        fill_aggression=0.78,
        ghost_target=0.32,
        syncopation_target=0.61,
    )
    assert hints["preferredGrooveFamilies"][0] == "ride_lead"
    assert "open_hat_lift" in hints["preferredGrooveFamilies"]
    assert hints["grooveFamilyWeights"]["ride_lead"] > hints["grooveFamilyWeights"]["pocket_backbeat"]


def test_shuffle_section_prefers_shuffle_and_triplet_fill_language():
    profile = {
        "instrument_shares": {"ride": 0.24, "hihat": 0.22},
        "ghost_note_frequency": 0.58,
        "technique_breakdown": {"flam": 2, "linear": 1},
    }
    hints = derive_section_asset_scoring(
        profile,
        section_type="bridge",
        local_time_feel="shuffle",
        timekeeper="mixed",
        energy=0.66,
        fill_aggression=0.57,
        ghost_target=0.61,
        syncopation_target=0.43,
    )
    assert hints["preferredGrooveFamilies"][0] == "shuffle_pocket"
    assert "triplet_turnaround" in hints["preferredFillFamilies"]
    assert hints["retrievalPolicy"]["preferFeelMatch"] is True


def test_tight_verse_prefers_pocket_and_can_choose_no_fill():
    profile = {
        "instrument_shares": {"hihat": 0.48, "kick": 0.28},
        "pocket_tightness": 0.9,
        "humanness": 0.35,
        "fills_per_min": 0.5,
    }
    hints = derive_section_asset_scoring(
        profile,
        section_type="verse",
        local_time_feel="straight",
        timekeeper="hats",
        energy=0.54,
        fill_aggression=0.21,
        ghost_target=0.18,
        syncopation_target=0.24,
    )
    assert hints["preferredGrooveFamilies"][0] == "pocket_backbeat"
    assert "none" in hints["preferredFillFamilies"]
    assert hints["retrievalPolicy"]["maxCandidatePool"] == 8
