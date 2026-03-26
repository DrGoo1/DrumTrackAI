#!/usr/bin/env python3
"""
Jamstix-Style Drum Event Attributes
====================================
Enriches drum events with Jamstix-inspired attributes:
- Limb assignment
- Priority (importance weighting)
- Timing offset (laid-back/pushed feel)
- Hit style (single/double/bounce)
- Aspect (groove/accent/fill)
- Hat openness level
"""
from typing import List, Dict, Any
from dataclasses import dataclass

# Limb assignment by instrument
LIMBS_BY_INSTRUMENT = {
    "kick": "RF",
    "snare_center": "RH",
    "snare_rim": "RH",
    "snare_ghost": "RH",
    "hihat_closed": "LH",
    "hihat_open": "LH",
    "hihat_pedal": "LF",
    "ride_bow": "RH",
    "ride_bell": "RH",
    "ride_edge": "RH",
    "tom_high": "RH",
    "tom_mid": "RH",
    "tom_floor": "RH",
    "tom_low": "RH",
    "crash_1": "RH",
    "crash_2": "RH",
    "splash": "RH",
    "china": "RH",
}

@dataclass
class JamstixNoteAttributes:
    """Jamstix-style note attributes"""
    velocity: int  # 1-127
    priority: float  # 0.0-1.0
    timing_offset_ms: float  # -50 to +50
    aspect: str  # "groove", "accent", "fill"
    limb_id: str  # "LH", "RH", "LF", "RF"
    hit_style: str  # "single", "double", "bounce"
    hat_open_level: float  # 0.0-1.0 (for hi-hats only)
    locked: bool  # preserve across regeneration

def assign_limb(instrument_id: str) -> str:
    """Assign limb based on instrument"""
    return LIMBS_BY_INSTRUMENT.get(instrument_id, "RH")

def calculate_priority(
    instrument_id: str,
    is_accent: bool,
    is_ghost: bool,
    beat_position: float,
    bar_position: float
) -> float:
    """
    Calculate Jamstix-style priority (0.0-1.0)
    
    High priority:
    - Accented snares
    - Crashes on beat 1
    - Kick on strong beats
    
    Low priority:
    - Ghost notes
    - Hi-hat upbeats
    """
    priority = 0.5  # base
    
    # Accent boost
    if is_accent:
        priority += 0.3
    
    # Ghost reduction
    if is_ghost:
        priority -= 0.3
    
    # Strong beat boost
    if beat_position % 1.0 == 0:  # On the beat
        priority += 0.15
    
    # Backbeat boost (beats 2 and 4)
    beat_in_bar = (bar_position * 4) % 4
    if instrument_id == "snare_center" and beat_in_bar in (2, 4):
        priority += 0.2
    
    # Crash on downbeat
    if "crash" in instrument_id and bar_position == 0:
        priority += 0.25
    
    return max(0.0, min(1.0, priority))

def calculate_timing_offset(
    feel: str,
    instrument_id: str,
    subdivision: int
) -> float:
    """
    Calculate timing offset in milliseconds
    
    Feel types:
    - "on_the_beat": 0ms offset
    - "laid_back": +5 to +15ms (snare/hats delayed)
    - "pushed": -5 to -10ms (ahead of beat)
    - "swing": varies by subdivision
    """
    if feel == "on_the_beat":
        return 0.0
    
    elif feel == "laid_back":
        if instrument_id == "snare_center":
            return 10.0  # Snare behind
        elif "hihat" in instrument_id:
            return 7.0  # Hats slightly behind
        else:
            return 3.0
    
    elif feel == "pushed":
        if instrument_id == "snare_center":
            return -8.0  # Snare ahead
        elif "hihat" in instrument_id:
            return -5.0
        else:
            return -3.0
    
    elif feel == "swing":
        # Swing: eighth notes alternating long-short
        if subdivision % 2 == 1:  # Off-beat
            return 15.0  # Delay off-beats
        else:
            return 0.0
    
    return 0.0

