"""
Drum Generation API - Drum Builder v2.0 Integration
===================================================
Integrates the three-layer drum builder with existing DrumTracKAI system.

This is the bridge between the aiohttp API and the new drum builder.
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import Drum Builder v2.0 components
try:
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from drum_generation.drum_generation_config import DrumGenerationConfig as NewConfig
    from drum_generation.llm_performance_spec import (
        get_performance_spec_from_llm,
        build_songmap_summary as llm_build_songmap_summary,
    )
    from drum_generation.part_types_config import (
        get_part_type_preset,
        apply_part_type_defaults,
    )
    from drum_generation.power_model import (
        compute_power_curve_from_guide,
        compute_power_curve_from_sections,
    )
    from dcsmpiano.dcsm_drumtrack_builder import build_drumtrack_for_dcsm
    from dcsmpiano.dcsm_drumtrack_schema import instrument_id_to_midi_pitch
    from drum_generation.jamstix_attributes import enrich_internal_events_with_jamstix_attrs
    DRUM_BUILDER_V2_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Drum Builder v2.0 not available: {e}")
    DRUM_BUILDER_V2_AVAILABLE = False

# Import existing tools
try:
    from drummer_mapping_service import get_drummer_service
    DRUMMER_SERVICE_AVAILABLE = True
except ImportError:
    DRUMMER_SERVICE_AVAILABLE = False
    logging.warning("Drummer mapping service not available")

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration Classes
# ============================================================================

class DrumGenerationConfig:
    """
    Legacy configuration class for backward compatibility.
    Converts old API format to new Drum Builder v2.0 format.
    """
    
    def __init__(self, data: Dict):
        # Required fields
        self.section_id = data['sectionId']
        self.start_measure = data['startMeasure']
        self.end_measure = data['endMeasure']
        self.tempos = data['tempos']  # BPM per measure
        self.time_signature = tuple(data['timeSignature'])
        self.style = data['style']
        self.drummer = data['drummer']
        # Public, app-facing drummer/profile identifier (e.g. "studio_rock").
        # This is decoupled from any real drummer names used internally.
        self.public_drummer_id = data.get('publicDrummerId')
        self.intensity = data['intensity']  # 0.0-1.0
        self.variation = data['variation']  # 0.0-1.0
        self.generation_mode = data['generationMode']  # 'template', 'ai_variation', 'full_ai'
        self.humanize = data['humanize']
        
        # Optional fields (v1.1 compatible)
        self.fill_locations = data.get('fillLocations', [])
        self.fill_type = data.get('fillType', 'auto')
        
        # New fields (Drum Builder v2.0)
        self.humanize_amount = data.get('humanizeAmount', 0.7)
        self.ghost_note_amount = data.get('ghostNoteAmount', 0.7)
        self.swing_amount = data.get('swingAmount', 0.0)
        self.build_scope = data.get('buildScope', 'full_song')
        self.guide_enabled = data.get('guideEnabled', False)
        self.guide_instrument = data.get('guideInstrument', 'mix')
        self.fill_density = data.get('fillDensity', 0.7)
        self.articulation_profile = data.get('articulationProfile', 'balanced')
        self.euclidean_lanes = data.get('euclideanLanes')
        # Limb Bar Editor meta (optional)
        self.bars = data.get('bars')
        self.slots = data.get('slots')
        
        # Additional metadata
        self.audio_key = data.get('audioKey')  # File key for analysis
        self.file_id = data.get('file_id') or data.get('audioKey')  # Alias
    
    @property
    def measure_count(self) -> int:
        return self.end_measure - self.start_measure + 1
    
    def to_v2_config(self) -> Optional[Any]:
        """Convert to Drum Builder v2.0 config."""
        if not DRUM_BUILDER_V2_AVAILABLE:
            return None
        
        return NewConfig(
            sectionId=self.section_id,
            startMeasure=self.start_measure,
            endMeasure=self.end_measure,
            tempos=self.tempos,
            timeSignature=self.time_signature,
            style=self.style,
            drummer=self.drummer,
            publicDrummerId=self.public_drummer_id,
            intensity=self.intensity,
            variation=self.variation,
            generationMode=self.generation_mode,
            humanize=self.humanize,
            fillLocations=self.fill_locations,
            fillType=self.fill_type,
            humanizeAmount=self.humanize_amount,
            ghostNoteAmount=self.ghost_note_amount,
            swingAmount=self.swing_amount,
            buildScope=self.build_scope,
            guideEnabled=self.guide_enabled,
            guideInstrument=self.guide_instrument,
            fillDensity=self.fill_density,
            articulationProfile=self.articulation_profile,
            euclideanLanes=self.euclidean_lanes,
            bars=self.bars,
            slots=self.slots,
        )


# ============================================================================
# Main Generation Function
# ============================================================================

def generate_drums(config: DrumGenerationConfig) -> Dict:
    """
    Main drum generation function - uses Drum Builder v2.0 if available.
    
    Returns:
    {
        'ok': bool,
        'midi_notes': [...],  # Legacy format
        'drum_track': {...},  # New high-res format (v2.0)
        'midi_base64': '...',
        'metadata': {...}
    }
    """
    start_time = time.time()
    
    if DRUM_BUILDER_V2_AVAILABLE:
        logger.info("Using Drum Builder v2.0")
        try:
            result = generate_with_v2_builder(config)
            result['metadata']['builder_version'] = 'v2.0'
            result['metadata']['generation_time_ms'] = round((time.time() - start_time) * 1000, 1)
            return result
        except Exception as e:
            logger.error(f"Drum Builder v2.0 failed: {e}", exc_info=True)
            logger.warning("Falling back to legacy generation")
    
    # Fallback to legacy generation
    logger.info("Using legacy drum generation")
    result = generate_with_legacy_system(config)
    result['metadata']['builder_version'] = 'v1.1_legacy'
    result['metadata']['generation_time_ms'] = round((time.time() - start_time) * 1000, 1)
    return result


# ============================================================================
# Drum Builder v2.0 Integration
# ============================================================================

def generate_with_v2_builder(config: DrumGenerationConfig) -> Dict:
    """
    Generate drums using Drum Builder v2.0 three-layer architecture.
    """
    
    # 1. Convert to v2.0 config
    v2_config = config.to_v2_config()
    if not v2_config:
        raise Exception("Could not convert to v2.0 config")
    
    # 2. Get drummer profile
    drummer_profile = get_drummer_profile_simple(config.drummer)
    
    # 3. Create mock SongMap (TODO: integrate real SongMap analysis)
    songmap = create_mock_songmap(config)
    songmap_summary = build_songmap_summary(songmap, config)
    
    # 3.5. Compute power curve if guide track enabled
    power_curve = None
    if config.guide_enabled and DRUM_BUILDER_V2_AVAILABLE:
        try:
            # Mock RMS values for now - replace with real guide track analysis
            mock_rms = [0.5 + (i % 4) * 0.1 for i in range(config.measure_count)]
            power_curve = compute_power_curve_from_guide(
                rms_values=mock_rms,
                user_intensity=config.intensity,
                smoothing_window=3,
            )
            logger.info(f"Computed power curve: avg={sum(power_curve)/len(power_curve):.2f}")
        except Exception as e:
            logger.warning(f"Power curve computation failed: {e}")
    
    # 4. Get performance spec from LLM
    section_label = config.section_id.replace("_", " ").title()
    
    # Apply part type defaults if available
    if DRUM_BUILDER_V2_AVAILABLE:
        try:
            preset = get_part_type_preset(section_label.lower())
            logger.info(f"Using part type: {preset.label} (intensity={preset.defaultIntensity})")
        except Exception as e:
            logger.debug(f"Could not get part type preset: {e}")
    
    perf_spec = get_performance_spec_from_llm(
        cfg=v2_config,
        section_label=section_label,
        songmap_summary=songmap_summary,
        drummer_profile=drummer_profile,
        power_curve=power_curve,
    )
    
    # 5. Generate pattern (placeholder - use Rust audio-core or templates)
    # If Euclidean lanes are provided and mode is 'euclidean', use them to
    # construct internal events; otherwise fall back to the existing pattern
    # generator.
    if getattr(v2_config, "generationMode", None) == "euclidean" and getattr(v2_config, "euclideanLanes", None):
        internal_events = generate_euclidean_internal_events(config, v2_config)
    else:
        internal_events = generate_pattern_events(config, drummer_profile)
    
    # 5.5. Enrich with Jamstix-style attributes
    if DRUM_BUILDER_V2_AVAILABLE:
        try:
            # Compute laid-back amount from humanize settings
            laid_back_amount = (config.humanize_amount - 0.5) * 2.0  # Map 0-1 to -1 to +1
            global_hat_openness = config.swing_amount * 0.5  # Use swing as hat openness proxy

            # Nudge Jamstix parameters based on articulation profile
            profile = getattr(config, "articulation_profile", "balanced")
            if profile == "ghosty":
                laid_back_amount += 0.2
            elif profile == "tight_hats":
                global_hat_openness *= 0.6
            elif profile == "crashy":
                global_hat_openness = max(global_hat_openness, 0.6)

            internal_events = enrich_internal_events_with_jamstix_attrs(
                internal_events,
                laid_back_amount=laid_back_amount,
                global_hat_openness=global_hat_openness,
                drum_config=v2_config,
            )
            logger.info(f"Enriched {len(internal_events)} events with Jamstix attributes (profile={profile})")
        except Exception as e:
            logger.warning(f"Jamstix enrichment failed: {e}")
    
    # 6. Build high-resolution DCSM track
    dcsm_track = build_drumtrack_for_dcsm(
        songmap=songmap,
        internal_drum_events=internal_events,
        style_id=config.style,
        performance_spec=perf_spec,
        resolution_ppq=960,
    )
    
    # 7. Export to MIDI
    midi_b64 = export_track_to_midi_base64(dcsm_track, config)
    
    # 8. Convert to legacy format for backward compatibility
    legacy_notes = convert_dcsm_track_to_legacy_format(dcsm_track)
    
    return {
        'ok': True,
        'drum_track': dcsm_track.to_dict(),  # NEW high-res format
        'midi_notes': legacy_notes,  # OLD format for compatibility
        'midi_base64': midi_b64,
        'metadata': {
            'drummer_used': config.drummer,
            'style': config.style,
            'mode': config.generation_mode,
            'humanized': config.humanize,
            'humanize_amount': config.humanize_amount,
            'ghost_notes': config.ghost_note_amount,
            'swing': config.swing_amount,
            'measure_count': config.measure_count,
            'tempo_range': f"{min(config.tempos):.0f}-{max(config.tempos):.0f} BPM",
            'resolution_ppq': 960,
            'performance_from_llm': True,
            'fill_density': getattr(config, 'fill_density', None),
            'articulation_profile': getattr(config, 'articulation_profile', None),
        }
    }


def generate_euclidean_internal_events(config: DrumGenerationConfig, v2_config: Any) -> List[Dict[str, Any]]:
    """Generate internal events from Euclidean lanes.

    This mirrors the frontend Euclidean grid concept but works directly in
    seconds using the mock SongMap timing model (tempo + timeSignature).

    Each lane describes a ring with N steps and K hits distributed as evenly
    as possible, optionally rotated, with base and accent velocities.
    """

    lanes = getattr(v2_config, "euclideanLanes", None) or []
    if not lanes:
        # Fallback to the simple pattern if no lanes are defined
        return generate_pattern_events(config, {})

    events: List[Dict[str, Any]] = []

    # Basic timing: assume constant tempo per bar from config.tempos[0]
    beats_per_bar = config.time_signature[0]
    bar_duration = (60.0 / config.tempos[0]) * beats_per_bar
    beat_duration = bar_duration / beats_per_bar

    def build_euclidean_pattern(steps: int, hits: int) -> List[int]:
        """Simple Bjorklund-style distribution returning 0/1 pattern."""
        if steps <= 0 or hits <= 0:
            return [0] * max(steps, 0)
        hits = min(hits, steps)

        pattern = []
        step = 0
        acc = 0
        for _ in range(steps):
            acc += hits
            if acc >= steps:
                acc -= steps
                pattern.append(1)
            else:
                pattern.append(0)
        return pattern

    for bar_idx in range(config.measure_count):
        bar_time = bar_idx * bar_duration

        is_fill_bar = bar_idx in fill_bars

        for lane in lanes:
            # lane may be a dataclass or a plain dict depending on origin
            instrument_id = getattr(lane, "instrumentId", None) or lane.get("instrumentId")
            steps = getattr(lane, "steps", None) or lane.get("steps", 0)
            hits = getattr(lane, "hits", None) or lane.get("hits", 0)
            accents = getattr(lane, "accents", None) or lane.get("accents", 0)
            rotate = getattr(lane, "rotate", None) or lane.get("rotate", 0)
            base_vel = getattr(lane, "velocity", None) or lane.get("velocity", 100)
            accent_vel = getattr(lane, "accentVelocity", None) or lane.get("accentVelocity", 120)

            if not instrument_id or steps <= 0 or hits <= 0:
                continue

            pattern = build_euclidean_pattern(steps, hits)

            # Build accent pattern as first `accents` hits in the cycle
            accent_idxs: List[int] = []
            for i, v in enumerate(pattern):
                if v:
                    accent_idxs.append(i)
                if len(accent_idxs) >= accents:
                    break

            def is_accent(step_index: int) -> bool:
                return step_index in accent_idxs

            # Rotate pattern
            rotate_mod = rotate % steps
            rotated = pattern[-rotate_mod:] + pattern[:-rotate_mod] if rotate_mod else pattern

            step_duration = bar_duration / steps

            for step_idx, hit in enumerate(rotated):
                if not hit:
                    continue

                time_sec = bar_time + step_idx * step_duration
                accent_flag = is_accent((step_idx - rotate_mod) % steps)
                velocity = int(accent_vel if accent_flag else base_vel)

                events.append(
                    {
                        "time_sec": time_sec,
                        "length_sec": step_duration * 0.9,
                        "instrument_id": instrument_id,
                        "midi_pitch": instrument_id_to_midi_pitch(instrument_id),
                        "velocity": velocity,
                        "isGhost": False,
                        "isAccent": accent_flag,
                        "isFlam": False,
                        "isDrag": False,
                    }
                )

    return events


# ============================================================================
# Helper Functions for v2.0 Integration
# ============================================================================

def get_drummer_profile_simple(drummer_name: str) -> Dict[str, Any]:
    """
    Get drummer profile for LLM integration.
    
    TODO: Replace with database query to drumtrackai.db
    """
    
    # Try to get from drummer service if available
    if DRUMMER_SERVICE_AVAILABLE:
        try:
            drummer_service = get_drummer_service()
            profile = drummer_service.get_drummer_by_name(drummer_name)
            if profile:
                return {
                    "name": drummer_name,
                    "timing_tightness": profile.get("timing_precision", 0.8),
                    "ghost_note_frequency": profile.get("ghost_frequency", 0.5),
                    "preferred_feel": profile.get("feel", "straight"),
                    "style_specialties": [profile.get("style", "rock")],
                }
        except Exception as e:
            logger.warning(f"Could not get drummer profile from service: {e}")
    
    # Fallback to simple defaults with per-drummer adjustments
    profile = {
        "name": drummer_name,
        "timing_tightness": 0.8,
        "ghost_note_frequency": 0.5,
        "preferred_feel": "straight",
        "style_specialties": ["rock"],
    }
    
    # Adjust for known drummers
    drummer_lower = drummer_name.lower()
    if "porcaro" in drummer_lower:
        profile["timing_tightness"] = 0.85
        profile["ghost_note_frequency"] = 0.7
        profile["preferred_feel"] = "laid_back"
        profile["style_specialties"] = ["rock", "pop", "funk"]
    elif "bonham" in drummer_lower:
        profile["timing_tightness"] = 0.75
        profile["ghost_note_frequency"] = 0.3
        profile["preferred_feel"] = "pushed"
        profile["style_specialties"] = ["rock", "hard_rock"]
    elif "bernard" in drummer_lower:
        profile["timing_tightness"] = 0.9
        profile["ghost_note_frequency"] = 0.8
        profile["preferred_feel"] = "straight"
        profile["style_specialties"] = ["funk", "disco"]
    
    return profile


def create_mock_songmap(config: DrumGenerationConfig):
    """
    Create mock SongMap for pattern generation.
    
    TODO: Replace with real SongMap from audio analysis.
    """
    class MockBar:
        def __init__(self, idx, tempo):
            bar_duration = (60.0 / tempo) * config.time_signature[0]
            self.start_time = idx * bar_duration
            self.end_time = (idx + 1) * bar_duration
            self.tempo_bpm = tempo
            self.meter = config.time_signature
    
    class MockSongMap:
        def __init__(self):
            self.bars = [
                MockBar(i, config.tempos[min(i, len(config.tempos) - 1)])
                for i in range(config.start_measure, config.end_measure + 1)
            ]
            self.global_bpm_estimate = sum(config.tempos) / len(config.tempos)
            self.sections = []
    
    return MockSongMap()


def build_songmap_summary(songmap, config: DrumGenerationConfig) -> Dict[str, Any]:
    """
    Create condensed SongMap summary for LLM prompt.
    """
    return {
        "bars": len(songmap.bars),
        "sections": [],
        "avgEnergy": 0.5,
        "globalBPM": songmap.global_bpm_estimate,
        "timeSignature": config.time_signature,
    }


def convert_dcsm_track_to_legacy_format(dcsm_track) -> List[Dict[str, Any]]:
    """
    Convert DrumTrackForDCSM to legacy MIDI notes format.
    """
    legacy_notes = []
    
    for note in dcsm_track.notes:
        # Find the bar to get timing info
        bar_duration = 2.0  # Approximate - should come from songmap
        beat_duration = bar_duration / 4  # Assume 4/4
        
        # Calculate time from bar + tick position
        ticks_per_bar = dcsm_track.resolution_ppq * 4
        bar_time = note.barIndex * bar_duration
        tick_fraction = note.tickInBar / ticks_per_bar
        time_sec = bar_time + (tick_fraction * bar_duration)
        
        legacy_notes.append({
            "time": time_sec,
            "note": note.midiPitch,
            "velocity": note.velocity,
            "drum": note.instrumentId,
            "length": (note.tickLength / dcsm_track.resolution_ppq) * beat_duration,
        })
    
    return legacy_notes


def generate_pattern_events(config: DrumGenerationConfig, drummer_profile: Dict) -> List[Dict[str, Any]]:
    """
    Generate basic pattern events.
    
    TODO: Replace with real pattern generation (templates, AI, Rust audio-core)
    """
    if not DRUM_BUILDER_V2_AVAILABLE:
        # Fallback to simple pattern
        return generate_simple_pattern_fallback(config)
    
    # Use proper instrument_id_to_midi_pitch from schema
    
    events = []
    bar_duration = (60.0 / config.tempos[0]) * config.time_signature[0]
    beat_duration = bar_duration / config.time_signature[0]

    # Treat fillLocations as bar indices (relative to startMeasure) where we should
    # increase density / energy. Use fillDensity (0..1) to nudge velocities and mark
    # certain hits as fills so Jamstix / performance layers can respond.
    fill_bars = set(getattr(config, "fill_locations", []) or [])
    fill_intensity = float(getattr(config, "fill_density", 0.7) or 0.0)
    
    for bar_idx in range(config.measure_count):
        bar_time = bar_idx * bar_duration
        
        # Basic rock beat pattern
        # Kick on 1 and 3
        for beat in [0, 2]:
            events.append({
                "time_sec": bar_time + beat * beat_duration,
                "length_sec": 0.2,
                "instrument_id": "kick",
                "midi_pitch": instrument_id_to_midi_pitch("kick"),
                "velocity": int(100 + config.intensity * 20 + (10 * fill_intensity if is_fill_bar and beat == 2 else 0)),
                "isGhost": False,
                "isAccent": beat == 0,
                "isFlam": False,
                "isDrag": False,
            })
        
        # Snare on 2 and 4
        for beat in [1, 3]:
            events.append({
                "time_sec": bar_time + beat * beat_duration,
                "length_sec": 0.15,
                "instrument_id": "snare_center",
                "midi_pitch": instrument_id_to_midi_pitch("snare_center"),
                "velocity": int(95 + config.intensity * 25 + (15 * fill_intensity if is_fill_bar and beat == 3 else 0)),
                "isGhost": False,
                "isAccent": True,
                "isFlam": False,
                "isDrag": False,
            })
        
        # Hi-hat on 8th notes
        for eighth in range(config.time_signature[0] * 2):
            events.append({
                "time_sec": bar_time + eighth * (beat_duration / 2),
                "length_sec": 0.1,
                "instrument_id": "hihat_closed",
                "midi_pitch": instrument_id_to_midi_pitch("hihat_closed"),
                "velocity": int(75 + config.intensity * 15 + (8 * fill_intensity if is_fill_bar and eighth >= (config.time_signature[0] * 2 - 2) else 0)),
                "isGhost": eighth % 2 == 1,  # Off-beats are ghosts
                "isAccent": eighth % 2 == 0,
                "isFlam": False,
                "isDrag": False,
                # Mark the last beat of fill bars as fill hats so downstream layers
                # can treat them differently or emphasize them.
                "isFill": bool(is_fill_bar and eighth >= (config.time_signature[0] * 2 - 2)),
            })
    
    return events


def generate_simple_pattern_fallback(config: DrumGenerationConfig) -> List[Dict[str, Any]]:
    """
    Simple fallback pattern when Drum Builder v2.0 is not available.
    """
    events = []
    bar_duration = (60.0 / config.tempos[0]) * config.time_signature[0]
    beat_duration = bar_duration / config.time_signature[0]
    
    for bar_idx in range(config.measure_count):
        bar_time = bar_idx * bar_duration
        
        # Simple kick and snare
        events.append({
            "time_sec": bar_time,
            "length_sec": 0.2,
            "instrument_id": "kick",
            "midi_pitch": 36,
            "velocity": 100,
            "isGhost": False,
            "isAccent": False,
            "isFlam": False,
            "isDrag": False,
            "isFill": False,
        })
        
        events.append({
            "time_sec": bar_time + beat_duration,
            "length_sec": 0.15,
            "instrument_id": "snare_center",
            "midi_pitch": 38,
            "velocity": 95,
            "isGhost": False,
            "isAccent": False,
            "isFlam": False,
            "isDrag": False,
            "isFill": False,
        })
    
    return events


def export_track_to_midi_base64(dcsm_track, config: DrumGenerationConfig) -> str:
    """
    Export DrumTrackForDCSM to MIDI SMF base64.
    
    TODO: Replace with proper MIDI export
    """
    import base64
    
    # Simple mock MIDI file (just return empty for now)
    # In production, use mido or similar to create proper Type 1 MIDI
    mock_midi = b'MThd\x00\x00\x00\x06\x00\x01\x00\x02\x03\xc0MTrk\x00\x00\x00\x04\x00\xff\x2f\x00'
    return base64.b64encode(mock_midi).decode('utf-8')


# ============================================================================
# Legacy Generation (Fallback)
# ============================================================================

def generate_with_legacy_system(config: DrumGenerationConfig) -> Dict:
    """
    Legacy drum generation system (simple fallback).
    """
    
    logger.warning("Using simple fallback generation")
    
    # Generate basic MIDI notes
    midi_notes = []
    bar_duration = (60.0 / config.tempos[0]) * config.time_signature[0]
    beat_duration = bar_duration / config.time_signature[0]
    
    for bar_idx in range(config.measure_count):
        bar_time = bar_idx * bar_duration
        
        # Kick
        midi_notes.append({
            "time": bar_time,
            "note": 36,
            "velocity": 110,
            "drum": "kick",
            "length": 0.2,
        })
        
        # Snare
        midi_notes.append({
            "time": bar_time + beat_duration,
            "note": 38,
            "velocity": 100,
            "drum": "snare",
            "length": 0.15,
        })
    
    return {
        'ok': True,
        'midi_notes': midi_notes,
        'midi_base64': '',
        'metadata': {
            'drummer_used': config.drummer,
            'style': config.style,
            'mode': 'legacy_fallback',
            'humanized': False,
            'measure_count': config.measure_count,
        }
    }
