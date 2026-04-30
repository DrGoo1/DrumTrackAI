from backend.drummerbrain.performance_spec_sentient import build_sentient_instrument_profile


def test_build_sentient_instrument_profile_uses_role_aware_timing_and_dynamics():
    drummer_profile = {
        "instrument_timing_profiles": {
            "profiles": [
                {
                    "instrument": "snare",
                    "role": "backbeat",
                    "subdivision": "1",
                    "mean_offset_ms": 5.0,
                    "std_offset_ms": 2.0,
                    "sample_count": 12,
                },
                {
                    "instrument": "snare",
                    "role": "backbeat",
                    "subdivision": "&",
                    "mean_offset_ms": 1.5,
                    "std_offset_ms": 2.0,
                    "sample_count": 8,
                },
            ]
        },
        "instrument_dynamic_profiles": {
            "profiles": [
                {
                    "instrument": "snare",
                    "role": "backbeat",
                    "velocity_mean": 108.0,
                    "velocity_std": 12.0,
                    "sample_count": 20,
                }
            ]
        },
        "transition_model": {
            "transitions": [
                {"from": "groove", "to": "fill", "probability": 0.55},
                {"from": "fill", "to": "groove", "probability": 0.9},
            ]
        },
    }

    prof = build_sentient_instrument_profile(
        instrument_id="snare_center",
        section_label="Chorus A",
        local_base_velocity=96,
        humanize_amount=0.7,
        swing_amount=0.1,
        laid_back=0.15,
        global_var_ms=3.0,
        ghost_density=0.25,
        drummer_profile=drummer_profile,
        energy_intensity=0.8,
        variation=0.7,
    )

    assert prof["instrumentId"] == "snare_center"
    assert len(prof["microTiming"]["subdivisionOffsetsMs"]) == 16
    assert prof["microTiming"]["subdivisionOffsetsMs"][0] > 4.0
    assert prof["velocityProfile"]["base"] >= 100
    assert prof["velocityProfile"]["phraseShape"] == "swell"
    assert prof["microTiming"]["randomStdMs"] >= 2.0
