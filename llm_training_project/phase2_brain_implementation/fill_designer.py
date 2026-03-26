#!/usr/bin/env python3
"""
Jamstix-Style Fill Designer
============================
Generates drum fills based on Jamstix logic:
- Fill types (tom run, snare roll, cymbal swell)
- Build-ups and transitions
- Rudiment-based fills
"""
from typing import List, Dict, Any
from dataclasses import dataclass
import random

@dataclass
class FillSegment:
    """A drum fill segment"""
    start_beat: float
    duration_beats: float
    fill_type: str  # "tom_run", "snare_roll", "cymbal_build", "rudiment"
    complexity: float  # 0.0-1.0
    direction: str  # "ascending", "descending", "random"
    ends_with_crash: bool

RUDIMENTS = {
    "single_stroke": ["R", "L", "R", "L"],
    "double_stroke": ["RR", "LL", "RR", "LL"],
    "paradiddle": ["R", "L", "RR", "L", "R", "LL"],
    "flam": ["Lf", "R", "Rf", "L"],  # f = flam
    "drag": ["LLr", "R", "RRl", "L"]  # r/l = drag
}

TOM_SEQUENCE_ASCENDING = ["tom_floor", "tom_mid", "tom_high"]
TOM_SEQUENCE_DESCENDING = ["tom_high", "tom_mid", "tom_floor"]

def generate_fill(
    fill_type: str,
    start_beat: float,
    duration_beats: float,
    complexity: float,
    style: str = "rock"
) -> List[Dict[str, Any]]:
    """
    Generate a drum fill
    
    Args:
        fill_type: "tom_run", "snare_roll", "cymbal_build", "mixed"
        start_beat: When fill starts
        duration_beats: How long (typically 1-2 beats)
        complexity: 0.0-1.0 (density and technicality)
        style: "rock", "jazz", "funk"
    
    Returns:
        List of drum hit events
    """
    
    if fill_type == "tom_run":
        return _generate_tom_run(start_beat, duration_beats, complexity)
    
    elif fill_type == "snare_roll":
        return _generate_snare_roll(start_beat, duration_beats, complexity, style)
    
    elif fill_type == "cymbal_build":
        return _generate_cymbal_build(start_beat, duration_beats, complexity)
    
    elif fill_type == "mixed":
        return _generate_mixed_fill(start_beat, duration_beats, complexity, style)
    
    else:
        # Default: simple snare
        return [
            {
                "instrument_id": "snare_center",
                "beat_position": start_beat + i * 0.25,
                "velocity": 100 + int(i * 5),
                "is_fill": True
            }
            for i in range(int(duration_beats * 4))
        ]

def _generate_tom_run(
    start_beat: float,
    duration_beats: float,
    complexity: float
) -> List[Dict[str, Any]]:
    """Generate ascending tom run"""
    hits = []
    
    # Number of hits based on complexity
    num_hits = int(4 + (complexity * 12))  # 4-16 hits
    interval = duration_beats / num_hits
    
    toms = TOM_SEQUENCE_ASCENDING * 10  # Repeat pattern
    
    for i in range(num_hits):
        tom = toms[i % len(TOM_SEQUENCE_ASCENDING)]
        
        hits.append({
            "instrument_id": tom,
            "beat_position": start_beat + (i * interval),
            "velocity": 90 + int(i * 2),  # Build velocity
            "is_fill": True,
            "sticking": "R" if i % 2 == 0 else "L"
        })
    
    # End with crash
    hits.append({
        "instrument_id": "crash_1",
        "beat_position": start_beat + duration_beats,
        "velocity": 120,
        "is_fill": True
    })
    
    return hits

