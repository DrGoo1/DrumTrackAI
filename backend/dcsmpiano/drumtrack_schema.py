"""
DCSM Drum Track Schema
=====================
High-resolution drum track schema for DCSM piano roll.

Includes:
- DrumNoteEvent: Individual note with micro-timing
- DrumPerformanceSpec: LLM-generated performance profiles
- DrumTrackForDCSM: Complete track for frontend
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Literal
import uuid

# Type aliases
DrumInstrumentId = Literal[
    "kick",
    "snare_center",
    "snare_rim",
    "snare_ghost",
    "hihat_closed",
    "hihat_open",
    "hihat_pedal",
    "ride_bow",
    "ride_bell",
    "ride_edge",
    "tom_high",
    "tom_mid",
    "tom_floor",
    "crash_1",
    "crash_2",
    "other"
]

GlobalFeel = Literal["straight", "swing", "shuffle", "laid_back", "pushed"]
QuantizationBase = Literal["16th", "8th", "triplet_8th", "triplet_16th"]
PhraseShape = Literal["flat", "swell", "decay", "wave"]


@dataclass
class DrumNoteEvent:
    """
    Individual drum note with high-resolution timing and metadata.
    
    This is what appears in the DCSM piano roll.
    """
    id: str                               # UUID for editing
    barIndex: int                         # Absolute bar index in song
    tickInBar: int                        # 0..barTicks (high precision)
    tickLength: int                       # Note duration in ticks
    channel: int                          # MIDI channel (typically 9 for drums)
    midiPitch: int                        # MIDI note number
    velocity: int                         # 1..127
    
    instrumentId: DrumInstrumentId        # Semantic instrument ID
    isGhost: bool = False                 # Ghost note flag
    isAccent: bool = False                # Accent flag
    isFlam: bool = False                  # Flam flag
    isDrag: bool = False                  # Drag flag
    
    performanceGroupId: Optional[str] = None   # Links to phrase (e.g. "verse_1")
    microTimingMs: Optional[float] = None      # Micro-timing offset in milliseconds


@dataclass
class MicroTimingProfile:
    """Micro-timing specification for an instrument."""
    subdivisionOffsetsMs: List[float]     # Offsets per subdivision (in ms)
    swingAmount: float                    # 0.0-1.0
    laidBackAmount: float                 # -1.0 (pushed) to +1.0 (laid back)


@dataclass
class VelocityProfile:
    """Velocity/dynamics specification for an instrument."""
    base: int                             # Base velocity (1-127)
    accentBoost: int                      # Added to accents (0-40)
    ghostReduction: float                 # Multiplier for ghosts (0.0-1.0)
    randomRange: int                      # ±velocity variation (0-20)
    phraseShape: PhraseShape              # Overall shape of phrase


@dataclass
class InstrumentPerformanceProfile:
    """Complete performance profile for a single instrument."""
    instrumentId: DrumInstrumentId
    microTiming: MicroTimingProfile
    velocityProfile: VelocityProfile
    ghostDensity: float                   # 0.0-1.0 (probability of ghost notes)
    flamProbability: float                # 0.0-1.0
    dragProbability: float                # 0.0-1.0


@dataclass
class DrumPhrasePerformance:
    """Performance specification for a phrase (section range)."""
    phraseId: str                         # E.g. "verse_1", "chorus_2"
    barStart: int                         # Absolute bar index
    barEnd: int                           # Inclusive
    profiles: List[InstrumentPerformanceProfile]


@dataclass
class DrumPerformanceSpec:
    """
    Complete performance specification (from LLM + analytics).
    
    Describes HOW the drummer plays, not WHAT notes.
    """
    styleId: str
    globalFeel: GlobalFeel
    quantizationBase: QuantizationBase
    phrases: List[DrumPhrasePerformance]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "styleId": self.styleId,
            "globalFeel": self.globalFeel,
            "quantizationBase": self.quantizationBase,
            "phrases": [
                {
                    "phraseId": p.phraseId,
                    "barStart": p.barStart,
                    "barEnd": p.barEnd,
                    "profiles": [
                        {
                            "instrumentId": prof.instrumentId,
                            "microTiming": {
                                "subdivisionOffsetsMs": prof.microTiming.subdivisionOffsetsMs,
                                "swingAmount": prof.microTiming.swingAmount,
                                "laidBackAmount": prof.microTiming.laidBackAmount,
                            },
                            "velocityProfile": {
                                "base": prof.velocityProfile.base,
                                "accentBoost": prof.velocityProfile.accentBoost,
                                "ghostReduction": prof.velocityProfile.ghostReduction,
                                "randomRange": prof.velocityProfile.randomRange,
                                "phraseShape": prof.velocityProfile.phraseShape,
                            },
                            "ghostDensity": prof.ghostDensity,
                            "flamProbability": prof.flamProbability,
                            "dragProbability": prof.dragProbability,
                        }
                        for prof in p.profiles
                    ],
                }
                for p in self.phrases
            ],
        }


@dataclass
class DrumTrackForDCSM:
    """
    Complete drum track for DCSM piano roll.
    
    This is the main output from the backend to the frontend.
    """
    track_id: str
    style_id: str
    resolution_ppq: int                   # 960 or 1920 (high precision)
    notes: List[DrumNoteEvent]
    performance_spec: DrumPerformanceSpec
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "track_id": self.track_id,
            "style_id": self.style_id,
            "resolution_ppq": self.resolution_ppq,
            "notes": [asdict(n) for n in self.notes],
            "performance_spec": self.performance_spec.to_dict(),
        }


# Utility functions

def create_default_performance_spec(
    style_id: str,
    bar_count: int,
    phrase_id: str = "default_phrase"
) -> DrumPerformanceSpec:
    """
    Create a default performance spec when LLM is not used.
    
    Args:
        style_id: Style identifier
        bar_count: Number of bars
        phrase_id: Phrase identifier
    
    Returns:
        DrumPerformanceSpec with reasonable defaults
    """
    # Default profiles for common instruments
    default_profiles = [
        InstrumentPerformanceProfile(
            instrumentId="snare_center",
            microTiming=MicroTimingProfile(
                subdivisionOffsetsMs=[-2.0, 1.0, -1.0, 0.5] * 4,  # 16 subdivisions
                swingAmount=0.0,
                laidBackAmount=0.0,
            ),
            velocityProfile=VelocityProfile(
                base=96,
                accentBoost=15,
                ghostReduction=0.5,
                randomRange=5,
                phraseShape="flat",
            ),
            ghostDensity=0.3,
            flamProbability=0.1,
            dragProbability=0.05,
        ),
        InstrumentPerformanceProfile(
            instrumentId="hihat_closed",
            microTiming=MicroTimingProfile(
                subdivisionOffsetsMs=[-1.0, 0.5] * 8,
                swingAmount=0.0,
                laidBackAmount=0.0,
            ),
            velocityProfile=VelocityProfile(
                base=85,
                accentBoost=10,
                ghostReduction=0.6,
                randomRange=4,
                phraseShape="flat",
            ),
            ghostDensity=0.2,
            flamProbability=0.0,
            dragProbability=0.0,
        ),
        InstrumentPerformanceProfile(
            instrumentId="kick",
            microTiming=MicroTimingProfile(
                subdivisionOffsetsMs=[0.0] * 16,
                swingAmount=0.0,
                laidBackAmount=0.0,
            ),
            velocityProfile=VelocityProfile(
                base=110,
                accentBoost=10,
                ghostReduction=0.7,
                randomRange=3,
                phraseShape="flat",
            ),
            ghostDensity=0.0,
            flamProbability=0.0,
            dragProbability=0.0,
        ),
    ]
    
    phrase = DrumPhrasePerformance(
        phraseId=phrase_id,
        barStart=0,
        barEnd=bar_count - 1,
        profiles=default_profiles,
    )
    
    return DrumPerformanceSpec(
        styleId=style_id,
        globalFeel="straight",
        quantizationBase="16th",
        phrases=[phrase],
    )


# MIDI pitch mapping
DRUM_INSTRUMENT_MIDI_MAP: Dict[str, int] = {
    "kick": 36,
    "snare_center": 38,
    "snare_rim": 37,
    "snare_ghost": 38,  # Same pitch, different velocity
    "hihat_closed": 42,
    "hihat_open": 46,
    "hihat_pedal": 44,
    "ride_bow": 51,
    "ride_bell": 53,
    "ride_edge": 59,
    "tom_high": 48,
    "tom_mid": 47,
    "tom_floor": 41,
    "crash_1": 49,
    "crash_2": 57,
    "other": 56,  # Cowbell as default
}


def instrument_id_to_midi_pitch(instrument_id: str) -> int:
    """Convert instrument ID to MIDI pitch."""
    return DRUM_INSTRUMENT_MIDI_MAP.get(instrument_id, 38)  # Default to snare
