#!/usr/bin/env python3
"""
Jamstix Attributes - COMPLETE BRAIN IMPLEMENTATION
==================================================
Re-implements Jamstix-style drum event attributes in modern Python
for DrumTracKAI backend integration

This module enriches drum events with:
- Limb assignment (LH, RH, LF, RF)
- Priority (0.0-1.0 for limb conflict resolution)
- Timing offset (micro-timing adjustments)
- Aspect (groove/accent/fill)
- Hit style (single/double/bounce/flam)
- Hat openness (0.0-1.0)
- Playability validation
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# ============================================================================
# CONSTANTS & ENUMS
# ============================================================================

class Limb(str, Enum):
    """Limb assignments for drum hits"""
    LEFT_HAND = "LH"
    RIGHT_HAND = "RH"
    LEFT_FOOT = "LF"
    RIGHT_FOOT = "RF"
    OTHER = "other"

class Aspect(str, Enum):
    """Hit aspect classification"""
    GROOVE = "groove"      # Main pattern hits
    ACCENT = "accent"      # Emphasized hits
    FILL = "fill"          # Fill/transition hits
    GHOST = "ghost"        # Ghost notes

class HitStyle(str, Enum):
    """How the hit is executed"""
    SINGLE = "single"      # Normal single stroke
    DOUBLE = "double"      # Double stroke (diddle)
    BOUNCE = "bounce"      # Controlled bounce
    FLAM = "flam"          # Flam (grace note + main)
    DRAG = "drag"          # Drag (double grace + main)

# Limb assignment map by instrument
LIMBS_BY_INSTRUMENT = {
    "kick": Limb.RIGHT_FOOT,
    "snare_center": Limb.RIGHT_HAND,
    "snare_rim": Limb.RIGHT_HAND,
    "snare_ghost": Limb.LEFT_HAND,
    "hihat_closed": Limb.LEFT_HAND,
    "hihat_open": Limb.LEFT_HAND,
    "hihat_pedal": Limb.LEFT_FOOT,
    "ride_bow": Limb.RIGHT_HAND,
    "ride_bell": Limb.RIGHT_HAND,
    "ride_edge": Limb.RIGHT_HAND,
    "tom_high": Limb.RIGHT_HAND,
    "tom_mid": Limb.RIGHT_HAND,
    "tom_low": Limb.RIGHT_HAND,
    "tom_floor": Limb.RIGHT_HAND,
    "crash_1": Limb.RIGHT_HAND,
    "crash_2": Limb.RIGHT_HAND,
    "splash": Limb.RIGHT_HAND,
    "crash_china": Limb.RIGHT_HAND,
}

# Priority base values by instrument (0.0-1.0)
PRIORITY_BY_INSTRUMENT = {
    "kick": 1.0,           # Highest priority (foundation)
    "snare_center": 0.95,  # Very high (backbeat)
    "crash_1": 0.9,        # High (accents)
    "crash_2": 0.9,
    "ride_bow": 0.7,       # Medium-high (timekeeping)
    "tom_high": 0.7,
    "tom_mid": 0.7,
    "tom_low": 0.7,
    "tom_floor": 0.7,
    "hihat_closed": 0.6,   # Medium (pattern)
    "hihat_open": 0.6,
    "snare_rim": 0.5,      # Medium-low (color)
    "ride_bell": 0.5,
    "hihat_pedal": 0.4,    # Lower (subtle)
    "snare_ghost": 0.2,    # Lowest (texture)
}

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class JamstixNoteAttributes:
    """Complete Jamstix-style attributes for a drum note"""
    # Core attributes
    velocity: int                    # MIDI velocity (0-127)
    priority: float                  # Limb conflict priority (0.0-1.0)
    timing_offset_ms: float          # Micro-timing offset in milliseconds
    aspect: str                      # groove/accent/fill/ghost
    
    # Physical attributes
    limb_id: str                     # LH/RH/LF/RF/other
    hit_style: str                   # single/double/bounce/flam/drag
    hat_open_level: float            # 0.0=closed, 1.0=fully open
    
    # Flags
    locked: bool = False             # If true, don't modify in generation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "velocity": self.velocity,
            "priority": self.priority,
            "timingOffsetMs": self.timing_offset_ms,
            "aspect": self.aspect,
            "limbId": self.limb_id,
            "hitStyle": self.hit_style,
            "hatOpenLevel": self.hat_open_level,
            "locked": self.locked
        }

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def assign_limb(instrument_id: str) -> str:
    """Assign limb based on instrument"""
    return LIMBS_BY_INSTRUMENT.get(instrument_id, Limb.OTHER).value

def calculate_priority(
    instrument_id: str,
    aspect: str,
    velocity: int,
    is_downbeat: bool = False
) -> float:
    """
    Calculate note priority for limb conflict resolution
    
    Priority factors:
    - Base instrument priority
    - Aspect (accent/fill > groove > ghost)
    - Velocity (higher = slightly higher priority)
    - Position (downbeat = higher priority)
    """
    base = PRIORITY_BY_INSTRUMENT.get(instrument_id, 0.5)
    
    # Aspect multiplier
    aspect_mult = 1.0
    if aspect == Aspect.ACCENT.value:
        aspect_mult = 1.2
    elif aspect == Aspect.FILL.value:
        aspect_mult = 1.1
    elif aspect == Aspect.GHOST.value:
        aspect_mult = 0.5
    
    # Velocity factor (0-127 -> 0.9-1.1)
    vel_factor = 0.9 + (velocity / 127.0) * 0.2
    
    # Downbeat boost
    position_mult = 1.15 if is_downbeat else 1.0
    
    priority = base * aspect_mult * vel_factor * position_mult
    
    # Clamp to 0.0-1.0
    return max(0.0, min(1.0, priority))

def calculate_timing_offset(
    feel: str,
    subdivision_pos: float,
    instrument_id: str,
    aspect: str
) -> float:
    """
    Calculate micro-timing offset in milliseconds
    
    Feel types:
    - on_the_beat: 0ms offset
    - laid_back: -5 to -20ms
    - pushed: +2 to +8ms
    - swing: varies by subdivision
    """
    if feel == "on_the_beat":
        return 0.0
    
    elif feel == "laid_back":
        # Hihat on the beat, snare slightly behind
        if "hihat" in instrument_id:
            return 0.0
        elif "snare" in instrument_id:
            return -15.0  # 15ms late (pocket)
        elif "kick" in instrument_id:
            return -5.0   # Slightly late
        else:
            return -8.0
    
    elif feel == "pushed":
        # Slightly ahead of the beat
        if "snare" in instrument_id:
            return +5.0
        else:
            return +3.0
    
    elif feel == "swing":
        # 8th notes on 2 and 4 are delayed
        frac = subdivision_pos % 1.0
        if 0.4 < frac < 0.6:  # Around the "and" of each beat
            return +20.0  # Swing the 8th note
        return 0.0
    
    return 0.0

def determine_aspect(
    bar_pos_frac: float,
    velocity: int,
    instrument_id: str,
    is_fill_bar: bool = False
) -> str:
    """
    Determine note aspect (groove/accent/fill/ghost)
    
    Rules:
    - Ghost notes: low velocity (<40)
    - Fills: in designated fill bars
    - Accents: high velocity (>100) or crash hits
    - Groove: everything else
    """
    # Ghost notes
    if velocity < 40:
        return Aspect.GHOST.value
    
    # Fills
    if is_fill_bar:
        return Aspect.FILL.value
    
    # Accents
    if velocity > 100 or "crash" in instrument_id:
        return Aspect.ACCENT.value
    
    # Default: groove
    return Aspect.GROOVE.value

def determine_hit_style(
    instrument_id: str,
    prev_same_limb_time: Optional[float],
    current_time: float
) -> str:
    """
    Determine hit style based on timing and instrument
    
    Rules:
    - Flam: If preceded by opposite hand within 30ms
    - Double: If preceded by same hand within 50-150ms (diddle)
    - Bounce: For fast repeated hits on same drum
    - Single: Default
    """
    if prev_same_limb_time is None:
        return HitStyle.SINGLE.value
    
    time_diff_ms = (current_time - prev_same_limb_time) * 1000
    
    # Flam detection (would need opposite hand timing)
    # Simplified: check for very fast hits
    if time_diff_ms < 30:
        return HitStyle.FLAM.value
    
    # Double stroke (diddle)
    if 50 < time_diff_ms < 150 and "snare" in instrument_id:
        return HitStyle.DOUBLE.value
    
    # Bounce
    if time_diff_ms < 100 and instrument_id == "snare_center":
        return HitStyle.BOUNCE.value
    
    return HitStyle.SINGLE.value

def calculate_hat_openness(
    global_hat_openness: float,
    bar_pos_frac: float,
    aspect: str
) -> float:
    """
    Calculate hihat openness level (0.0-1.0)
    
    Factors:
    - Global setting (user preference)
    - Position in bar (open on offbeats)
    - Aspect (accents more open)
    """
    base_open = global_hat_openness
    
    # Offbeat positions slightly more open
    beat_frac = (bar_pos_frac * 4) % 1.0  # 0-1 within each quarter note
    if 0.4 < beat_frac < 0.6:  # Around the "and"
        base_open += 0.2
    
    # Accents more open
    if aspect == Aspect.ACCENT.value:
        base_open += 0.3
    
    return max(0.0, min(1.0, base_open))

# ============================================================================
# MAIN ENRICHMENT FUNCTION
# ============================================================================

def enrich_drum_events_with_jamstix_attrs(
    events: List[Dict[str, Any]],
    feel: str = "on_the_beat",
    global_hat_openness: float = 0.2,
    fill_bar_indices: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    """
    Enrich drum events with complete Jamstix-style attributes
    
    Args:
        events: List of drum events with at minimum:
                - time_sec: time in seconds
                - instrument_id: drum instrument
                - velocity: MIDI velocity
                - barIndex: (optional) bar number
                - barStartTime: (optional) start time of bar
                - barEndTime: (optional) end time of bar
        
        feel: Timing feel (on_the_beat/laid_back/pushed/swing)
        global_hat_openness: Base hihat openness (0.0-1.0)
        fill_bar_indices: List of bar indices that are fills
    
    Returns:
        events: Same list with added Jamstix attributes
    """
    fill_bar_indices = fill_bar_indices or []
    limb_last_hit_time = {}  # Track last hit time per limb
    
    for ev in events:
        inst = ev["instrument_id"]
        bar_index = ev.get("barIndex", 0)
        bar_start = ev.get("barStartTime", 0.0)
        bar_end = ev.get("barEndTime", bar_start + 4.0)
        t_sec = ev["time_sec"]
        velocity = ev.get("velocity", 80)
        
        # Calculate bar position fraction (0.0-1.0)
        bar_len = max(bar_end - bar_start, 1e-6)
        bar_pos_frac = (t_sec - bar_start) / bar_len
        bar_pos_frac = max(0.0, min(0.999999, bar_pos_frac))
        
        # Determine if this is a downbeat
        is_downbeat = bar_pos_frac < 0.05
        
        # Determine if this is in a fill bar
        is_fill_bar = bar_index in fill_bar_indices
        
        # Assign limb
        limb_id = assign_limb(inst)
        
        # Determine aspect
        aspect = determine_aspect(bar_pos_frac, velocity, inst, is_fill_bar)
        
        # Calculate priority
        priority = calculate_priority(inst, aspect, velocity, is_downbeat)
        
        # Calculate timing offset
        timing_offset_ms = calculate_timing_offset(
            feel, bar_pos_frac, inst, aspect
        )
        explicit_offset = ev.get("timing_offset_ms")
        if explicit_offset is None:
            explicit_offset = ev.get("humanize_offset_ms")
        if explicit_offset is not None:
            try:
                timing_offset_ms += float(explicit_offset)
            except (TypeError, ValueError):
                pass
        
        # Determine hit style
        prev_time = limb_last_hit_time.get(limb_id)
        hit_style = determine_hit_style(inst, prev_time, t_sec)
        limb_last_hit_time[limb_id] = t_sec
        
        # Calculate hat openness
        if "hihat" in inst:
            hat_open_level = calculate_hat_openness(
                global_hat_openness, bar_pos_frac, aspect
            )
        else:
            hat_open_level = 0.0
        
        # Create Jamstix attributes
        attrs = JamstixNoteAttributes(
            velocity=velocity,
            priority=priority,
            timing_offset_ms=timing_offset_ms,
            aspect=aspect,
            limb_id=limb_id,
            hit_style=hit_style,
            hat_open_level=hat_open_level,
            locked=False
        )
        
        # Add to event
        ev["jamstix_attrs"] = attrs.to_dict()
        ev["bar_pos_frac"] = bar_pos_frac
    
    return events

# ============================================================================
# LIMB CONFLICT DETECTION
# ============================================================================

def detect_limb_conflicts(events: List[Dict[str, Any]], time_window_ms: float = 50.0) -> List[Dict[str, Any]]:
    """
    Detect limb conflicts (same limb, two hits within time window)
    
    Returns list of conflict warnings:
    [{
        "limb": "RH",
        "time1": 1.5,
        "time2": 1.52,
        "instrument1": "snare",
        "instrument2": "tom_high",
        "priority1": 0.9,
        "priority2": 0.7
    }]
    """
    conflicts = []
    
    # Group by limb
    by_limb = {}
    for ev in events:
        limb = ev.get("jamstix_attrs", {}).get("limbId", "other")
        if limb not in by_limb:
            by_limb[limb] = []
        by_limb[limb].append(ev)
    
    # Check each limb for conflicts
    for limb, limb_events in by_limb.items():
        # Sort by time
        sorted_events = sorted(limb_events, key=lambda e: e["time_sec"])
        
        for i in range(len(sorted_events) - 1):
            ev1 = sorted_events[i]
            ev2 = sorted_events[i + 1]
            
            time_diff_ms = (ev2["time_sec"] - ev1["time_sec"]) * 1000
            
            if time_diff_ms < time_window_ms:
                conflicts.append({
                    "limb": limb,
                    "time1": ev1["time_sec"],
                    "time2": ev2["time_sec"],
                    "time_diff_ms": time_diff_ms,
                    "instrument1": ev1["instrument_id"],
                    "instrument2": ev2["instrument_id"],
                    "priority1": ev1.get("jamstix_attrs", {}).get("priority", 0.5),
                    "priority2": ev2.get("jamstix_attrs", {}).get("priority", 0.5),
                })
    
    return conflicts

def resolve_limb_conflicts(events: List[Dict[str, Any]], conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Resolve limb conflicts by removing lower-priority hits
    
    Returns filtered events list with conflicts resolved
    """
    remove_times = set()
    
    for conflict in conflicts:
        p1 = conflict["priority1"]
        p2 = conflict["priority2"]
        
        # Remove lower priority event
        if p1 < p2:
            remove_times.add(conflict["time1"])
        else:
            remove_times.add(conflict["time2"])
    
    # Filter events
    filtered = [ev for ev in events if ev["time_sec"] not in remove_times]
    
    return filtered

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Example usage
    test_events = [
        {"time_sec": 0.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 4.0},
        {"time_sec": 0.5, "instrument_id": "snare_center", "velocity": 90, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 4.0},
        {"time_sec": 1.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 4.0},
        {"time_sec": 1.5, "instrument_id": "snare_center", "velocity": 95, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 4.0},
    ]
    
    enriched = enrich_drum_events_with_jamstix_attrs(
        test_events,
        feel="laid_back",
        global_hat_openness=0.3
    )
    
    print("Enriched Events:")
    for ev in enriched:
        print(f"  {ev['time_sec']:.2f}s - {ev['instrument_id']}")
        print(f"    Limb: {ev['jamstix_attrs']['limbId']}")
        print(f"    Priority: {ev['jamstix_attrs']['priority']:.2f}")
        print(f"    Timing: {ev['jamstix_attrs']['timingOffsetMs']:.1f}ms")
        print(f"    Aspect: {ev['jamstix_attrs']['aspect']}")
        print()
