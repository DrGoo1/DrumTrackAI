"""
Test Suite for Drum Builder v2.0
================================
Comprehensive tests for the three-layer drum builder.
"""

import unittest
import json
from typing import Dict, Any
from unittest.mock import Mock, patch

# Import modules to test
from drum_generation import DrumGenerationConfig
from drum_generation.llm_performance_spec import (
    build_llm_prompt_for_performance,
    build_default_performance_spec,
    build_flat_performance_spec,
)
from dcsmpiano import (
    DrumNoteEvent,
    DrumTrackForDCSM,
    build_drumtrack_for_dcsm,
    convert_dcsm_track_to_legacy_midi_notes,
)


class TestDrumGenerationConfig(unittest.TestCase):
    """Test configuration dataclass."""
    
    def test_config_creation(self):
        """Test creating config with all fields."""
        config = DrumGenerationConfig(
            sectionId="verse_1",
            startMeasure=0,
            endMeasure=7,
            tempos=[120.0] * 8,
            timeSignature=(4, 4),
            style="rock",
            drummer="jeff_porcaro",
            intensity=0.7,
            variation=0.5,
            generationMode="full_ai",
            humanize=True,
            fillLocations=[7],
            fillType="auto",
            humanizeAmount=0.7,
            ghostNoteAmount=0.6,
            swingAmount=0.2,
            buildScope="full_song",
        )
        
        self.assertEqual(config.style, "rock")
        self.assertEqual(config.drummer, "jeff_porcaro")
        self.assertTrue(config.humanize)
        self.assertEqual(config.humanizeAmount, 0.7)
    
    def test_config_to_dict(self):
        """Test config serialization."""
        config = DrumGenerationConfig(
            sectionId="verse_1",
            startMeasure=0,
            endMeasure=7,
            tempos=[120.0] * 8,
            timeSignature=(4, 4),
            style="rock",
            drummer="jeff_porcaro",
            intensity=0.7,
            variation=0.5,
            generationMode="full_ai",
            humanize=True,
            fillLocations=[],
            fillType="auto",
        )
        
        data = config.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["style"], "rock")
        self.assertEqual(data["timeSignature"], (4, 4))
    
    def test_config_from_dict(self):
        """Test config deserialization."""
        data = {
            "sectionId": "verse_1",
            "startMeasure": 0,
            "endMeasure": 7,
            "tempos": [120.0] * 8,
            "timeSignature": [4, 4],
            "style": "rock",
            "drummer": "jeff_porcaro",
            "intensity": 0.7,
            "variation": 0.5,
            "generationMode": "full_ai",
            "humanize": True,
            "fillLocations": [],
            "fillType": "auto",
        }
        
        config = DrumGenerationConfig.from_dict(data)
        self.assertEqual(config.style, "rock")
        self.assertEqual(config.timeSignature, (4, 4))


class TestPerformanceSpec(unittest.TestCase):
    """Test performance spec generation."""
    
    def test_flat_spec_generation(self):
        """Test flat performance spec (no humanization)."""
        config = self._create_test_config()
        config.humanize = False
        
        spec = build_flat_performance_spec(
            config,
            {"bars": 8, "sections": []},
        )
        
        self.assertIsInstance(spec, dict)
        self.assertEqual(spec["styleId"], "rock")
        self.assertEqual(spec["globalFeel"], "straight")
        self.assertEqual(len(spec["phrases"]), 1)
        
        # Check micro-timing is zero
        phrase = spec["phrases"][0]
        for profile in phrase["profiles"]:
            offsets = profile["microTiming"]["subdivisionOffsetsMs"]
            self.assertTrue(all(o == 0.0 for o in offsets))
    
    def test_default_spec_generation(self):
        """Test default performance spec (analytics-based)."""
        config = self._create_test_config()
        config.humanize = True
        config.humanizeAmount = 0.8
        config.ghostNoteAmount = 0.7
        
        spec = build_default_performance_spec(
            config,
            {"bars": 8, "sections": []},
            {"timing_tightness": 0.85, "ghost_note_frequency": 0.6},
        )
        
        self.assertIsInstance(spec, dict)
        self.assertEqual(spec["styleId"], "rock")
        self.assertEqual(len(spec["phrases"]), 1)
        
        # Check micro-timing has variation
        phrase = spec["phrases"][0]
        snare_profile = None
        for profile in phrase["profiles"]:
            if profile["instrumentId"] == "snare_center":
                snare_profile = profile
                break
        
        self.assertIsNotNone(snare_profile)
        offsets = snare_profile["microTiming"]["subdivisionOffsetsMs"]
        # Should have some non-zero offsets
        self.assertTrue(any(o != 0.0 for o in offsets))
    
    def test_prompt_generation(self):
        """Test LLM prompt generation."""
        config = self._create_test_config()
        
        prompt = build_llm_prompt_for_performance(
            config,
            "Verse 1",
            {"bars": 8, "sections": [{"label": "Verse 1", "energy": 0.6}]},
            {"timing_tightness": 0.85},
        )
        
        self.assertIsInstance(prompt, str)
        self.assertIn("rock", prompt.lower())
        self.assertIn("jeff_porcaro", prompt.lower())
        self.assertIn("verse", prompt.lower())
        self.assertIn("DrumPerformanceSpec", prompt)
    
    def _create_test_config(self) -> DrumGenerationConfig:
        """Helper to create test config."""
        return DrumGenerationConfig(
            sectionId="verse_1",
            startMeasure=0,
            endMeasure=7,
            tempos=[120.0] * 8,
            timeSignature=(4, 4),
            style="rock",
            drummer="jeff_porcaro",
            intensity=0.7,
            variation=0.5,
            generationMode="full_ai",
            humanize=True,
            fillLocations=[],
            fillType="auto",
        )


