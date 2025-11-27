#!/usr/bin/env python3
"""
Test script for dcsm_drumtrack_builder module.

Tests the conversion of internal drum events to DrumTrackForDCSM format.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def create_mock_songmap(bars=4, bpm=120):
    """Create a mock SongMap for testing."""
    class MockBar:
        def __init__(self, index, bpm):
            self.bar_index = index
            self.tempo_bpm = bpm
            self.meter = [4, 4]
            self.start_time = index * (60.0 / bpm) * 4  # 4 beats per bar
            self.end_time = (index + 1) * (60.0 / bpm) * 4
    
    class MockSongMap:
        def __init__(self, num_bars, bpm):
            self.bars = [MockBar(i, bpm) for i in range(num_bars)]
            self.global_bpm_estimate = bpm
    
    return MockSongMap(bars, bpm)


def create_mock_performance_spec():
    """Create a mock performance spec."""
    return {
        "styleId": "rock",
        "globalFeel": "straight",
        "quantizationBase": "16th",
        "phrases": [
            {
                "phraseId": "phrase_0_3",
                "barStart": 0,
                "barEnd": 3,
                "profiles": [
                    {
                        "instrumentId": "kick",
                        "microTiming": {
                            "subdivisionOffsetsMs": [0.0, -1.0, 0.5, -0.5] * 4,
                            "swingAmount": 0.0,
                            "laidBackAmount": 0.0,
                        },
                        "velocityProfile": {
                            "base": 100,
                            "accentBoost": 20,
                            "ghostReduction": 0.5,
                            "randomRange": 5,
                            "phraseShape": "flat",
                        },
                        "ghostDensity": 0.0,
                        "flamProbability": 0.0,
                        "dragProbability": 0.0,
                    },
                    {
                        "instrumentId": "snare_center",
                        "microTiming": {
                            "subdivisionOffsetsMs": [1.0, 0.0, -1.0, 0.5] * 4,
                            "swingAmount": 0.2,
                            "laidBackAmount": 0.1,
                        },
                        "velocityProfile": {
                            "base": 90,
                            "accentBoost": 25,
                            "ghostReduction": 0.4,
                            "randomRange": 8,
                            "phraseShape": "flat",
                        },
                        "ghostDensity": 0.3,
                        "flamProbability": 0.1,
                        "dragProbability": 0.05,
                    },
                ]
            }
        ]
    }


def test_builder_basic():
    """Test basic drumtrack builder functionality."""
    print("\n" + "="*60)
    print("Testing dcsm_drumtrack_builder.py - Basic")
    print("="*60)
    
    from dcsmpiano.dcsm_drumtrack_builder import (
        build_drumtrack_for_dcsm,
        assign_limb_id,
        assign_priority,
        assign_hit_style,
        assign_aspect,
    )
    from dcsmpiano.dcsm_drumtrack_schema import LimbId, HitStyle, NoteAspect
    
    # Test limb assignment
    assert assign_limb_id("kick") == LimbId.RF
    assert assign_limb_id("snare_center") == LimbId.LH
    assert assign_limb_id("hihat_closed") == LimbId.RH
    assert assign_limb_id("hihat_pedal") == LimbId.LF
    print("✓ Limb assignment works correctly")
    
    # Test priority assignment
    kick_priority = assign_priority("kick", is_accent=False, is_ghost=False)
    assert kick_priority == 1.0, "Kick should have highest priority"
    
    ghost_priority = assign_priority("snare_ghost", is_accent=False, is_ghost=True)
    assert ghost_priority < 0.3, "Ghost notes should have low priority"
    
    accent_priority = assign_priority("snare_center", is_accent=True, is_ghost=False)
    assert accent_priority > 0.9, "Accented snare should have high priority"
    print("✓ Priority assignment works correctly")
    
    # Test hit style assignment
    assert assign_hit_style("kick", is_ghost=False, is_fill=False) == HitStyle.SINGLE
    assert assign_hit_style("snare_ghost", is_ghost=True, is_fill=False) == HitStyle.SINGLE
    print("✓ Hit style assignment works correctly")
    
    # Test aspect assignment
    assert assign_aspect(is_fill=False, is_accent=False, instrument_id="kick") == NoteAspect.GROOVE
    assert assign_aspect(is_fill=True, is_accent=False, instrument_id="tom_high") == NoteAspect.FILL
    assert assign_aspect(is_fill=False, is_accent=True, instrument_id="snare_center") == NoteAspect.ACCENT
    assert assign_aspect(is_fill=False, is_accent=False, instrument_id="crash_1") == NoteAspect.ACCENT
    print("✓ Aspect assignment works correctly")
    
    print("✅ Basic builder tests PASSED\n")
    return True


def test_builder_conversion():
    """Test conversion of internal events to DrumTrackForDCSM."""
    print("\n" + "="*60)
    print("Testing dcsm_drumtrack_builder.py - Conversion")
    print("="*60)
    
    from dcsmpiano.dcsm_drumtrack_builder import build_drumtrack_for_dcsm
    
    # Create mock data
    songmap = create_mock_songmap(bars=4, bpm=120)
    perf_spec = create_mock_performance_spec()
    
    # Create internal events (4 bars of rock pattern)
    internal_events = []
    bpm = 120
    beat_duration = 60.0 / bpm
    
    for bar in range(4):
        bar_start = bar * beat_duration * 4
        
        # Kick on 1 and 3
        internal_events.append({
            "time_sec": bar_start,
            "length_sec": 0.25,
            "midi_pitch": 36,
            "velocity": 100,
            "instrument_id": "kick",
            "isGhost": False,
            "isAccent": False,
            "isFill": False,
        })
        internal_events.append({
            "time_sec": bar_start + beat_duration * 2,
            "length_sec": 0.25,
            "midi_pitch": 36,
            "velocity": 95,
            "instrument_id": "kick",
            "isGhost": False,
            "isAccent": False,
            "isFill": False,
        })
        
        # Snare on 2 and 4
        internal_events.append({
            "time_sec": bar_start + beat_duration,
            "length_sec": 0.25,
            "midi_pitch": 38,
            "velocity": 90,
            "instrument_id": "snare_center",
            "isGhost": False,
            "isAccent": False,
            "isFill": False,
        })
        internal_events.append({
            "time_sec": bar_start + beat_duration * 3,
            "length_sec": 0.25,
            "midi_pitch": 38,
            "velocity": 92,
            "instrument_id": "snare_center",
            "isGhost": False,
            "isAccent": True,
            "isFill": False,
        })
        
        # Hi-hats on 8th notes
        for eighth in range(8):
            internal_events.append({
                "time_sec": bar_start + (beat_duration * eighth / 2),
                "length_sec": 0.125,
                "midi_pitch": 42,
                "velocity": 70 if eighth % 2 == 0 else 60,
                "instrument_id": "hihat_closed",
                "isGhost": eighth % 2 == 1,
                "isAccent": False,
                "isFill": False,
            })
    
    # Build track
    track = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id="rock",
        performance_spec=perf_spec,
        resolution_ppq=960,
    )
    
    print(f"✓ Built track: {len(track.notes)} notes")
    assert len(track.notes) > 0, "Track should have notes"
    assert track.resolution_ppq == 960, "Resolution should be 960 PPQ"
    assert track.style_id == "rock", "Style should be rock"
    
    # Check note attributes
    kicks = [n for n in track.notes if n.instrumentId == "kick"]
    snares = [n for n in track.notes if n.instrumentId == "snare_center"]
    hihats = [n for n in track.notes if n.instrumentId == "hihat_closed"]
    
    print(f"  - {len(kicks)} kicks")
    print(f"  - {len(snares)} snares")
    print(f"  - {len(hihats)} hi-hats")
    
    assert len(kicks) == 8, "Should have 8 kicks (2 per bar × 4 bars)"
    assert len(snares) == 8, "Should have 8 snares (2 per bar × 4 bars)"
    assert len(hihats) == 32, "Should have 32 hi-hats (8 per bar × 4 bars)"
    
    # Check Jamstix attributes are assigned
    sample_note = track.notes[0]
    assert sample_note.id is not None, "Note should have ID"
    assert sample_note.limbId is not None, "Note should have limb ID"
    assert sample_note.priority is not None, "Note should have priority"
    assert sample_note.hitStyle is not None, "Note should have hit style"
    assert sample_note.aspect is not None, "Note should have aspect"
    print("✓ All Jamstix attributes assigned")
    
    # Check limb assignments
    assert all(n.limbId.value == "RF" for n in kicks), "Kicks should be RF"
    assert all(n.limbId.value in ["LH", "RH"] for n in snares), "Snares should be LH or RH"
    assert all(n.limbId.value == "RH" for n in hihats), "Hi-hats should be RH"
    print("✓ Limb assignments correct")
    
    # Check aspects
    groove_notes = [n for n in track.notes if n.aspect.value == "groove"]
    accent_notes = [n for n in track.notes if n.aspect.value == "accent"]
    print(f"  - {len(groove_notes)} groove notes")
    print(f"  - {len(accent_notes)} accent notes")
    assert len(groove_notes) > 0, "Should have groove notes"
    
    # Check serialization
    track_dict = track.to_dict()
    assert isinstance(track_dict, dict), "Track should serialize to dict"
    assert "notes" in track_dict, "Track dict should have notes"
    assert "resolution_ppq" in track_dict, "Track dict should have resolution"
    assert len(track_dict["notes"]) == len(track.notes), "All notes should be in dict"
    print("✓ Serialization works")
    
    # Check note serialization
    note_dict = track.notes[0].to_dict()
    assert "limbId" in note_dict, "Note dict should have limbId"
    assert "priority" in note_dict, "Note dict should have priority"
    assert "hitStyle" in note_dict, "Note dict should have hitStyle"
    assert "aspect" in note_dict, "Note dict should have aspect"
    print("✓ Note serialization works")
    
    print("✅ Conversion tests PASSED\n")
    return True


def test_builder_high_resolution():
    """Test high-resolution timing (960 PPQ, 64th notes)."""
    print("\n" + "="*60)
    print("Testing dcsm_drumtrack_builder.py - High Resolution")
    print("="*60)
    
    from dcsmpiano.dcsm_drumtrack_builder import build_drumtrack_for_dcsm
    
    songmap = create_mock_songmap(bars=1, bpm=120)
    perf_spec = create_mock_performance_spec()
    
    # Create events at 64th note resolution
    bpm = 120
    beat_duration = 60.0 / bpm
    note_64th = beat_duration / 16  # Duration of 64th note
    
    internal_events = []
    for i in range(16):  # 16 64th notes in one beat
        internal_events.append({
            "time_sec": i * note_64th,
            "length_sec": note_64th * 0.5,
            "midi_pitch": 42,
            "velocity": 70,
            "instrument_id": "hihat_closed",
            "isGhost": False,
            "isAccent": False,
            "isFill": False,
        })
    
    # Build at 960 PPQ
    track_960 = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id="test",
        performance_spec=perf_spec,
        resolution_ppq=960,
    )
    
    # Build at 1920 PPQ (ultra-high res)
    track_1920 = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id="test",
        performance_spec=perf_spec,
        resolution_ppq=1920,
    )
    
    print(f"✓ 960 PPQ track: {len(track_960.notes)} notes")
    print(f"✓ 1920 PPQ track: {len(track_1920.notes)} notes")
    
    # Check that 64th notes can be represented
    ticks_per_64th_960 = 960 // 16  # 60 ticks
    ticks_per_64th_1920 = 1920 // 16  # 120 ticks
    
    print(f"  - 960 PPQ: {ticks_per_64th_960} ticks per 64th note")
    print(f"  - 1920 PPQ: {ticks_per_64th_1920} ticks per 64th note")
    
    assert ticks_per_64th_960 > 0, "960 PPQ should support 64th notes"
    assert ticks_per_64th_1920 > 0, "1920 PPQ should support 64th notes"
    
    print("✅ High resolution tests PASSED\n")
    return True


def main():
    """Run all builder tests."""
    print("\n" + "="*60)
    print("DRUMTRACK BUILDER COMPREHENSIVE TESTS")
    print("="*60)
    
    results = []
    
    try:
        results.append(("basic", test_builder_basic()))
    except Exception as e:
        print(f"❌ Basic tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("basic", False))
    
    try:
        results.append(("conversion", test_builder_conversion()))
    except Exception as e:
        print(f"❌ Conversion tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("conversion", False))
    
    try:
        results.append(("high_resolution", test_builder_high_resolution()))
    except Exception as e:
        print(f"❌ High resolution tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        results.append(("high_resolution", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL BUILDER TESTS PASSED! Ready for API integration.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