def _generate_snare_roll(
    start_beat: float,
    duration_beats: float,
    complexity: float,
    style: str
) -> List[Dict[str, Any]]:
    """Generate snare roll with rudiment"""
    hits = []
    
    # Choose rudiment based on style
    if style == "jazz":
        rudiment = RUDIMENTS["double_stroke"]
    elif complexity > 0.7:
        rudiment = RUDIMENTS["paradiddle"]
    else:
        rudiment = RUDIMENTS["single_stroke"]
    
    # Calculate hits per beat
    if complexity > 0.7:
        hits_per_beat = 8  # 32nd notes
    elif complexity > 0.4:
        hits_per_beat = 4  # 16th notes
    else:
        hits_per_beat = 2  # 8th notes
    
    total_hits = int(duration_beats * hits_per_beat)
    interval = duration_beats / total_hits
    
    for i in range(total_hits):
        sticking = rudiment[i % len(rudiment)]
        
        # Check for flam or drag
        is_flam = "f" in sticking.lower()
        is_drag = sticking.startswith("RR") or sticking.startswith("LL")
        
        base_velocity = 70 + int((i / total_hits) * 40)  # Build from 70 to 110
        
        hits.append({
            "instrument_id": "snare_center",
            "beat_position": start_beat + (i * interval),
            "velocity": base_velocity,
            "is_fill": True,
            "sticking": sticking.replace("f", "").replace("r", "").replace("l", ""),
            "is_flam": is_flam,
            "is_drag": is_drag
        })
    
    return hits

def _generate_cymbal_build(
    start_beat: float,
    duration_beats: float,
    complexity: float
) -> List[Dict[str, Any]]:
    """Generate cymbal crash build-up"""
    hits = []
    
    # Crashes building up
    num_crashes = int(2 + (complexity * 4))  # 2-6 crashes
    interval = duration_beats / num_crashes
    
    for i in range(num_crashes):
        hits.append({
            "instrument_id": "crash_1" if i % 2 == 0 else "crash_2",
            "beat_position": start_beat + (i * interval),
            "velocity": 80 + int((i / num_crashes) * 40),  # Build to 120
            "is_fill": True
        })
    
    # Add kick hits underneath
    for i in range(int(duration_beats * 2)):
        hits.append({
            "instrument_id": "kick",
            "beat_position": start_beat + (i * 0.5),
            "velocity": 110,
            "is_fill": True
        })
    
    return hits

def _generate_mixed_fill(
    start_beat: float,
    duration_beats: float,
    complexity: float,
    style: str
) -> List[Dict[str, Any]]:
    """Generate mixed fill (snare + toms + crash)"""
    hits = []
    
    # First half: snare pattern
    half_duration = duration_beats / 2
    snare_hits = _generate_snare_roll(start_beat, half_duration, complexity * 0.7, style)
    hits.extend(snare_hits)
    
    # Second half: tom run
    tom_hits = _generate_tom_run(start_beat + half_duration, half_duration, complexity * 0.8)
    hits.extend(tom_hits)
    
    return hits

def suggest_fill_placement(
    bar_index: int,
    bars_per_section: int,
    section_type: str
) -> bool:
    """Decide if a fill should be placed at this bar"""
    
    # End of section: always fill
    if (bar_index + 1) % bars_per_section == 0:
        return True
    
    # Mid-section fills for choruses
    if section_type == "chorus" and (bar_index + 1) % 4 == 0:
        return random.random() < 0.6
    
    # Occasional verse fills
    if section_type == "verse" and (bar_index + 1) % 8 == 0:
        return random.random() < 0.4
    
    return False

# Example usage
if __name__ == "__main__":
    import json
    
    # Generate tom run fill
    tom_fill = generate_fill(
        fill_type="tom_run",
        start_beat=15.0,  # Last beat of 4-bar phrase
        duration_beats=1.0,
        complexity=0.8,
        style="rock"
    )
    
    print("Tom Run Fill:")
    print(json.dumps(tom_fill, indent=2))
    
    # Generate snare roll fill
    snare_fill = generate_fill(
        fill_type="snare_roll",
        start_beat=31.0,
        duration_beats=1.0,
        complexity=0.9,
        style="jazz"
    )
    
    print("\nSnare Roll Fill:")
    print(json.dumps(snare_fill, indent=2))
