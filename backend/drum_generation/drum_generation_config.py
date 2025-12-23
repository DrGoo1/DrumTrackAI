"""
Drum Generation Configuration
=============================
Complete config dataclass with all user controls.
Includes existing + new performance layer controls.
"""

from dataclasses import dataclass, field
from typing import List, Literal, Tuple, Optional, Dict, Any

GenerationMode = Literal["template", "ai_variation", "full_ai", "euclidean"]
StyleSourceMode = Literal["jamstix", "signature", "combined"]
BuildScope = Literal["full_song", "selected_section"]
GuideInstrument = Literal["mix", "bass", "guitar", "keys", "vocal", "other"]
GlobalFeel = Literal["straight", "swing", "shuffle", "laid_back", "pushed"]
ArticulationProfile = Literal["balanced", "ghosty", "tight_hats", "crashy"]
LimbId = Literal["LH", "RH", "LF", "RF"]
ShuffleMode = Literal["straight", "swing_8th", "swing_16th"]

# High-level song style presets for Song Mode generation.
SongStyle = Literal[
    "pop",
    "rock",
    "blues",
    "jazz",
    "metal",
    "funk",
    "shoegaze",
    "edm",
    "dance",
]

# How often fills should appear in Song Mode.
FillFrequency = Literal[
    "none",
    "every_4_bars",
    "section_transitions",
    "all_transitions",
]

RudimentHandLead = Literal["auto", "left", "right"]


@dataclass
class BarDefaults:
    """Per-bar modifiers from the Limb Bar Editor.

    Values are 0..1 with ~0.5 as 'neutral'.
    """
    barIndex: int
    open: float = 0.5
    power: float = 0.5
    timing: float = 0.5
    priority: float = 0.5


@dataclass
class SlotMeta:
    """Per-slot (limb + step) modifiers from the Limb Bar Editor."""

    barIndex: int
    limb: LimbId
    step: int
    open: Optional[float] = None
    power: Optional[float] = None
    timing: Optional[float] = None
    priority: Optional[float] = None


@dataclass
class SongSection:
    """High-level song section descriptor used in Song Mode.

    Each section has a label ("intro", "verse", "chorus", etc.) and a bar count.
    """

    name: str
    bars: int


@dataclass
class FillControls:
    """Controls for how fills are generated in Song Mode."""

    fillType: str = "auto"          # "auto", "tom_run", "crash_buildup", etc.
    density: float = 0.7             # 0.0 (sparse) - 1.0 (very busy)
    frequency: FillFrequency = "section_transitions"


@dataclass
class RudimentControls:
    """Global preferences for rudiment selection on fill bars."""

    enabled: bool = True
    preferredFamilies: List[str] = field(default_factory=list)
    preferredRudiments: List[str] = field(default_factory=list)
    density: float = 0.7
    ensureDownbeatKick: bool = True
    preserveHatTail: bool = True
    handLead: RudimentHandLead = "auto"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "preferredFamilies": list(self.preferredFamilies),
            "preferredRudiments": list(self.preferredRudiments),
            "density": self.density,
            "ensureDownbeatKick": self.ensureDownbeatKick,
            "preserveHatTail": self.preserveHatTail,
            "handLead": self.handLead,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RudimentControls":
        return cls(
            enabled=data.get("enabled", True),
            preferredFamilies=list(data.get("preferredFamilies", []) or []),
            preferredRudiments=list(data.get("preferredRudiments", []) or []),
            density=data.get("density", 0.7),
            ensureDownbeatKick=data.get("ensureDownbeatKick", True),
            preserveHatTail=data.get("preserveHatTail", True),
            handLead=data.get("handLead", "auto"),
        )


@dataclass
class RudimentBlock:
    """Targeted rudiment directives for a contiguous bar range."""

    blockId: str
    startBar: int
    lengthBars: int
    families: List[str] = field(default_factory=list)
    rudimentId: Optional[str] = None
    density: Optional[float] = None
    ensureDownbeatKick: Optional[bool] = None
    preserveHatTail: Optional[bool] = None

    def covers_bar(self, bar_index: int) -> bool:
        return self.startBar <= bar_index < self.startBar + max(0, self.lengthBars)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blockId": self.blockId,
            "startBar": self.startBar,
            "lengthBars": self.lengthBars,
            "families": list(self.families),
            "rudimentId": self.rudimentId,
            "density": self.density,
            "ensureDownbeatKick": self.ensureDownbeatKick,
            "preserveHatTail": self.preserveHatTail,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RudimentBlock":
        return cls(
            blockId=data["blockId"],
            startBar=int(data.get("startBar", 0)),
            lengthBars=int(data.get("lengthBars", 0)),
            families=list(data.get("families", []) or []),
            rudimentId=data.get("rudimentId"),
            density=data.get("density"),
            ensureDownbeatKick=data.get("ensureDownbeatKick"),
            preserveHatTail=data.get("preserveHatTail"),
        )


