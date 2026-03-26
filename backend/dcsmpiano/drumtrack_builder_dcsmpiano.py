"""
DCSM Drumtrack Builder
======================
Main builder that combines Pattern + Performance + Rendering layers.

Takes:
- SongMap (analysis)
- DrumGenerationConfig (user controls)
- DrumPerformanceSpec (from LLM or defaults)

Produces:
- DrumTrackForDCSM (high-resolution MIDI with metadata)
"""

import logging
import uuid
import math
import random
from typing import List, Dict, Any, Optional

from .drumtrack_schema import (
    DrumNoteEvent,
    DrumTrackForDCSM,
    DrumPerformanceSpec,
    instrument_id_to_midi_pitch,
)

logger = logging.getLogger(__name__)


def build_drumtrack_for_dcsm(
    songmap: Any,  # SongMap type
    internal_drum_events: List[Dict[str, Any]],
    style_id: str,
    performance_spec: Dict[str, Any],
    resolution_ppq: int = 960,
) -> DrumTrackForDCSM:
    """
    Main builder: Convert internal drum events + performance spec → high-res DCSM track.
    
    Args:
        songmap: SongMap with bars, tempos, sections
        internal_drum_events: Raw pattern events from pattern layer
            Each event: {
                "time_sec": float,
                "length_sec": float,
                "instrument_id": str,
                "midi_pitch": int,
                "velocity": int,
                "isGhost": bool,
                "isAccent": bool,
                "isFlam": bool,
                "isDrag": bool,
            }
        style_id: Style identifier
        performance_spec: DrumPerformanceSpec as dict (from LLM or defaults)
        resolution_ppq: MIDI resolution (960 or 1920)
    
    Returns:
        DrumTrackForDCSM ready for frontend
    """
    
    logger.info(f"Building DCSM drum track: {len(internal_drum_events)} events, {resolution_ppq} PPQ")
    
    notes: List[DrumNoteEvent] = []
    
    # Precompute bar timing for efficient time→bar mapping
    bar_start_times = [b.start_time for b in songmap.bars]
    bar_end_times = [b.end_time for b in songmap.bars]
    
    def find_bar_index(t_sec: float) -> int:
        """Find which bar contains this timestamp."""
        for i, (s, e) in enumerate(zip(bar_start_times, bar_end_times)):
            if s <= t_sec < e:
                return i
        # Clamp to last bar if beyond
        return len(bar_start_times) - 1
    
    # Convert each internal event to DrumNoteEvent
    for ev in internal_drum_events:
        t_sec = ev["time_sec"]
        dur_sec = ev.get("length_sec", 0.25)
        pitch = ev["midi_pitch"]
        vel = ev["velocity"]
        inst_id = ev["instrument_id"]
        is_ghost = ev.get("isGhost", False)
        is_accent = ev.get("isAccent", False)
        is_flam = ev.get("isFlam", False)
        is_drag = ev.get("isDrag", False)
        
        # Find bar
        bar_index = find_bar_index(t_sec)
        bar = songmap.bars[bar_index]
        bar_len_sec = bar.end_time - bar.start_time
        
        # Fraction through bar
        frac = (t_sec - bar.start_time) / max(bar_len_sec, 1e-6)
        frac = max(0.0, min(0.999999, frac))
        
        # Base tick in bar (before micro-timing)
        bar_ticks = resolution_ppq * bar.meter[0]  # meter[0] = beats per bar
        base_tick_in_bar = int(round(frac * bar_ticks))
        
        # Apply micro-timing from performance spec
        micro_ms = compute_microtiming_ms(
            performance_spec=performance_spec,
            bar_index=bar_index,
            inst_id=inst_id,
            frac=frac,
        )
        
        # Convert micro_ms → ticks
        bpm = bar.tempo_bpm if hasattr(bar, 'tempo_bpm') and bar.tempo_bpm > 0 else \
              getattr(songmap, 'global_bpm_estimate', 120.0) or 120.0
        ticks_per_ms = (resolution_ppq * bpm) / 60000.0
        micro_ticks = int(round(micro_ms * ticks_per_ms))
        
        tick_in_bar = base_tick_in_bar + micro_ticks
        tick_length = int(round(dur_sec * (bpm / 60.0) * resolution_ppq))
        
        # Apply velocity adjustments from performance spec
        vel = apply_velocity_profile(
            base_velocity=vel,
            performance_spec=performance_spec,
            bar_index=bar_index,
            inst_id=inst_id,
            is_ghost=is_ghost,
            is_accent=is_accent,
        )
        
        # Get phrase ID
        phrase_id = find_phrase_id_for_bar(performance_spec, bar_index)
        
        # Create note event
        note = DrumNoteEvent(
            id=str(uuid.uuid4()),
            barIndex=bar_index,
            tickInBar=tick_in_bar,
            tickLength=tick_length,
            channel=9,  # Standard MIDI drum channel
            midiPitch=pitch,
            velocity=vel,
            instrumentId=inst_id,
            isGhost=is_ghost,
            isAccent=is_accent,
            isFlam=is_flam,
            isDrag=is_drag,
            performanceGroupId=phrase_id,
            microTimingMs=micro_ms,
        )
        notes.append(note)
    
    # Sort by bar then tick
    notes.sort(key=lambda n: (n.barIndex, n.tickInBar))
    
    logger.info(f"Built {len(notes)} DCSM notes with micro-timing and metadata")
    
    # Create track
    return DrumTrackForDCSM(
        track_id=str(uuid.uuid4()),
        style_id=style_id,
        resolution_ppq=resolution_ppq,
        notes=notes,
        performance_spec=performance_spec,
    )


