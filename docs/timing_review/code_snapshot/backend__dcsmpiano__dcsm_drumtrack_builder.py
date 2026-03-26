# backend/dcsmpiano/dcsm_drumtrack_builder.py
"""
DCSM DrumTrack Builder

Converts internal drum events to rich DrumTrackForDCSM format with
Jamstix-style attributes (limb assignment, priority, timing, etc.).
"""

from typing import List, Dict, Any, Optional, Type, TypeVar
import math
import logging
from enum import Enum

from .dcsm_drumtrack_schema import (
    DrumNoteEvent,
    DrumTrackForDCSM,
    LimbId,
    HitStyle,
    NoteAspect,
    make_note_id,
    make_track_id,
    make_phrase_id,
    instrument_id_to_midi_pitch,
)

from backend.articulation_selector import select_articulation_for_note

logger = logging.getLogger(__name__)

EnumT = TypeVar("EnumT", bound=Enum)


def coerce_enum(enum_cls: Type[EnumT], value: Any) -> Optional[EnumT]:
    """Best-effort conversion of loose values (strings) into Enum members."""
    if value is None:
        return None
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        for member in enum_cls:
            if member.value.lower() == normalized or member.name.lower() == normalized:
                return member
    return None


def find_phrase_id_for_bar(performance_spec: dict, bar_index: int) -> Optional[str]:
    """
    Find which phrase a given bar belongs to.
    
    Args:
        performance_spec: DrumPerformanceSpec dictionary
        bar_index: Bar number to check
        
    Returns:
        Phrase ID string, or None if not found
    """
    for phrase in performance_spec.get("phrases", []):
        if phrase["barStart"] <= bar_index <= phrase["barEnd"]:
            return phrase["phraseId"]
    return None