@dataclass
class PartPerformanceOverrides:
    """Per-part Jamstix-style overrides (timing, shuffle, kit routing)."""

    partId: str
    timingOffsetMs: float = 0.0
    shuffleMode: ShuffleMode = "straight"
    useSecondaryKick: bool = False
    useSecondarySnare: bool = False
    powerHandOverride: Optional[str] = None
    alternateKitMap: Optional[Dict[str, str]] = None
    redirectionTarget: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "partId": self.partId,
            "timingOffsetMs": self.timingOffsetMs,
            "shuffleMode": self.shuffleMode,
            "useSecondaryKick": self.useSecondaryKick,
            "useSecondarySnare": self.useSecondarySnare,
            "powerHandOverride": self.powerHandOverride,
            "alternateKitMap": self.alternateKitMap,
            "redirectionTarget": self.redirectionTarget,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PartPerformanceOverrides":
        return cls(
            partId=data["partId"],
            timingOffsetMs=data.get("timingOffsetMs", 0.0),
            shuffleMode=data.get("shuffleMode", "straight"),
            useSecondaryKick=data.get("useSecondaryKick", False),
            useSecondarySnare=data.get("useSecondarySnare", False),
            powerHandOverride=data.get("powerHandOverride"),
            alternateKitMap=data.get("alternateKitMap"),
            redirectionTarget=data.get("redirectionTarget"),
        )


@dataclass
class BrainElementSetting:
    """Single controllable brain element value."""

    elementId: str
    value: float
    frozen: bool = False
    disabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "elementId": self.elementId,
            "value": self.value,
            "frozen": self.frozen,
            "disabled": self.disabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrainElementSetting":
        return cls(
            elementId=data["elementId"],
            value=data.get("value", 0.0),
            frozen=data.get("frozen", False),
            disabled=data.get("disabled", False),
        )


