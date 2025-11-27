# backend/dcsmpiano/dcsm_drumtrack_schema.py
"""
DCSM DrumTrack schema with Jamstix-style note attributes.

This module defines the rich drum track structure used by DrumTracKAI,
including per-note attributes for professional editing (priority, limb
assignment, timing offsets, hit styles, etc.).
"""

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from enum import Enum
import uuid


class LimbId(str, Enum):
    """Drummer limb identifiers (Jamstix-style)."""
    LH = "LH"  # Left Hand
    RH = "RH"  # Right Hand
    LF = "LF"  # Left Foot
    RF = "RF"  # Right Foot
    LS = "LS"  # Left Stick (for cross-stick, rim shots)
    RS = "RS"  # Right Stick
    OTHER = "other"


class HitStyle(str, Enum):
    """Note hit style (Jamstix-inspired)."""
    SINGLE = "single"    # Standard single hit
    DOUBLE = "double"    # Double stroke (diddle)
    BOUNCE = "bounce"    # Bounce/roll stroke


class NoteAspect(str, Enum):
    """Note aspect for filtering (Jamstix-style views)."""
    GROOVE = "groove"    # Core groove pattern
    ACCENT = "accent"    # Accented/emphasized hits
    FILL = "fill"        # Fill/transitional notes


@dataclass
class DrumNoteEvent:
    """
    Individual drum note with comprehensive attributes.
    
    Combines MIDI basics with Jamstix-style performance attributes
    for professional drum editing and humanization.
    """
    # Core identification
    id: str
    
    # Timing (high-resolution)
    barIndex: int                      # Which bar (0-indexed)
    tickInBar: int                     # Tick position within bar
    tickLength: int                    # Note duration in ticks
    
    # MIDI attributes
    channel: int                       # MIDI channel (typically 9 for drums)
    midiPitch: int                     # MIDI note number (GM drum mapping)
    velocity: int                      # MIDI velocity (1-127)
    
    # Drum-specific identification
    instrumentId: str                  # e.g., "kick", "snare_center", "hihat_closed"
    
    # Optional aspect classification
    aspect: Optional[NoteAspect] = None
    
    # Jamstix-style attributes
    limbId: Optional[LimbId] = None              # Which limb plays this note
    priority: Optional[float] = None             # 0..1 (importance in limb conflicts)
    timingOffsetMs: Optional[float] = None       # Per-note timing offset (±50ms)
    hatOpenLevel: Optional[float] = None         # 0..1 (for hi-hat open amount)
    hitStyle: Optional[HitStyle] = None          # Single/double/bounce
    locked: bool = False                         # If True, note cannot be overwritten
    
    # Performance flags
    isGhost: bool = False              # Ghost note (low velocity)
    isAccent: bool = False             # Accented note
    isFlam: bool = False               # Flam (grace note before main hit)
    isDrag: bool = False               # Drag (grace notes)
    
    # Performance grouping
    performanceGroupId: Optional[str] = None     # Phrase/section ID
    
    # Micro-timing from performance spec
    microTimingMs: Optional[float] = None        # From LLM performance spec
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = asdict(self)
        # Convert enums to strings
        if self.aspect:
            result['aspect'] = self.aspect.value
        if self.limbId:
            result['limbId'] = self.limbId.value
        if self.hitStyle:
            result['hitStyle'] = self.hitStyle.value
        return result


@dataclass
class MicroTimingProfile:
    """Micro-timing profile for an instrument in a phrase."""
    subdivisionOffsetsMs: List[float]  # Offsets per subdivision (ms)
    swingAmount: float                 # 0..1
    laidBackAmount: float              # -1..1 (negative=pushed, positive=laid-back)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VelocityProfile:
    """Velocity profile for an instrument in a phrase."""
    base: int                          # Base velocity (1-127)
    accentBoost: int                   # Boost for accented notes (0-40)
    ghostReduction: float              # Reduction factor for ghosts (0-1)
    randomRange: int                   # Random variation (0-20)
    phraseShape: str                   # "flat" | "swell" | "decay" | "wave"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InstrumentPerformanceProfile:
    """Performance profile for a specific instrument in a phrase."""
    instrumentId: str
    microTiming: MicroTimingProfile
    velocityProfile: VelocityProfile
    ghostDensity: float                # 0..1
    flamProbability: float             # 0..1
    dragProbability: float             # 0..1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'instrumentId': self.instrumentId,
            'microTiming': self.microTiming.to_dict(),
            'velocityProfile': self.velocityProfile.to_dict(),
            'ghostDensity': self.ghostDensity,
            'flamProbability': self.flamProbability,
            'dragProbability': self.dragProbability,
        }


@dataclass
class DrumPhrasePerformance:
    """Performance spec for a phrase (contiguous bars with consistent feel)."""
    phraseId: str
    barStart: int                      # Absolute bar index in song
    barEnd: int                        # Inclusive
    profiles: List[InstrumentPerformanceProfile]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'phraseId': self.phraseId,
            'barStart': self.barStart,
            'barEnd': self.barEnd,
            'profiles': [p.to_dict() for p in self.profiles],
        }