def get_instrument_profile(
    performance_spec: dict,
    bar_index: int,
    inst_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Get performance profile for a specific instrument at a given bar.
    
    Args:
        performance_spec: DrumPerformanceSpec dictionary
        bar_index: Bar number
        inst_id: Instrument ID (e.g., "kick", "snare_center")
        
    Returns:
        Instrument performance profile dict, or None if not found
    """
    # Find phrase containing this bar
    phrase = None
    for ph in performance_spec.get("phrases", []):
        if ph["barStart"] <= bar_index <= ph["barEnd"]:
            phrase = ph
            break
    
    if not phrase:
        return None
    
    # Find instrument profile within phrase
    for prof in phrase.get("profiles", []):
        if prof["instrumentId"] == inst_id:
            return prof
    
    return None


def compute_microtiming_ms(
    performance_spec: dict,
    bar_index: int,
    inst_id: str,
    frac: float,
) -> float:
    """
    Compute micro-timing offset in milliseconds for a note.
    
    Args:
        performance_spec: DrumPerformanceSpec dictionary
        bar_index: Bar number
        inst_id: Instrument ID
        frac: Fractional position within bar (0.0 - 1.0)
        
    Returns:
        Micro-timing offset in milliseconds (can be negative)
    """
    prof = get_instrument_profile(performance_spec, bar_index, inst_id)
    if not prof:
        return 0.0
    
    mt = prof.get("microTiming", {})
    offs = mt.get("subdivisionOffsetsMs", [])
    if not offs:
        return 0.0
    
    # Map fractional position to subdivision index
    idx = int(math.floor(frac * len(offs)))
    idx = max(0, min(len(offs) - 1, idx))
    
    return float(offs[idx])


def assign_limb_id(instrument_id: str) -> LimbId:
    """
    Assign limb based on instrument.
    
    This is a simplified heuristic. More sophisticated logic could
    consider patterns, technique, and drummer profile.
    
    Args:
        instrument_id: Drum instrument ID
        
    Returns:
        LimbId enum value
    """
    limb_map = {
        "kick": LimbId.RF,
        "hihat_pedal": LimbId.LF,
        "snare_center": LimbId.LH,
        "snare_rim": LimbId.LH,
        "snare_ghost": LimbId.LH,
        "hihat_closed": LimbId.RH,
        "hihat_open": LimbId.RH,
        "ride_bow": LimbId.RH,
        "ride_bell": LimbId.RH,
        "ride_edge": LimbId.RH,
        "tom_high": LimbId.RH,
        "tom_mid": LimbId.LH,
        "tom_floor": LimbId.LH,
        "crash_1": LimbId.RH,
        "crash_2": LimbId.LH,
    }
    
    return limb_map.get(instrument_id, LimbId.OTHER)


def assign_priority(
    instrument_id: str,
    is_accent: bool = False,
    is_ghost: bool = False,
) -> float:
    """
    Assign priority value for limb conflict resolution.
    
    Higher priority notes win when two notes compete for the same limb
    at the same time.
    
    Args:
        instrument_id: Drum instrument ID
        is_accent: Whether this is an accented note
        is_ghost: Whether this is a ghost note
        
    Returns:
        Priority value (0.0 - 1.0)
    """
    # Base priorities
    base_priority = {
        "kick": 1.0,          # Kick always wins
        "snare_center": 0.9,
        "crash_1": 0.85,
        "crash_2": 0.85,
        "ride_bow": 0.7,
        "hihat_closed": 0.6,
        "hihat_open": 0.65,
        "tom_high": 0.75,
        "tom_mid": 0.75,
        "tom_floor": 0.75,
        "snare_rim": 0.5,
        "snare_ghost": 0.2,
        "hihat_pedal": 0.3,
    }
    
    priority = base_priority.get(instrument_id, 0.5)
    
    # Modify based on note flags
    if is_accent:
        priority = min(1.0, priority + 0.1)
    if is_ghost:
        priority = max(0.0, priority - 0.3)
    
    return priority


def assign_hit_style(
    instrument_id: str,
    is_ghost: bool = False,
    is_fill: bool = False,
) -> HitStyle:
    """
    Assign hit style (single/double/bounce) based on context.
    
    Args:
        instrument_id: Drum instrument ID
        is_ghost: Whether this is a ghost note
        is_fill: Whether this is part of a fill
        
    Returns:
        HitStyle enum value
    """
    # Most notes are single strokes
    # TODO: Implement more sophisticated logic for diddles/bounces
    # based on drummer style and pattern analysis
    
    if is_ghost:
        return HitStyle.SINGLE  # Ghosts are usually singles
    
    if is_fill and instrument_id.startswith("tom"):
        # Tom fills might use bounces
        return HitStyle.SINGLE  # For now, keep simple
    
    return HitStyle.SINGLE


def _is_hand_played_instrument(instrument_id: str) -> bool:
    if not instrument_id:
        return False
    inst = str(instrument_id).lower()
    if inst.startswith("kick"):
        return False
    if "pedal" in inst:
        return False
    if "hat" in inst:
        return True
    if inst.startswith("snare"):
        return True
    if inst.startswith("tom"):
        return True
    if inst.startswith("crash") or inst.startswith("ride") or "cym" in inst:
        return True
    return False


def _alternate_sticking(notes: List[DrumNoteEvent], resolution_ppq: int) -> None:
    if not notes:
        return

    hand_limbs = {LimbId.LH, LimbId.RH, LimbId.LS, LimbId.RS}
    last_hand_for_key: Dict[str, LimbId] = {}
    last_tick_for_key: Dict[str, int] = {}

    threshold_ticks = max(1, int(round(resolution_ppq / 4)))

    for n in notes:
        if not _is_hand_played_instrument(getattr(n, "instrumentId", "")):
            continue

        limb = getattr(n, "limbId", None)
        if limb not in hand_limbs:
            if limb is None or limb == LimbId.OTHER:
                limb = LimbId.RH
            else:
                continue

        inst = str(getattr(n, "instrumentId", "") or "")
        aspect = getattr(n, "aspect", None)
        is_fill = bool(aspect == NoteAspect.FILL)
        key = inst if is_fill else (inst if inst.startswith("snare") or inst.startswith("tom") else "")
        if not key:
            continue

        abs_tick = int(getattr(n, "barIndex", 0)) * int(resolution_ppq) * 4 + int(getattr(n, "tickInBar", 0))
        prev_tick = last_tick_for_key.get(key)
        prev_limb = last_hand_for_key.get(key)

        if prev_tick is not None and prev_limb is not None:
            if abs_tick > prev_tick and (abs_tick - prev_tick) <= threshold_ticks:
                if limb in {LimbId.LS, LimbId.LH}:
                    norm = LimbId.LH
                else:
                    norm = LimbId.RH
                if prev_limb in {LimbId.LS, LimbId.LH}:
                    prev_norm = LimbId.LH
                else:
                    prev_norm = LimbId.RH

                if norm == prev_norm:
                    limb = LimbId.RH if prev_norm == LimbId.LH else LimbId.LH

        n.limbId = limb
        last_hand_for_key[key] = limb
        last_tick_for_key[key] = abs_tick


def assign_aspect(
    is_fill: bool = False,
    is_accent: bool = False,
    instrument_id: str = "",
) -> NoteAspect:
    """
    Assign note aspect (groove/accent/fill) for filtering.
    
    Args:
        is_fill: Whether this note is part of a fill
        is_accent: Whether this is an accented note
        instrument_id: Drum instrument ID
        
    Returns:
        NoteAspect enum value
    """
    if is_fill:
        return NoteAspect.FILL
    
    if is_accent or instrument_id.startswith("crash"):
        return NoteAspect.ACCENT
    
    return NoteAspect.GROOVE


def build_drumtrack_for_dcsm(
    songmap,
    internal_drum_events: List[Dict[str, Any]],
    style_id: str,
    performance_spec: Dict[str, Any],
    resolution_ppq: int = 960,
    section_label: str = "",
) -> DrumTrackForDCSM:
    """
    Build complete DrumTrackForDCSM from internal events + performance spec.
    
    This is the main conversion function that transforms your existing
    internal drum events into the rich DCSM format with all Jamstix attributes.
    
    Args:
        songmap: SongMap object with bars and timing
        internal_drum_events: List of internal event dictionaries, each with:
            - time_sec: Event time in seconds
            - length_sec: Note duration in seconds
            - midi_pitch: MIDI note number
            - velocity: MIDI velocity (1-127)
            - instrument_id: Instrument identifier
            - isGhost: Optional ghost note flag
            - isAccent: Optional accent flag
            - isFlam: Optional flam flag
            - isDrag: Optional drag flag
            - isFill: Optional fill flag
        style_id: Style identifier (e.g., "rock", "funk")
        performance_spec: DrumPerformanceSpec dictionary from LLM
        resolution_ppq: Ticks per quarter note (default 960)
        
    Returns:
        DrumTrackForDCSM object ready for frontend
    """
    notes: List[DrumNoteEvent] = []
    
    # Build lookup tables for bars
    bar_start_times = [b.start_time for b in songmap.bars]
    bar_end_times = [b.end_time for b in songmap.bars]
    
    def find_bar_index(t_sec: float) -> int:
        """Find which bar a time value falls into."""
        for i, (s, e) in enumerate(zip(bar_start_times, bar_end_times)):
            if s <= t_sec < e:
                return i
        return len(bar_start_times) - 1
    
    # Process each internal event
    for ev in internal_drum_events:
        t_sec = ev.get("time_sec", 0.0)
        dur_sec = ev.get("length_sec", 0.25)
        pitch = ev.get("midi_pitch", 36)
        vel = ev.get("velocity", 100)
        inst_id = ev.get("instrument_id", "kick")
        
        # Extract flags
        is_ghost = ev.get("isGhost", False)
        is_accent = ev.get("isAccent", False)
        is_flam = ev.get("isFlam", False)
        is_drag = ev.get("isDrag", False)
        is_fill = ev.get("isFill", False)
        
        # Find bar and compute position
        bar_index = find_bar_index(t_sec)
        bar = songmap.bars[bar_index]
        bar_len_sec = bar.end_time - bar.start_time
        
        # Fractional position within bar (0.0 - 1.0)
        frac = (t_sec - bar.start_time) / max(bar_len_sec, 1e-6)
        frac = max(0.0, min(0.999999, frac))
        
        # Convert to ticks
        bar_ticks = resolution_ppq * bar.meter[0]  # Assume quarter = beat
        base_tick_in_bar = int(round(frac * bar_ticks))
        
        # Compute micro-timing offset
        micro_ms = compute_microtiming_ms(performance_spec, bar_index, inst_id, frac)
        
        # Convert micro-timing to ticks
        bpm = bar.tempo_bpm or songmap.global_bpm_estimate or 120.0
        ticks_per_ms = (resolution_ppq * bpm) / 60000.0
        micro_ticks = int(round(micro_ms * ticks_per_ms))
        
        # Final tick position
        tick_in_bar = base_tick_in_bar + micro_ticks
        
        # Note duration in ticks
        tick_length = int(round(dur_sec * (bpm / 60.0) * resolution_ppq))
        tick_length = max(1, tick_length)  # At least 1 tick
        
        # Phrase/performance group ID
        phrase_id = find_phrase_id_for_bar(performance_spec, bar_index)
        
        # Assign Jamstix-style attributes
        limb_id = assign_limb_id(inst_id)
        priority = assign_priority(inst_id, is_accent, is_ghost)
        hit_style = assign_hit_style(inst_id, is_ghost, is_fill)
        aspect = assign_aspect(is_fill, is_accent, inst_id)
        
        # Hat open level (only for hi-hats)
        hat_open_level = None
        if inst_id == "hihat_open":
            hat_open_level = 0.8  # TODO: Get from performance spec
        elif inst_id == "hihat_closed":
            hat_open_level = 0.0

        articulation_id = None
        try:
            articulation_id = select_articulation_for_note(
                {
                    "instrumentId": inst_id,
                    "velocity": int(vel) if vel is not None else 0,
                    "isGhost": bool(is_ghost),
                    "isAccent": bool(is_accent),
                },
                performance_spec or {},
                section_label or "",
            )
        except Exception:
            articulation_id = None
        
        # Create note
        note = DrumNoteEvent(
            id=make_note_id(),
            barIndex=bar_index,
            tickInBar=tick_in_bar,
            tickLength=tick_length,
            channel=9,  # Standard drum channel
            midiPitch=pitch,
            velocity=vel,
            instrumentId=inst_id,
            articulationId=articulation_id,
            aspect=aspect,
            limbId=limb_id,
            priority=priority,
            timingOffsetMs=micro_ms,
            hatOpenLevel=hat_open_level,
            hitStyle=hit_style,
            locked=False,  # New notes are not locked
            isGhost=is_ghost,
            isAccent=is_accent,
            isFlam=is_flam,
            isDrag=is_drag,
            performanceGroupId=phrase_id,
            microTimingMs=micro_ms,  # Same as timingOffsetMs for now
        )

        note.phraseMarker = ev.get("phraseMarker")
        note.rudimentId = ev.get("rudimentId")
        
        # Copy Jamstix-style attributes from internal event if present
        # (allows external enrichment to override defaults)
        if "limbId" in ev:
            coerced_limb = coerce_enum(LimbId, ev["limbId"])
            if coerced_limb:
                note.limbId = coerced_limb
        if "priority" in ev:
            note.priority = ev["priority"]
        if "timingOffsetMs" in ev:
            # Merge with micro timing
            note.timingOffsetMs = ev.get("timingOffsetMs", 0.0)
            note.microTimingMs = micro_ms + ev.get("timingOffsetMs", 0.0)
        if "hatOpenLevel" in ev:
            note.hatOpenLevel = ev["hatOpenLevel"]
        if "hitStyle" in ev:
            coerced_hit = coerce_enum(HitStyle, ev["hitStyle"])
            if coerced_hit:
                note.hitStyle = coerced_hit
        if "locked" in ev:
            note.locked = ev["locked"]
        if "aspect" in ev:
            coerced_aspect = coerce_enum(NoteAspect, ev["aspect"])
            if coerced_aspect:
                note.aspect = coerced_aspect
        
        notes.append(note)
    
    # Sort notes by position
    notes.sort(key=lambda n: (n.barIndex, n.tickInBar))

    _alternate_sticking(notes, resolution_ppq)
    
    # Log statistics
    logger.info(f"Built DCSM track: {len(notes)} notes, {resolution_ppq} PPQ")
    if notes:
        bar_range = f"bars {notes[0].barIndex}-{notes[-1].barIndex}"
        logger.info(f"  Range: {bar_range}")
        
        # Count by aspect
        groove_count = sum(1 for n in notes if n.aspect == NoteAspect.GROOVE)
        accent_count = sum(1 for n in notes if n.aspect == NoteAspect.ACCENT)
        fill_count = sum(1 for n in notes if n.aspect == NoteAspect.FILL)
        logger.info(f"  Aspects: {groove_count} groove, {accent_count} accent, {fill_count} fill")
    
    # Create track
    track = DrumTrackForDCSM(
        track_id=make_track_id(),
        style_id=style_id,
        resolution_ppq=resolution_ppq,
        notes=notes,
        performance_spec=performance_spec,
    )
    
    return track


def apply_velocity_adjustments(
    track: DrumTrackForDCSM,
    intensity_scale: float = 1.0,
) -> DrumTrackForDCSM:
    """
    Apply velocity adjustments based on intensity or other factors.
    
    Useful for post-processing after initial generation.
    
    Args:
        track: DrumTrackForDCSM to modify
        intensity_scale: Multiplier for velocities (0.5 - 1.5)
        
    Returns:
        Modified track (notes list is updated in place)
    """
    for note in track.notes:
        # Scale velocity
        new_vel = int(note.velocity * intensity_scale)
        note.velocity = max(1, min(127, new_vel))
    
    return track


def lock_notes_in_sections(
    track: DrumTrackForDCSM,
    locked_section_ids: List[str],
) -> DrumTrackForDCSM:
    """
    Lock all notes in specific sections to prevent overwriting.
    
    Args:
        track: DrumTrackForDCSM to modify
        locked_section_ids: List of section IDs to lock
        
    Returns:
        Modified track (note.locked flags updated)
    """
    for note in track.notes:
        if note.performanceGroupId in locked_section_ids:
            note.locked = True
    
    return track