@dataclass
class DrumBrainConfig:
    """Collection of brain element overrides and display preferences."""

    mode: Literal["easy", "normal", "pro"] = "normal"
    randomizeSeed: Optional[int] = None
    elementSettings: List[BrainElementSetting] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "randomizeSeed": self.randomizeSeed,
            "elementSettings": [e.to_dict() for e in self.elementSettings],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DrumBrainConfig":
        element_settings = [
            BrainElementSetting.from_dict(entry)
            for entry in data.get("elementSettings", [])
        ]
        return cls(
            mode=data.get("mode", "normal"),
            randomizeSeed=data.get("randomizeSeed"),
            elementSettings=element_settings,
        )


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
    publicDrummerId: Optional[str]         # Public, app-facing drummer/profile identifier (e.g. "studio_rock").
                                            # This is decoupled from any real drummer names used internally in the
                                            # admin/analysis tooling.
    intensity: float                       # 0.0 (soft) - 1.0 (aggressive)
    variation: float                       # 0.0 (static) - 1.0 (changey)
    generationMode: GenerationMode         # "template" | "ai_variation" | "full_ai"
    humanize: bool                         # Enable/disable performance layer
    fillLocations: List[int]               # Measure indices (relative to range)
    fillType: str                          # "auto", "tom_run", "crash_buildup", etc.
    fillDensity: float = 0.7               # 0.0 (sparse) - 1.0 (busy) for fills
    # Which analysis source to use for persona style metrics: Jamstix-only,
    # signature-song (MVSEP) only, or a combined style vector.
    styleSourceMode: StyleSourceMode = "combined"
    
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
    bars: Optional[List[BarDefaults]] = None
    slots: Optional[List[SlotMeta]] = None
    partOverrides: Optional[List[PartPerformanceOverrides]] = None
    brainConfig: Optional[DrumBrainConfig] = None
    # Optional extra preference to favor ride cymbal in chorus sections.
    # 0.0 = neutral, 1.0 = strongly ride-focused in choruses only.
    chorusRidePreference: float = 0.0

    # ================================================================
    # SONG MODE (High-level full-song generation)
    # ================================================================
    # When using Song Mode, these optional fields further describe the
    # target song. Existing callers that only use loop/section-based
    # generation can ignore them safely.
    songStyle: Optional[SongStyle] = None
    songSections: Optional[List[SongSection]] = None
    fillControls: Optional[FillControls] = None
    rudimentControls: Optional[RudimentControls] = None
    rudimentBlocks: Optional[List[RudimentBlock]] = None
    
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
            "publicDrummerId": self.publicDrummerId,
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
            "chorusRidePreference": self.chorusRidePreference,
            "styleSourceMode": self.styleSourceMode,
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
        if self.bars is not None:
            data["bars"] = [
                {
                    "barIndex": b.barIndex,
                    "open": b.open,
                    "power": b.power,
                    "timing": b.timing,
                    "priority": b.priority,
                }
                for b in self.bars
            ]
        if self.slots is not None:
            out_slots = []
            for s in self.slots:
                d: Dict[str, Any] = {
                    "barIndex": s.barIndex,
                    "limb": s.limb,
                    "step": s.step,
                }
                if s.open is not None:
                    d["open"] = s.open
                if s.power is not None:
                    d["power"] = s.power
                if s.timing is not None:
                    d["timing"] = s.timing
                if s.priority is not None:
                    d["priority"] = s.priority
                out_slots.append(d)
            data["slots"] = out_slots
        if self.partOverrides is not None:
            data["partOverrides"] = [
                ov.to_dict() if isinstance(ov, PartPerformanceOverrides) else ov
                for ov in self.partOverrides
            ]
        if self.brainConfig is not None:
            data["brainConfig"] = (
                self.brainConfig.to_dict()
                if isinstance(self.brainConfig, DrumBrainConfig)
                else self.brainConfig
            )
        if self.songStyle is not None:
            data["songStyle"] = self.songStyle
        if self.songSections is not None:
            data["songSections"] = [
                {"name": s.name, "bars": s.bars} for s in self.songSections
            ]
        if self.fillControls is not None:
            data["fillControls"] = {
                "fillType": self.fillControls.fillType,
                "density": self.fillControls.density,
                "frequency": self.fillControls.frequency,
            }
        if self.rudimentControls is not None:
            data["rudimentControls"] = (
                self.rudimentControls.to_dict()
                if isinstance(self.rudimentControls, RudimentControls)
                else self.rudimentControls
            )
        if self.rudimentBlocks is not None:
            data["rudimentBlocks"] = [
                block.to_dict() if isinstance(block, RudimentBlock) else block
                for block in self.rudimentBlocks
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
        bars_data = data.get("bars") or None
        bars = None
        if bars_data is not None:
            bars = [
                BarDefaults(
                    barIndex=b["barIndex"],
                    open=b.get("open", 0.5),
                    power=b.get("power", 0.5),
                    timing=b.get("timing", 0.5),
                    priority=b.get("priority", 0.5),
                )
                for b in bars_data
            ]
        slots_data = data.get("slots") or None
        slots = None
        if slots_data is not None:
            slots = [
                SlotMeta(
                    barIndex=s["barIndex"],
                    limb=s["limb"],
                    step=s["step"],
                    open=s.get("open"),
                    power=s.get("power"),
                    timing=s.get("timing"),
                    priority=s.get("priority"),
                )
                for s in slots_data
            ]
        part_overrides_data = data.get("partOverrides") or None
        part_overrides: Optional[List[PartPerformanceOverrides]] = None
        if part_overrides_data is not None:
            part_overrides = [
                PartPerformanceOverrides.from_dict(entry)
                for entry in part_overrides_data
            ]
        brain_config_data = data.get("brainConfig")
        brain_config: Optional[DrumBrainConfig] = None
        if brain_config_data is not None:
            brain_config = DrumBrainConfig.from_dict(brain_config_data)
        song_style: Optional[SongStyle] = data.get("songStyle")
        song_sections_data = data.get("songSections") or None
        song_sections: Optional[List[SongSection]] = None
        if song_sections_data is not None:
            song_sections = [
                SongSection(name=s["name"], bars=int(s["bars"]))
                for s in song_sections_data
            ]
        fill_controls_data = data.get("fillControls") or None
        fill_controls: Optional[FillControls] = None
        if fill_controls_data is not None:
            fill_controls = FillControls(
                fillType=fill_controls_data.get("fillType", "auto"),
                density=fill_controls_data.get("density", 0.7),
                frequency=fill_controls_data.get("frequency", "section_transitions"),
            )
        rudiment_controls_data = data.get("rudimentControls") or None
        rudiment_controls: Optional[RudimentControls] = None
        if rudiment_controls_data is not None:
            rudiment_controls = RudimentControls.from_dict(rudiment_controls_data)

        rudiment_blocks_data = data.get("rudimentBlocks") or None
        rudiment_blocks: Optional[List[RudimentBlock]] = None
        if rudiment_blocks_data is not None:
            rudiment_blocks = [
                RudimentBlock.from_dict(entry)
                for entry in rudiment_blocks_data
            ]

        return cls(
            sectionId=data["sectionId"],
            startMeasure=data["startMeasure"],
            endMeasure=data["endMeasure"],
            tempos=data["tempos"],
            timeSignature=tuple(data["timeSignature"]),
            style=data["style"],
            drummer=data["drummer"],
            publicDrummerId=data.get("publicDrummerId"),
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
            chorusRidePreference=data.get("chorusRidePreference", 0.0),
            styleSourceMode=data.get("styleSourceMode", "combined"),
            euclideanLanes=euclidean_lanes,
            bars=bars,
            slots=slots,
            partOverrides=part_overrides,
            brainConfig=brain_config,
            songStyle=song_style,
            songSections=song_sections,
            fillControls=fill_controls,
            rudimentControls=rudiment_controls,
            rudimentBlocks=rudiment_blocks,
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
    bar_role: Optional[str] = None          # "groove" | "fill" | future roles
    phrase_marker: Optional[str] = None     # Additional tag for downstream planners/UI
    rudiment_id: Optional[str] = None       # Identifier when event belongs to a rudiment pattern


@dataclass
class EuclideanLaneConfig:
    instrumentId: str
    steps: int
    hits: int
    accents: int
    rotate: int
    velocity: int
    accentVelocity: int


@dataclass
class DrummerGenerationBrain:
    """Runtime "brain" derived from analysis for a public drummer persona.

    This object is built from admin-side analysis artifacts (style vectors,
    hit-type statistics, etc.) and used internally by the generation pipeline
    and Jamstix enrichment. It is intentionally compact and aligned with the
    controls exposed in DrumGenerationConfig.
    """

    # Global defaults for core knobs (0.0-1.0)
    defaultIntensity: float
    defaultHumanize: float
    defaultGhosts: float
    defaultSwing: float
    defaultDrumDensity: float
    defaultCymbalDensity: float
    defaultFillDensity: float

    # Timing feel: -1 = lay back, 0 = neutral, +1 = push
    globalTimingFeel: float
    sectionTimingFeel: Dict[str, float]

    # Energy / crescendo per section (0.0-1.0 target energy) and how aggressive
    # fills should be as energy rises.
    sectionEnergy: Dict[str, float]
    fillAggression: float

    # Per-instrument / articulation biases (typically -1.0..+1.0 or 0.0..1.0)
    hatOpenBias: float
    ghostSnareBias: float
    rimshotBias: float
    crashBias: float
    rideBellBias: float


@dataclass
class DrummerProfileVisualSection:
    """Public view of section-level timing feel and energy for visualization."""

    id: str
    label: str
    timingFeel: float  # -1 = lay back, 0 = neutral, +1 = push
    energy: float      # 0.0-1.0


@dataclass
class DrummerProfileVisual:
    """Lightweight DTO for the Drummer Profile page in the DAW UI.

    This structure is safe to expose publicly: it uses only abstract traits and
    the publicDrummerId, never any internal real-drummer names.
    """

    publicDrummerId: str
    label: str

    # Global feel / groove traits (0.0-1.0)
    grooveScore: float
    ghostNoteTendency: float
    syncopationTendency: float
    fillFrequency: float
    pocketScore: float

    # Kit preference summaries (0.0-1.0)
    hatOpenness: float
    snareGhostBias: float
    snareRimshotBias: float
    rideBellUsage: float
    crashUsage: float

    # Section-wise timing feel and energy curve
    sections: List[DrummerProfileVisualSection]
