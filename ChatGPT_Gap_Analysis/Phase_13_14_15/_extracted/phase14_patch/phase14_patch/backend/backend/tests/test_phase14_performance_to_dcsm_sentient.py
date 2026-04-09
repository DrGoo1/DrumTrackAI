from pathlib import Path
import importlib.util
import sys

REPO_BACKEND = "/mnt/data/repo/backend"
if REPO_BACKEND not in sys.path:
    sys.path.insert(0, REPO_BACKEND)

MODULE_PATH = Path(__file__).resolve().parents[1] / "drummerbrain" / "performance_to_dcsm_sentient.py"
spec = importlib.util.spec_from_file_location("phase14_performance_to_dcsm_sentient", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = module
spec.loader.exec_module(module)

build_dcsm_payload_from_sentient_spec = module.build_dcsm_payload_from_sentient_spec
phrase_pattern_events_to_internal_events = module.phrase_pattern_events_to_internal_events


def _spec():
    return {
        "styleId": "rock",
        "globalFeel": "straight",
        "quantizationBase": "16th",
        "phrases": [
            {
                "phraseId": "verse_1",
                "barStart": 0,
                "barEnd": 1,
                "profiles": [
                    {
                        "instrumentId": "kick",
                        "microTiming": {"subdivisionOffsetsMs": [0.0] * 16, "swingAmount": 0.0, "laidBackAmount": 0.0},
                        "velocityProfile": {"base": 100, "accentBoost": 10, "ghostReduction": 0.5, "randomRange": 0, "phraseShape": "flat"},
                        "ghostDensity": 0.0,
                        "flamProbability": 0.0,
                        "dragProbability": 0.0,
                    },
                    {
                        "instrumentId": "snare_center",
                        "microTiming": {"subdivisionOffsetsMs": [0.0] * 16, "swingAmount": 0.0, "laidBackAmount": 0.0},
                        "velocityProfile": {"base": 110, "accentBoost": 10, "ghostReduction": 0.5, "randomRange": 0, "phraseShape": "flat"},
                        "ghostDensity": 0.2,
                        "flamProbability": 0.0,
                        "dragProbability": 0.0,
                    },
                ],
                "phraseEventPattern": {
                    "sourceGrooveAssetId": "family:pocket_backbeat",
                    "bars": 2,
                    "events": [
                        {"barOffset": 0, "stepIndex": 0, "instrumentId": "kick", "velocity": 104, "source": "family:pocket_backbeat", "aspect": "groove"},
                        {"barOffset": 0, "stepIndex": 4, "instrumentId": "snare_center", "velocity": 112, "source": "family:pocket_backbeat", "aspect": "groove"},
                        {"barOffset": 1, "stepIndex": 8, "instrumentId": "kick", "velocity": 100, "source": "family:pocket_backbeat", "aspect": "groove"},
                        {"barOffset": 1, "stepIndex": 12, "instrumentId": "snare_ghost", "velocity": 48, "source": "family:pocket_backbeat", "aspect": "fill"},
                    ],
                    "eventSummary": {"totalEvents": 4},
                },
            }
        ],
    }


def test_phrase_pattern_events_to_internal_events_builds_absolute_timeline():
    events = phrase_pattern_events_to_internal_events(_spec(), {"tempo": 120.0})
    assert len(events) == 4
    assert events[0]["instrument_id"] == "kick"
    assert events[0]["time_sec"] == 0.0
    assert events[-1]["instrument_id"] == "snare_ghost"
    assert events[-1]["isGhost"] is True
    assert events[-1]["time_sec"] > events[1]["time_sec"]


def test_build_dcsm_payload_from_sentient_spec_returns_track_and_legacy_notes():
    payload = build_dcsm_payload_from_sentient_spec(spec=_spec(), cfg={"tempo": 120.0})
    assert payload["available"] is True
    assert payload["internalEventCount"] == 4
    assert payload["drum_track"]["resolution_ppq"] == 960
    assert len(payload["drum_track"]["notes"]) == 4
    assert len(payload["legacy_midi_notes"]) == 4
    drums = {n["drum"] for n in payload["legacy_midi_notes"]}
    assert "kick" in drums
    assert "snare_ghost" in drums
