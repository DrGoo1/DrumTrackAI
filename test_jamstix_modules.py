#!/usr/bin/env python3
"""
Test script for Jamstix integration modules.

Tests the newly created backend modules independently to ensure
they work correctly before integration with the rest of the system.
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

def test_part_types():
    """Test part_types_config module."""
    print("\n" + "="*60)
    print("Testing part_types_config.py")
    print("="*60)
    
    from drum_generation.part_types_config import (
        get_part_type_preset,
        list_part_types,
        get_part_type_label,
        apply_part_type_defaults,
    )
    
    # Test listing part types
    part_types = list_part_types()
    print(f"✓ Found {len(part_types)} part types: {', '.join(part_types)}")
    
    # Test getting presets
    verse = get_part_type_preset("verse")
    print(f"✓ Verse preset: intensity={verse.defaultIntensity}, variation={verse.defaultVariation}")
    
    chorus = get_part_type_preset("chorus")
    print(f"✓ Chorus preset: intensity={chorus.defaultIntensity}, variation={chorus.defaultVariation}")
    
    # Test label lookup
    label = get_part_type_label("prechorus")
    print(f"✓ Pre-chorus label: {label}")
    
    # Test applying defaults
    config = {}
    config = apply_part_type_defaults(config, "intro")
    print(f"✓ Intro defaults applied: {config}")
    
    # Test normalization
    preset = get_part_type_preset("Pre-Chorus")  # Different case
    assert preset.id == "prechorus", "Normalization failed"
    print(f"✓ Name normalization works (Pre-Chorus → prechorus)")
    
    print("✅ part_types_config tests PASSED\n")
    return True


def test_power_model():
    """Test power_model module."""
    print("\n" + "="*60)
    print("Testing power_model.py")
    print("="*60)
    
    from drum_generation.power_model import (
        compute_power_curve_from_guide,
        compute_power_curve_from_sections,
        interpolate_power_curve,
        analyze_power_transitions,
        power_to_velocity_scale,
        power_to_fill_probability,
        power_to_ghost_note_density,
    )
    
    # Test basic power curve
    rms = [0.2, 0.3, 0.5, 0.7, 0.6, 0.4]
    power = compute_power_curve_from_guide(rms, user_intensity=0.7)
    print(f"✓ Power curve from RMS: {[f'{p:.2f}' for p in power]}")
    assert len(power) == len(rms), "Power curve length mismatch"
    assert all(0 <= p <= 1 for p in power), "Power values out of range"
    
    # Test section-based power
    energies = [0.4, 0.6, 0.9]  # intro, verse, chorus
    bars = [4, 8, 8]
    power_sections = compute_power_curve_from_sections(energies, bars, 0.7)
    print(f"✓ Power from sections: {len(power_sections)} bars")
    assert len(power_sections) == sum(bars), "Section power length mismatch"
    
    # Test interpolation
    coarse_power = [0.3, 0.7, 0.9, 0.5]
    fine_power = interpolate_power_curve(coarse_power, target_length=16)
    print(f"✓ Interpolated {len(coarse_power)} → {len(fine_power)} values")
    assert len(fine_power) == 16, "Interpolation failed"
    
    # Test transition detection
    power_with_changes = [0.4, 0.4, 0.5, 0.7, 0.9, 0.5, 0.4]
    transitions = analyze_power_transitions(power_with_changes, threshold=0.2)
    print(f"✓ Found {len(transitions)} power transitions")
    for bar, change, trans_type in transitions:
        print(f"  - Bar {bar}: {change:+.2f} ({trans_type})")
    
    # Test conversion functions
    vel_scale = power_to_velocity_scale(0.9)
    fill_prob = power_to_fill_probability(0.8)
    ghost_density = power_to_ghost_note_density(0.65)
    print(f"✓ Conversions: vel_scale={vel_scale:.2f}, fill_prob={fill_prob:.2f}, ghost={ghost_density:.2f}")
    
    print("✅ power_model tests PASSED\n")
    return True


def test_drumtrack_schema():
    """Test dcsm_drumtrack_schema module."""
    print("\n" + "="*60)
    print("Testing dcsm_drumtrack_schema.py")
    print("="*60)
    
    from dcsmpiano.dcsm_drumtrack_schema import (
        DrumNoteEvent,
        DrumTrackForDCSM,
        LimbId,
        HitStyle,
        NoteAspect,
        make_note_id,
        make_track_id,
        create_drum_note,
        instrument_id_to_midi_pitch,
        midi_pitch_to_instrument_id,
        GM_DRUM_MAP,
        create_default_performance_spec,
    )
    
    # Test note creation
    note = create_drum_note(
        bar_index=0,
        tick_in_bar=0,
        midi_pitch=36,
        velocity=100,
        instrument_id="kick",
        limbId=LimbId.RF,
        hitStyle=HitStyle.SINGLE,
        aspect=NoteAspect.GROOVE,
        priority=0.9,
    )
    print(f"✓ Created note: {note.instrumentId} at bar {note.barIndex}")
    print(f"  Attributes: limb={note.limbId}, style={note.hitStyle}, aspect={note.aspect}")
    
    # Test note serialization
    note_dict = note.to_dict()
    assert isinstance(note_dict, dict), "Note serialization failed"
    assert note_dict['instrumentId'] == 'kick', "Note data mismatch"
    print(f"✓ Note serialization works")
    
    # Test GM drum mapping
    kick_pitch = instrument_id_to_midi_pitch("kick")
    assert kick_pitch == 36, "Kick mapping incorrect"
    snare_pitch = instrument_id_to_midi_pitch("snare_center")
    assert snare_pitch == 38, "Snare mapping incorrect"
    print(f"✓ GM mapping: kick={kick_pitch}, snare={snare_pitch}")
    
    # Test reverse mapping
    inst_from_pitch = midi_pitch_to_instrument_id(42)
    print(f"✓ Reverse mapping: pitch 42 → {inst_from_pitch}")
    
    # Test track creation
    notes = [
        create_drum_note(0, 0, 36, 100, "kick"),
        create_drum_note(0, 480, 38, 90, "snare_center"),
        create_drum_note(0, 960, 42, 70, "hihat_closed"),
    ]
    
    perf_spec = create_default_performance_spec("rock")
    
    track = DrumTrackForDCSM(
        track_id=make_track_id(),
        style_id="rock",
        resolution_ppq=960,
        notes=notes,
        performance_spec=perf_spec,
    )
    print(f"✓ Created track: {len(track.notes)} notes, {track.resolution_ppq} PPQ")
    
    # Test track serialization
    track_dict = track.to_dict()
    assert isinstance(track_dict, dict), "Track serialization failed"
    assert len(track_dict['notes']) == 3, "Track notes count mismatch"
    assert track_dict['resolution_ppq'] == 960, "Resolution mismatch"
    print(f"✓ Track serialization works")
    
    # Test enums
    print(f"✓ Enums: Limbs={len(LimbId)}, HitStyles={len(HitStyle)}, Aspects={len(NoteAspect)}")
    
    print("✅ dcsm_drumtrack_schema tests PASSED\n")
    return True


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("JAMSTIX INTEGRATION MODULE TESTS")
    print("="*60)
    
    results = []
    
    try:
        results.append(("part_types_config", test_part_types()))
    except Exception as e:
        print(f"❌ part_types_config FAILED: {e}")
        results.append(("part_types_config", False))
    
    try:
        results.append(("power_model", test_power_model()))
    except Exception as e:
        print(f"❌ power_model FAILED: {e}")
        results.append(("power_model", False))
    
    try:
        results.append(("dcsm_drumtrack_schema", test_drumtrack_schema()))
    except Exception as e:
        print(f"❌ dcsm_drumtrack_schema FAILED: {e}")
        results.append(("dcsm_drumtrack_schema", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for module, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {module}")
    
    print(f"\nTotal: {passed}/{total} modules passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Modules are ready for integration.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix issues before proceeding.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