class TestDrumTrackBuilder(unittest.TestCase):
    """Test drum track building."""
    
    def test_track_building(self):
        """Test building a complete drum track."""
        # Create mock SongMap
        songmap = self._create_mock_songmap()
        
        # Create internal events
        internal_events = self._create_mock_internal_events()
        
        # Create performance spec
        perf_spec = build_flat_performance_spec(
            self._create_test_config(),
            {"bars": 8, "sections": []},
        )
        
        # Build track
        track = build_drumtrack_for_dcsm(
            songmap=songmap,
            internal_drum_events=internal_events,
            style_id="rock",
            performance_spec=perf_spec,
            resolution_ppq=960,
        )
        
        self.assertIsInstance(track, DrumTrackForDCSM)
        self.assertEqual(track.style_id, "rock")
        self.assertEqual(track.resolution_ppq, 960)
        self.assertGreater(len(track.notes), 0)
    
    def test_track_serialization(self):
        """Test track to dict conversion."""
        track = DrumTrackForDCSM(
            track_id="test-123",
            style_id="rock",
            resolution_ppq=960,
            notes=[],
            performance_spec={
                "styleId": "rock",
                "globalFeel": "straight",
                "quantizationBase": "16th",
                "phrases": [],
            },
        )
        
        data = track.to_dict()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["style_id"], "rock")
        self.assertEqual(data["resolution_ppq"], 960)
    
    def test_legacy_conversion(self):
        """Test conversion to legacy midi_notes format."""
        note = DrumNoteEvent(
            id="test-note",
            barIndex=0,
            tickInBar=0,
            tickLength=480,
            channel=9,
            midiPitch=38,
            velocity=100,
            instrumentId="snare_center",
            isGhost=False,
            isAccent=True,
        )
        
        track = DrumTrackForDCSM(
            track_id="test-123",
            style_id="rock",
            resolution_ppq=960,
            notes=[note],
            performance_spec={
                "styleId": "rock",
                "globalFeel": "straight",
                "quantizationBase": "16th",
                "phrases": [],
            },
        )
        
        legacy_notes = convert_dcsm_track_to_legacy_midi_notes(track)
        
        self.assertEqual(len(legacy_notes), 1)
        self.assertEqual(legacy_notes[0]["note"], 38)
        self.assertEqual(legacy_notes[0]["velocity"], 100)
        self.assertEqual(legacy_notes[0]["drum"], "snare_center")
    
    def _create_test_config(self) -> DrumGenerationConfig:
        """Helper to create test config."""
        return DrumGenerationConfig(
            sectionId="verse_1",
            startMeasure=0,
            endMeasure=7,
            tempos=[120.0] * 8,
            timeSignature=(4, 4),
            style="rock",
            drummer="jeff_porcaro",
            intensity=0.7,
            variation=0.5,
            generationMode="full_ai",
            humanize=False,
            fillLocations=[],
            fillType="auto",
        )
    
    def _create_mock_songmap(self):
        """Helper to create mock SongMap."""
        class MockBar:
            def __init__(self, idx):
                self.start_time = idx * 2.0
                self.end_time = (idx + 1) * 2.0
                self.tempo_bpm = 120.0
                self.meter = (4, 4)
        
        class MockSongMap:
            def __init__(self):
                self.bars = [MockBar(i) for i in range(8)]
                self.global_bpm_estimate = 120.0
        
        return MockSongMap()
    
    def _create_mock_internal_events(self):
        """Helper to create mock internal events."""
        return [
            {
                "time_sec": 0.0,
                "length_sec": 0.2,
                "instrument_id": "kick",
                "midi_pitch": 36,
                "velocity": 110,
                "isGhost": False,
                "isAccent": True,
                "isFlam": False,
                "isDrag": False,
            },
            {
                "time_sec": 1.0,
                "length_sec": 0.2,
                "instrument_id": "snare_center",
                "midi_pitch": 38,
                "velocity": 100,
                "isGhost": False,
                "isAccent": True,
                "isFlam": False,
                "isDrag": False,
            },
            {
                "time_sec": 0.5,
                "length_sec": 0.15,
                "instrument_id": "hihat_closed",
                "midi_pitch": 42,
                "velocity": 85,
                "isGhost": False,
                "isAccent": False,
                "isFlam": False,
                "isDrag": False,
            },
        ]