def determine_aspect(
    is_fill: bool,
    is_accent: bool,
    bar_position: float
) -> str:
    """Determine note aspect: groove, accent, or fill"""
    if is_fill:
        return "fill"
    elif is_accent:
        return "accent"
    else:
        return "groove"

def enrich_drum_events_with_jamstix_attrs(
    events: List[Dict[str, Any]],
    feel: str = "on_the_beat",
    global_hat_openness: float = 0.2
) -> List[Dict[str, Any]]:
    """
    Enrich drum events with Jamstix-style attributes
    
    Args:
        events: List of drum events with basic info
        feel: "on_the_beat", "laid_back", "pushed", "swing"
        global_hat_openness: 0.0-1.0
    
    Returns:
        Events enriched with Jamstix attributes
    """
    enriched = []
    
    for ev in events:
        inst = ev["instrument_id"]
        velocity = ev.get("velocity", 100)
        
        # Determine characteristics
        is_ghost = velocity < 45
        is_accent = velocity > 100
        is_fill = ev.get("is_fill", False)
        
        # Calculate attributes
        limb = assign_limb(inst)
        priority = calculate_priority(
            inst,
            is_accent,
            is_ghost,
            ev.get("beat_position", 0),
            ev.get("bar_position", 0)
        )
        timing_offset = calculate_timing_offset(
            feel,
            inst,
            ev.get("subdivision", 16)
        )
        aspect = determine_aspect(is_fill, is_accent, ev.get("bar_position", 0))
        
        # Hit style (single by default, double for rolls)
        hit_style = "double" if ev.get("is_roll", False) else "single"
        
        # Hat openness
        hat_open = global_hat_openness if "hihat" in inst else 0.0
        if inst == "hihat_open":
            hat_open = 1.0
        elif inst == "hihat_closed":
            hat_open = 0.0
        
        # Build enriched event
        enriched_ev = {
            **ev,
            "velocity": velocity,
            "priority": priority,
            "timing_offset_ms": timing_offset,
            "aspect": aspect,
            "limb_id": limb,
            "hit_style": hit_style,
            "hat_open_level": hat_open,
            "locked": False
        }
        
        enriched.append(enriched_ev)
    
    return enriched

def validate_limb_conflicts(events: List[Dict[str, Any]]) -> List[str]:
    """
    Check for limb conflicts (impossible to play)
    
    Returns list of conflict descriptions
    """
    conflicts = []
    
    # Sort by time
    sorted_events = sorted(events, key=lambda e: e.get("time_sec", 0))
    
    for i in range(len(sorted_events) - 1):
        ev1 = sorted_events[i]
        ev2 = sorted_events[i + 1]
        
        time_diff = ev2.get("time_sec", 0) - ev1.get("time_sec", 0)
        
        # If same limb and < 50ms apart, likely impossible
        if (ev1.get("limb_id") == ev2.get("limb_id") and 
            time_diff < 0.05 and time_diff > 0):
            
            conflicts.append(
                f"Limb conflict: {ev1['limb_id']} at {ev1.get('time_sec', 0):.3f}s "
                f"and {ev2.get('time_sec', 0):.3f}s ({time_diff*1000:.1f}ms apart)"
            )
    
    return conflicts

# Example usage
if __name__ == "__main__":
    # Test data
    test_events = [
        {
            "instrument_id": "kick",
            "time_sec": 0.0,
            "velocity": 110,
            "beat_position": 1.0,
            "bar_position": 0.0
        },
        {
            "instrument_id": "snare_center",
            "time_sec": 0.5,
            "velocity": 115,
            "beat_position": 2.0,
            "bar_position": 0.25
        },
        {
            "instrument_id": "hihat_closed",
            "time_sec": 0.25,
            "velocity": 65,
            "beat_position": 1.5,
            "bar_position": 0.125
        }
    ]
    
    enriched = enrich_drum_events_with_jamstix_attrs(
        test_events,
        feel="laid_back",
        global_hat_openness=0.3
    )
    
    import json
    print(json.dumps(enriched, indent=2))
    
    conflicts = validate_limb_conflicts(enriched)
    if conflicts:
        print("\nLimb Conflicts:")
        for c in conflicts:
            print(f"  - {c}")
