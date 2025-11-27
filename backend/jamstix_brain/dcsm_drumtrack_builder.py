#!/usr/bin/env python3
"""
DCSM DrumTrack Builder - COMPLETE INTEGRATION
==============================================
Combines pattern generation + Jamstix brain + performance spec
to create high-resolution drum tracks for DCSM piano roll

This is the "glue" that brings together:
- Audio analysis (tempo, sections, beats)
- LLM-generated patterns
- Jamstix-style attributes
- Performance specifications
- SongMap structure

Output: DrumTrack compatible with DCSM frontend
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

# Import Jamstix brain modules (relative import)
from .jamstix_attributes_complete import (
    enrich_drum_events_with_jamstix_attrs,
    detect_limb_conflicts,
    resolve_limb_conflicts
)

# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DrumNoteEvent:
    """Complete drum note event for DCSM"""
    tickInBar: int           # Tick position within bar (0-3840 for 960 PPQN)
    tickLength: int          # Note duration in ticks
    instrument: str          # Drum instrument ID
    velocity: int            # MIDI velocity (0-127)
    
    # Jamstix attributes
    limbId: str              # LH/RH/LF/RF
    priority: float          # 0.0-1.0
    microTimingMs: float     # Micro-timing offset in ms
    aspect: str              # groove/accent/fill/ghost
    hitStyle: str            # single/double/bounce/flam
    hatOpenLevel: float      # 0.0-1.0
    locked: bool = False     # Don't modify if true
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization"""
        return {
            "tickInBar": self.tickInBar,
            "tickLength": self.tickLength,
            "instrument": self.instrument,
            "velocity": self.velocity,
            "limbId": self.limbId,
            "priority": self.priority,
            "microTimingMs": self.microTimingMs,
            "aspect": self.aspect,
            "hitStyle": self.hitStyle,
            "hatOpenLevel": self.hatOpenLevel,
            "locked": self.locked
        }

@dataclass
class DrumBar:
    """One bar of drums for DCSM"""
    barIndex: int
    startTime: float         # Seconds
    endTime: float           # Seconds
    notes: List[DrumNoteEvent]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "barIndex": self.barIndex,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "notes": [n.to_dict() for n in self.notes]
        }

@dataclass
class DrumTrack:
    """Complete drum track for DCSM"""
    tempo: float
    timeSignature: str       # "4/4", "3/4", etc.
    bars: List[DrumBar]
    sections: List[Dict[str, Any]]  # SongMap sections
    performanceSpec: Dict[str, Any]  # From LLM
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tempo": self.tempo,
            "timeSignature": self.timeSignature,
            "bars": [b.to_dict() for b in self.bars],
            "sections": self.sections,
            "performanceSpec": self.performanceSpec
        }

# ============================================================================
# BUILDER CLASS
# ============================================================================

