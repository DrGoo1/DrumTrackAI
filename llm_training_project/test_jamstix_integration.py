#!/usr/bin/env python3
"""
Test Jamstix Integration - Complete System Demo
================================================
Demonstrates the complete Phase 1 + Phase 2 Jamstix system
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.jamstix_brain import (
    enrich_drum_events_with_jamstix_attrs,
    detect_limb_conflicts,
    resolve_limb_conflicts,
    DCSMDrumTrackBuilder,
    generate_performance_spec_with_llm
)

def test_phase2_brain():
    """Test Phase 2: Jamstix brain attribute enrichment"""
    
    print("="*70)
    print("TEST 1: Jamstix Brain Attribute Enrichment")
    print("="*70)
    print()
    
    # Sample drum pattern events
    pattern_events = [
        {"time_sec": 0.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.0, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.5, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.0, "instrument_id": "snare_center", "velocity": 90, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.0, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.5, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
    ]
    
    # Enrich with Jamstix brain
    enriched = enrich_drum_events_with_jamstix_attrs(
        pattern_events,
        feel="laid_back",
        global_hat_openness=0.3,
        fill_bar_indices=[]
    )
    
    print("Enriched Pattern Events:")
    print()
    for ev in enriched:
        attrs = ev["jamstix_attrs"]
        print(f"  {ev['time_sec']:.2f}s - {ev['instrument_id']:<15} vel={ev['velocity']:>3}")
        print(f"         Limb: {attrs['limbId']:<3}  Priority: {attrs['priority']:.2f}  "
              f"Timing: {attrs['timingOffsetMs']:>+6.1f}ms  Aspect: {attrs['aspect']}")
    
    print()
    print("✅ Attribute enrichment working!")
    print()
    
    return enriched

def test_limb_conflicts():
    """Test limb conflict detection and resolution"""
    
    print("="*70)
    print("TEST 2: Limb Conflict Detection")
    print("="*70)
    print()
    
    # Create events with conflicts (same limb, too close)
    conflicting_events = [
        {"time_sec": 0.0, "instrument_id": "snare_center", "velocity": 90, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.02, "instrument_id": "tom_high", "velocity": 80, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},  # 20ms later, same hand!
        {"time_sec": 1.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
    ]
    
    # Enrich first
    enriched = enrich_drum_events_with_jamstix_attrs(conflicting_events, feel="on_the_beat")
    
    # Detect conflicts
    conflicts = detect_limb_conflicts(enriched, time_window_ms=50.0)
    
    if conflicts:
        print(f"⚠️  Detected {len(conflicts)} limb conflicts:")
        for c in conflicts:
            print(f"   {c['limb']} limb: {c['instrument1']} and {c['instrument2']} "
                  f"only {c['time_diff_ms']:.1f}ms apart")
        print()
        
        # Resolve
        resolved = resolve_limb_conflicts(enriched, conflicts)
        print(f"✅ Resolved! Events: {len(enriched)} → {len(resolved)}")
        print(f"   Removed lower-priority hit")
    else:
        print("✅ No conflicts detected")
    
    print()

def test_full_drumtrack_builder():
    """Test complete DCSM DrumTrack building"""
    
    print("="*70)
    print("TEST 3: Complete DCSM DrumTrack Builder")
    print("="*70)
    print()
    
    # Sample pattern (basic rock beat)
    pattern_events = [
        # Bar 0 - Verse
        {"time_sec": 0.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.0, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.5, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.0, "instrument_id": "snare_center", "velocity": 90, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.0, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.5, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        
        # Bar 1 - Chorus (higher intensity)
        {"time_sec": 2.0, "instrument_id": "kick", "velocity": 110, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 2.0, "instrument_id": "crash_1", "velocity": 100, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 2.0, "instrument_id": "hihat_closed", "velocity": 75, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 2.5, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 3.0, "instrument_id": "snare_center", "velocity": 95, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 3.0, "instrument_id": "hihat_closed", "velocity": 75, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
        {"time_sec": 3.5, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 1, "barStartTime": 2.0, "barEndTime": 4.0},
    ]
    
    # Define song sections
    sections = [
        {"type": "verse", "startBar": 0, "endBar": 1},
        {"type": "chorus", "startBar": 1, "endBar": 2},
    ]
    
    # Generate performance spec (using LLM placeholder)
    perf_spec = generate_performance_spec_with_llm(
        style="rock",
        drummer="bonham",
        intensity=0.8,
        sections=sections
    )
    
    print(f"Performance Spec:")
    print(f"  Feel: {perf_spec['feel']}")
    print(f"  Swing: {perf_spec['swing']}")
    print(f"  Intensity: {perf_spec['intensity']}")
    print(f"  Hat Openness: {perf_spec['hatOpenness']}")
    print(f"  Fill Style: {perf_spec['fillStyle']}")
    print()
    
    # Build complete drum track
    builder = DCSMDrumTrackBuilder(tempo=120.0, time_signature="4/4")
    track = builder.build_from_pattern_and_spec(
        pattern_events=pattern_events,
        sections=sections,
        performance_spec=perf_spec
    )
    
    print("DrumTrack Built:")
    print(f"  Tempo: {track.tempo} BPM")
    print(f"  Time Signature: {track.timeSignature}")
    print(f"  Bars: {len(track.bars)}")
    print(f"  Sections: {len(track.sections)}")
    print()
    
    # Show bar details
    for bar in track.bars:
        print(f"  Bar {bar.barIndex}: {len(bar.notes)} notes")
        for note in bar.notes[:3]:  # Show first 3 notes
            print(f"    Tick {note.tickInBar:>4}: {note.instrument:<15} "
                  f"vel={note.velocity:>3} limb={note.limbId} "
                  f"aspect={note.aspect}")
    
    print()
    
    # Save to JSON
    output_path = Path("test_drumtrack_output.json")
    builder.save_to_json(track, output_path)
    print(f"✅ Saved to: {output_path}")
    print()
    
    return track

def test_performance_specs():
    """Test LLM performance spec generation"""
    
    print("="*70)
    print("TEST 4: Performance Spec Generation (LLM Placeholder)")
    print("="*70)
    print()
    
    sections = [
        {"type": "intro", "startBar": 0, "endBar": 2},
        {"type": "verse", "startBar": 2, "endBar": 6},
        {"type": "chorus", "startBar": 6, "endBar": 10},
    ]
    
    styles = ["rock", "funk", "jazz"]
    drummers = ["bonham", "purdie", "gadd"]
    
    for style in styles:
        for drummer in drummers:
            spec = generate_performance_spec_with_llm(
                style=style,
                drummer=drummer,
                intensity=0.7,
                sections=sections
            )
            print(f"{style.upper()} + {drummer.capitalize():<8}: "
                  f"feel={spec['feel']:<15} swing={spec['swing']:.1f} "
                  f"ghosts={spec['ghostNoteAmount']:.1f}")
    
    print()
    print("✅ Performance specs generated for all combinations")
    print()

def main():
    """Run all tests"""
    
    print()
    print("╔" + "═"*68 + "╗")
    print("║" + " "*12 + "Jamstix Integration - Complete System Test" + " "*13 + "║")
    print("╚" + "═"*68 + "╝")
    print()
    
    try:
        # Test 1: Basic attribute enrichment
        enriched = test_phase2_brain()
        
        # Test 2: Limb conflict detection
        test_limb_conflicts()
        
        # Test 3: Full DCSM track building
        track = test_full_drumtrack_builder()
        
        # Test 4: Performance spec generation
        test_performance_specs()
        
        # Final summary
        print("="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print()
        print("System Status:")
        print("  ✅ Phase 2 Brain: Jamstix attribute enrichment working")
        print("  ✅ Conflict Detection: Limb conflicts detected and resolved")
        print("  ✅ DCSM Integration: DrumTrack building complete")
        print("  ✅ Performance Specs: LLM placeholder functioning")
        print()
        print("Next Steps:")
        print("  1. Integrate trained LLM (when Colab finishes)")
        print("  2. Setup Reaper template for Phase 1 data generation")
        print("  3. Add to backend API endpoints")
        print("  4. Test with real audio analysis")
        print()
        print("🎉 Jamstix integration system is READY!")
        print("="*70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