class TestMicroTiming(unittest.TestCase):
    """Test micro-timing application."""
    
    def test_microtiming_varies_by_humanize_amount(self):
        """Test that higher humanizeAmount creates more variation."""
        config_tight = self._create_config(humanizeAmount=0.2)
        config_loose = self._create_config(humanizeAmount=0.9)
        
        spec_tight = build_default_performance_spec(
            config_tight,
            {"bars": 8, "sections": []},
            {"timing_tightness": 0.8},
        )
        
        spec_loose = build_default_performance_spec(
            config_loose,
            {"bars": 8, "sections": []},
            {"timing_tightness": 0.8},
        )
        
        # Get offsets
        tight_offsets = spec_tight["phrases"][0]["profiles"][0]["microTiming"]["subdivisionOffsetsMs"]
        loose_offsets = spec_loose["phrases"][0]["profiles"][0]["microTiming"]["subdivisionOffsetsMs"]
        
        # Loose should have larger absolute values
        tight_max = max(abs(o) for o in tight_offsets)
        loose_max = max(abs(o) for o in loose_offsets)
        
        self.assertLess(tight_max, loose_max)
    
    def _create_config(self, humanizeAmount: float) -> DrumGenerationConfig:
        """Helper to create config with specific humanize amount."""
        return DrumGenerationConfig(
            sectionId="verse_1",
            startMeasure=0,
            endMeasure=7,
            tempos=[120.0] * 8,
            timeSignature=(4, 4),
            style="rock",
            drummer="jeff_porcaro",
            intensity=0.7,
            variation=0.5,
            generationMode="full_ai",
            humanize=True,
            humanizeAmount=humanizeAmount,
            fillLocations=[],
            fillType="auto",
        )


class TestVelocityProfile(unittest.TestCase):
    """Test velocity profile application."""
    
    def test_velocity_varies_by_intensity(self):
        """Test that higher intensity creates louder velocities."""
        config_soft = self._create_config(intensity=0.2)
        config_hard = self._create_config(intensity=0.9)
        
        spec_soft = build_default_performance_spec(
            config_soft,
            {"bars": 8, "sections": []},
            {"timing_tightness": 0.8},
        )
        
        spec_hard = build_default_performance_spec(
            config_hard,
            {"bars": 8, "sections": []},
            {"timing_tightness": 0.8},
        )
        
        # Get base velocities
        soft_vel = spec_soft["phrases"][0]["profiles"][0]["velocityProfile"]["base"]
        hard_vel = spec_hard["phrases"][0]["profiles"][0]["velocityProfile"]["base"]
        
        self.assertLess(soft_vel, hard_vel)
    
    def _create_config(self, intensity: float) -> DrumGenerationConfig:
        """Helper to create config with specific intensity."""
        return DrumGenerationConfig(
            sectionId="verse_1",
            startMeasure=0,
            endMeasure=7,
            tempos=[120.0] * 8,
            timeSignature=(4, 4),
            style="rock",
            drummer="jeff_porcaro",
            intensity=intensity,
            variation=0.5,
            generationMode="full_ai",
            humanize=True,
            fillLocations=[],
            fillType="auto",
        )


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestDrumGenerationConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceSpec))
    suite.addTests(loader.loadTestsFromTestCase(TestDrumTrackBuilder))
    suite.addTests(loader.loadTestsFromTestCase(TestMicroTiming))
    suite.addTests(loader.loadTestsFromTestCase(TestVelocityProfile))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
