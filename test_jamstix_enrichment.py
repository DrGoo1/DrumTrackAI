#!/usr/bin/env python3
"""
Test the new Jamstix enrichment module
"""

import sys
from backend.drum_generation.jamstix_attributes import (
    assign_limb,
    compute_priority,
    assign_aspect,
    assign_hit_style,
    assign_hat_open_level,
    compute_timing_offset_ms,
    enrich_internal_events_with_jamstix_attrs,
)

def test_limb_assignment():
    """Test limb assignment"""
    print("Testing limb assignment...")
    assert assign_limb("kick") == "RF"
    assert assign_limb("snare_center") == "RH"
    assert assign_limb("hihat_closed") == "LH"
    assert assign_limb("hihat_pedal") == "LF"
    assert assign_limb("unknown") == "other"
    print("✓ Limb assignment works correctly")

def test_priority_computation():
    """Test priority computation"""
    print("\nTesting priority computation...")
    
    # Fill should be high priority
    fill_event = {
        "instrument_id": "snare_center",
        "isFill": True,
        "isAccent": False,
        "isGhost": False,
        "bar_pos_frac": 0.0,
    }
    priority = compute_priority(fill_event)
    assert priority >= 0.85, f"Fill priority should be high, got {priority}"
    print(f"✓ Fill priority: {priority:.2f}")
    
    # Ghost should be low priority
    ghost_event = {
        "instrument_id": "snare_center",
        "isFill": False,
        "isAccent": False,
        "isGhost": True,
        "bar_pos_frac": 0.25,
    }
    priority = compute_priority(ghost_event)
    assert priority <= 0.5, f"Ghost priority should be low, got {priority}"
    print(f"✓ Ghost priority: {priority:.2f}")
    
    # Accent snare should be high
    accent_event = {
        "instrument_id": "snare_center",
        "isFill": False,
        "isAccent": True,
        "isGhost": False,
        "bar_pos_frac": 0.5,
    }
    priority = compute_priority(accent_event)
    assert priority >= 0.75, f"Accent priority should be high, got {priority}"
    print(f"✓ Accent priority: {priority:.2f}")

def test_aspect_assignment():
    """Test aspect classification"""
    print("\nTesting aspect assignment...")
    
    fill_event = {"isFill": True, "isAccent": False}
    assert assign_aspect(fill_event) == "fill"
    
    accent_event = {"isFill": False, "isAccent": True}
    assert assign_aspect(accent_event) == "accent"
    
    groove_event = {"isFill": False, "isAccent": False}
    assert assign_aspect(groove_event) == "groove"
    
    print("✓ Aspect classification: fill, accent, groove")

def test_hit_style():
    """Test hit style detection"""
    print("\nTesting hit style detection...")
    
    ghost_snare = {
        "instrument_id": "snare_center",
        "isGhost": True,
        "isFill": False,
    }
    assert assign_hit_style(ghost_snare) == "bounce"
    
    fill_tom = {
        "instrument_id": "tom_high",
        "isGhost": False,
        "isFill": True,
    }
    assert assign_hit_style(fill_tom) == "double"
    
    normal_kick = {
        "instrument_id": "kick",
        "isGhost": False,
        "isFill": False,
    }
    assert assign_hit_style(normal_kick) == "single"
    
    print("✓ Hit styles: bounce, double, single")

def test_hat_open_level():
    """Test hat open level"""
    print("\nTesting hat open level...")
    
    # Non-hat should return 0
    kick_event = {"instrument_id": "kick", "isAccent": False}
    assert assign_hat_open_level(kick_event, 0.5) == 0.0
    
    # Hat with global openness
    hat_event = {"instrument_id": "hihat_closed", "isAccent": False}
    level = assign_hat_open_level(hat_event, 0.5)
    assert level == 0.5
    
    # Hat with accent
    hat_accent = {"instrument_id": "hihat_open", "isAccent": True}
    level = assign_hat_open_level(hat_accent, 0.3)
    assert level == 0.5  # 0.3 + 0.2
    
    print(f"✓ Hat open levels computed correctly")

