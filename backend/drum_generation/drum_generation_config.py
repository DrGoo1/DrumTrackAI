"""
Drum Generation Configuration
=============================
Complete config dataclass with all user controls.
Includes existing + new performance layer controls.
"""

from dataclasses import dataclass
from typing import List, Literal, Tuple, Optional

GenerationMode = Literal["template", "ai_variation", "full_ai", "euclidean"]
BuildScope = Literal["full_song", "selected_section"]
GuideInstrument = Literal["mix", "bass", "guitar", "keys", "vocal", "other"]
GlobalFeel = Literal["straight", "swing", "shuffle", "laid_back", "pushed"]
ArticulationProfile = Literal["balanced", "ghosty", "tight_hats", "crashy"]

@dataclass
class DrumGenerationConfig:
    """
    Complete configuration for drum track generation.
    
    Includes:
    - Section/range controls
    - Pattern controls (style, drummer, intensity, etc.)
    - Performance controls (humanize, ghosts, swing)
    - Build scope (full song vs section)
    - Guide track integration
    """
    
    # ================================================================
    # SECTION & RANGE
    # ================================================================
    sectionId: str
    startMeasure: int
    endMeasure: int
    tempos: List[float]                    # One per measure
    timeSignature: Tuple[int, int]         # (numerator, denominator)
    
    # ================================================================
    # CORE PATTERN CONTROLS (Existing)
    # ================================================================
    style: str                             # "rock", "funk", "jazz", etc.
    drummer: str                           # "jeff_porcaro", "john_bonham", etc.
    intensity: float                       # 0.0 (soft) - 1.0 (aggressive)
    variation: float                       # 0.0 (static) - 1.0 (changey)
    generationMode: GenerationMode         # "template" | "ai_variation" | "full_ai"
    humanize: bool                         # Enable/disable performance layer
    fillLocations: List[int]               # Measure indices (relative to range)
    fillType: str                          # "auto", "tom_run", "crash_buildup", etc.
    fillDensity: float = 0.7               # 0.0 (sparse) - 1.0 (busy) for fills
    
    # ================================================================
    # PERFORMANCE LAYER CONTROLS (New)
    # ================================================================
    humanizeAmount: float = 0.7            # 0.0 (tight/robotic) - 1.0 (loose/human)
    ghostNoteAmount: float = 0.7           # 0.0 (no ghosts) - 1.0 (dense ghosts)
    swingAmount: float = 0.0               # 0.0 (straight) - 1.0 (heavy swing)
    
    # ================================================================
    # BUILD SCOPE CONTROL (New)
    # ================================================================
    buildScope: BuildScope = "full_song"   # "full_song" | "selected_section"
    
    # ================================================================
    # GUIDE TRACK (Optional)
    # ================================================================
    guideEnabled: bool = False
    guideInstrument: GuideInstrument = "mix"
    articulationProfile: ArticulationProfile = "balanced"
    euclideanLanes: Optional[List["EuclideanLaneConfig"]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        data = {
            "sectionId": self.sectionId,
            "startMeasure": self.startMeasure,
            "endMeasure": self.endMeasure,
            "tempos": self.tempos,
            "timeSignature": self.timeSignature,
            "style": self.style,
            "drummer": self.drummer,
            "intensity": self.intensity,
            "variation": self.variation,
            "generationMode": self.generationMode,
            "humanize": self.humanize,
            "fillLocations": self.fillLocations,
            "fillType": self.fillType,
            "humanizeAmount": self.humanizeAmount,
            "ghostNoteAmount": self.ghostNoteAmount,
            "swingAmount": self.swingAmount,
            "buildScope": self.buildScope,
            "guideEnabled": self.guideEnabled,
            "guideInstrument": self.guideInstrument,
            "fillDensity": self.fillDensity,
            "articulationProfile": self.articulationProfile,
        }
        if self.euclideanLanes is not None:
            data["euclideanLanes"] = [
                {
                    "instrumentId": lane.instrumentId,
                    "steps": lane.steps,
                    "hits": lane.hits,
                    "accents": lane.accents,
                    "rotate": lane.rotate,
                    "velocity": lane.velocity,
                    "accentVelocity": lane.accentVelocity,
                }
                for lane in self.euclideanLanes
            ]
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "DrumGenerationConfig":
        """Create from dictionary (JSON deserialization)."""
        euclidean_lanes_data = data.get("euclideanLanes") or None
        euclidean_lanes = None
        if euclidean_lanes_data is not None:
            euclidean_lanes = [
                EuclideanLaneConfig(
                    instrumentId=lane["instrumentId"],
                    steps=lane["steps"],
                    hits=lane["hits"],
                    accents=lane["accents"],
                    rotate=lane["rotate"],
                    velocity=lane["velocity"],
                    accentVelocity=lane["accentVelocity"],
                )
                for lane in euclidean_lanes_data
            ]
        return cls(
            sectionId=data["sectionId"],
            startMeasure=data["startMeasure"],
            endMeasure=data["endMeasure"],
            tempos=data["tempos"],
            timeSignature=tuple(data["timeSignature"]),
            style=data["style"],
            drummer=data["drummer"],
            intensity=data["intensity"],
            variation=data["variation"],
            generationMode=data["generationMode"],
            humanize=data["humanize"],
            fillLocations=data["fillLocations"],
            fillType=data["fillType"],
            humanizeAmount=data.get("humanizeAmount", 0.7),
            ghostNoteAmount=data.get("ghostNoteAmount", 0.7),
            swingAmount=data.get("swingAmount", 0.0),
            buildScope=data.get("buildScope", "full_song"),
            guideEnabled=data.get("guideEnabled", False),
            guideInstrument=data.get("guideInstrument", "mix"),
            fillDensity=data.get("fillDensity", 0.7),
            articulationProfile=data.get("articulationProfile", "balanced"),
            euclideanLanes=euclidean_lanes,
        )


@dataclass
class GridEvent:
    """
    Pattern Layer output: grid-level drum event (no micro-timing).
    """
    bar_index: int
    subdivision_index: int                 # 0..subdivisions_per_bar-1
    subdivisions_per_bar: int              # Typically 16 (16th notes)
    instrument_id: str                     # "kick", "snare_center", "hihat_closed", etc.
    is_ghost: bool = False
    is_accent: bool = False
    is_flam: bool = False
    is_drag: bool = False


@dataclass
class EuclideanLaneConfig:
    instrumentId: str
    steps: int
    hits: int
    accents: int
    rotate: int
    velocity: int
    accentVelocity: int
