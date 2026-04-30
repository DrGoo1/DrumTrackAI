"""
Jamstix Brain - Complete Implementation
========================================
Modern Python reimplementation of Jamstix-style drum intelligence

Modules:
- jamstix_attributes_complete: Attribute enrichment and limb logic
- dcsm_drumtrack_builder: DCSM integration and track building
"""

from .jamstix_attributes_complete import (
    enrich_drum_events_with_jamstix_attrs,
    detect_limb_conflicts,
    resolve_limb_conflicts,
    JamstixNoteAttributes,
    Limb,
    Aspect,
    HitStyle
)

from .dcsm_drumtrack_builder import (
    DCSMDrumTrackBuilder,
    DrumTrack,
    DrumBar,
    DrumNoteEvent,
    generate_performance_spec_with_llm
)

__all__ = [
    # Attributes
    "enrich_drum_events_with_jamstix_attrs",
    "detect_limb_conflicts",
    "resolve_limb_conflicts",
    "JamstixNoteAttributes",
    "Limb",
    "Aspect",
    "HitStyle",
    
    # Builder
    "DCSMDrumTrackBuilder",
    "DrumTrack",
    "DrumBar",
    "DrumNoteEvent",
    "generate_performance_spec_with_llm",
]

__version__ = "1.0.0"