def test_timing_offset():
    """Test timing offset calculation"""
    print("\nTesting timing offset...")
    
    # Kick should have minimal offset
    kick_event = {
        "instrument_id": "kick",
        "bar_pos_frac": 0.0,
    }
    offset = compute_timing_offset_ms(kick_event, 0.5)
    assert abs(offset) <= 2.0, f"Kick offset should be small, got {offset}"
    print(f"✓ Kick offset: {offset:.2f}ms (minimal)")
    
    # Snare with laid-back feel
    snare_event = {
        "instrument_id": "snare_center",
        "bar_pos_frac": 0.5,
    }
    offset = compute_timing_offset_ms(snare_event, 0.8)
    assert offset > 0, f"Laid-back should delay, got {offset}"
    print(f"✓ Laid-back snare offset: {offset:.2f}ms (delayed)")
    
    # Pushed feel
    offset = compute_timing_offset_ms(snare_event, -0.8)
    assert offset < 0, f"Pushed should advance, got {offset}"
    print(f"✓ Pushed snare offset: {offset:.2f}ms (early)")

def test_full_enrichment():
    """Test complete enrichment pipeline"""
    print("\nTesting full enrichment pipeline...")
    
    # Create mock internal events
    events = [
        {
            "time_sec": 0.0,
            "length_sec": 0.125,
            "instrument_id": "kick",
            "midi_pitch": 36,
            "velocity": 100,
            "isGhost": False,
            "isAccent": False,
            "isFill": False,
            "barIndex": 0,
            "barStartTime": 0.0,
            "barEndTime": 2.0,
        },
        {
            "time_sec": 1.0,
            "length_sec": 0.125,
            "instrument_id": "snare_center",
            "midi_pitch": 38,
            "velocity": 110,
            "isGhost": False,
            "isAccent": True,
            "isFill": False,
            "barIndex": 0,
            "barStartTime": 0.0,
            "barEndTime": 2.0,
        },
        {
            "time_sec": 0.5,
            "length_sec": 0.125,
            "instrument_id": "hihat_closed",
            "midi_pitch": 42,
            "velocity": 80,
            "isGhost": True,
            "isAccent": False,
            "isFill": False,
            "barIndex": 0,
            "barStartTime": 0.0,
            "barEndTime": 2.0,
        },
    ]
    
    # Enrich events
    enriched = enrich_internal_events_with_jamstix_attrs(
        events,
        laid_back_amount=0.5,
        global_hat_openness=0.3,
    )
    
    print(f"✓ Enriched {len(enriched)} events")
    
    # Verify enrichment
    kick = enriched[0]
    assert "limbId" in kick
    assert kick["limbId"] == "RF"
    assert "priority" in kick
    assert "aspect" in kick
    assert kick["aspect"] == "groove"
    assert "hitStyle" in kick
    assert "hatOpenLevel" in kick
    assert "timingOffsetMs" in kick
    assert "bar_pos_frac" in kick
    print(f"✓ Kick enriched: limb={kick['limbId']}, priority={kick['priority']:.2f}, aspect={kick['aspect']}")
    
    snare = enriched[1]
    assert snare["aspect"] == "accent"
    assert snare["priority"] > 0.7  # Accent should be high priority
    print(f"✓ Snare enriched: aspect={snare['aspect']}, priority={snare['priority']:.2f}")
    
    hat = enriched[2]
    assert hat["limbId"] == "LH"
    assert hat["hatOpenLevel"] > 0  # Should have openness
    assert hat["aspect"] == "groove"
    print(f"✓ Hat enriched: limb={hat['limbId']}, hatOpen={hat['hatOpenLevel']:.2f}")

def main():
    print("=" * 60)
    print("JAMSTIX ENRICHMENT MODULE TESTS")
    print("=" * 60)
    
    try:
        test_limb_assignment()
        test_priority_computation()
        test_aspect_assignment()
        test_hit_style()
        test_hat_open_level()
        test_timing_offset()
        test_full_enrichment()
        
        print("\n" + "=" * 60)
        print("✅ ALL ENRICHMENT TESTS PASSED!")
        print("=" * 60)
        print("\nJamstix enrichment module is ready for production!")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