def compute_microtiming_ms(
    performance_spec: Dict[str, Any],
    bar_index: int,
    inst_id: str,
    frac: float,
) -> float:
    """
    Compute micro-timing offset for a note.
    
    Args:
        performance_spec: DrumPerformanceSpec dict
        bar_index: Absolute bar index
        inst_id: Instrument ID
        frac: Fraction through bar (0.0-1.0)
    
    Returns:
        Micro-timing offset in milliseconds
    """
    
    # Find phrase containing this bar
    phrase = None
    for ph in performance_spec.get("phrases", []):
        if ph["barStart"] <= bar_index <= ph["barEnd"]:
            phrase = ph
            break
    
    if not phrase:
        return 0.0
    
    # Find instrument profile
    prof = None
    for p in phrase.get("profiles", []):
        if p["instrumentId"] == inst_id:
            prof = p
            break
    
    if not prof:
        return 0.0
    
    # Get micro-timing data
    mt = prof.get("microTiming", {})
    offs = mt.get("subdivisionOffsetsMs", [])
    
    if not offs:
        return 0.0
    
    # Map fraction to subdivision index
    idx = int(math.floor(frac * len(offs)))
    idx = max(0, min(len(offs) - 1, idx))
    
    return float(offs[idx])


def apply_velocity_profile(
    base_velocity: int,
    performance_spec: Dict[str, Any],
    bar_index: int,
    inst_id: str,
    is_ghost: bool,
    is_accent: bool,
) -> int:
    """
    Apply velocity adjustments from performance spec.
    
    Args:
        base_velocity: Original velocity
        performance_spec: DrumPerformanceSpec dict
        bar_index: Absolute bar index
        inst_id: Instrument ID
        is_ghost: Is ghost note
        is_accent: Is accent note
    
    Returns:
        Adjusted velocity (1-127)
    """
    
    # Find phrase
    phrase = None
    for ph in performance_spec.get("phrases", []):
        if ph["barStart"] <= bar_index <= ph["barEnd"]:
            phrase = ph
            break
    
    if not phrase:
        return base_velocity
    
    # Find profile
    prof = None
    for p in phrase.get("profiles", []):
        if p["instrumentId"] == inst_id:
            prof = p
            break
    
    if not prof:
        return base_velocity
    
    # Get velocity profile
    vp = prof.get("velocityProfile", {})
    
    # Start with profile base or use original
    vel = vp.get("base", base_velocity)
    
    # Apply accent boost
    if is_accent:
        vel += vp.get("accentBoost", 15)
    
    # Apply ghost reduction
    if is_ghost:
        vel = int(vel * vp.get("ghostReduction", 0.5))
    
    # Add randomization
    rand_range = vp.get("randomRange", 5)
    if rand_range > 0:
        vel += random.randint(-rand_range, rand_range)
    
    # Clamp to valid MIDI range
    return max(1, min(127, vel))


def find_phrase_id_for_bar(
    performance_spec: Dict[str, Any],
    bar_index: int,
) -> Optional[str]:
    """
    Find phrase ID containing this bar.
    
    Args:
        performance_spec: DrumPerformanceSpec dict
        bar_index: Absolute bar index
    
    Returns:
        Phrase ID or None
    """
    for phrase in performance_spec.get("phrases", []):
        if phrase["barStart"] <= bar_index <= phrase["barEnd"]:
            return phrase["phraseId"]
    return None


def convert_dcsm_track_to_legacy_midi_notes(
    track: DrumTrackForDCSM,
    resolution_ppq: int = 960,
) -> List[Dict[str, Any]]:
    """
    Convert DrumTrackForDCSM to legacy midi_notes format for backward compatibility.
    
    Args:
        track: DrumTrackForDCSM
        resolution_ppq: PPQ resolution
    
    Returns:
        List of legacy midi_notes dicts
    """
    
    legacy_notes = []
    
    for note in track.notes:
        # Convert tick to time in seconds (approximate)
        # Assume 120 BPM for legacy format
        bpm = 120.0
        tick_total = note.barIndex * (resolution_ppq * 4) + note.tickInBar
        time_sec = (tick_total / resolution_ppq) * (60.0 / bpm)
        
        legacy_notes.append({
            "time": time_sec,
            "note": note.midiPitch,
            "velocity": note.velocity,
            "drum": note.instrumentId,
            "length": note.tickLength / resolution_ppq * (60.0 / bpm),
            "is_ghost": note.isGhost,
            "is_accent": note.isAccent,
        })
    
    return legacy_notes
