"""
DCSM Piano Roll Module
======================
High-resolution drum track schema and builder for DCSM.
"""

from .drumtrack_schema import (
    DrumNoteEvent,
    DrumTrackForDCSM,
    DrumPerformanceSpec,
    MicroTimingProfile,
    VelocityProfile,
    InstrumentPerformanceProfile,
    DrumPhrasePerformance,
    DrumInstrumentId,
    GlobalFeel,
    QuantizationBase,
    PhraseShape,
    instrument_id_to_midi_pitch,
    create_default_performance_spec,
    DRUM_INSTRUMENT_MIDI_MAP,
)

from .drumtrack_builder_dcsmpiano import (
    build_drumtrack_for_dcsm,
    convert_dcsm_track_to_legacy_midi_notes,
)

__all__ = [
    # Schema types
    "DrumNoteEvent",
    "DrumTrackForDCSM",
    "DrumPerformanceSpec",
    "MicroTimingProfile",
    "VelocityProfile",
    "InstrumentPerformanceProfile",
    "DrumPhrasePerformance",
    "DrumInstrumentId",
    "GlobalFeel",
    "QuantizationBase",
    "PhraseShape",
    
    # Utilities
    "instrument_id_to_midi_pitch",
    "create_default_performance_spec",
    "DRUM_INSTRUMENT_MIDI_MAP",
    
    # Builder
    "build_drumtrack_for_dcsm",
    "convert_dcsm_track_to_legacy_midi_notes",
]
