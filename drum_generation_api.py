"""
Drum Generation API - Drum Builder v2.0 Integration
===================================================
Integrates the three-layer drum builder with existing DrumTracKAI system.

This is the bridge between the aiohttp API and the new drum builder.
"""

import json
import time
import logging
import uuid
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sqlite3
import random

# Import Drum Builder v2.0 components
try:
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent / "backend"
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    
    from drum_generation.drum_generation_config import (
        DrumGenerationConfig as NewConfig,
        PartPerformanceOverrides,
        DrumBrainConfig,
        FillControls,
        RudimentControls,
        RudimentBlock,
        SongSection,
    )
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
    from drum_generation.song_drum_planner import generate_song_grid_events
    from drum_generation.rudiment_fill_planner import enrich_grid_with_rudiments
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

        self.style_group = data.get('styleGroup') or data.get('style_group')
        
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
        self.style_source_mode = data.get('styleSourceMode', 'combined')
        self.chorus_ride_preference = float(data.get('chorusRidePreference', 0.0) or 0.0)
        # Limb Bar Editor meta (optional)
        self.bars = data.get('bars')
        self.slots = data.get('slots')
        self.part_overrides = data.get('partOverrides')
        self.brain_config = data.get('brainConfig')

        # Song mode + rudiment directives
        self.song_style = data.get('songStyle')
        self.song_sections = data.get('songSections')
        self.fill_controls = data.get('fillControls')
        self.rudiment_controls = data.get('rudimentControls')
        self.rudiment_blocks = data.get('rudimentBlocks')
        
        # Additional metadata
        self.audio_key = data.get('audioKey')  # File key for analysis
        self.file_id = data.get('file_id') or data.get('audioKey')  # Alias

        # Optional: output MIDI mapping profile (e.g., Mixosaurus_EZ_Drummer)
        self.midi_map_name = data.get('midiMapName') or data.get('midi_map_name') or 'gm'

        self.groove_source = data.get('grooveSource') or data.get('groove_source')
        self.groove_controls = data.get('grooveControls') or data.get('groove_controls')
    
    @property
    def measure_count(self) -> int:
        return self.end_measure - self.start_measure + 1
    
    def _convert_part_overrides(self) -> Optional[List[PartPerformanceOverrides]]:
        if not self.part_overrides or not DRUM_BUILDER_V2_AVAILABLE:
            return None
        converted: List[PartPerformanceOverrides] = []
        for entry in self.part_overrides:
            if isinstance(entry, PartPerformanceOverrides):
                converted.append(entry)
            elif isinstance(entry, dict):
                try:
                    converted.append(PartPerformanceOverrides.from_dict(entry))
                except Exception:
                    continue
        return converted or None

    def _convert_brain_config(self) -> Optional[DrumBrainConfig]:
        data = self.brain_config
        if not data or not DRUM_BUILDER_V2_AVAILABLE:
            return None
        if isinstance(data, DrumBrainConfig):
            return data
        if isinstance(data, dict):
            try:
                return DrumBrainConfig.from_dict(data)
            except Exception:
                return None
        return None

    def _convert_song_sections(self) -> Optional[List[SongSection]]:
        if not self.song_sections or not DRUM_BUILDER_V2_AVAILABLE:
            return None
        converted: List[SongSection] = []
        for entry in self.song_sections:
            if isinstance(entry, SongSection):
                converted.append(entry)
                continue
            if not isinstance(entry, dict):
                continue
            name = entry.get('name') or entry.get('label') or entry.get('type') or 'section'
            bars_value = (
                entry.get('bars')
                or entry.get('lengthBars')
                or entry.get('measureCount')
                or entry.get('measures')
                or 0
            )
            try:
                bars = max(0, int(bars_value))
            except Exception:
                bars = 0
            converted.append(SongSection(name=name, bars=bars))
        return converted or None

    def _convert_fill_controls(self) -> Optional[FillControls]:
        data = self.fill_controls
        if not data or not DRUM_BUILDER_V2_AVAILABLE:
            return None
        if isinstance(data, FillControls):
            return data
        if isinstance(data, dict):
            return FillControls(
                fillType=data.get('fillType', self.fill_type),
                density=float(data.get('density', self.fill_density)),
                frequency=data.get('frequency', 'section_transitions'),
            )
        return None

    def _convert_rudiment_controls(self) -> Optional[RudimentControls]:
        data = self.rudiment_controls
        if not data or not DRUM_BUILDER_V2_AVAILABLE:
            return None
        if isinstance(data, RudimentControls):
            return data
        if isinstance(data, dict):
            return RudimentControls.from_dict(data)
        return None

    def _convert_rudiment_blocks(self) -> Optional[List[RudimentBlock]]:
        if not self.rudiment_blocks or not DRUM_BUILDER_V2_AVAILABLE:
            return None
        converted: List[RudimentBlock] = []
        for entry in self.rudiment_blocks:
            if isinstance(entry, RudimentBlock):
                converted.append(entry)
            elif isinstance(entry, dict):
                try:
                    converted.append(RudimentBlock.from_dict(entry))
                except Exception:
                    continue
        return converted or None

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
            styleSourceMode=self.style_source_mode,
            partOverrides=self._convert_part_overrides(),
            brainConfig=self._convert_brain_config(),
            songStyle=self.song_style,
            songSections=self._convert_song_sections(),
            fillControls=self._convert_fill_controls(),
            rudimentControls=self._convert_rudiment_controls(),
            rudimentBlocks=self._convert_rudiment_blocks(),
            chorusRidePreference=self.chorus_ride_preference,
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
    # IMPORTANT: For section-scoped generation the internal events are section-relative
    # (time_sec starts near 0), so the SongMap bars must also be section-relative.
    # Using absolute bar indices here causes the DCSM builder's find_bar_index() to miss
    # and clamp everything into the last bar of the section.
    songmap = build_mock_songmap_for_section(config)
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
    # construct internal events. When Song Mode metadata is supplied, hand off
    # to the SongDrumPlanner grid + rudiment pipeline before falling back to
    # the pattern layer.
    song_mode_active = bool(
        getattr(v2_config, "songSections", None)
        or getattr(v2_config, "songStyle", None)
    )

    groove_source = (getattr(config, "groove_source", None) or "").lower()
    egmd_phrase_info: Optional[Dict[str, Any]] = None
    egmd_transform_plan: Optional[Dict[str, Any]] = None
    if getattr(v2_config, "generationMode", None) == "euclidean" and getattr(v2_config, "euclideanLanes", None):
        internal_events = generate_euclidean_internal_events(config, v2_config)
    elif song_mode_active:
        grid_events = generate_song_grid_events(songmap, v2_config)
        if not grid_events:
            logger.info("SongDrumPlanner produced no events; falling back to pattern generator")
            internal_events = generate_pattern_events(config, drummer_profile)
        else:
            try:
                grid_events = enrich_grid_with_rudiments(grid_events=grid_events, config=v2_config)
            except Exception as err:
                logger.warning(f"Rudiment enrichment failed: {err}")
            internal_events = convert_song_grid_to_internal_events(
                grid_events=grid_events,
                songmap=songmap,
                config=config,
            )
            logger.info(
                "Song Mode: converted %d SongDrumPlanner grid events into %d internal events",
                len(grid_events),
                len(internal_events),
            )
    elif groove_source in {"egmd", "egmd_phrase", "egmd_phrases"}:
        phrase = _select_best_egmd_phrase(config)
        if phrase:
            egmd_phrase_info = phrase
            internal_events = _load_internal_events_from_midi_path(
                midi_path=phrase["midi_path"],
                config=config,
            )
            if internal_events:
                controls = getattr(config, 'groove_controls', None)
                if not isinstance(controls, dict):
                    controls = _default_groove_controls_from_config(config)
                measured = phrase.get('measured') if isinstance(phrase, dict) else None
                if isinstance(measured, dict):
                    egmd_transform_plan = _transform_plan_from_diff(controls, measured)
                    internal_events = _apply_transform_stack_v0(
                        internal_events=internal_events,
                        config=config,
                        transform_plan=egmd_transform_plan,
                    )
            if not internal_events:
                internal_events = generate_pattern_events(config, drummer_profile)
        else:
            internal_events = generate_pattern_events(config, drummer_profile)
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
    legacy_notes = convert_dcsm_track_to_legacy_format(dcsm_track, config)
    
    frontend_track = serialize_dcsm_track_for_frontend(dcsm_track, config)
    logger.info(
        "Frontend drum_track serialized for %s: %d notes (%s PPQ)",
        config.section_id,
        len(frontend_track.get("notes", [])),
        frontend_track.get("resolution_ppq")
    )

    metadata = {
        'drummer_used': config.drummer,
        'style': config.style,
        'mode': config.generation_mode,
        'humanized': config.humanize,
        'humanize_amount': config.humanize_amount,
        'ghost_notes': config.ghost_note_amount,
        'swing': config.swing_amount,
        'measure_count': config.measure_count,
        'tempo_range': f"{min(config.tempos):.0f}-{max(config.tempos):.0f} BPM",
        'resolution_ppq': frontend_track.get('resolution_ppq', 960),
        'performance_from_llm': True,
        'fill_density': getattr(config, 'fill_density', None),
        'articulation_profile': getattr(config, 'articulation_profile', None),
    }

    if egmd_phrase_info:
        metadata['egmdPhrase'] = {
            'phrase_id': egmd_phrase_info.get('phrase_id'),
            'midi_path': egmd_phrase_info.get('midi_path'),
            'audio_path': egmd_phrase_info.get('audio_path'),
            'measured': egmd_phrase_info.get('measured'),
            'controls': getattr(config, 'groove_controls', None) if isinstance(getattr(config, 'groove_controls', None), dict) else None,
            'style_group': getattr(config, 'style_group', None),
        }
        if egmd_transform_plan:
            metadata['egmdPhrase']['transformPlan'] = egmd_transform_plan

    return {
        'ok': True,
        'drum_track': frontend_track,  # New high-res format aligned with WebDAW expectations
        'midi_notes': legacy_notes,  # Legacy piano-roll compatibility
        'midi_base64': midi_b64,
        'metadata': metadata,
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


_DRUM_TRAINING_DB_PATH = Path(__file__).parent / "admin" / "data" / "drum_training.db"


def _egmd_db_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DRUM_TRAINING_DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _select_rudiment_midi_asset(
    *,
    family: Optional[str] = None,
    limit: int = 200,
) -> Optional[Dict[str, Any]]:
    if not _DRUM_TRAINING_DB_PATH.exists():
        return None

    fam = (family or "").strip().lower()
    conn = _egmd_db_connect()
    try:
        cur = conn.cursor()
        if fam:
            cur.execute(
                """
                SELECT id, rudiment_name, rudiment_family, midi_path
                FROM rudiment_fragments
                WHERE midi_path IS NOT NULL
                  AND rudiment_family = ?
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (fam, int(limit)),
            )
        else:
            cur.execute(
                """
                SELECT id, rudiment_name, rudiment_family, midi_path
                FROM rudiment_fragments
                WHERE midi_path IS NOT NULL
                ORDER BY RANDOM()
                LIMIT ?
                """,
                (int(limit),),
            )

        rows = cur.fetchall()
        if not rows:
            return None
        chosen = random.choice(rows)
        return {
            "id": int(chosen["id"]),
            "name": chosen["rudiment_name"],
            "family": chosen["rudiment_family"],
            "midi_path": chosen["midi_path"],
        }
    finally:
        conn.close()


def _load_rudiment_events_from_midi_path(*, midi_path: str) -> List[Dict[str, Any]]:
    """Load rudiment MIDI (snare-only) into internal events with times relative to start (>=0)."""
    try:
        import mido
    except Exception:
        return []

    midi_file = Path(midi_path)
    if not midi_file.exists():
        return []

    try:
        mid = mido.MidiFile(str(midi_file))
    except Exception:
        return []

    tempo_us = 500000
    hits: List[Tuple[float, int]] = []
    for track in mid.tracks:
        t = 0.0
        tempo_us_local = tempo_us
        for msg in track:
            t += mido.tick2second(msg.time, mid.ticks_per_beat, tempo_us_local)
            if msg.type == "set_tempo":
                tempo_us_local = int(msg.tempo)
            elif msg.type == "note_on" and msg.velocity and msg.velocity > 0:
                if getattr(msg, "channel", None) != 9:
                    continue
                hits.append((float(t), int(msg.velocity)))

    if not hits:
        return []

    t0 = min(t for t, _ in hits)
    events: List[Dict[str, Any]] = []
    for t, vel in hits:
        events.append(
            {
                "time_sec": float(t - t0),
                "length_sec": 0.08,
                "instrument_id": "snare_center",
                "midi_pitch": int(instrument_id_to_midi_pitch("snare_center")),
                "velocity": int(max(1, min(127, vel))),
                "isGhost": int(vel) < 30,
                "isAccent": int(vel) > 100,
                "isFlam": False,
                "isDrag": False,
                "isFill": True,
            }
        )
    events.sort(key=lambda e: float(e.get("time_sec", 0.0)))
    return events


def _safe_ratio(n: float, d: float) -> float:
    if d <= 0:
        return 0.0
    return float(n) / float(d)


def _derive_phrase_features_from_json(feature_json: Dict[str, Any]) -> Dict[str, float]:
    drum_counts = feature_json.get("drum_counts") or {}
    total_hits = float(feature_json.get("total_hits") or 0.0)
    duration = float(feature_json.get("duration") or 0.0)
    density = float(feature_json.get("pattern_density") or (total_hits / duration if duration > 0 else 0.0))
    swing = float(feature_json.get("swing_amount") or 0.0)

    hihat_art = feature_json.get("hihat_articulations") or {}
    hihat_hits = float(hihat_art.get("total_hihat_hits") or 0.0)

    ghost_notes = float(feature_json.get("ghost_notes") or 0.0)
    accents = float(feature_json.get("accents") or 0.0)

    fill_segments = feature_json.get("fill_segments") or []
    fill_count = float(len(fill_segments))

    kick = float(drum_counts.get("kick") or 0.0)
    snare = float(drum_counts.get("snare") or 0.0)
    ride = float(drum_counts.get("ride") or 0.0)
    crash = float(drum_counts.get("crash") or 0.0)

    return {
        "tempo": float(feature_json.get("tempo") or 0.0),
        "duration": duration,
        "density": density,
        "swing": swing,
        "kick_ratio": _safe_ratio(kick, total_hits),
        "snare_ratio": _safe_ratio(snare, total_hits),
        "hihat_ratio": _safe_ratio(hihat_hits, total_hits),
        "ride_ratio": _safe_ratio(ride, total_hits),
        "cymbal_ratio": _safe_ratio(ride + crash, total_hits),
        "ghost_ratio": _safe_ratio(ghost_notes, total_hits),
        "accent_ratio": _safe_ratio(accents, total_hits),
        "fill_rate": _safe_ratio(fill_count, max(duration, 0.001)),
    }


def _score_phrase(target: Dict[str, Any], pf: Dict[str, float]) -> float:
    tempo_target = float(target.get("tempo_bpm") or 120.0)
    tempo_tol = float(target.get("tempo_tolerance_bpm") or 10.0)
    tempo_err = abs(pf.get("tempo", 0.0) - tempo_target) / max(tempo_tol, 1.0)

    density_target = float(target.get("density_hps") or 8.0)
    density_err = abs(pf.get("density", 0.0) - density_target) / max(density_target, 1e-3)

    swing_target = float(target.get("swing") or 0.0)
    swing_err = abs(pf.get("swing", 0.0) - swing_target)

    hihat_target = float(target.get("hihat_ratio") or 0.2)
    hihat_err = abs(pf.get("hihat_ratio", 0.0) - hihat_target)

    fill_target = float(target.get("fill_rate") or 0.0)
    fill_err = abs(pf.get("fill_rate", 0.0) - fill_target) / max(fill_target, 1e-3)

    ghost_target = float(target.get("ghost_ratio") or 0.0)
    ghost_err = abs(pf.get("ghost_ratio", 0.0) - ghost_target) / max(ghost_target, 1e-3)

    kick_target = float(target.get("kick_ratio") or 0.12)
    kick_err = abs(pf.get("kick_ratio", 0.0) - kick_target) / max(kick_target, 1e-3)

    snare_target = float(target.get("snare_ratio") or 0.12)
    snare_err = abs(pf.get("snare_ratio", 0.0) - snare_target) / max(snare_target, 1e-3)

    return (
        2.5 * tempo_err
        + 1.5 * density_err
        + 1.0 * swing_err
        + 1.0 * hihat_err
        + 0.6 * fill_err
        + 0.6 * ghost_err
        + 0.4 * kick_err
        + 0.4 * snare_err
    )


def _default_groove_controls_from_config(config: DrumGenerationConfig) -> Dict[str, Any]:
    style_group = getattr(config, "style_group", None)
    if isinstance(style_group, str) and style_group.strip():
        style_group = style_group.strip().lower()
    else:
        style_group = (getattr(config, "style", None) or "").split("_")[0].split("-")[0].lower() or "rock"
    tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)
    meter = f"{int(getattr(config, 'time_signature', (4, 4))[0])}/{int(getattr(config, 'time_signature', (4, 4))[1])}"

    intensity = float(getattr(config, "intensity", 0.7) or 0.7)
    density = 6.0 + intensity * 6.0
    swing = float(getattr(config, "swing_amount", 0.0) or 0.0)

    return {
        "style_group": style_group,
        "meter": meter,
        "tempo_bpm": tempo,
        "tempo_tolerance_bpm": 12,
        "density_hps": density,
        "swing": swing,
        "hihat_ratio": 0.25,
        "kick_ratio": 0.12,
        "snare_ratio": 0.12,
        "fill_rate": 0.04,
        "ghost_ratio": 0.08,
    }


def _select_best_egmd_phrase(config: DrumGenerationConfig) -> Optional[Dict[str, Any]]:
    if not _DRUM_TRAINING_DB_PATH.exists():
        logger.warning("drum_training.db not found at %s", _DRUM_TRAINING_DB_PATH)
        return None

    controls = getattr(config, "groove_controls", None)
    if not isinstance(controls, dict):
        controls = _default_groove_controls_from_config(config)

    style_group = (controls.get("style_group") or "").lower()
    if not style_group:
        style_group = "rock"

    meter = controls.get("meter")
    tempo = float(controls.get("tempo_bpm") or 120.0)
    tol = float(controls.get("tempo_tolerance_bpm") or 12.0)
    tempo_min = tempo - tol
    tempo_max = tempo + tol

    pool = int(controls.get("candidate_pool", 2500) or 2500)
    top_k = int(controls.get("top_k", 50) or 50)
    top_k = max(1, min(200, top_k))

    conn = _egmd_db_connect()
    try:
        cur = conn.cursor()
        if meter:
            cur.execute(
                """
                SELECT id, midi_path, audio_path, feature_json
                FROM egmd_phrases
                WHERE style_group = ?
                  AND time_signature = ?
                  AND tempo BETWEEN ? AND ?
                  AND feature_json IS NOT NULL
                ORDER BY RANDOM() LIMIT ?
                """,
                (style_group, meter, tempo_min, tempo_max, pool),
            )
        else:
            cur.execute(
                """
                SELECT id, midi_path, audio_path, feature_json
                FROM egmd_phrases
                WHERE style_group = ?
                  AND tempo BETWEEN ? AND ?
                  AND feature_json IS NOT NULL
                ORDER BY RANDOM() LIMIT ?
                """,
                (style_group, tempo_min, tempo_max, pool),
            )
        rows = cur.fetchall()
        if not rows:
            return None

        best_rows: List[Tuple[float, sqlite3.Row, Dict[str, float]]] = []
        for row in rows:
            try:
                fj = json.loads(row["feature_json"]) if row["feature_json"] else {}
            except Exception:
                continue
            pf = _derive_phrase_features_from_json(fj)
            score = _score_phrase(controls, pf)
            best_rows.append((score, row, pf))

        if not best_rows:
            return None

        best_rows.sort(key=lambda x: x[0])
        shortlist = best_rows[:top_k]
        chosen = random.choice(shortlist)
        _, row, pf = chosen
        return {
            "phrase_id": int(row["id"]),
            "midi_path": row["midi_path"],
            "audio_path": row["audio_path"],
            "measured": pf,
        }
    finally:
        conn.close()


def _load_internal_events_from_midi_path(*, midi_path: str, config: DrumGenerationConfig) -> List[Dict[str, Any]]:
    try:
        import mido
    except Exception:
        return []

    from dcsmpiano.dcsm_drumtrack_schema import midi_pitch_to_instrument_id

    midi_file = Path(midi_path)
    if not midi_file.exists():
        return []

    try:
        mid = mido.MidiFile(str(midi_file))
    except Exception:
        return []

    tempo_us = 500000
    events: List[Dict[str, Any]] = []
    max_time = 0.0

    for track in mid.tracks:
        t = 0.0
        tempo_us_local = tempo_us
        for msg in track:
            t += mido.tick2second(msg.time, mid.ticks_per_beat, tempo_us_local)
            if msg.type == "set_tempo":
                tempo_us_local = int(msg.tempo)
            elif msg.type == "note_on" and msg.velocity and msg.velocity > 0:
                if getattr(msg, "channel", None) != 9:
                    continue
                try:
                    instrument_id = midi_pitch_to_instrument_id(int(msg.note))
                except Exception:
                    instrument_id = "unknown"
                length = 0.12
                is_ghost = int(msg.velocity) < 30
                is_accent = int(msg.velocity) > 100
                events.append(
                    {
                        "time_sec": float(t),
                        "length_sec": float(length),
                        "instrument_id": instrument_id,
                        "midi_pitch": int(msg.note),
                        "velocity": int(msg.velocity),
                        "isGhost": bool(is_ghost),
                        "isAccent": bool(is_accent),
                        "isFlam": False,
                        "isDrag": False,
                    }
                )
                if t > max_time:
                    max_time = t

    if not events:
        return []

    beats_per_bar = int(getattr(config, "time_signature", (4, 4))[0] or 4)
    tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)
    total_bars = int(getattr(config, "measure_count", 1) or 1)
    max_allowed = (60.0 / max(tempo, 1e-3)) * beats_per_bar * total_bars

    if max_allowed > 0:
        events = [e for e in events if float(e.get("time_sec", 0.0)) < max_allowed]
    return events


def _transform_plan_from_diff(target: Dict[str, Any], measured: Dict[str, Any]) -> Dict[str, Any]:
    def clamp(x: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, x))

    density_delta = float(target.get("density_hps", 8.0)) - float(measured.get("density", 8.0))
    swing_delta = float(target.get("swing", 0.0)) - float(measured.get("swing", 0.0))

    base_density = max(float(measured.get("density", 8.0)), 1e-3)
    density_multiplier = clamp(1.0 + (density_delta / base_density) * 0.5, 0.4, 2.0)

    ghost_boost = clamp(float(target.get("ghost_ratio", 0.08)) - float(measured.get("ghost_ratio", 0.08)), -0.3, 0.3)
    fill_injection = clamp(float(target.get("fill_rate", 0.04)) - float(measured.get("fill_rate", 0.04)), -0.5, 0.5)
    hats_to_ride = clamp(float(target.get("cymbal_preference", 0.2)), 0.0, 1.0)

    return {
        "density_multiplier": density_multiplier,
        "swing_delta": clamp(swing_delta, -0.35, 0.35),
        "ghost_note_boost": ghost_boost,
        "fill_injection": fill_injection,
        "hats_to_ride": hats_to_ride,
        "kick_bias": clamp(float(target.get("kick_ratio", 0.12)) - float(measured.get("kick_ratio", 0.12)), -0.25, 0.25),
        "snare_bias": clamp(float(target.get("snare_ratio", 0.12)) - float(measured.get("snare_ratio", 0.12)), -0.25, 0.25),
    }


def _apply_transform_stack_v0(
    *,
    internal_events: List[Dict[str, Any]],
    config: DrumGenerationConfig,
    transform_plan: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not internal_events:
        return internal_events

    beats_per_bar = int(getattr(config, "time_signature", (4, 4))[0] or 4)
    tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)
    bar_duration = (60.0 / max(tempo, 1e-3)) * beats_per_bar
    measure_count = int(getattr(config, "measure_count", 1) or 1)

    density_multiplier = float(transform_plan.get("density_multiplier", 1.0))
    swing_delta = float(transform_plan.get("swing_delta", 0.0))
    hats_to_ride = float(transform_plan.get("hats_to_ride", 0.0))
    ghost_boost = float(transform_plan.get("ghost_note_boost", 0.0))
    fill_injection = float(transform_plan.get("fill_injection", 0.0))

    rng = random.Random(int(getattr(config, "start_measure", 0) or 0) + 1337)
    events = [dict(e) for e in internal_events]

    # (1) hats↔ride orchestrator
    if hats_to_ride >= 0.05:
        for e in events:
            inst = e.get("instrument_id")
            if inst in {"hihat_closed", "hihat_open", "hihat_pedal"}:
                if rng.random() < hats_to_ride * 0.6:
                    e["instrument_id"] = "ride_bow"
                    try:
                        e["midi_pitch"] = instrument_id_to_midi_pitch("ride_bow")
                    except Exception:
                        pass

    # (2) density scaling (drop or add hats)
    if density_multiplier < 0.98:
        keep_prob = max(0.2, min(1.0, density_multiplier))
        filtered: List[Dict[str, Any]] = []
        for e in events:
            inst = e.get("instrument_id")
            if inst in {"hihat_closed", "hihat_open", "ride_bow", "ride_edge"}:
                if rng.random() <= keep_prob:
                    filtered.append(e)
            else:
                filtered.append(e)
        events = filtered
    elif density_multiplier > 1.02:
        add_rate = min(1.0, (density_multiplier - 1.0) * 0.6)
        extra: List[Dict[str, Any]] = []
        step = bar_duration / (beats_per_bar * 4.0)  # 16th
        for bar_idx in range(measure_count):
            bar_time = bar_idx * bar_duration
            for step_idx in range(int(beats_per_bar * 4)):
                if rng.random() > add_rate:
                    continue
                time_sec = bar_time + step_idx * step
                extra.append(
                    {
                        "time_sec": float(time_sec),
                        "length_sec": float(step * 0.9),
                        "instrument_id": "hihat_closed",
                        "midi_pitch": int(instrument_id_to_midi_pitch("hihat_closed")),
                        "velocity": int(55 + rng.randint(0, 25)),
                        "isGhost": True,
                        "isAccent": False,
                        "isFlam": False,
                        "isDrag": False,
                    }
                )
        events.extend(extra)

    # (3) swing delta: push even 16ths a bit later/earlier
    if abs(swing_delta) > 1e-4:
        step = bar_duration / (beats_per_bar * 4.0)
        max_offset = step * 0.33
        for e in events:
            t = float(e.get("time_sec", 0.0))
            bar_pos = (t % bar_duration) / step if step > 0 else 0.0
            step_idx = int(round(bar_pos))
            # even 16th subdivisions (1,3,5...) are the "off" positions
            if step_idx % 2 == 1:
                e["time_sec"] = float(t + max(-max_offset, min(max_offset, swing_delta * max_offset)))

    # (4) ghost boost: inject soft snare notes before backbeats
    if ghost_boost > 0.02:
        ghosts: List[Dict[str, Any]] = []
        beat = bar_duration / beats_per_bar
        for bar_idx in range(measure_count):
            bar_time = bar_idx * bar_duration
            for backbeat in (1, 3):
                ghost_time = bar_time + backbeat * beat - beat * 0.25
                if ghost_time < bar_time:
                    continue
                if rng.random() < min(0.9, ghost_boost * 3.0):
                    ghosts.append(
                        {
                            "time_sec": float(ghost_time),
                            "length_sec": float(0.08),
                            "instrument_id": "snare_center",
                            "midi_pitch": int(instrument_id_to_midi_pitch("snare_center")),
                            "velocity": int(25 + rng.randint(0, 18)),
                            "isGhost": True,
                            "isAccent": False,
                            "isFlam": False,
                            "isDrag": False,
                        }
                    )
        events.extend(ghosts)

    # (5) fill injection: prefer MIDI-backed rudiment assets, fallback to tom run
    if fill_injection > 0.05:
        fills: List[Dict[str, Any]] = []
        beat = bar_duration / beats_per_bar
        rudiment_family = rng.choice(["roll", "flam", "drag", "paradiddle", "ratamacue", "other"])
        asset = _select_rudiment_midi_asset(family=rudiment_family)
        rudiment_events = _load_rudiment_events_from_midi_path(midi_path=asset["midi_path"]) if asset else []

        for bar_idx in range(measure_count):
            if rng.random() > min(0.9, fill_injection * 2.0):
                continue
            bar_time = bar_idx * bar_duration
            start = bar_time + bar_duration - beat

            if rudiment_events:
                # Fit rudiment into the last beat by scaling its time range.
                max_r_time = float(rudiment_events[-1].get("time_sec", 0.0))
                scale = (beat * 0.95) / max(max_r_time, 1e-3)
                for e in rudiment_events:
                    injected = dict(e)
                    injected["time_sec"] = float(start + float(e.get("time_sec", 0.0)) * scale)
                    fills.append(injected)
            else:
                for i, inst in enumerate(["tom_low", "tom_mid", "tom_high", "snare_center"]):
                    t = start + i * (beat / 4.0)
                    fills.append(
                        {
                            "time_sec": float(t),
                            "length_sec": float(0.1),
                            "instrument_id": inst,
                            "midi_pitch": int(instrument_id_to_midi_pitch(inst)),
                            "velocity": int(75 + rng.randint(0, 35)),
                            "isGhost": False,
                            "isAccent": True,
                            "isFlam": False,
                            "isDrag": False,
                            "isFill": True,
                        }
                    )

        events.extend(fills)

    events.sort(key=lambda e: float(e.get("time_sec", 0.0)))
    max_allowed = bar_duration * measure_count
    events = [e for e in events if 0.0 <= float(e.get("time_sec", 0.0)) <= max_allowed]
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


def build_mock_songmap_for_section(config: DrumGenerationConfig):
    """
    Build minimal SongMap object for a section.
    TODO: Replace with real SongMap from audio analysis.
    """
    class MockBar:
        def __init__(self, idx, tempo):
            bar_duration = (60.0 / tempo) * config.time_signature[0]
            # IMPORTANT: internal_drum_events are section-relative (time_sec starts near 0).
            # If we use absolute bar indices here, find_bar_index() will miss and clamp
            # everything into the last bar of the section (collapsing barIndex).
            rel_idx = idx - config.start_measure
            self.start_time = rel_idx * bar_duration
            self.end_time = (rel_idx + 1) * bar_duration
            self.tempo_bpm = tempo
            self.meter = config.time_signature
    
    class MockSongMap:
        def __init__(self):
            self.bars = [
                MockBar(
                    i,
                    config.tempos[
                        min(
                            max(0, i - config.start_measure),
                            len(config.tempos) - 1,
                        )
                    ],
                )
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


def serialize_dcsm_track_for_frontend(dcsm_track, config: DrumGenerationConfig) -> Dict[str, Any]:
    """Flatten DrumTrack (bars + note objects) into DrumTrackForDCSM schema used by the WebDAW."""

    if not dcsm_track:
        return {
            "track_id": f"{config.section_id}-{uuid.uuid4().hex[:8]}",
            "style_id": config.style,
            "resolution_ppq": 960,
            "notes": [],
            "performance_spec": {},
        }

    def note_attr(note_obj, attr: str, default=None):
        if isinstance(note_obj, dict):
            return note_obj.get(attr, default)
        return getattr(note_obj, attr, default)

    resolution = getattr(dcsm_track, "resolution_ppq", 960) or 960
    notes: List[Dict[str, Any]] = []

    raw_notes = getattr(dcsm_track, "notes", None)
    if raw_notes:
        iterable = enumerate(raw_notes)
        get_bar_index = lambda n, idx: int(note_attr(n, "barIndex", 0) or 0)
    else:
        bars = getattr(dcsm_track, "bars", []) or []
        iterable = (
            (idx * 10_000 + n_idx, note)
            for idx, bar in enumerate(bars)
            for n_idx, note in enumerate(getattr(bar, "notes", []) or [])
        )

        def get_bar_index(note_obj, idx_token):
            return int(
                note_attr(note_obj, "barIndex", note_attr(note_obj, "bar_index", idx_token // 10_000))
                or 0
            )

    for idx_token, note in iterable:
        bar_index = get_bar_index(note, idx_token)
        instrument_id = (
            note_attr(note, "instrumentId")
            or note_attr(note, "instrument")
            or "snare_center"
        )
        midi_pitch = note_attr(note, "midiPitch") or instrument_id_to_midi_pitch(instrument_id)
        note_id = note_attr(note, "id") or f"{config.section_id}-{bar_index}-{idx_token}-{uuid.uuid4().hex[:6]}"

        aspect = note_attr(note, "aspect")
        is_ghost = bool(note_attr(note, "isGhost", False) or aspect == "ghost")
        is_accent = bool(note_attr(note, "isAccent", False) or aspect == "accent")

        notes.append(
            {
                "id": note_id,
                "barIndex": bar_index,
                "tickInBar": int(note_attr(note, "tickInBar", 0) or 0),
                "tickLength": int(note_attr(note, "tickLength", resolution // 4) or resolution // 4),
                "instrumentId": instrument_id,
                "channel": int(note_attr(note, "channel", 10) or 10),
                "midiPitch": int(midi_pitch or instrument_id_to_midi_pitch("snare_center")),
                "velocity": int(note_attr(note, "velocity", 96) or 96),
                "aspect": aspect,
                "limbId": note_attr(note, "limbId"),
                "priority": note_attr(note, "priority"),
                "microTimingMs": note_attr(note, "microTimingMs", note_attr(note, "micro_timing_ms")),
                "hatOpenLevel": note_attr(note, "hatOpenLevel"),
                "hitStyle": note_attr(note, "hitStyle"),
                "locked": bool(note_attr(note, "locked", False)),
                "isGhost": is_ghost,
                "isAccent": is_accent,
                "isFlam": bool(note_attr(note, "isFlam", False)),
                "isDrag": bool(note_attr(note, "isDrag", False)),
                "phraseMarker": note_attr(note, "phraseMarker"),
                "rudimentId": note_attr(note, "rudimentId"),
            }
        )

    performance_spec = getattr(dcsm_track, "performanceSpec", {}) or {}

    return {
        "track_id": getattr(dcsm_track, "track_id", f"{config.section_id}-{uuid.uuid4().hex[:8]}"),
        "style_id": getattr(dcsm_track, "style_id", config.style),
        "resolution_ppq": resolution,
        "notes": notes,
        "performance_spec": performance_spec,
    }


def convert_dcsm_track_to_legacy_format(
    dcsm_track,
    config: DrumGenerationConfig,
) -> List[Dict[str, Any]]:
    """Convert DrumTrackForDCSM notes into the legacy time-based schema."""

    if not dcsm_track or not getattr(dcsm_track, "notes", None):
        return []

    beats_per_bar = config.time_signature[0] or 4
    tempos = config.tempos or [120.0]

    max_bar_index = 0
    for note in dcsm_track.notes:
        max_bar_index = max(max_bar_index, getattr(note, "barIndex", 0))

    total_bars = max(1, config.measure_count, max_bar_index + 1, len(tempos))
    bar_start_times: List[float] = []
    bar_tempos: List[float] = []
    cumulative_time = 0.0

    for idx in range(total_bars):
        tempo = tempos[min(idx, len(tempos) - 1)]
        bar_tempos.append(tempo)
        bar_start_times.append(cumulative_time)
        cumulative_time += (60.0 / tempo) * beats_per_bar

    resolution = getattr(dcsm_track, "resolution_ppq", 960) or 960
    seconds_per_tick_cache: Dict[int, float] = {}

    legacy_notes: List[Dict[str, Any]] = []
    for note in dcsm_track.notes:
        bar_index = getattr(note, "barIndex", 0)
        safe_index = min(bar_index, len(bar_start_times) - 1)
        tempo = bar_tempos[safe_index]
        bar_start = bar_start_times[safe_index]
        if tempo not in seconds_per_tick_cache:
            seconds_per_tick_cache[tempo] = (60.0 / tempo) / resolution
        seconds_per_tick = seconds_per_tick_cache[tempo]

        tick_in_bar = getattr(note, "tickInBar", 0)
        tick_length = getattr(note, "tickLength", 0)

        time_sec = bar_start + tick_in_bar * seconds_per_tick
        length_sec = max(0.01, tick_length * seconds_per_tick)

        legacy_notes.append(
            {
                "time": time_sec,
                "note": note.midiPitch,
                "velocity": note.velocity,
                "drum": note.instrumentId,
                "length": length_sec,
            }
        )

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
        is_fill_bar = bar_idx in fill_bars
        
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


def _velocity_from_grid_event(instrument_id: str, intensity: float, is_accent: bool, override: Optional[int]) -> int:
    if isinstance(override, (int, float)) and override > 0:
        return max(1, min(127, int(override)))

    base_map = {
        "kick": 108,
        "kick_sub": 110,
        "snare_center": 102,
        "snare": 100,
        "rimshot": 115,
        "hihat_closed": 82,
        "hihat_pedal": 78,
        "hihat_open": 92,
        "ride_bow": 90,
        "ride_bell": 95,
        "tom_high": 92,
        "tom_mid": 95,
        "tom_low": 98,
        "crash": 118,
    }
    base = base_map.get(instrument_id, 96)
    accent_bonus = 12 if is_accent else 0
    intensity_bias = (float(intensity) - 0.5) * 30.0
    velocity = int(base + accent_bonus + intensity_bias)
    return max(30, min(127, velocity))


def convert_song_grid_to_internal_events(
    grid_events: List[Any],
    songmap: Any,
    config: DrumGenerationConfig,
) -> List[Dict[str, Any]]:
    """Convert SongDrumPlanner GridEvents into Drum Builder internal events."""

    bars = getattr(songmap, "bars", []) or []
    beats_per_bar = config.time_signature[0] or 4

    def bar_times(idx: int) -> Tuple[float, float]:
        if 0 <= idx < len(bars):
            bar = bars[idx]
            start = getattr(bar, "start_time", None)
            end = getattr(bar, "end_time", None)
            if start is not None and end is not None and end > start:
                return start, end

        tempo = config.tempos[min(idx, len(config.tempos) - 1)] if config.tempos else 120.0
        bar_duration = (60.0 / tempo) * beats_per_bar
        start = idx * bar_duration
        end = start + bar_duration
        return start, end

    internal_events: List[Dict[str, Any]] = []

    for grid_event in grid_events:
        bar_index = int(getattr(grid_event, "bar_index", 0))
        bar_start, bar_end = bar_times(bar_index)
        subdivisions = max(1, int(getattr(grid_event, "subdivisions_per_bar", 16)))
        step_length = (bar_end - bar_start) / subdivisions
        subdivision_index = int(getattr(grid_event, "subdivision_index", 0))
        subdivision_index = max(0, min(subdivision_index, subdivisions - 1))

        subdivision_offset = float(getattr(grid_event, "swing_offset_seconds", 0.0))
        time_sec = bar_start + subdivision_index * step_length + subdivision_offset

        instrument_id = getattr(grid_event, "instrument_id", None) or "kick"
        velocity_override = getattr(grid_event, "velocity", None)
        is_accent = bool(getattr(grid_event, "is_accent", False))

        velocity = _velocity_from_grid_event(
            instrument_id=instrument_id,
            intensity=getattr(config, "intensity", 0.7),
            is_accent=is_accent,
            override=velocity_override,
        )

        length_override = getattr(grid_event, "duration_seconds", None)
        if length_override is None:
            length_override = getattr(grid_event, "length_seconds", None)
        length_sec = float(length_override) if length_override else step_length * 0.9

        rudiment_id = getattr(grid_event, "rudiment_id", None)
        is_fill = bool(getattr(grid_event, "is_fill", False))
        if rudiment_id:
            is_fill = True

        internal_events.append(
            {
                "time_sec": time_sec,
                "length_sec": length_sec,
                "instrument_id": instrument_id,
                "midi_pitch": instrument_id_to_midi_pitch(instrument_id),
                "velocity": velocity,
                "isGhost": bool(getattr(grid_event, "is_ghost", False)),
                "isAccent": is_accent,
                "isFlam": bool(getattr(grid_event, "is_flam", False)),
                "isDrag": bool(getattr(grid_event, "is_drag", False)),
                "isFill": is_fill,
                "phraseMarker": getattr(grid_event, "phrase_marker", None),
                "rudimentId": rudiment_id,
            }
        )

    return internal_events


def export_track_to_midi_base64(dcsm_track, config: DrumGenerationConfig) -> str:
    """
    Export DrumTrackForDCSM to MIDI SMF base64.
    
    Emits a single-track SMF with drum notes on channel 10 (0-indexed channel 9).
    If `config.midi_map_name` is set to "Mixosaurus_EZ_Drummer", we additionally emit
    CC4 (Foot Controller) for hi-hat openness using Mixosaurus polarity:
      - CC4 0   = very loose/open
      - CC4 127 = very tight/closed
    """
    import base64
    from io import BytesIO

    try:
        from mido import Message, MidiFile, MidiTrack, MetaMessage
    except Exception:
        # Fallback to a tiny empty MIDI if mido isn't available.
        mock_midi = b'MThd\x00\x00\x00\x06\x00\x01\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\xff\x2f\x00'
        return base64.b64encode(mock_midi).decode('utf-8')

    ppq = 480
    tempo_bpm = float(config.tempos[0]) if getattr(config, 'tempos', None) else 120.0
    tempo_bpm = max(20.0, min(400.0, tempo_bpm))
    tempo_us_per_beat = int(60_000_000 / tempo_bpm)
    beats_per_bar = int(config.time_signature[0]) if getattr(config, 'time_signature', None) else 4
    beats_per_bar = max(1, beats_per_bar)
    bar_ticks = beats_per_bar * ppq

    mid = MidiFile(type=1)
    mid.ticks_per_beat = ppq
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(MetaMessage('set_tempo', tempo=tempo_us_per_beat, time=0))

    # Flatten note list
    raw_notes = []
    if dcsm_track and getattr(dcsm_track, 'notes', None):
        raw_notes = list(dcsm_track.notes)
    elif dcsm_track and isinstance(dcsm_track, dict) and dcsm_track.get('notes'):
        raw_notes = list(dcsm_track.get('notes') or [])

    def note_attr(note_obj, key, default=None):
        if isinstance(note_obj, dict):
            return note_obj.get(key, default)
        return getattr(note_obj, key, default)

    def clamp_int(v, lo, hi, default):
        try:
            iv = int(v)
        except Exception:
            return default
        return max(lo, min(hi, iv))

    midi_map = (getattr(config, 'midi_map_name', None) or 'gm').strip()

    # Mixosaurus core mappings are consistent with GM/EZ for these pieces.
    # We keep notes as-is and focus on CC4 hat openness + any future articulation mappings.
    def map_note_number(instrument_id: str, midi_pitch: int) -> int:
        if midi_map != 'Mixosaurus_EZ_Drummer':
            return midi_pitch

        # Preserve core mapping; add a couple of safe upgrades.
        inst = (instrument_id or '').lower()
        if inst == 'snare_rim':
            # Your confirmation: EZ note 40 commonly maps to center rimshot.
            return 40
        return midi_pitch

    def cc4_from_hat_open_level(hat_open_level) -> int:
        # hatOpenLevel: 0..1 where 0=closed, 1=open
        # Mixosaurus CC4 polarity: 0=open/loose, 127=closed/tight
        try:
            v = float(hat_open_level)
        except Exception:
            v = 0.5
        v = max(0.0, min(1.0, v))
        return int(round((1.0 - v) * 127.0))

    events = []
    for note in raw_notes:
        bar_index = clamp_int(note_attr(note, 'barIndex', 0), 0, 1_000_000, 0)
        tick_in_bar = clamp_int(note_attr(note, 'tickInBar', 0), 0, 10_000_000, 0)
        tick_len = clamp_int(note_attr(note, 'tickLength', ppq // 4), 1, 10_000_000, ppq // 4)
        channel = clamp_int(note_attr(note, 'channel', 9), 0, 15, 9)
        velocity = clamp_int(note_attr(note, 'velocity', 100), 1, 127, 100)
        midi_pitch = clamp_int(note_attr(note, 'midiPitch', 36), 0, 127, 36)
        instrument_id = str(note_attr(note, 'instrumentId', ''))
        hat_open_level = note_attr(note, 'hatOpenLevel', None)

        t0 = bar_index * bar_ticks + tick_in_bar
        t1 = max(t0 + 1, t0 + tick_len)

        out_note = map_note_number(instrument_id, midi_pitch)

        ccs = []
        if midi_map == 'Mixosaurus_EZ_Drummer' and instrument_id in ('hihat_closed', 'hihat_open'):
            ccs.append({'controller': 4, 'value': cc4_from_hat_open_level(hat_open_level)})

        events.append({'tick': t0, 'kind': 'note_on', 'note': out_note, 'vel': velocity, 'chan': channel, 'ccs': ccs})
        events.append({'tick': t1, 'kind': 'note_off', 'note': out_note, 'vel': 0, 'chan': channel, 'ccs': []})

    events.sort(key=lambda e: (e['tick'], 0 if e['kind'] == 'note_off' else 1))

    last_tick = 0
    for ev in events:
        dt = max(0, int(ev['tick']) - last_tick)
        last_tick = int(ev['tick'])

        first_cc = True
        for cc_spec in ev.get('ccs', []) or []:
            track.append(
                Message(
                    'control_change',
                    control=int(cc_spec.get('controller', 0)),
                    value=clamp_int(cc_spec.get('value', 0), 0, 127, 0),
                    channel=int(ev['chan']),
                    time=dt if first_cc else 0,
                )
            )
            first_cc = False
            dt = 0

        msg_type = 'note_on' if ev['kind'] == 'note_on' else 'note_off'
        track.append(
            Message(
                msg_type,
                note=clamp_int(ev['note'], 0, 127, 36),
                velocity=clamp_int(ev['vel'], 0, 127, 0),
                channel=int(ev['chan']),
                time=dt if first_cc else 0,
            )
        )

    track.append(MetaMessage('end_of_track', time=0))

    buf = BytesIO()
    mid.save(file=buf)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


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
        'midi_base64': export_track_to_midi_base64(None, config),
        'metadata': {
            'drummer_used': config.drummer,
            'style': config.style,
            'mode': 'legacy_fallback',
            'humanized': False,
            'measure_count': config.measure_count,
        }
    }