class DCSMDrumTrackBuilder:
    """Build complete DCSM drum tracks from patterns + brain logic"""
    
    def __init__(
        self,
        tempo: float = 120.0,
        time_signature: str = "4/4",
        ppqn: int = 960
    ):
        self.tempo = tempo
        self.time_signature = time_signature
        self.ppqn = ppqn
        
        # Calculate ticks per bar
        num, denom = map(int, time_signature.split('/'))
        self.ticks_per_bar = ppqn * 4 * (num / denom)
    
    def build_from_pattern_and_spec(
        self,
        pattern_events: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
        performance_spec: Dict[str, Any]
    ) -> DrumTrack:
        """
        Build complete drum track from:
        - pattern_events: List of {time_sec, instrument_id, velocity, barIndex, ...}
        - sections: SongMap sections [{type, startBar, endBar, ...}]
        - performance_spec: {feel, swing, intensity, fillStyle, ...}
        
        Returns: DrumTrack ready for DCSM
        """
        
        # Extract performance parameters
        feel = performance_spec.get("feel", "on_the_beat")
        global_hat_openness = performance_spec.get("hatOpenness", 0.2)
        fill_bar_indices = self._identify_fill_bars(sections)
        
        # Enrich events with Jamstix attributes
        enriched_events = enrich_drum_events_with_jamstix_attrs(
            pattern_events,
            feel=feel,
            global_hat_openness=global_hat_openness,
            fill_bar_indices=fill_bar_indices
        )
        
        # Detect and resolve limb conflicts
        conflicts = detect_limb_conflicts(enriched_events, time_window_ms=50.0)
        if conflicts:
            print(f"⚠️  Detected {len(conflicts)} limb conflicts, resolving...")
            enriched_events = resolve_limb_conflicts(enriched_events, conflicts)
        
        # Group events by bar
        bars_dict = {}
        for ev in enriched_events:
            bar_idx = ev.get("barIndex", 0)
            if bar_idx not in bars_dict:
                bars_dict[bar_idx] = {
                    "startTime": ev.get("barStartTime", bar_idx * 4.0 / (self.tempo / 60.0)),
                    "endTime": ev.get("barEndTime", (bar_idx + 1) * 4.0 / (self.tempo / 60.0)),
                    "notes": []
                }
            bars_dict[bar_idx]["notes"].append(ev)
        
        # Convert to DrumBar objects
        bars = []
        for bar_idx in sorted(bars_dict.keys()):
            bar_data = bars_dict[bar_idx]
            
            notes = []
            for ev in bar_data["notes"]:
                note = self._event_to_drum_note(ev, bar_data["startTime"])
                notes.append(note)
            
            bar = DrumBar(
                barIndex=bar_idx,
                startTime=bar_data["startTime"],
                endTime=bar_data["endTime"],
                notes=notes
            )
            bars.append(bar)
        
        # Create DrumTrack
        track = DrumTrack(
            tempo=self.tempo,
            timeSignature=self.time_signature,
            bars=bars,
            sections=sections,
            performanceSpec=performance_spec
        )
        
        return track
    
    def _identify_fill_bars(self, sections: List[Dict[str, Any]]) -> List[int]:
        """Identify which bars should have fills (typically last bar of sections)"""
        fill_bars = []
        for section in sections:
            end_bar = section.get("endBar", 0)
            # Fill on last bar of section
            if end_bar > 0:
                fill_bars.append(end_bar - 1)
        return fill_bars
    
    def _event_to_drum_note(self, event: Dict[str, Any], bar_start_time: float) -> DrumNoteEvent:
        """Convert enriched event to DrumNoteEvent"""
        
        # Calculate tick position within bar
        time_in_bar = event["time_sec"] - bar_start_time
        bar_frac = event.get("bar_pos_frac", 0.0)
        tick_in_bar = int(bar_frac * self.ticks_per_bar)
        
        # Note length (default to 16th note)
        tick_length = self.ppqn // 4
        
        # Extract Jamstix attributes
        attrs = event.get("jamstix_attrs", {})
        
        note = DrumNoteEvent(
            tickInBar=tick_in_bar,
            tickLength=tick_length,
            instrument=event["instrument_id"],
            velocity=event.get("velocity", 80),
            limbId=attrs.get("limbId", "other"),
            priority=attrs.get("priority", 0.5),
            microTimingMs=attrs.get("timingOffsetMs", 0.0),
            aspect=attrs.get("aspect", "groove"),
            hitStyle=attrs.get("hitStyle", "single"),
            hatOpenLevel=attrs.get("hatOpenLevel", 0.0),
            locked=attrs.get("locked", False)
        )
        
        return note
    
    def save_to_json(self, track: DrumTrack, output_path: Path):
        """Save DrumTrack to JSON file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w') as f:
            json.dump(track.to_dict(), f, indent=2)
        print(f"✅ Saved DrumTrack to {output_path}")

# ============================================================================
# LLM INTEGRATION
# ============================================================================

def generate_performance_spec_with_llm(
    style: str,
    drummer: str,
    intensity: float,
    sections: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Generate performance spec using trained LLM
    (Placeholder - integrate with your trained model)
    
    Args:
        style: "rock", "funk", "jazz", etc.
        drummer: "bonham", "purdie", "gadd", etc.
        intensity: 0.0-1.0
        sections: SongMap sections
    
    Returns:
        Performance spec dict with feel, swing, fills, etc.
    """
    
    # TODO: Replace with actual LLM call once trained
    # For now, return template based on style
    
    specs_by_style = {
        "rock": {
            "feel": "on_the_beat",
            "swing": 0.0,
            "intensity": intensity,
            "hatOpenness": 0.2,
            "fillStyle": "tom_run",
            "accentPattern": "2_and_4",
            "ghostNoteAmount": 0.3
        },
        "funk": {
            "feel": "laid_back",
            "swing": 0.0,
            "intensity": intensity,
            "hatOpenness": 0.4,
            "fillStyle": "snare_buzz",
            "accentPattern": "syncopated",
            "ghostNoteAmount": 0.7
        },
        "jazz": {
            "feel": "swing",
            "swing": 0.6,
            "intensity": intensity * 0.7,
            "hatOpenness": 0.5,
            "fillStyle": "cymbal_build",
            "accentPattern": "ride_emphasis",
            "ghostNoteAmount": 0.4
        }
    }
    
    base_spec = specs_by_style.get(style, specs_by_style["rock"])
    
    # Drummer adjustments
    if drummer == "bonham":
        base_spec["intensity"] *= 1.2
        base_spec["fillStyle"] = "tom_run"
    elif drummer == "purdie":
        base_spec["feel"] = "laid_back"
        base_spec["ghostNoteAmount"] = 0.8
    elif drummer == "gadd":
        base_spec["fillStyle"] = "complex_linear"
        base_spec["intensity"] *= 1.1
    
    return base_spec

# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Example: Build drum track from pattern
    
    # 1. Sample pattern events (normally from LLM or audio analysis)
    pattern_events = [
        {"time_sec": 0.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.25, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.5, "instrument_id": "snare_center", "velocity": 90, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 0.75, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.0, "instrument_id": "kick", "velocity": 100, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.25, "instrument_id": "hihat_closed", "velocity": 70, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.5, "instrument_id": "snare_center", "velocity": 95, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
        {"time_sec": 1.75, "instrument_id": "hihat_closed", "velocity": 65, "barIndex": 0, "barStartTime": 0.0, "barEndTime": 2.0},
    ]
    
    # 2. Sample sections (SongMap)
    sections = [
        {"type": "verse", "startBar": 0, "endBar": 4},
        {"type": "chorus", "startBar": 4, "endBar": 8},
    ]
    
    # 3. Generate performance spec
    perf_spec = generate_performance_spec_with_llm(
        style="rock",
        drummer="bonham",
        intensity=0.8,
        sections=sections
    )
    
    # 4. Build drum track
    builder = DCSMDrumTrackBuilder(tempo=120.0, time_signature="4/4")
    track = builder.build_from_pattern_and_spec(
        pattern_events=pattern_events,
        sections=sections,
        performance_spec=perf_spec
    )
    
    # 5. Save to JSON
    output_path = Path("test_drumtrack.json")
    builder.save_to_json(track, output_path)
    
    print(f"\n✅ DrumTrack created!")
    print(f"   Bars: {len(track.bars)}")
    print(f"   Total notes: {sum(len(b.notes) for b in track.bars)}")
    print(f"   Performance feel: {perf_spec['feel']}")