@dataclass
class DrumPerformanceSpec:
    """
    Complete performance specification from LLM.
    
    Defines HOW the drummer plays the pattern: micro-timing, dynamics,
    ghost notes, etc. This is the "feel" layer on top of the pattern.
    """
    styleId: str
    globalFeel: str                    # "straight" | "swing" | "shuffle" | "laid_back" | "pushed"
    quantizationBase: str              # "16th" | "8th" | "triplet_8th" | "triplet_16th"
    phrases: List[DrumPhrasePerformance]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'styleId': self.styleId,
            'globalFeel': self.globalFeel,
            'quantizationBase': self.quantizationBase,
            'phrases': [p.to_dict() for p in self.phrases],
        }


@dataclass
class DrumTrackForDCSM:
    """
    Complete drum track for DCSM piano roll.
    
    This is the main data structure that gets sent to the frontend
    and can be edited in the Jamstix-style piano roll.
    """
    track_id: str
    style_id: str
    resolution_ppq: int                # Ticks per quarter note (e.g., 960, 1920)
    notes: List[DrumNoteEvent]
    performance_spec: Dict[str, Any]   # DrumPerformanceSpec as dict
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "track_id": self.track_id,
            "style_id": self.style_id,
            "resolution_ppq": self.resolution_ppq,
            "notes": [n.to_dict() for n in self.notes],
            "performance_spec": self.performance_spec,
        }


# Helper functions

def make_note_id() -> str:
    """Generate unique note ID."""
    return str(uuid.uuid4())


def make_track_id() -> str:
    """Generate unique track ID."""
    return str(uuid.uuid4())


def make_phrase_id(bar_start: int, bar_end: int) -> str:
    """Generate phrase ID from bar range."""
    return f"phrase_{bar_start}_{bar_end}"


def create_default_performance_spec(style_id: str) -> Dict[str, Any]:
    """
    Create a minimal default performance spec.
    
    Used when humanization is disabled or LLM generation fails.
    """
    return {
        'styleId': style_id,
        'globalFeel': 'straight',
        'quantizationBase': '16th',
        'phrases': []
    }


def create_drum_note(
    bar_index: int,
    tick_in_bar: int,
    midi_pitch: int,
    velocity: int,
    instrument_id: str,
    resolution_ppq: int = 960,
    tick_length: Optional[int] = None,
    **kwargs
) -> DrumNoteEvent:
    """
    Convenience function to create a DrumNoteEvent.
    
    Args:
        bar_index: Bar number (0-indexed)
        tick_in_bar: Tick position within bar
        midi_pitch: MIDI note number
        velocity: MIDI velocity (1-127)
        instrument_id: Drum instrument ID
        resolution_ppq: Resolution (default 960)
        tick_length: Note duration (default: 16th note)
        **kwargs: Additional DrumNoteEvent fields
        
    Returns:
        DrumNoteEvent instance
    """
    if tick_length is None:
        # Default to 16th note length
        tick_length = resolution_ppq // 4
    
    return DrumNoteEvent(
        id=make_note_id(),
        barIndex=bar_index,
        tickInBar=tick_in_bar,
        tickLength=tick_length,
        channel=9,  # Standard drum channel
        midiPitch=midi_pitch,
        velocity=velocity,
        instrumentId=instrument_id,
        **kwargs
    )


# GM Drum Mapping (General MIDI standard)
GM_DRUM_MAP = {
    'kick': 36,
    'snare_center': 38,
    'snare_rim': 37,
    'snare_ghost': 38,  # Same as center, but with low velocity + isGhost flag
    'hihat_closed': 42,
    'hihat_open': 46,
    'hihat_pedal': 44,
    'ride_bow': 51,
    'ride_bell': 53,
    'ride_edge': 59,
    'tom_high': 48,
    'tom_mid': 47,
    'tom_floor': 43,
    'crash_1': 49,
    'crash_2': 57,
    'splash': 55,
    'china': 52,
    'cowbell': 56,
    'clap': 39,
    'tambourine': 54,
}


def instrument_id_to_midi_pitch(instrument_id: str) -> int:
    """
    Convert instrument ID to GM MIDI pitch.
    
    Args:
        instrument_id: Instrument identifier (e.g., "kick", "snare_center")
        
    Returns:
        MIDI pitch number (35-81 for drums)
        
    Raises:
        ValueError: If instrument_id is not recognized
    """
    if instrument_id in GM_DRUM_MAP:
        return GM_DRUM_MAP[instrument_id]
    
    # Try without suffix
    base_id = instrument_id.split('_')[0]
    if base_id in GM_DRUM_MAP:
        return GM_DRUM_MAP[base_id]
    
    raise ValueError(f"Unknown instrument ID: {instrument_id}")


def midi_pitch_to_instrument_id(midi_pitch: int) -> str:
    """
    Convert GM MIDI pitch to instrument ID (best guess).
    
    Args:
        midi_pitch: MIDI note number
        
    Returns:
        Instrument identifier string
    """
    # Reverse lookup
    for inst_id, pitch in GM_DRUM_MAP.items():
        if pitch == midi_pitch:
            return inst_id
    
    # Fallback: generic mapping
    return f"drum_{midi_pitch}"
