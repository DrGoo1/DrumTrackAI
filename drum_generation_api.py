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
import math
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sqlite3
import random

# Admin DB service for drummer presets (optional; fail-soft if unavailable)
try:
    from admin.services.central_database_service import get_database_service as get_admin_db_service
    ADMIN_DB_AVAILABLE = True
except Exception:
    ADMIN_DB_AVAILABLE = False

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
        get_song_roadmap_from_llm,
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

        # Optional: per-bar fill directives (absolute bar indices)
        self.force_fill_bars = data.get('forceFillBars') or data.get('force_fill_bars')
        self.suppress_fill_bars = data.get('suppressFillBars') or data.get('suppress_fill_bars')

        # Continuous cymbal blend controls (0 = hats, 1 = ride)
        self.hats_to_ride_blend = float(data.get('hatsToRideBlend', 0.0) or 0.0)
        self.hats_to_ride_threshold = float(data.get('hatsToRideThreshold', 0.6) or 0.6)

        # Left-foot hat pulse while on ride (hihat_pedal)
        self.foot_hat_pulse_subdivision = data.get('footHatPulseSubdivision', 'off')
        self.foot_hat_pulse_apply = data.get('footHatPulseApply', 'both')
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
        self.groove_mode = data.get('grooveMode') or data.get('groove_mode')
        self.groove_controls = data.get('grooveControls') or data.get('groove_controls')

        # Optional: force a specific EGMD phrase/clip id
        self.egmd_phrase_id = data.get('egmdPhraseId') or data.get('egmd_phrase_id')

        # Optional: force a specific EGMD midi path (pins exact phrase file)
        self.egmd_midi_path = data.get('egmdMidiPath') or data.get('egmd_midi_path')
        self.egmd_fill_midi_path = data.get('egmdFillMidiPath') or data.get('egmd_fill_midi_path')

        # Optional: per-section EGMD phrase overrides (full-song generation)
        self.egmd_phrase_overrides = data.get('egmdPhraseOverrides') or data.get('egmd_phrase_overrides')

        # Preset stacks (v3 frontend)
        self.global_preset_stack = data.get('globalPresetStack') or data.get('global_preset_stack') or []
        self.section_preset_stack = data.get('sectionPresetStack') or data.get('section_preset_stack') or []
    
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
        
        v2 = NewConfig(
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
            hatsToRideBlend=self.hats_to_ride_blend,
            hatsToRideThreshold=self.hats_to_ride_threshold,
            footHatPulseSubdivision=self.foot_hat_pulse_subdivision,
            footHatPulseApply=self.foot_hat_pulse_apply,
            forceFillBars=self.force_fill_bars,
            suppressFillBars=self.suppress_fill_bars,
        )

        try:
            _apply_preset_stacks_to_v2_config(
                v2_config=v2,
                global_stack=self.global_preset_stack,
                section_stack=self.section_preset_stack,
            )
        except Exception as e:
            logger.warning(f"Preset stack application failed: {e}")

        return v2


def _coerce_tier(v: Any) -> str:
    s = str(v or "").strip().lower()
    if s in {"song", "flavor", "utility"}:
        return s
    return "flavor"


def _merge_deltas(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(dst or {})
    for k, v in (src or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge_deltas(out.get(k) or {}, v)
        else:
            out[k] = v
    return out


def _apply_delta_value(base: Any, target: Any, alpha: float) -> Any:
    if alpha <= 0:
        return base
    if alpha >= 1:
        return target
    try:
        if isinstance(base, (int, float)) and isinstance(target, (int, float)):
            return (1.0 - alpha) * float(base) + alpha * float(target)
    except Exception:
        pass
    # Non-numeric or mismatched types: treat as override at any alpha > 0.
    return target


def _apply_deltas_to_v2_config(v2_config: Any, deltas: Dict[str, Any], alpha: float) -> None:
    if not deltas:
        return

    # Nested dataclass helpers
    def _ensure_fill_controls() -> Any:
        fc = getattr(v2_config, "fillControls", None)
        if fc is None and DRUM_BUILDER_V2_AVAILABLE:
            try:
                fc = FillControls()
                setattr(v2_config, "fillControls", fc)
            except Exception:
                fc = None
        return fc

    def _ensure_rudiment_controls() -> Any:
        rc = getattr(v2_config, "rudimentControls", None)
        if rc is None and DRUM_BUILDER_V2_AVAILABLE:
            try:
                rc = RudimentControls()
                setattr(v2_config, "rudimentControls", rc)
            except Exception:
                rc = None
        return rc

    for key, val in (deltas or {}).items():
        if key == "fillControls" and isinstance(val, dict):
            fc = _ensure_fill_controls()
            if not fc:
                continue
            for kk, vv in val.items():
                prev = getattr(fc, kk, None)
                setattr(fc, kk, _apply_delta_value(prev, vv, alpha))
            continue

        if key == "rudimentControls" and isinstance(val, dict):
            rc = _ensure_rudiment_controls()
            if not rc:
                continue
            for kk, vv in val.items():
                prev = getattr(rc, kk, None)
                setattr(rc, kk, _apply_delta_value(prev, vv, alpha))
            continue

        prev = getattr(v2_config, key, None)
        if prev is None and not hasattr(v2_config, key):
            continue
        setattr(v2_config, key, _apply_delta_value(prev, val, alpha))


def _load_preset_deltas(preset_id: str) -> Dict[str, Any]:
    if not ADMIN_DB_AVAILABLE:
        return {}
    pid = str(preset_id or "").strip()
    if not pid:
        return {}
    try:
        db = get_admin_db_service()
        db.initialize()
        preset = db.get_drummer_preset(pid)
        if not isinstance(preset, dict):
            return {}
        deltas = preset.get("deltas")
        return deltas if isinstance(deltas, dict) else {}
    except Exception:
        return {}


def _apply_preset_stacks_to_v2_config(*, v2_config: Any, global_stack: Any, section_stack: Any) -> None:
    # Stacks come from frontend as [{presetId, tier, intensity}, ...]
    def _normalize_stack(stack: Any) -> List[Dict[str, Any]]:
        if not isinstance(stack, list):
            return []
        out: List[Dict[str, Any]] = []
        for it in stack:
            if not isinstance(it, dict):
                continue
            pid = str(it.get("presetId") or it.get("preset_id") or "").strip()
            if not pid:
                continue
            tier = _coerce_tier(it.get("tier"))
            try:
                intensity = float(it.get("intensity", 100.0))
            except Exception:
                intensity = 100.0
            out.append({"presetId": pid, "tier": tier, "intensity": max(0.0, min(100.0, intensity))})
        return out

    g = _normalize_stack(global_stack)
    s = _normalize_stack(section_stack)

    # Apply in stack order, but if you want deterministic tier order you can sort.
    # Here we respect the request ordering (UI stack).
    for entry in g:
        alpha = float(entry.get("intensity", 100.0)) / 100.0
        deltas = _load_preset_deltas(entry["presetId"])
        _apply_deltas_to_v2_config(v2_config, deltas, alpha)

    for entry in s:
        alpha = float(entry.get("intensity", 100.0)) / 100.0
        deltas = _load_preset_deltas(entry["presetId"])
        _apply_deltas_to_v2_config(v2_config, deltas, alpha)

    try:
        logger.info(
            "Applied preset stacks to v2 config",
            extra={
                "global_presets": [e.get("presetId") for e in g],
                "section_presets": [e.get("presetId") for e in s],
            },
        )
    except Exception:
        pass


def _inject_foot_hat_pulse(
    *,
    internal_events: List[Dict[str, Any]],
    songmap: Any,
    v2_config: Any,
) -> List[Dict[str, Any]]:
    """Inject hihat_pedal pulse notes on ride-focused bars.

    This implements the user option:
    - pulse subdivision: quarter/eighth/sixteenth
    - apply: transition|ride_bars|both
    - ride bars: determined by hatsToRideBlend >= hatsToRideThreshold

    Notes are appended as internal events (pattern layer). Jamstix enrichment and
    DCSM builder will preserve them.
    """

    try:
        subdivision = str(getattr(v2_config, "footHatPulseSubdivision", "off") or "off").strip().lower()
        apply_mode = str(getattr(v2_config, "footHatPulseApply", "both") or "both").strip().lower()
        blend = float(getattr(v2_config, "hatsToRideBlend", 0.0) or 0.0)
        threshold = float(getattr(v2_config, "hatsToRideThreshold", 0.6) or 0.6)
    except Exception:
        return internal_events

    if subdivision in {"", "off", "none"}:
        return internal_events

    steps_by_subdivision = {
        "quarter": [0, 4, 8, 12],
        "eighth": [0, 2, 4, 6, 8, 10, 12, 14],
        "sixteenth": list(range(16)),
    }
    steps = steps_by_subdivision.get(subdivision)
    if not steps:
        return internal_events

    bars = getattr(songmap, "bars", None) or []
    if not bars:
        return internal_events

    ride_bars_enabled = blend >= threshold
    if not ride_bars_enabled and apply_mode not in {"transition", "both"}:
        return internal_events

    num_bars = len(bars)
    ride_bars = set(range(num_bars)) if ride_bars_enabled else set()
    transition_bars: set[int] = set()
    if ride_bars_enabled:
        # With global blend, the transition is the first ride bar.
        transition_bars.add(0)

    target_bars: set[int] = set()
    if apply_mode in {"ride_bars", "both"}:
        target_bars |= ride_bars
    if apply_mode in {"transition", "both"}:
        target_bars |= transition_bars

    if not target_bars:
        return internal_events

    existing = set()
    for ev in internal_events:
        try:
            if str(ev.get("instrument_id")) != "hihat_pedal":
                continue
            bi = int(ev.get("barIndex") or 0)
            existing.add((bi, float(ev.get("time_sec") or 0.0)))
        except Exception:
            continue

    out = [dict(e) for e in internal_events]
    base_velocity = 55
    for bi in sorted(target_bars):
        if bi < 0 or bi >= num_bars:
            continue
        bar = bars[bi]
        start = float(getattr(bar, "start_time", 0.0) or 0.0)
        end = float(getattr(bar, "end_time", start) or start)
        length = max(1e-6, end - start)

        for s in steps:
            t = start + (float(s) / 16.0) * length
            key = (bi, float(t))
            if key in existing:
                continue
            out.append(
                {
                    "time_sec": float(t),
                    "length_sec": float(length / 16.0),
                    "instrument_id": "hihat_pedal",
                    "midi_pitch": int(instrument_id_to_midi_pitch("hihat_pedal")),
                    "velocity": int(base_velocity),
                    "isGhost": True,
                    "isAccent": False,
                    "isFlam": False,
                    "isDrag": False,
                    "isFill": False,
                    "barIndex": int(bi),
                    "barStartTime": float(start),
                    "barEndTime": float(end),
                }
            )

    return out

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

    if not DRUM_BUILDER_V2_AVAILABLE:
        return {
            'ok': False,
            'error': 'Drum Builder v2.0 is not available (import failed). No fallback generation is allowed.',
            'metadata': {
                'builder_version': 'v2.0_unavailable',
                'generation_time_ms': round((time.time() - start_time) * 1000, 1),
            },
        }

    logger.info("Using Drum Builder v2.0")
    try:
        result = generate_with_v2_builder(config)
        result['metadata']['builder_version'] = 'v2.0'
        result['metadata']['generation_time_ms'] = round((time.time() - start_time) * 1000, 1)
        return result
    except Exception as e:
        logger.error(f"Drum Builder v2.0 failed: {e}", exc_info=True)
        return {
            'ok': False,
            'error': f"Drum Builder v2.0 failed: {e}",
            'metadata': {
                'builder_version': 'v2.0_failed',
                'generation_time_ms': round((time.time() - start_time) * 1000, 1),
            },
        }


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
    
    # 2. Get drummer profile (persona/service-backed)
    drummer_profile = build_drummer_profile(config)
    
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
    
    groove_source = (getattr(config, "groove_source", None) or "").lower()
    groove_mode = (getattr(config, "groove_mode", None) or "").lower()

    # Validation path: Default/Neutral drummer + pinned EGMD midi path must preserve the chosen EGMD phrase.
    try:
        neutral_ids = {"default_neutral", "default", "neutral"}
        public_id = str(getattr(config, "public_drummer_id", None) or "").strip().lower()
        drummer_id = str(getattr(config, "drummer", None) or "").strip().lower()
        is_neutral = (public_id in neutral_ids) or (drummer_id in neutral_ids)
    except Exception:
        is_neutral = False

    try:
        pinned_midi = str(getattr(config, "egmd_midi_path", None) or "").strip()
    except Exception:
        pinned_midi = ""

    try:
        pinned_phrase_id = getattr(config, "egmd_phrase_id", None)
        pinned_phrase_id = int(pinned_phrase_id) if pinned_phrase_id is not None and str(pinned_phrase_id).strip() != "" else None
    except Exception:
        pinned_phrase_id = None

    # Preserve mode should engage when the user explicitly pins either the EGMD midi_path OR phrase_id.
    # This must be authoritative regardless of drummer selection; otherwise downstream layers can
    # legitimately reshape the pattern and the user will not get the chosen Basic Drum Style.
    preserve_selected_egmd = bool(pinned_midi or pinned_phrase_id is not None)

    if preserve_selected_egmd:
        if not groove_source:
            groove_source = "egmd_phrases"
        if not groove_mode:
            groove_mode = "exact"

    try:
        logger.info(
            "EGMD selection debug: build_scope=%s groove_source=%s groove_mode=%s egmd_exact_mode(pending)=%s preserve_selected_egmd=%s egmd_phrase_id=%s egmd_midi_path=%s drummer=%s public_drummer_id=%s",
            getattr(config, "build_scope", None),
            groove_source,
            groove_mode,
            None,
            bool(preserve_selected_egmd),
            getattr(config, "egmd_phrase_id", None),
            getattr(config, "egmd_midi_path", None),
            getattr(config, "drummer", None),
            getattr(config, "public_drummer_id", None),
        )
    except Exception:
        pass

    # Default: full-song builds should use EGMD as the base groove vocabulary.
    if getattr(config, "build_scope", None) == "full_song" and not groove_source:
        groove_source = "egmd_phrases"

    style_group_hint = (getattr(config, "style_group", None) or "").strip().lower()
    meter_hint = f"{int(getattr(config, 'time_signature', (4, 4))[0])}/{int(getattr(config, 'time_signature', (4, 4))[1])}"
    is_full_song = (getattr(config, "build_scope", None) or "").lower() == "full_song"
    is_basic_rock_full_song = is_full_song and style_group_hint in {"rock", "metal", "hardrock", "hard_rock"} and meter_hint == "4/4"

    # If we're building a full-song rock groove from EGMD, default to exact playback
    # so we do not delete/remap hits via transforms/enrichment.
    # NOTE: The frontend has historically used 'enhanced' to mean "EGMD-based".
    # For full-song EGMD, treat 'enhanced' as exact as well so we actually preserve
    # the database phrase content (tiled), rather than mutating it.
    egmd_exact_mode = (
        groove_source in {"egmd", "egmd_phrase", "egmd_phrases"}
        and (
            groove_mode in {"exact", "clip", "database"}
            or (is_full_song and groove_mode == "enhanced")
            or (not groove_mode and is_basic_rock_full_song)
        )
    )

    try:
        logger.info(
            "EGMD selection debug: egmd_exact_mode=%s groove_source=%s groove_mode=%s preserve_selected_egmd=%s",
            bool(egmd_exact_mode),
            groove_source,
            groove_mode,
            bool(preserve_selected_egmd),
        )
    except Exception:
        pass

    song_roadmap: Optional[Dict[str, Any]] = None
    perf_spec = None
    if egmd_exact_mode:
        # In exact EGMD playback we must not introduce any LLM-derived micro-timing.
        # build_drumtrack_for_dcsm() will apply micro-timing offsets from this spec.
        perf_spec = {
            "styleId": str(getattr(v2_config, "style", None) or getattr(config, "style", "")),
            "globalFeel": "straight",
            "quantizationBase": "16th",
            "phrases": [],
        }
    else:
        # Director layer (roadmap) is only meaningful for full-song generation.
        if getattr(config, "build_scope", None) == "full_song" and DRUM_BUILDER_V2_AVAILABLE:
            try:
                song_roadmap = get_song_roadmap_from_llm(
                    cfg=v2_config,
                    songmap_summary=songmap_summary,
                    drummer_profile=drummer_profile,
                )
            except Exception as e:
                logger.warning("Song roadmap generation failed: %s", e)
                song_roadmap = None

        perf_spec = get_performance_spec_from_llm(
            cfg=v2_config,
            section_label=section_label,
            songmap_summary=songmap_summary,
            drummer_profile=drummer_profile,
            power_curve=power_curve,
        )
    
    # 5. Generate pattern (placeholder - use Rust audio-core or templates)
    # IMPORTANT: This codebase intentionally avoids silent fallbacks.
    # If a requested generation mode cannot produce events, we raise an error
    # rather than substituting an unrelated groove.
    song_mode_active = bool(
        getattr(v2_config, "songSections", None)
        or getattr(v2_config, "songStyle", None)
    )

    egmd_phrase_info: Optional[Dict[str, Any]] = None
    egmd_transform_plan: Optional[Dict[str, Any]] = None
    def _generate_fallback_internal_events_for_meter() -> List[Dict[str, Any]]:
        raise Exception("Fallback pattern generation is not allowed")
    def _normalize_section_key(name: str) -> str:
        key = str(name or "").strip().lower()
        key = "_".join(key.split())
        key = "".join(ch for ch in key if (ch.isalnum() or ch == "_"))
        return key.strip("_") or "section"

    def _egmd_phrase_by_id(phrase_id: int) -> Optional[Dict[str, Any]]:
        try:
            pid = int(phrase_id)
        except Exception:
            return None
        conn = _egmd_db_connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, midi_path, audio_path, feature_json FROM egmd_phrases WHERE id = ? LIMIT 1",
                (pid,),
            )
            row = cur.fetchone()
            if not row:
                return None
            try:
                fj = json.loads(row["feature_json"]) if row["feature_json"] else {}
            except Exception:
                fj = {}
            pf = _derive_phrase_features_from_json(fj)
            return {
                "phrase_id": int(row["id"]),
                "midi_path": row["midi_path"],
                "audio_path": row["audio_path"],
                "measured": pf,
            }
        finally:
            conn.close()

    def _bar_duration_seconds() -> float:
        beats_per_bar = int(getattr(config, "time_signature", (4, 4))[0] or 4)
        tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)
        return (60.0 / max(tempo, 1e-3)) * float(beats_per_bar)

    def _load_phrase_events_for_bars(*, phrase: Dict[str, Any], bars: int) -> List[Dict[str, Any]]:
        class _Tmp:
            time_signature = getattr(config, "time_signature", (4, 4))
            tempos = getattr(config, "tempos", [120])
            measure_count = int(max(1, bars))

        return _load_internal_events_from_midi_path(midi_path=phrase["midi_path"], config=_Tmp())

    def _loop_and_trim_events(
        *,
        events: List[Dict[str, Any]],
        duration_sec: float,
    ) -> List[Dict[str, Any]]:
        if not events:
            return []
        phrase_len_hint = None
        try:
            phrase_len_hint = float(events[0].get("phrase_len_sec") or 0.0)
        except Exception:
            phrase_len_hint = None

        if phrase_len_hint and phrase_len_hint > 0.1:
            phrase_len = float(phrase_len_hint)
        else:
            max_t = max(float(e.get("time_sec", 0.0)) for e in events)
            phrase_len = max(0.5, max_t + 0.25)
        if phrase_len <= 0:
            return []
        loops = int(math.ceil(max(duration_sec, 1e-3) / phrase_len))
        out: List[Dict[str, Any]] = []
        for k in range(max(1, loops)):
            offset = k * phrase_len
            for e in events:
                t = float(e.get("time_sec", 0.0)) + offset
                if t >= duration_sec:
                    continue
                ne = dict(e)
                ne["time_sec"] = t
                out.append(ne)
        return out

    def _estimate_phrase_bars(*, phrase_events: List[Dict[str, Any]]) -> int:
        if not phrase_events:
            return 1
        bar_dur_local = _bar_duration_seconds()
        try:
            phrase_len_hint = float(phrase_events[0].get("phrase_len_sec") or 0.0)
        except Exception:
            phrase_len_hint = 0.0
        if phrase_len_hint and phrase_len_hint > 0.1:
            return max(1, int(round(float(phrase_len_hint) / max(bar_dur_local, 1e-3))))
        try:
            max_t = max(float(e.get("time_sec", 0.0)) for e in phrase_events)
        except Exception:
            return 1
        phrase_len = max(0.5, float(max_t) + 0.25)
        return max(1, int(round(phrase_len / max(bar_dur_local, 1e-3))))

    def _fill_score_from_measured(measured: Optional[Dict[str, Any]]) -> float:
        if not isinstance(measured, dict):
            return -1e9
        # Heuristic "fill-likeness" scoring from existing EGMD features.
        # Prefer tom/crash activity and higher density.
        density = float(measured.get("density", 0.0) or 0.0)
        tom = float(measured.get("tom_ratio", 0.0) or 0.0)
        crash = float(measured.get("crash_ratio", 0.0) or 0.0)
        snare = float(measured.get("snare_ratio", 0.0) or 0.0)
        hat = float(measured.get("hat_ratio", 0.0) or 0.0)
        return (2.0 * density) + (3.0 * tom) + (2.0 * crash) + (0.8 * snare) - (0.6 * hat)

    def _load_one_bar_fill_events(*, fill_phrase: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Load as a 1-bar clip, then trim hard to 1 bar.
        bar_dur_local = _bar_duration_seconds()
        events = _load_phrase_events_for_bars(phrase=fill_phrase, bars=1)
        events = _loop_and_trim_events(events=events, duration_sec=bar_dur_local)
        out: List[Dict[str, Any]] = []
        for e in events:
            ne = dict(e)
            ne["barRole"] = "fill"
            out.append(ne)
        return out

    def _build_full_song_events_from_egmd_sections() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        raw_sections = getattr(v2_config, "songSections", None) or []
        if not isinstance(raw_sections, list) or not raw_sections:
            return ([], [])

        overrides = getattr(config, "egmd_phrase_overrides", None)
        override_mode = None
        by_type: Dict[str, Any] = {}
        by_index: Dict[str, Any] = {}
        if isinstance(overrides, dict):
            override_mode = str(overrides.get("mode") or "").lower()
            by_type = overrides.get("byType") if isinstance(overrides.get("byType"), dict) else {}
            by_index = overrides.get("byIndex") if isinstance(overrides.get("byIndex"), dict) else {}

        bar_dur = _bar_duration_seconds()
        cursor_time = 0.0
        all_events: List[Dict[str, Any]] = []
        section_debug: List[Dict[str, Any]] = []

        # Pre-rank EGMD phrases once per request; then rotate/avoid repeats across sections.
        ranked = _rank_egmd_phrases(config)
        ranked_ids = [int(p.get("phrase_id")) for p in ranked if isinstance(p, dict) and p.get("phrase_id") is not None]
        recent_ids: List[int] = []
        recent_window = 3

        def _egmd_phrase_by_midi_path(midi_path: str) -> Optional[Dict[str, Any]]:
            mp = str(midi_path or "").strip()
            if not mp:
                return None
            conn = _egmd_db_connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, midi_path, audio_path, feature_json FROM egmd_phrases WHERE midi_path = ? LIMIT 1",
                    (mp,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                try:
                    fj = json.loads(row["feature_json"]) if row["feature_json"] else {}
                except Exception:
                    fj = {}
                pf = _derive_phrase_features_from_json(fj) if isinstance(fj, dict) else {}
                phrase = {
                    "phrase_id": int(row["id"]),
                    "midi_path": row["midi_path"],
                    "audio_path": row["audio_path"],
                    "measured": pf,
                }
                try:
                    logger.info("EGMD forced midi_path resolved: phrase_id=%s midi_path=%s", phrase.get("phrase_id"), phrase.get("midi_path"))
                except Exception:
                    pass
                return phrase
            finally:
                conn.close()

        for idx, sec in enumerate(raw_sections):
            name = getattr(sec, "name", None) if not isinstance(sec, dict) else sec.get("name")
            bars_val = getattr(sec, "bars", None) if not isinstance(sec, dict) else sec.get("bars")
            try:
                bars = int(bars_val)
            except Exception:
                bars = 0
            bars = max(1, bars)

            section_key = _normalize_section_key(str(name or "section"))
            # Default: if the request globally forces an EGMD phrase, apply it to every section.
            # Per-section overrides (by_index/by_type) below can still override this.
            forced_phrase_id = getattr(config, "egmd_phrase_id", None)
            if forced_phrase_id is not None and str(forced_phrase_id).strip() == "":
                forced_phrase_id = None
            forced_reason = "global_forced_phrase" if forced_phrase_id is not None else None
            forced_midi_path = getattr(config, "egmd_midi_path", None)
            if forced_midi_path is not None and str(forced_midi_path).strip() == "":
                forced_midi_path = None
            if forced_midi_path is not None and forced_reason is None:
                forced_reason = "global_forced_midi_path"

            if override_mode == "by_index":
                raw = by_index.get(str(idx)) if isinstance(by_index, dict) else None
                if raw is not None and str(raw) != "":
                    forced_phrase_id = raw
                    forced_reason = "override_by_index"
            if forced_phrase_id is None and override_mode == "by_type":
                raw = by_type.get(section_key) if isinstance(by_type, dict) else None
                if raw is not None and str(raw) != "":
                    forced_phrase_id = raw
                    forced_reason = "override_by_type"

            phrase: Optional[Dict[str, Any]] = None
            candidate_rank = None
            reuse_avoided = False
            reused_phrase_id = None
            if forced_phrase_id is not None:
                phrase = _egmd_phrase_by_id(int(forced_phrase_id))
            if not phrase and forced_midi_path is not None:
                phrase = _egmd_phrase_by_midi_path(str(forced_midi_path).strip())
                if not phrase:
                    try:
                        logger.warning("EGMD forced midi_path not found in egmd_phrases table: %s", str(forced_midi_path).strip())
                    except Exception:
                        pass
                    phrase = {
                        "phrase_id": forced_phrase_id,
                        "midi_path": str(forced_midi_path).strip(),
                        "audio_path": None,
                        "measured": None,
                    }
            if not phrase:
                forced_reason = forced_reason or "auto_ranked_match"
                if ranked and ranked_ids:
                    # Deterministic rotation: choose an index derived from section index.
                    base_i = idx % max(1, len(ranked_ids))
                    chosen_i = base_i
                    # Avoid recently-used ids when possible.
                    if len(ranked_ids) > 1:
                        # Bound the avoid window to available ids.
                        w = min(recent_window, max(0, len(ranked_ids) - 1))
                        avoid = set(recent_ids[-w:]) if w > 0 else set()
                        for step in range(len(ranked_ids)):
                            probe_i = (base_i + step) % len(ranked_ids)
                            probe_id = ranked_ids[probe_i]
                            if probe_id not in avoid:
                                chosen_i = probe_i
                                break
                        if ranked_ids[chosen_i] != ranked_ids[base_i] and ranked_ids[base_i] in avoid:
                            reuse_avoided = True

                    chosen = ranked[chosen_i]
                    if isinstance(chosen, dict):
                        phrase = {
                            "phrase_id": int(chosen.get("phrase_id")),
                            "midi_path": chosen.get("midi_path"),
                            "audio_path": chosen.get("audio_path"),
                            "measured": chosen.get("measured"),
                        }
                        candidate_rank = int(chosen_i)
                        if phrase.get("phrase_id") in recent_ids:
                            reused_phrase_id = int(phrase.get("phrase_id"))
                if not phrase:
                    phrase = _select_best_egmd_phrase(config)
                    forced_reason = "auto_best_match"

            if not phrase:
                raise Exception("EGMD full-song requested but no phrase could be selected")

            section_duration = float(bars) * bar_dur

            # Within-section variation: stitch multiple phrases when section is long,
            # instead of looping one phrase for the entire section.
            phrase_ids_used: List[int] = []
            section_events: List[Dict[str, Any]] = []
            try:
                base_events = _load_phrase_events_for_bars(phrase=phrase, bars=bars)
            except Exception:
                base_events = []
            phrase_bars = _estimate_phrase_bars(phrase_events=base_events)
            phrase_bars = max(1, min(bars, phrase_bars))

            remaining = int(bars)
            bar_cursor = 0
            chunk_i = 0
            while remaining > 0:
                chunk_bars = min(remaining, phrase_bars)
                chosen_phrase = phrase
                if (not preserve_selected_egmd) and forced_phrase_id is None and ranked and ranked_ids and len(ranked_ids) > 1:
                    base_i2 = (idx + chunk_i) % max(1, len(ranked_ids))
                    chosen_i2 = base_i2
                    w2 = min(recent_window, max(0, len(ranked_ids) - 1))
                    avoid2 = set(recent_ids[-w2:]) if w2 > 0 else set()
                    for step2 in range(len(ranked_ids)):
                        probe_i2 = (base_i2 + step2) % len(ranked_ids)
                        probe_id2 = ranked_ids[probe_i2]
                        if probe_id2 not in avoid2:
                            chosen_i2 = probe_i2
                            break
                    chosen2 = ranked[chosen_i2]
                    if isinstance(chosen2, dict):
                        chosen_phrase = {
                            "phrase_id": int(chosen2.get("phrase_id")),
                            "midi_path": chosen2.get("midi_path"),
                            "audio_path": chosen2.get("audio_path"),
                            "measured": chosen2.get("measured"),
                        }
                try:
                    pid_chunk = int(chosen_phrase.get("phrase_id"))
                except Exception:
                    pid_chunk = None
                if pid_chunk is not None:
                    phrase_ids_used.append(pid_chunk)
                    recent_ids.append(pid_chunk)

                chunk_events = _load_phrase_events_for_bars(phrase=chosen_phrase, bars=chunk_bars)
                chunk_events = _loop_and_trim_events(events=chunk_events, duration_sec=float(chunk_bars) * bar_dur)
                chunk_offset = float(bar_cursor) * bar_dur
                for e in chunk_events:
                    ne = dict(e)
                    ne["time_sec"] = float(ne.get("time_sec", 0.0)) + chunk_offset
                    section_events.append(ne)

                remaining -= chunk_bars
                bar_cursor += chunk_bars
                chunk_i += 1

            # Boundary fill insertion (EGMD-first) for transitions.
            # In exact mode we still want musical transitions, but without mutating grooves.
            fill_phrase_id = None
            fill_reason = None
            if (not preserve_selected_egmd) and egmd_exact_mode and idx < (len(raw_sections) - 1) and bars >= 2:
                # Choose a "fill-like" phrase deterministically from ranked candidates.
                # If none found, we'll fall back to a simple crash+kick marker at next section start.
                try:
                    avoid = set(recent_ids[-min(recent_window, len(recent_ids)) :])
                    best = None
                    best_score = -1e9
                    for cand in ranked[:200]:
                        if not isinstance(cand, dict):
                            continue
                        pid = cand.get("phrase_id")
                        if pid is None:
                            continue
                        pid = int(pid)
                        if pid in avoid:
                            continue
                        s = _fill_score_from_measured(cand.get("measured"))
                        if s > best_score:
                            best_score = s
                            best = cand
                    if best and best_score > -1e8:
                        fill_phrase = {
                            "phrase_id": int(best.get("phrase_id")),
                            "midi_path": best.get("midi_path"),
                            "audio_path": best.get("audio_path"),
                            "measured": best.get("measured"),
                        }
                        fill_events = _load_one_bar_fill_events(fill_phrase=fill_phrase)
                        if fill_events:
                            # Replace the final bar of the section with the fill bar.
                            last_bar_start = float(section_duration) - float(bar_dur)
                            kept: List[Dict[str, Any]] = []
                            for e in section_events:
                                try:
                                    t = float(e.get("time_sec", 0.0))
                                except Exception:
                                    kept.append(e)
                                    continue
                                if t < last_bar_start:
                                    kept.append(e)
                            # Shift fill to last bar window
                            for e in fill_events:
                                ne = dict(e)
                                ne["time_sec"] = float(ne.get("time_sec", 0.0)) + last_bar_start
                                kept.append(ne)
                            kept.sort(key=lambda x: float(x.get("time_sec", 0.0)))
                            section_events = kept
                            fill_phrase_id = int(fill_phrase.get("phrase_id"))
                            fill_reason = "egmd_fill_phrase_last_bar_replacement"
                except Exception:
                    pass
            for e in section_events:
                ne = dict(e)
                ne["time_sec"] = float(ne.get("time_sec", 0.0)) + cursor_time
                all_events.append(ne)

            # No fallback transitions: if a fill was requested but not found, it must be surfaced
            # explicitly by upstream logic.

            section_debug.append(
                {
                    "sectionIndex": idx,
                    "sectionName": str(name or "section"),
                    "sectionKey": section_key,
                    "bars": bars,
                    "phrase_id": phrase.get("phrase_id"),
                    "phrase_ids_used": phrase_ids_used,
                    "midi_path": phrase.get("midi_path"),
                    "reason": "egmd_exact_per_section" if egmd_exact_mode else forced_reason,
                    "candidate_rank": candidate_rank,
                    "reuse_avoided": bool(reuse_avoided),
                    "reused_phrase_id": reused_phrase_id,
                    "fillPhraseId": fill_phrase_id,
                    "fillReason": fill_reason,
                }
            )

            # recent_ids already updated per chunk above

            cursor_time += section_duration

        # Apply roadmap-driven directives (first pass):
        # - section-start crash signaling
        # - orchestration: hats -> ride for chorus/sections that request ride timekeeper
        # IMPORTANT: In EGMD exact mode we must not mutate the database phrase content.
        if egmd_exact_mode:
            return (all_events, section_debug)

        try:
            if isinstance(song_roadmap, dict):
                global_cfg = song_roadmap.get("global") if isinstance(song_roadmap.get("global"), dict) else {}
                crash_policy = global_cfg.get("crashPolicy") if isinstance(global_cfg.get("crashPolicy"), dict) else {}
                on_section_start = bool(crash_policy.get("onSectionStart", True))
                intensity_threshold = float(crash_policy.get("intensityThreshold", 0.55) or 0.55)

                roadmap_debug: List[Dict[str, Any]] = []

                sections_cfg = song_roadmap.get("sections") if isinstance(song_roadmap.get("sections"), list) else []
                sections_by_index: Dict[int, Dict[str, Any]] = {}
                for entry in sections_cfg:
                    if not isinstance(entry, dict):
                        continue
                    try:
                        sections_by_index[int(entry.get("sectionIndex"))] = entry
                    except Exception:
                        continue

                # Build section time ranges from bar counts
                bar_dur_local = _bar_duration_seconds()
                start_time = 0.0
                section_ranges: List[Tuple[int, float, float]] = []
                for sdbg in section_debug:
                    idx2 = int(sdbg.get("sectionIndex", 0) or 0)
                    bars2 = int(sdbg.get("bars", 1) or 1)
                    end_time = start_time + float(bars2) * bar_dur_local
                    section_ranges.append((idx2, start_time, end_time))
                    start_time = end_time

                # Deterministic RNG
                rng = random.Random(f"roadmap|{getattr(config, 'section_id', '')}|{getattr(config, 'drummer', '')}|{getattr(config, 'style', '')}")

                beats_per_bar_local = int(getattr(config, "time_signature", (4, 4))[0] or 4)
                beat_dur_local = bar_dur_local / max(1.0, float(beats_per_bar_local))

                # (0) annotate events with barIndex + default barRole
                for e in all_events:
                    if "barRole" not in e:
                        e["barRole"] = "groove"
                    if "barIndex" not in e:
                        try:
                            e["barIndex"] = int(float(e.get("time_sec", 0.0)) // bar_dur_local)
                        except Exception:
                            e["barIndex"] = 0

                # (0.5) macro timing feel per section (Jamstix-like part shuffle)
                # This is NOT microtiming; it reshapes the grid inside each section.
                # - swing_8th: delay the "and" of each beat
                # - swing_16th: delay even 16ths slightly
                default_swing = float(global_cfg.get("defaultSwing", 0.0) or 0.0)
                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    timing = sec_cfg.get("timing") if isinstance(sec_cfg.get("timing"), dict) else {}
                    shuffle_mode = str(timing.get("shuffleMode") or "straight").strip().lower()
                    swing_amt = float(default_swing)
                    # Keep swing bounded and subtle at macro-level.
                    swing_amt = max(0.0, min(1.0, swing_amt))
                    if shuffle_mode == "straight" or swing_amt <= 1e-4:
                        continue

                    # Amount of delay expressed as fraction of subdivision.
                    # Keep conservative to avoid rhythmic drift.
                    if shuffle_mode == "swing_8th":
                        max_shift = beat_dur_local * 0.18
                        shift = swing_amt * max_shift
                        for e in all_events:
                            try:
                                t = float(e.get("time_sec", 0.0))
                            except Exception:
                                continue
                            if t < t0 or t >= t1:
                                continue
                            # position within beat
                            beat_pos = (t - t0) % beat_dur_local
                            # move second 8th later
                            if beat_pos >= beat_dur_local * 0.5:
                                e["time_sec"] = float(min(t1 - 1e-3, t + shift))
                    elif shuffle_mode == "swing_16th":
                        step = beat_dur_local / 4.0
                        max_shift = step * 0.22
                        shift = swing_amt * max_shift
                        for e in all_events:
                            try:
                                t = float(e.get("time_sec", 0.0))
                            except Exception:
                                continue
                            if t < t0 or t >= t1:
                                continue
                            pos = (t - t0) % step
                            # even 16ths are those in the second half of each 8th; approximate by delaying every other 16th
                            step_idx = int(((t - t0) / step) % 16)
                            if step_idx % 2 == 1:
                                e["time_sec"] = float(min(t1 - 1e-3, t + shift))

                # (0.75) per-section snare shaping: backbeat strength + ghost density
                # This is a musical macro-control on dynamics and note density.
                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    intent = sec_cfg.get("grooveIntent") if isinstance(sec_cfg.get("grooveIntent"), dict) else {}
                    energy = float(sec_cfg.get("energy", 0.6) or 0.6)

                    ghost_target = float(intent.get("ghostDensityTarget", 0.6) or 0.6)
                    ghost_target = max(0.0, min(1.0, ghost_target))
                    # global knob from UI/config
                    global_ghost = float(getattr(config, "ghost_note_amount", 0.7) or 0.7)
                    keep_ghost_prob = max(0.05, min(0.98, 0.15 + 0.75 * ghost_target * global_ghost))

                    backbeat_strength = float(intent.get("backbeatStrength", 0.65) or 0.65)
                    backbeat_strength = max(0.0, min(1.0, backbeat_strength))
                    # convert to velocity multiplier range
                    backbeat_mul = 0.85 + backbeat_strength * 0.45

                    # Track bar count for potential ghost insertion
                    bars_in_section = 0
                    for sdbg in section_debug:
                        if int(sdbg.get("sectionIndex", -1) or -1) == sec_idx:
                            try:
                                bars_in_section = int(sdbg.get("bars", 0) or 0)
                            except Exception:
                                bars_in_section = 0
                            break

                    # (a) thin existing ghost-ish snare hits when ghost density is low
                    kept = 0
                    dropped = 0
                    for e in list(all_events):
                        try:
                            t = float(e.get("time_sec", 0.0))
                        except Exception:
                            continue
                        if t < t0 or t >= t1:
                            continue
                        inst = e.get("instrument_id")
                        if inst not in {"snare_center", "snare_ghost"}:
                            continue
                        vel = int(e.get("velocity", 90) or 90)
                        is_ghost_flag = bool(e.get("isGhost", False))
                        ghostish = (inst == "snare_ghost") or is_ghost_flag or (vel <= 78)
                        if ghostish:
                            if rng.random() > keep_ghost_prob:
                                try:
                                    all_events.remove(e)
                                    dropped += 1
                                except Exception:
                                    pass
                                continue
                            # keep but ensure it is treated as ghost
                            e["isGhost"] = True
                            e["barRole"] = "groove" if e.get("barRole") == "groove" else e.get("barRole")
                            # soften slightly in lower energy sections
                            e["velocity"] = int(max(20, min(100, vel * (0.85 + 0.25 * energy))))
                            kept += 1

                    # (b) strengthen backbeats on beats 2 and 4 when present
                    # Detect backbeat by position within bar.
                    for e in all_events:
                        try:
                            t = float(e.get("time_sec", 0.0))
                        except Exception:
                            continue
                        if t < t0 or t >= t1:
                            continue
                        inst = e.get("instrument_id")
                        if inst != "snare_center":
                            continue
                        if bool(e.get("isGhost", False)):
                            continue
                        bar_pos = (t - t0) % bar_dur_local
                        # beat index (0-based)
                        beat_idx = int(bar_pos // beat_dur_local)
                        if beat_idx not in {1, 3}:
                            continue
                        vel = int(e.get("velocity", 100) or 100)
                        e["velocity"] = int(max(1, min(127, vel * backbeat_mul)))
                        e["isAccent"] = True

                    # (c) optionally insert light ghost notes (only when target is high)
                    inserted = 0
                    if ghost_target >= 0.72 and bars_in_section > 0:
                        # keep insertion subtle; avoid very short sections
                        insert_prob_per_bar = max(0.0, min(0.65, (ghost_target - 0.7) * 1.4))
                        for b in range(int(bars_in_section)):
                            if rng.random() > insert_prob_per_bar:
                                continue
                            bar_start = t0 + float(b) * bar_dur_local
                            # choose a safe 16th position away from downbeats/backbeats
                            # positions: 1e, 1a, 2e, 3e, 3a, 4e
                            rels = [0.25, 0.375, 0.625, 0.25 + 0.5, 0.375 + 0.5, 0.625 + 0.5]
                            rel = rng.choice(rels)
                            tt = bar_start + rel * bar_dur_local
                            if tt <= t0 or tt >= t1:
                                continue
                            all_events.append(
                                {
                                    "time_sec": float(tt),
                                    "length_sec": 0.10,
                                    "instrument_id": "snare_ghost",
                                    "velocity": int(40 + 26 * ghost_target + rng.randint(-6, 8)),
                                    "barIndex": int(float(tt) // bar_dur_local),
                                    "barRole": "groove",
                                    "isGhost": True,
                                    "isAccent": False,
                                    "isFlam": False,
                                    "isDrag": False,
                                }
                            )
                            inserted += 1

                    roadmap_debug.append(
                        {
                            "sectionIndex": sec_idx,
                            "ghostDensityTarget": ghost_target,
                            "backbeatStrength": backbeat_strength,
                            "keptGhostish": kept,
                            "droppedGhostish": dropped,
                            "insertedGhost": inserted,
                            "shuffleMode": str((sec_cfg.get("timing") or {}).get("shuffleMode") or "straight"),
                        }
                    )

                # (0.8) per-section kick shaping: density + low-end power
                # Goal: verses breathe, choruses drive, breakdowns thin.
                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    intent = sec_cfg.get("grooveIntent") if isinstance(sec_cfg.get("grooveIntent"), dict) else {}
                    energy = float(sec_cfg.get("energy", 0.6) or 0.6)

                    kick_target = float(intent.get("kickDensityTarget", 0.65) or 0.65)
                    kick_target = max(0.0, min(1.0, kick_target))
                    low_end_power = float(intent.get("lowEndPower", energy) or energy)
                    low_end_power = max(0.0, min(1.0, low_end_power))

                    # Compute bars_in_section
                    bars_in_section = 0
                    for sdbg in section_debug:
                        if int(sdbg.get("sectionIndex", -1) or -1) == sec_idx:
                            try:
                                bars_in_section = int(sdbg.get("bars", 0) or 0)
                            except Exception:
                                bars_in_section = 0
                            break

                    kick_ids = {"kick", "kick_sub", "kick_in", "kick_out"}
                    # Keep probability for non-downbeat kicks (downbeats kept more)
                    keep_offbeat_prob = max(0.10, min(0.98, 0.20 + 0.75 * kick_target))
                    keep_downbeat_prob = max(0.70, min(0.995, 0.80 + 0.20 * kick_target))

                    kept_kick = 0
                    dropped_kick = 0

                    # Thin kicks in low-density sections (primarily offbeats)
                    for e in list(all_events):
                        try:
                            t = float(e.get("time_sec", 0.0))
                        except Exception:
                            continue
                        if t < t0 or t >= t1:
                            continue
                        if e.get("instrument_id") not in kick_ids:
                            continue
                        bar_pos = (t - t0) % bar_dur_local
                        beat_idx = int(bar_pos // beat_dur_local)
                        is_downbeat = (beat_idx == 0) and (bar_pos < (beat_dur_local * 0.15))
                        keep_prob = keep_downbeat_prob if is_downbeat else keep_offbeat_prob
                        if rng.random() > keep_prob:
                            try:
                                all_events.remove(e)
                                dropped_kick += 1
                            except Exception:
                                pass
                            continue
                        kept_kick += 1

                        # Low-end power: scale kick velocity (avoid clipping)
                        vel = int(e.get("velocity", 100) or 100)
                        vel_mul = 0.85 + 0.35 * low_end_power
                        e["velocity"] = int(max(1, min(127, vel * vel_mul)))
                        if low_end_power >= 0.7 and is_downbeat:
                            e["isAccent"] = True

                    # Add extra drive kicks only when target is high and section not too short.
                    inserted_kick = 0
                    if kick_target >= 0.78 and bars_in_section >= 4:
                        insert_prob_per_bar = max(0.0, min(0.55, (kick_target - 0.75) * 1.6))

                        def _has_kick_near(tt: float, window: float = 0.06) -> bool:
                            for ee in all_events:
                                if ee.get("instrument_id") not in kick_ids:
                                    continue
                                try:
                                    tte = float(ee.get("time_sec", 0.0))
                                except Exception:
                                    continue
                                if abs(tte - tt) <= window:
                                    return True
                            return False

                        for b in range(int(bars_in_section)):
                            if rng.random() > insert_prob_per_bar:
                                continue
                            bar_start = t0 + float(b) * bar_dur_local

                            # candidate offsets inside the bar (avoid 1/3 downbeats already likely present)
                            # "and of 1" and "and of 3" feel good in rock.
                            candidates = [0.5 / beats_per_bar_local, (2.5 / beats_per_bar_local)]
                            rel = rng.choice(candidates)
                            tt = bar_start + rel * bar_dur_local
                            if tt <= t0 or tt >= t1:
                                continue
                            if _has_kick_near(tt):
                                continue
                            all_events.append(
                                {
                                    "time_sec": float(tt),
                                    "length_sec": 0.12,
                                    "instrument_id": "kick",
                                    "velocity": int(max(1, min(127, 92 + int(28 * low_end_power) + rng.randint(-6, 8)))),
                                    "barIndex": int(float(tt) // bar_dur_local),
                                    "barRole": "groove",
                                    "isGhost": False,
                                    "isAccent": False,
                                    "isFlam": False,
                                    "isDrag": False,
                                }
                            )
                            inserted_kick += 1

                    # Add kick decisions to debug
                    try:
                        for d in roadmap_debug:
                            if int(d.get("sectionIndex", -1) or -1) == sec_idx:
                                d["kickDensityTarget"] = kick_target
                                d["lowEndPower"] = low_end_power
                                d["keptKick"] = int(kept_kick)
                                d["droppedKick"] = int(dropped_kick)
                                d["insertedKick"] = int(inserted_kick)
                                break
                    except Exception:
                        pass

                # (0.85) cymbal orchestration: hat openness + ride bell accents + extra crash placement
                cymbal_plan = global_cfg.get("cymbalPlan") if isinstance(global_cfg.get("cymbalPlan"), dict) else {}
                crash_every_n_bars = int(cymbal_plan.get("crashEveryNBars", 0) or 0)
                ride_bell_prob = float(cymbal_plan.get("rideBellAccentProb", 0.18) or 0.18)
                # hat openness target is per section, fallback to global swing/hat proxy
                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    orch = sec_cfg.get("orchestration") if isinstance(sec_cfg.get("orchestration"), dict) else {}
                    intent = sec_cfg.get("grooveIntent") if isinstance(sec_cfg.get("grooveIntent"), dict) else {}
                    energy = float(sec_cfg.get("energy", 0.6) or 0.6)

                    hat_open_target = float(orch.get("hatOpennessTarget", getattr(config, "swing_amount", 0.0) or 0.0) or 0.0)
                    hat_open_target = max(0.0, min(1.0, hat_open_target))
                    # Convert to probability of open hats during this section
                    open_prob = max(0.0, min(0.85, 0.05 + 0.75 * hat_open_target))
                    close_prob = max(0.10, min(1.0, 0.65 + 0.35 * (1.0 - hat_open_target)))

                    hats_opened = 0
                    hats_closed = 0
                    bellified = 0
                    extra_crashes = 0

                    for e in all_events:
                        try:
                            t = float(e.get("time_sec", 0.0))
                        except Exception:
                            continue
                        if t < t0 or t >= t1:
                            continue
                        inst = e.get("instrument_id")

                        # Hat openness shaping
                        if inst == "hihat_closed":
                            if rng.random() <= open_prob and energy >= 0.45:
                                e["instrument_id"] = "hihat_open"
                                try:
                                    e["midi_pitch"] = instrument_id_to_midi_pitch("hihat_open")
                                except Exception:
                                    pass
                                hats_opened += 1
                        elif inst == "hihat_open":
                            if rng.random() > open_prob or energy < 0.35:
                                e["instrument_id"] = "hihat_closed"
                                try:
                                    e["midi_pitch"] = instrument_id_to_midi_pitch("hihat_closed")
                                except Exception:
                                    pass
                                hats_closed += 1
                            # tame overly loud open hats
                            try:
                                v = int(e.get("velocity", 90) or 90)
                                e["velocity"] = int(max(1, min(127, v * (0.85 + 0.15 * energy))))
                            except Exception:
                                pass

                        # Ride bell accents (only when ride is the timekeeper or section is high energy)
                        if inst == "ride_bow" and (str(orch.get("timekeeper") or "").strip().lower() in {"ride", "mixed"} or energy >= 0.72):
                            bar_pos = (t - t0) % bar_dur_local
                            is_downbeat = bar_pos < (beat_dur_local * 0.12)
                            if is_downbeat and rng.random() <= ride_bell_prob:
                                e["instrument_id"] = "ride_bell"
                                try:
                                    e["midi_pitch"] = instrument_id_to_midi_pitch("ride_bell")
                                except Exception:
                                    pass
                                try:
                                    v = int(e.get("velocity", 96) or 96)
                                    e["velocity"] = int(max(1, min(127, v + 12)))
                                except Exception:
                                    pass
                                bellified += 1

                    # Extra crash placement beyond fills (phrase/build markers)
                    if crash_every_n_bars > 0:
                        start_bar = int(float(t0) // bar_dur_local)
                        end_bar = int(max(start_bar, int(float(t1 - 1e-3) // bar_dur_local)))
                        for bar_idx in range(start_bar, end_bar + 1):
                            if bar_idx <= 0:
                                continue
                            if (bar_idx % crash_every_n_bars) != 0:
                                continue
                            # place on bar downbeat if section energy supports
                            if energy < 0.55:
                                continue
                            tt = float(bar_idx) * bar_dur_local
                            if tt < t0 or tt >= t1:
                                continue
                            all_events.append(
                                {
                                    "time_sec": float(tt),
                                    "length_sec": 0.12,
                                    "instrument_id": "crash_1",
                                    "velocity": int(100 + 22 * energy),
                                    "barIndex": int(float(tt) // bar_dur_local),
                                    "barRole": "accent",
                                    "isGhost": False,
                                    "isAccent": True,
                                    "isFlam": False,
                                    "isDrag": False,
                                }
                            )
                            extra_crashes += 1

                    # debug
                    try:
                        for d in roadmap_debug:
                            if int(d.get("sectionIndex", -1) or -1) == sec_idx:
                                d["hatOpennessTarget"] = hat_open_target
                                d["hatsOpened"] = int(hats_opened)
                                d["hatsClosed"] = int(hats_closed)
                                d["rideBellified"] = int(bellified)
                                d["extraCrashes"] = int(extra_crashes)
                                break
                    except Exception:
                        pass

                # (0.9) breakdown / dropout mechanics (reduction)
                # Strip elements based on section energy or explicit reduction directive.
                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    intent = sec_cfg.get("grooveIntent") if isinstance(sec_cfg.get("grooveIntent"), dict) else {}
                    arrangement = sec_cfg.get("arrangement") if isinstance(sec_cfg.get("arrangement"), dict) else {}
                    energy = float(sec_cfg.get("energy", 0.6) or 0.6)

                    reduction = intent.get("reduction")
                    if reduction is None:
                        reduction = arrangement.get("reduction")
                    try:
                        reduction = float(reduction) if reduction is not None else (0.45 if energy < 0.4 else 0.0)
                    except Exception:
                        reduction = 0.0
                    reduction = max(0.0, min(1.0, reduction))
                    if reduction <= 1e-3:
                        continue

                    # Keep core pulse, strip ornaments.
                    keep_core = {"kick", "kick_in", "kick_out", "kick_sub", "snare_center"}
                    drop_cymbals_prob = max(0.0, min(0.95, 0.25 + 0.75 * reduction))
                    drop_ghost_prob = max(0.0, min(0.98, 0.35 + 0.65 * reduction))
                    drop_toms_prob = max(0.0, min(0.98, 0.20 + 0.80 * reduction))

                    stripped = 0
                    kept = 0
                    for e in list(all_events):
                        try:
                            t = float(e.get("time_sec", 0.0))
                        except Exception:
                            continue
                        if t < t0 or t >= t1:
                            continue
                        inst = e.get("instrument_id")
                        if inst in keep_core:
                            kept += 1
                            continue
                        if bool(e.get("barRole") == "fill"):
                            # allow fills to remain unless reduction is extreme
                            if reduction < 0.85:
                                kept += 1
                                continue
                        if inst in {"hihat_closed", "hihat_open", "hihat_pedal", "ride_bow", "ride_edge", "ride_bell", "crash_1", "crash_2"}:
                            if rng.random() < drop_cymbals_prob:
                                try:
                                    all_events.remove(e)
                                    stripped += 1
                                except Exception:
                                    pass
                                continue
                        if inst in {"snare_ghost"} or bool(e.get("isGhost", False)):
                            if rng.random() < drop_ghost_prob:
                                try:
                                    all_events.remove(e)
                                    stripped += 1
                                except Exception:
                                    pass
                                continue
                        if inst in {"tom_high", "tom_mid", "tom_low"}:
                            if rng.random() < drop_toms_prob:
                                try:
                                    all_events.remove(e)
                                    stripped += 1
                                except Exception:
                                    pass
                                continue
                        kept += 1

                    try:
                        for d in roadmap_debug:
                            if int(d.get("sectionIndex", -1) or -1) == sec_idx:
                                d["reduction"] = reduction
                                d["dropoutStripped"] = int(stripped)
                                d["dropoutKept"] = int(kept)
                                break
                    except Exception:
                        pass

                # (1) section-start crash (except very low energy sections)
                if on_section_start and section_ranges:
                    for (sec_idx, t0, _t1) in section_ranges:
                        if sec_idx <= 0:
                            continue
                        sec_cfg = sections_by_index.get(sec_idx, {})
                        energy = float(sec_cfg.get("energy", 0.6) or 0.6)
                        if energy < intensity_threshold:
                            continue
                        if rng.random() > float(sec_cfg.get("orchestration", {}).get("crashDownbeatProbability", 0.5) or 0.5):
                            continue
                        all_events.append(
                            {
                                "time_sec": float(t0),
                                "length_sec": 0.12,
                                "instrument_id": "crash_1",
                                "velocity": int(108 + min(18, max(0, int(energy * 18)))),
                                "barIndex": int(float(t0) // bar_dur_local),
                                "barRole": "accent",
                                "isGhost": False,
                                "isAccent": True,
                                "isFlam": False,
                                "isDrag": False,
                            }
                        )

                # (2) orchestration: promote hats to ride when requested
                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    orch = sec_cfg.get("orchestration") if isinstance(sec_cfg.get("orchestration"), dict) else {}
                    timekeeper = str(orch.get("timekeeper") or "").strip().lower()
                    if timekeeper not in {"ride", "mixed"}:
                        continue
                    promote_prob = 0.85 if timekeeper == "ride" else 0.45
                    for e in all_events:
                        try:
                            t = float(e.get("time_sec", 0.0))
                        except Exception:
                            continue
                        if t < t0 or t >= t1:
                            continue
                        inst = e.get("instrument_id")
                        if inst in {"hihat_closed", "hihat_open", "hihat_pedal"}:
                            if rng.random() <= promote_prob:
                                e["instrument_id"] = "ride_bow"
                                try:
                                    e["midi_pitch"] = instrument_id_to_midi_pitch("ride_bow")
                                except Exception:
                                    pass

                # (3) section-end fills + optional fill start/end crashes
                fill_policy = global_cfg.get("fillPolicy") if isinstance(global_cfg.get("fillPolicy"), dict) else {}
                fill_crash_policy = global_cfg.get("fillCrashPolicy") if isinstance(global_cfg.get("fillCrashPolicy"), dict) else {}
                default_fill_len = str(fill_policy.get("defaultLength") or "last_bar").strip().lower()
                repetition_fills = bool(fill_policy.get("repetitionFills", False))
                default_fill_family = str(fill_policy.get("defaultFillFamily") or "").strip().lower()

                # Light persona hint (do not hard depend on any one field)
                persona_hint = str(getattr(config, "articulation_profile", "") or "").strip().lower()

                start_crash_prob = float(fill_crash_policy.get("startCrashProb", 0.55) or 0.55)
                end_crash_prob = float(fill_crash_policy.get("endCrashProb", 0.35) or 0.35)

                def _inject_fill_stub(*, start_time: float, bar_dur: float, aggression: float, family: str) -> int:
                    # Simple deterministic fill families.
                    # Higher-quality rudiment enrichment (if enabled) can replace/augment later.
                    fam = str(family or "").strip().lower()
                    base_vel = int(68 + aggression * 48)
                    added = 0

                    if fam == "snare_rudiment":
                        # Snare-heavy fill, approximating rudiment feel.
                        steps = [0.5, 0.625, 0.75, 0.8125, 0.875]
                        for rel in steps:
                            if rng.random() > max(0.20, min(1.0, aggression + 0.10)):
                                continue
                            t = start_time + rel * bar_dur
                            all_events.append(
                                {
                                    "time_sec": float(t),
                                    "length_sec": 0.10,
                                    "instrument_id": "snare_center",
                                    "velocity": int(max(30, min(127, base_vel + rng.randint(-10, 12)))),
                                    "barIndex": int(float(t) // bar_dur_local),
                                    "barRole": "fill",
                                    "isGhost": False,
                                    "isAccent": True,
                                    "isFlam": bool(rng.random() < 0.15 and aggression > 0.7),
                                    "isDrag": bool(rng.random() < 0.10 and aggression > 0.7),
                                }
                            )
                            added += 1
                        return added

                    # Default: tom run
                    steps = [0.5, 0.625, 0.75, 0.8125, 0.875]
                    surfaces = ["tom_high", "tom_mid", "tom_low", "snare_center", "tom_low"]
                    for rel, inst in zip(steps, surfaces):
                        if rng.random() > max(0.18, min(1.0, aggression)):
                            continue
                        t = start_time + rel * bar_dur
                        all_events.append(
                            {
                                "time_sec": float(t),
                                "length_sec": 0.10,
                                "instrument_id": inst,
                                "velocity": int(max(30, min(127, base_vel + rng.randint(-10, 14)))),
                                "barIndex": int(float(t) // bar_dur_local),
                                "barRole": "fill",
                                "isGhost": False,
                                "isAccent": True,
                                "isFlam": False,
                                "isDrag": False,
                            }
                        )
                        added += 1
                    return added

                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    transitions = sec_cfg.get("transitions") if isinstance(sec_cfg.get("transitions"), dict) else {}
                    fill_out = transitions.get("fillOut") if isinstance(transitions.get("fillOut"), dict) else {}
                    enabled = bool(fill_out.get("enabled", True))
                    if not enabled:
                        continue
                    aggression = float(fill_out.get("aggression", 0.55) or 0.55)

                    # Avoid overfilling very short sections.
                    bars_in_section = 0
                    for sdbg in section_debug:
                        if int(sdbg.get("sectionIndex", -1) or -1) == sec_idx:
                            try:
                                bars_in_section = int(sdbg.get("bars", 0) or 0)
                            except Exception:
                                bars_in_section = 0
                            break
                    if bars_in_section > 0 and bars_in_section < 4:
                        # Only allow small fills when aggression is high; default to last_2_beats.
                        if aggression < 0.78:
                            continue

                    # Determine fill start based on length
                    bar_dur_local = bar_dur_local  # already computed
                    fill_start = t1 - bar_dur_local
                    local_fill_len = default_fill_len
                    if bars_in_section > 0 and bars_in_section < 4:
                        local_fill_len = "last_2_beats"
                    if local_fill_len == "last_2_beats":
                        fill_start = t1 - bar_dur_local * 0.5

                    # Choose fill family
                    fill_family = str(fill_out.get("family") or default_fill_family or "").strip().lower()
                    if not fill_family:
                        if "crashy" in persona_hint:
                            fill_family = "tom_run"
                        elif "ghosty" in persona_hint:
                            fill_family = "snare_rudiment"
                        else:
                            fill_family = "tom_run" if aggression >= 0.6 else "snare_rudiment"

                    # Start crash (fill start)
                    if rng.random() <= start_crash_prob:
                        all_events.append(
                            {
                                "time_sec": float(fill_start),
                                "length_sec": 0.12,
                                "instrument_id": "crash_1",
                                "velocity": int(96 + aggression * 28),
                                "barIndex": int(float(fill_start) // bar_dur_local),
                                "barRole": "fill",
                                "isGhost": False,
                                "isAccent": True,
                                "isFlam": False,
                                "isDrag": False,
                            }
                        )

                    # Fill body: if length is last_bar, inject into last bar; else only tail.
                    fill_added = 0
                    if local_fill_len == "last_bar":
                        fill_added += _inject_fill_stub(
                            start_time=t1 - bar_dur_local,
                            bar_dur=bar_dur_local,
                            aggression=aggression,
                            family=fill_family,
                        )
                    else:
                        # only last half
                        fill_added += _inject_fill_stub(
                            start_time=t1 - bar_dur_local,
                            bar_dur=bar_dur_local,
                            aggression=max(0.35, aggression * 0.8),
                            family=fill_family,
                        )

                    # End crash (fill end)
                    if rng.random() <= end_crash_prob:
                        all_events.append(
                            {
                                "time_sec": float(t1 - 0.02),
                                "length_sec": 0.12,
                                "instrument_id": "crash_1",
                                "velocity": int(100 + aggression * 24),
                                "barIndex": int(float(t1 - 0.02) // bar_dur_local),
                                "barRole": "fill",
                                "isGhost": False,
                                "isAccent": True,
                                "isFlam": False,
                                "isDrag": False,
                            }
                        )

                    # Repetition fills: every 4 bars inside a section (excluding last bar already handled)
                    if repetition_fills:
                        if bars_in_section >= 8:
                            # place repetition fills at bar 4 boundary
                            rep_time = t0 + 3.0 * bar_dur_local
                            if rep_time > t0 and rep_time < (t1 - bar_dur_local * 1.1):
                                _inject_fill_stub(
                                    start_time=rep_time,
                                    bar_dur=bar_dur_local,
                                    aggression=max(0.3, aggression * 0.65),
                                    family="snare_rudiment" if fill_family == "tom_run" else "tom_run",
                                )

                    # add to debug
                    try:
                        for d in roadmap_debug:
                            if int(d.get("sectionIndex", -1) or -1) == sec_idx:
                                d["fillFamily"] = fill_family
                                d["fillAdded"] = int(fill_added)
                                d["fillLength"] = local_fill_len
                                break
                    except Exception:
                        pass

                # (4) per-section cymbal density shaping (reduce hat/ride clutter in softer sections)
                for (sec_idx, t0, t1) in section_ranges:
                    sec_cfg = sections_by_index.get(sec_idx, {})
                    intent = sec_cfg.get("grooveIntent") if isinstance(sec_cfg.get("grooveIntent"), dict) else {}
                    target = float(intent.get("cymbalDensityTarget", 0.7) or 0.7)
                    # Convert target into keep probability for cymbals/hats
                    keep_prob = max(0.25, min(1.0, 0.35 + target * 0.75))
                    filtered: List[Dict[str, Any]] = []
                    for e in all_events:
                        try:
                            t = float(e.get("time_sec", 0.0))
                        except Exception:
                            filtered.append(e)
                            continue
                        if t < t0 or t >= t1:
                            filtered.append(e)
                            continue
                        inst = e.get("instrument_id")
                        if inst in {"hihat_closed", "hihat_open", "hihat_pedal", "ride_bow", "ride_edge"}:
                            if rng.random() <= keep_prob:
                                filtered.append(e)
                        else:
                            filtered.append(e)
                    # mutate in-place to avoid rebinding the outer list
                    all_events[:] = filtered

                # (5) ending behavior on final section
                try:
                    ending = global_cfg.get("ending") if isinstance(global_cfg.get("ending"), dict) else {}
                    final_crash = bool(ending.get("finalCrash", True))
                    stop_time = bool(ending.get("stopTime", False))
                    stop_time_beats = float(ending.get("stopTimeBeats", 1.0) or 1.0)

                    if section_ranges:
                        last_idx, last_t0, last_t1 = section_ranges[-1]
                        last_bar_start = max(last_t0, last_t1 - bar_dur_local)
                        last_downbeat = float(last_bar_start)
                        if final_crash:
                            all_events.append(
                                {
                                    "time_sec": float(last_downbeat),
                                    "length_sec": 0.18,
                                    "instrument_id": "crash_1",
                                    "velocity": 118,
                                    "barIndex": int(float(last_downbeat) // bar_dur_local),
                                    "barRole": "accent",
                                    "isGhost": False,
                                    "isAccent": True,
                                    "isFlam": False,
                                    "isDrag": False,
                                }
                            )
                            # reinforce with kick
                            all_events.append(
                                {
                                    "time_sec": float(last_downbeat),
                                    "length_sec": 0.12,
                                    "instrument_id": "kick",
                                    "velocity": 120,
                                    "barIndex": int(float(last_downbeat) // bar_dur_local),
                                    "barRole": "accent",
                                    "isGhost": False,
                                    "isAccent": True,
                                    "isFlam": False,
                                    "isDrag": False,
                                }
                            )

                        if stop_time and stop_time_beats > 0:
                            window_start = float(last_t1) - float(stop_time_beats) * beat_dur_local
                            # keep only the final crash/kick accents and core hits during stop window
                            keep_ids = {"kick", "snare_center", "crash_1", "crash_2"}
                            removed = 0
                            for e in list(all_events):
                                try:
                                    t = float(e.get("time_sec", 0.0))
                                except Exception:
                                    continue
                                if t < window_start or t >= last_t1:
                                    continue
                                if e.get("instrument_id") in keep_ids and bool(e.get("barRole") == "accent"):
                                    continue
                                if e.get("barRole") == "fill":
                                    continue
                                # strip everything else in the stop-time window
                                try:
                                    all_events.remove(e)
                                    removed += 1
                                except Exception:
                                    pass

                            try:
                                for d in roadmap_debug:
                                    if int(d.get("sectionIndex", -1) or -1) == int(last_idx):
                                        d["endingStopTime"] = True
                                        d["endingStopTimeRemoved"] = int(removed)
                                        break
                            except Exception:
                                pass
                except Exception:
                    pass

                # attach debug in section_debug so callers can include in metadata
                try:
                    for sdbg in section_debug:
                        if not isinstance(sdbg, dict):
                            continue
                        # store only once to avoid bloat
                        if "roadmapDebug" not in sdbg and isinstance(roadmap_debug, list):
                            sdbg["roadmapDebug"] = roadmap_debug
                            break
                except Exception:
                    pass
        except Exception as _roadmap_err:
            logger.warning("Song roadmap directives failed: %s", _roadmap_err)

        return (all_events, section_debug)

    internal_events: List[Dict[str, Any]] = []
    if getattr(v2_config, "generationMode", None) == "euclidean":
        lanes = getattr(v2_config, "euclideanLanes", None)
        if not lanes:
            raise Exception("Euclidean mode requested but euclideanLanes is empty; no fallback generation is allowed")
        internal_events = generate_euclidean_internal_events(config, v2_config)
    elif groove_source in {"egmd", "egmd_phrase", "egmd_phrases"} and getattr(config, "build_scope", None) == "full_song":
        # In EGMD exact mode, full-song playback should be a true tiling of a single EGMD phrase
        # (no per-section rotation, no roadmap shaping), otherwise we are not "using EGMD as-is".
        if egmd_exact_mode:
            controls = getattr(config, "groove_controls", None)
            if not isinstance(controls, dict):
                controls = _default_groove_controls_from_config(config)
            internal_events, egmd_sections_debug = _build_full_song_events_from_egmd_sections()
            if not internal_events:
                raise Exception("EGMD full-song exact requested but no events could be built")
            # Promote the first section phrase as top-level egmdPhrase (for backwards compatibility)
            first_pid = None
            first_midi = None
            if isinstance(egmd_sections_debug, list) and egmd_sections_debug:
                try:
                    first_pid = egmd_sections_debug[0].get("phrase_id")
                    first_midi = egmd_sections_debug[0].get("midi_path")
                except Exception:
                    first_pid = None
                    first_midi = None
            egmd_phrase_info = {
                "phrase_id": first_pid,
                "midi_path": first_midi,
                "audio_path": None,
                "measured": None,
            }
        else:
            internal_events, egmd_sections_debug = _build_full_song_events_from_egmd_sections()
            if not internal_events:
                raise Exception("EGMD full-song requested but no events could be built")
            egmd_phrase_info = {
                "phrase_id": None,
                "midi_path": None,
                "audio_path": None,
                "measured": None,
            }
    elif song_mode_active:
        grid_events = generate_song_grid_events(songmap, v2_config)
        if not grid_events:
            raise Exception(
                f"SongDrumPlanner produced no events for timeSignature={getattr(v2_config,'timeSignature',None)} songSections={getattr(v2_config,'songSections',None)}; fallback generation is not allowed"
            )
        try:
            grid_events = enrich_grid_with_rudiments(grid_events=grid_events, config=v2_config)
        except Exception as err:
            raise Exception(f"Rudiment enrichment failed: {err}")
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
        if not phrase:
            raise Exception("EGMD grooveSource requested but no phrase could be selected; no fallback generation is allowed")
        egmd_phrase_info = phrase
        internal_events = _load_internal_events_from_midi_path(
            midi_path=phrase["midi_path"],
            config=config,
        )
        if not internal_events:
            raise Exception("EGMD phrase selected but internal events could not be loaded; no fallback generation is allowed")
        if not egmd_exact_mode:
            controls = getattr(config, 'groove_controls', None)
            if not isinstance(controls, dict):
                controls = _default_groove_controls_from_config(config)
            measured = phrase.get('measured') if isinstance(phrase, dict) else None
            if isinstance(measured, dict):
                egmd_transform_plan = _transform_plan_from_diff(controls, measured)
                internal_events = _apply_transform_stack_v0(
                    internal_events=internal_events,
                    transform_plan=egmd_transform_plan,
                )
    else:
        raise Exception(
            "No supported generation path selected for this request (song mode inactive, no euclidean lanes, no egmd grooveSource). "
            "No fallback generation is allowed."
        )

    # 5.25. Optional: inject left-foot hat pulse on ride-focused bars (hihat_pedal)
    try:
        internal_events = _inject_foot_hat_pulse(
            internal_events=internal_events,
            songmap=songmap,
            v2_config=v2_config,
        )
    except Exception:
        pass

    if not internal_events:
        raise Exception("No internal events were produced by the generation pipeline; no fallback generation is allowed")

    try:
        fp_rows: List[str] = []
        for e in (internal_events[:80] if isinstance(internal_events, list) else []):
            try:
                fp_rows.append(
                    f"{e.get('instrument_id','')}|{float(e.get('time_sec',0.0)):.6f}|{int(e.get('velocity',0))}"
                )
            except Exception:
                continue
        fp_blob = "\n".join(fp_rows).encode("utf-8", errors="ignore")
        internal_events_fingerprint = hashlib.md5(fp_blob).hexdigest()
    except Exception:
        internal_events_fingerprint = None
    
    # 5.5. Enrich with Jamstix-style attributes
    if DRUM_BUILDER_V2_AVAILABLE and not egmd_exact_mode:
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
                ride_bell_bias=float((getattr(v2_config, "rideBellPercent", 0.2) or 0.2) - 0.5) * 2.0,
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
        resolution_ppq=1920,
        section_label=section_label,
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

    internal_events_breakdown = None
    egmd_midi_breakdown = None
    final_track_breakdown = None
    breakdown_diff = None
    try:
        if isinstance(internal_events, list):
            counts: Dict[str, int] = {}
            vel_sum: Dict[str, int] = {}
            vel_min: Dict[str, int] = {}
            vel_max: Dict[str, int] = {}
            ghost_counts: Dict[str, int] = {}
            for e in internal_events:
                if not isinstance(e, dict):
                    continue
                inst = str(e.get("instrument_id") or "")
                if not inst:
                    inst = "(missing)"
                v = int(e.get("velocity") or 0)
                counts[inst] = int(counts.get(inst, 0)) + 1
                vel_sum[inst] = int(vel_sum.get(inst, 0)) + v
                if inst not in vel_min:
                    vel_min[inst] = v
                else:
                    vel_min[inst] = min(int(vel_min[inst]), v)
                if inst not in vel_max:
                    vel_max[inst] = v
                else:
                    vel_max[inst] = max(int(vel_max[inst]), v)
                if bool(e.get("isGhost")):
                    ghost_counts[inst] = int(ghost_counts.get(inst, 0)) + 1

            ordered = sorted(counts.items(), key=lambda kv: (-int(kv[1]), kv[0]))
            top = []
            for inst, c in ordered[:30]:
                avg = float(vel_sum.get(inst, 0)) / float(c or 1)
                top.append(
                    {
                        "instrument_id": inst,
                        "count": int(c),
                        "ghost_count": int(ghost_counts.get(inst, 0)),
                        "velocity_min": int(vel_min.get(inst, 0)),
                        "velocity_max": int(vel_max.get(inst, 0)),
                        "velocity_avg": float(avg),
                    }
                )
            internal_events_breakdown = {
                "unique_instruments": int(len(counts)),
                "top": top,
            }

        midi_path_for_breakdown = None
        try:
            if isinstance(egmd_phrase_info, dict) and isinstance(egmd_phrase_info.get("midi_path"), str):
                midi_path_for_breakdown = egmd_phrase_info.get("midi_path")
            if not midi_path_for_breakdown:
                midi_path_for_breakdown = getattr(config, "egmd_midi_path", None)
        except Exception:
            midi_path_for_breakdown = None

        if isinstance(midi_path_for_breakdown, str) and midi_path_for_breakdown:
            try:
                try:
                    import mido
                except Exception as err:
                    raise Exception(f"mido_import_failed: {err}")
                from dcsmpiano.dcsm_drumtrack_schema import midi_pitch_to_instrument_id as _midi_pitch_to_inst
                midi = mido.MidiFile(midi_path_for_breakdown)
                midi_counts: Dict[str, int] = {}
                pitch_counts: Dict[int, int] = {}
                note_on_total = 0
                note_on_vel_pos_total = 0
                channel_counts: Dict[str, int] = {}
                type_sample: List[str] = []
                for track in getattr(midi, "tracks", []) or []:
                    for msg in track:
                        try:
                            if len(type_sample) < 25:
                                type_sample.append(str(getattr(msg, "type", "")))
                            if not getattr(msg, "type", None) == "note_on":
                                continue
                            note_on_total += 1
                            if int(getattr(msg, "velocity", 0) or 0) <= 0:
                                continue
                            note_on_vel_pos_total += 1
                            try:
                                ch = getattr(msg, "channel", None)
                                if ch is None:
                                    ch_key = "(none)"
                                else:
                                    ch_key = str(int(ch))
                                channel_counts[ch_key] = int(channel_counts.get(ch_key, 0)) + 1
                            except Exception:
                                pass
                            pitch = int(getattr(msg, "note", 0) or 0)
                            pitch_counts[pitch] = int(pitch_counts.get(pitch, 0)) + 1
                            raw_inst = _midi_pitch_to_inst(pitch)
                            inst = _canonicalize_inst_id(raw_inst)
                            if not inst:
                                inst = "(unmapped)"
                            midi_counts[inst] = int(midi_counts.get(inst, 0)) + 1
                        except Exception:
                            continue
                ordered_m = sorted(midi_counts.items(), key=lambda kv: (-int(kv[1]), kv[0]))
                ordered_p = sorted(pitch_counts.items(), key=lambda kv: (-int(kv[1]), int(kv[0])))
                egmd_midi_breakdown = {
                    "midi_path": midi_path_for_breakdown,
                    "unique_instruments": int(len(midi_counts)),
                    "top": [{"instrument_id": inst, "count": int(c)} for inst, c in ordered_m[:30]],
                    "top_pitches": [{"midi_pitch": int(p), "count": int(c)} for p, c in ordered_p[:30]],
                    "note_on_total": int(note_on_total),
                    "note_on_vel_pos_total": int(note_on_vel_pos_total),
                    "channels": sorted(channel_counts.items(), key=lambda kv: (-int(kv[1]), kv[0]))[:12],
                    "msg_type_sample": type_sample,
                }
            except Exception as err:
                egmd_midi_breakdown = {
                    "midi_path": midi_path_for_breakdown,
                    "error": "failed_to_read_midi",
                    "error_detail": f"{type(err).__name__}: {err}",
                }

        try:
            ft_counts: Dict[str, int] = {}
            for n in (frontend_track.get("notes", []) if isinstance(frontend_track, dict) else []) or []:
                if not isinstance(n, dict):
                    continue
                inst = str(n.get("instrumentId") or n.get("instrument_id") or "")
                if not inst:
                    inst = "(missing)"
                ft_counts[inst] = int(ft_counts.get(inst, 0)) + 1
            ordered_ft = sorted(ft_counts.items(), key=lambda kv: (-int(kv[1]), kv[0]))
            final_track_breakdown = {
                "unique_instruments": int(len(ft_counts)),
                "top": [{"instrument_id": inst, "count": int(c)} for inst, c in ordered_ft[:30]],
            }
        except Exception:
            final_track_breakdown = None

        try:
            def _count_from_breakdown(bd: Any, inst_id: str) -> int:
                if not isinstance(bd, dict):
                    return 0
                total = 0
                for row in (bd.get("top") or []):
                    try:
                        if isinstance(row, dict) and str(row.get("instrument_id")) == inst_id:
                            total += int(row.get("count") or 0)
                    except Exception:
                        continue
                return int(total)

            breakdown_diff = {
                "snare_center": {
                    "egmd_midi": _count_from_breakdown(egmd_midi_breakdown, "snare_center"),
                    "internal_events": _count_from_breakdown(internal_events_breakdown, "snare_center"),
                    "final_track": _count_from_breakdown(final_track_breakdown, "snare_center"),
                },
                "snare_ghost": {
                    "egmd_midi": _count_from_breakdown(egmd_midi_breakdown, "snare_ghost"),
                    "internal_events": _count_from_breakdown(internal_events_breakdown, "snare_ghost"),
                    "final_track": _count_from_breakdown(final_track_breakdown, "snare_ghost"),
                },
            }
        except Exception:
            breakdown_diff = None
    except Exception:
        internal_events_breakdown = None

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
        'performance_from_llm': False if egmd_exact_mode else True,
        'fill_density': getattr(config, 'fill_density', None),
        'articulation_profile': getattr(config, 'articulation_profile', None),
        'groove_source': groove_source,
        'groove_mode': groove_mode,
        'egmd_exact_mode': bool(egmd_exact_mode),
        'egmd_midi_path': getattr(config, 'egmd_midi_path', None),
        'egmd_phrase_id': getattr(config, 'egmd_phrase_id', None),
        'preserve_selected_egmd': bool(preserve_selected_egmd),
        'internal_events_count': len(internal_events) if isinstance(internal_events, list) else None,
        'internal_events_fingerprint': internal_events_fingerprint,
        'internal_events_breakdown': internal_events_breakdown,
        'egmd_midi_breakdown': egmd_midi_breakdown,
        'final_track_breakdown': final_track_breakdown,
        'breakdown_diff': breakdown_diff,
    }

    if isinstance(song_roadmap, dict):
        metadata['songRoadmap'] = song_roadmap

    if 'egmd_sections_debug' in locals() and isinstance(locals().get('egmd_sections_debug'), list):
        metadata['egmdSections'] = locals().get('egmd_sections_debug')

        # Promote roadmap debug (if present) to top-level metadata for easier inspection.
        try:
            for sdbg in locals().get('egmd_sections_debug') or []:
                if isinstance(sdbg, dict) and isinstance(sdbg.get('roadmapDebug'), list):
                    metadata['roadmapDebug'] = sdbg.get('roadmapDebug')
                    break
        except Exception:
            pass

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
        raise Exception("Euclidean mode requested but euclideanLanes is empty; no fallback generation is allowed")

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


def list_egmd_phrases(
    *,
    style_group: str,
    meter: Optional[str] = None,
    tempo_bpm: Optional[float] = None,
    tempo_tolerance_bpm: float = 12.0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """List EGMD phrases for a given style group.

    This is used by the frontend to allow users to pick among multiple clips
    within a style. Returned entries are lightweight (id + paths + meter/tempo if available).
    """
    if not _DRUM_TRAINING_DB_PATH.exists():
        return []
    sg = (style_group or "").strip().lower() or "rock"
    meter = (meter or "").strip() or None
    try:
        tempo = float(tempo_bpm) if tempo_bpm is not None else None
    except Exception:
        tempo = None
    tol = float(tempo_tolerance_bpm or 12.0)
    limit = max(1, min(200, int(limit or 50)))

    conn = _egmd_db_connect()
    try:
        cur = conn.cursor()
        tempo_expr = "COALESCE(tempo_bpm, tempo)"
        meter_expr = "COALESCE(meter, time_signature)"
        where = ["style_group = ?", "midi_path IS NOT NULL"]
        params: List[Any] = [sg]
        if meter:
            where.append(f"{meter_expr} = ?")
            params.append(meter)
        if tempo is not None and math.isfinite(tempo):
            where.append(f"{tempo_expr} BETWEEN ? AND ?")
            params.extend([tempo - tol, tempo + tol])
            order = f"ORDER BY ABS({tempo_expr} - ?), id"
            params.append(tempo)
        else:
            order = "ORDER BY id"

        query = (
            "SELECT id, midi_path, audio_path, "
            + tempo_expr
            + " AS tempo_value, "
            + meter_expr
            + " AS meter_value "
            "FROM egmd_phrases WHERE "
            + " AND ".join(where)
            + f" {order} LIMIT ?"
        )
        params.append(limit)
        cur.execute(query, tuple(params))
        rows = cur.fetchall() or []
        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {
                    "phrase_id": int(r["id"]),
                    "midi_path": r["midi_path"],
                    "audio_path": r["audio_path"],
                    "tempo_bpm": float(r["tempo_value"]) if r["tempo_value"] is not None else None,
                    "meter": str(r["meter_value"]) if r["meter_value"] is not None else None,
                }
            )
        return out
    except Exception:
        return []
    finally:
        conn.close()


def list_egmd_style_groups(*, limit: int = 200) -> List[str]:
    """Return distinct EGMD style_group values present in the training DB.

    This powers user-facing style choices (rock/jazz/funk/...) without exposing internal taxonomies.
    """
    if not _DRUM_TRAINING_DB_PATH.exists():
        return []
    try:
        limit_n = max(1, min(500, int(limit or 200)))
    except Exception:
        limit_n = 200

    conn = _egmd_db_connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT style_group
            FROM egmd_phrases
            WHERE style_group IS NOT NULL
              AND TRIM(style_group) <> ''
              AND midi_path IS NOT NULL
            ORDER BY style_group
            LIMIT ?
            """,
            (limit_n,),
        )
        rows = cur.fetchall() or []
        out: List[str] = []
        for r in rows:
            sg = str(r[0] if isinstance(r, (tuple, list)) else r["style_group"]).strip().lower()
            if sg:
                out.append(sg)
        return out
    except Exception:
        return []
    finally:
        conn.close()


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


def _canonicalize_inst_id(inst: str) -> str:
    key = str(inst or "").strip().lower()
    if not key:
        return ""
    aliases = {
        "snare": "snare_center",
        "snare_main": "snare_center",
        "snare_hit": "snare_center",
        "rim": "snare_rim",
        "sidestick": "snare_rim",
        "side_stick": "snare_rim",
        "snare_electric": "snare_center",
        "bd": "kick",
        "bassdrum": "kick",
        "bass_drum": "kick",
        "hat": "hihat_closed",
        "hh": "hihat_closed",
        "hihat": "hihat_closed",
        "ride": "ride_bow",
        "crash": "crash_1",
        "crash2": "crash_2",
        "china": "crash_china",
    }
    key = aliases.get(key, key)
    try:
        instrument_id_to_midi_pitch(key)
        return key
    except Exception:
        return ""


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

    build_scope = (getattr(config, "build_scope", None) or "").lower()
    is_full_song = build_scope == "full_song"
    is_basic_rock = style_group in {"rock", "metal", "hardrock", "hard_rock"} and meter == "4/4"

    if is_full_song and is_basic_rock:
        density = 8.0
        swing = 0.0

    return {
        "style_group": style_group,
        "meter": meter,
        "tempo_bpm": tempo,
        "tempo_tolerance_bpm": 12,
        "density_hps": density,
        "swing": swing,
        "hihat_ratio": 0.55 if (is_full_song and is_basic_rock) else 0.25,
        "kick_ratio": 0.12,
        "snare_ratio": 0.12,
        "fill_rate": 0.0 if (is_full_song and is_basic_rock) else 0.04,
        "ghost_ratio": 0.0 if (is_full_song and is_basic_rock) else 0.08,
    }


def _select_best_egmd_phrase(config: DrumGenerationConfig) -> Optional[Dict[str, Any]]:
    if not _DRUM_TRAINING_DB_PATH.exists():
        logger.warning("drum_training.db not found at %s", _DRUM_TRAINING_DB_PATH)
        return None

    forced_phrase_id = getattr(config, "egmd_phrase_id", None)
    if forced_phrase_id is not None and str(forced_phrase_id).strip() != "":
        try:
            forced_id = int(forced_phrase_id)
        except Exception:
            forced_id = None
        if forced_id is not None:
            conn = _egmd_db_connect()
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, midi_path, audio_path, feature_json FROM egmd_phrases WHERE id = ? LIMIT 1",
                    (forced_id,),
                )
                row = cur.fetchone()
                if row:
                    try:
                        fj = json.loads(row["feature_json"]) if row["feature_json"] else {}
                    except Exception:
                        fj = {}
                    pf = _derive_phrase_features_from_json(fj) if isinstance(fj, dict) else {}
                    try:
                        logger.info(
                            "EGMD forced phrase honored: %s",
                            int(row["id"]),
                        )
                    except Exception:
                        pass
                    return {
                        "phrase_id": int(row["id"]),
                        "midi_path": row["midi_path"],
                        "audio_path": row["audio_path"],
                        "measured": pf,
                    }
            finally:
                conn.close()

    controls = getattr(config, "groove_controls", None)
    if not isinstance(controls, dict):
        controls = _default_groove_controls_from_config(config)

    explicit_style_group = False
    try:
        sg_raw = getattr(config, "style_group", None)
        if isinstance(sg_raw, str) and sg_raw.strip():
            explicit_style_group = True
    except Exception:
        explicit_style_group = False

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

    min_kick_ratio = float(controls.get("min_kick_ratio", 0.05) or 0.05)
    min_snare_ratio = float(controls.get("min_snare_ratio", 0.05) or 0.05)

    conn = _egmd_db_connect()
    try:
        cur = conn.cursor()
        # Strict selection only: do NOT relax constraints. If there are no matches,
        # the caller must handle it explicitly (surface error / adjust filters).
        tempo_expr = "COALESCE(tempo_bpm, tempo)"
        meter_expr = "COALESCE(meter, time_signature)"
        if meter:
            cur.execute(
                f"""
                SELECT id, midi_path, audio_path, feature_json
                FROM egmd_phrases
                WHERE style_group = ?
                  AND {meter_expr} = ?
                  AND {tempo_expr} BETWEEN ? AND ?
                  AND feature_json IS NOT NULL
                ORDER BY ABS({tempo_expr} - ?), id
                LIMIT ?
                """,
                (style_group, meter, tempo_min, tempo_max, tempo, pool),
            )
        else:
            cur.execute(
                f"""
                SELECT id, midi_path, audio_path, feature_json
                FROM egmd_phrases
                WHERE style_group = ?
                  AND {tempo_expr} BETWEEN ? AND ?
                  AND feature_json IS NOT NULL
                ORDER BY ABS({tempo_expr} - ?), id
                LIMIT ?
                """,
                (style_group, tempo_min, tempo_max, tempo, pool),
            )
        rows: List[sqlite3.Row] = cur.fetchall() or []
        fallback_reason: Optional[str] = None

        if not rows:
            return None

        best_rows: List[Tuple[float, sqlite3.Row, Dict[str, float]]] = []
        rejected_by_core_filter = 0
        for row in rows:
            try:
                fj = json.loads(row["feature_json"]) if row["feature_json"] else {}
            except Exception:
                fj = {}
            pf = _derive_phrase_features_from_json(fj) if isinstance(fj, dict) else {}

            # Safety filter: avoid phrases that are missing core rock anchors.
            # This prevents selection of clips with virtually no kick/snare, which will
            # sound broken downstream even if other features match.
            if pf.get("kick_ratio", 0.0) < min_kick_ratio or pf.get("snare_ratio", 0.0) < min_snare_ratio:
                rejected_by_core_filter += 1
                continue

            score = _score_phrase(controls, pf)
            best_rows.append((score, row, pf))

        if not best_rows:
            return None

        # Deterministic choice: pick the best-scoring phrase.
        # (If you want variety, drive it from musical controls/constraints, not randomness.)
        best_rows.sort(key=lambda x: (x[0], int(x[1]["id"]) if "id" in x[1].keys() else 0))
        _, row, pf = best_rows[0]
        return {
            "phrase_id": int(row["id"]),
            "midi_path": row["midi_path"],
            "audio_path": row["audio_path"],
            "measured": pf,
            "fallback_reason": fallback_reason,
        }
    finally:
        conn.close()


def _rank_egmd_phrases(config: DrumGenerationConfig) -> List[Dict[str, Any]]:
    """Return a deterministic ranking of candidate EGMD phrases for this config."""
    if not _DRUM_TRAINING_DB_PATH.exists():
        return []

    forced_phrase_id = getattr(config, "egmd_phrase_id", None)
    if forced_phrase_id is not None and str(forced_phrase_id).strip() != "":
        # In forced mode, ranking isn't meaningful; return just the forced phrase.
        try:
            forced_id = int(forced_phrase_id)
        except Exception:
            forced_id = None
        if forced_id is None:
            return []
        conn = _egmd_db_connect()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, midi_path, audio_path, feature_json FROM egmd_phrases WHERE id = ? LIMIT 1",
                (int(forced_id),),
            )
            row = cur.fetchone()
            if not row:
                return []
            try:
                fj = json.loads(row["feature_json"]) if row["feature_json"] else {}
            except Exception:
                fj = {}
            pf = _derive_phrase_features_from_json(fj) if isinstance(fj, dict) else {}
            return [
                {
                    "phrase_id": int(row["id"]),
                    "midi_path": row["midi_path"],
                    "audio_path": row["audio_path"],
                    "measured": pf,
                    "score": 0.0,
                }
            ]
        finally:
            conn.close()

    controls = getattr(config, "groove_controls", None)
    if not isinstance(controls, dict):
        controls = _default_groove_controls_from_config(config)

    style_group = (controls.get("style_group") or "").lower() or "rock"
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
        tempo_expr = "COALESCE(tempo_bpm, tempo)"
        meter_expr = "COALESCE(meter, time_signature)"
        rows: List[sqlite3.Row] = []
        fallback_reason: Optional[str] = None

        def _run_query(*, q_meter: Optional[str], q_style: Optional[str], q_min: float, q_max: float) -> List[sqlite3.Row]:
            if q_style:
                if q_meter:
                    cur.execute(
                        f"""
                        SELECT id, midi_path, audio_path, feature_json
                        FROM egmd_phrases
                        WHERE style_group = ?
                          AND {meter_expr} = ?
                          AND {tempo_expr} BETWEEN ? AND ?
                          AND feature_json IS NOT NULL
                        ORDER BY ABS({tempo_expr} - ?), id
                        LIMIT ?
                        """,
                        (q_style, q_meter, q_min, q_max, tempo, pool),
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT id, midi_path, audio_path, feature_json
                        FROM egmd_phrases
                        WHERE style_group = ?
                          AND {tempo_expr} BETWEEN ? AND ?
                          AND feature_json IS NOT NULL
                        ORDER BY ABS({tempo_expr} - ?), id
                        LIMIT ?
                        """,
                        (q_style, q_min, q_max, tempo, pool),
                    )
            else:
                if q_meter:
                    cur.execute(
                        f"""
                        SELECT id, midi_path, audio_path, feature_json
                        FROM egmd_phrases
                        WHERE {meter_expr} = ?
                          AND {tempo_expr} BETWEEN ? AND ?
                          AND feature_json IS NOT NULL
                        ORDER BY ABS({tempo_expr} - ?), id
                        LIMIT ?
                        """,
                        (q_meter, q_min, q_max, tempo, pool),
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT id, midi_path, audio_path, feature_json
                        FROM egmd_phrases
                        WHERE {tempo_expr} BETWEEN ? AND ?
                          AND feature_json IS NOT NULL
                        ORDER BY ABS({tempo_expr} - ?), id
                        LIMIT ?
                        """,
                        (q_min, q_max, tempo, pool),
                    )
            return cur.fetchall() or []

        # Pass 1: strict (style + meter + tempo window)
        rows = _run_query(q_meter=meter if meter else None, q_style=style_group, q_min=tempo_min, q_max=tempo_max)

        # Pass 2: relax meter (style + tempo window)
        if not rows and meter:
            fallback_reason = "relaxed_meter"
            rows = _run_query(q_meter=None, q_style=style_group, q_min=tempo_min, q_max=tempo_max)

        # Pass 3: widen tempo window (style + optional meter)
        if not rows:
            widened = 30.0
            fallback_reason = (fallback_reason or "widened_tempo")
            rows = _run_query(q_meter=meter if meter else None, q_style=style_group, q_min=tempo - widened, q_max=tempo + widened)
            if not rows and meter:
                fallback_reason = "relaxed_meter_widened_tempo"
                rows = _run_query(q_meter=None, q_style=style_group, q_min=tempo - widened, q_max=tempo + widened)

        # Pass 4: relax style_group (meter + tempo window)
        if not rows:
            fallback_reason = "relaxed_style_group"
            rows = _run_query(q_meter=meter if meter else None, q_style=None, q_min=tempo_min, q_max=tempo_max)
            if not rows and meter:
                fallback_reason = "relaxed_style_group_relaxed_meter"
                rows = _run_query(q_meter=None, q_style=None, q_min=tempo_min, q_max=tempo_max)

        # Pass 5: relax style_group + widen tempo
        if not rows:
            widened = 30.0
            fallback_reason = "relaxed_style_group_widened_tempo"
            rows = _run_query(q_meter=meter if meter else None, q_style=None, q_min=tempo - widened, q_max=tempo + widened)
            if not rows and meter:
                fallback_reason = "relaxed_style_group_relaxed_meter_widened_tempo"
                rows = _run_query(q_meter=None, q_style=None, q_min=tempo - widened, q_max=tempo + widened)

        scored: List[Tuple[float, sqlite3.Row, Dict[str, float]]] = []
        for row in rows:
            try:
                fj = json.loads(row["feature_json"]) if row["feature_json"] else {}
            except Exception:
                fj = {}
                continue
            pf = _derive_phrase_features_from_json(fj)
            score = _score_phrase(controls, pf)
            scored.append((score, row, pf))

        if not scored:
            return []

        scored.sort(key=lambda x: (x[0], int(x[1]["id"]) if "id" in x[1].keys() else 0))
        out: List[Dict[str, Any]] = []
        for score, row, pf in scored[:top_k]:
            out.append(
                {
                    "phrase_id": int(row["id"]),
                    "midi_path": row["midi_path"],
                    "audio_path": row["audio_path"],
                    "measured": pf,
                    "score": float(score),
                    "fallback_reason": fallback_reason,
                }
            )
        return out
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

    # Important: for pinned MIDI playback we want deterministic bar/tick placement so
    # cursor + playback stay locked. Compute timing from MIDI ticks, then derive time_sec
    # from the exact grid at the requested tempo.
    events: List[Dict[str, Any]] = []

    beats_per_bar = int(getattr(config, "time_signature", (4, 4))[0] or 4)
    tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)
    total_bars = int(getattr(config, "measure_count", 1) or 1)

    # Builder uses PPQ=1920; normalize MIDI ticks into that grid.
    resolution_ppq = 1920
    src_ppq = int(getattr(mid, "ticks_per_beat", 480) or 480)
    scale = float(resolution_ppq) / float(max(1, src_ppq))
    bar_ticks = int(beats_per_bar * resolution_ppq)
    bar_dur_sec = (60.0 / max(tempo, 1e-6)) * float(beats_per_bar)
    phrase_len_sec = float(max(1, total_bars)) * float(bar_dur_sec)

    for track in mid.tracks:
        abs_ticks = 0
        for msg in track:
            try:
                abs_ticks += int(getattr(msg, "time", 0) or 0)
            except Exception:
                continue

            if msg.type != "note_on" or not getattr(msg, "velocity", 0) or int(getattr(msg, "velocity", 0) or 0) <= 0:
                continue
            if getattr(msg, "channel", None) != 9:
                continue

            try:
                raw_inst = midi_pitch_to_instrument_id(int(msg.note))
                instrument_id = _canonicalize_inst_id(raw_inst)
            except Exception:
                instrument_id = ""
            if not instrument_id:
                continue

            # Normalize to builder grid.
            abs_tick_scaled = int(round(float(abs_ticks) * scale))
            bi = int(abs_tick_scaled // max(1, bar_ticks))
            if bi < 0 or bi >= max(1, total_bars):
                continue
            tib = int(abs_tick_scaled - (bi * bar_ticks))
            tsec = (float(abs_tick_scaled) / float(resolution_ppq)) * (60.0 / max(tempo, 1e-6))
            if tsec < 0 or tsec >= phrase_len_sec:
                continue

            length = 0.12
            is_ghost = int(msg.velocity) < 30
            is_accent = int(msg.velocity) > 100
            events.append(
                {
                    "time_sec": float(tsec),
                    "length_sec": float(length),
                    "instrument_id": instrument_id,
                    "midi_pitch": int(instrument_id_to_midi_pitch(instrument_id)),
                    "velocity": int(msg.velocity),
                    "isGhost": bool(is_ghost),
                    "isAccent": bool(is_accent),
                    "isFlam": False,
                    "isDrag": False,
                    "barIndex": int(bi),
                    "tickInBar": int(tib),
                    "resolution_ppq": int(resolution_ppq),
                    "phrase_len_sec": float(phrase_len_sec),
                }
            )

    if not events:
        return []

    # Final ordering (important for deterministic builder input)
    events.sort(key=lambda e: (int(e.get("barIndex") or 0), int(e.get("tickInBar") or 0), str(e.get("instrument_id") or "")))
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

    # Allow explicit UI override for cymbal focus.
    try:
        focus_mode = str(getattr(config, "cymbal_focus_mode", "continuous") or "continuous").strip().lower()
        user_blend = float(getattr(config, "hats_to_ride_blend", 0.0) or 0.0)
        user_thresh = float(getattr(config, "hats_to_ride_threshold", 0.6) or 0.6)
        user_chorus = float(getattr(config, "chorus_ride_preference", 0.0) or 0.0)
        if focus_mode == "continuous":
            hats_to_ride = user_blend if user_blend >= user_thresh else 0.0
        elif focus_mode == "section_rule":
            hats_to_ride = max(hats_to_ride, user_chorus)
    except Exception:
        pass

    try:
        ride_bell_percent = float(getattr(config, "ride_bell_percent", 0.2) or 0.2)
    except Exception:
        ride_bell_percent = 0.2

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

    # (1.5) ride bell percentage on accents (bow -> bell)
    if ride_bell_percent > 0.001:
        prob = max(0.0, min(1.0, ride_bell_percent))
        for e in events:
            inst = e.get("instrument_id")
            if inst != "ride_bow":
                continue
            if not bool(e.get("isAccent", False)):
                continue
            if rng.random() <= prob:
                e["instrument_id"] = "ride_bell"
                try:
                    e["midi_pitch"] = instrument_id_to_midi_pitch("ride_bell")
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


def build_drummer_profile(config: DrumGenerationConfig) -> Dict[str, Any]:
    """Resolve a drummer profile for LLM prompting."""

    drummer_name = getattr(config, "drummer", None) or "unknown"
    return get_drummer_profile_simple(str(drummer_name))


def _build_full_song_internal_events_from_egmd(
    *,
    config: DrumGenerationConfig,
    controls: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    beats_per_bar = int(getattr(config, "time_signature", (4, 4))[0] or 4)
    tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)
    bar_duration = (60.0 / max(tempo, 1e-3)) * beats_per_bar
    measure_count = int(getattr(config, "measure_count", 1) or 1)
    total_duration = bar_duration * measure_count

    chunk_bars = int(controls.get("egmd_chunk_bars", 4) or 4)
    chunk_bars = max(1, min(16, chunk_bars))
    chunk_duration = bar_duration * chunk_bars

    seed = int(getattr(config, "start_measure", 0) or 0) + 901
    rng = random.Random(seed)

    out: List[Dict[str, Any]] = []
    chosen_phrase: Optional[Dict[str, Any]] = None

    t0 = 0.0
    while t0 < total_duration - 1e-6:
        phrase = _select_best_egmd_phrase(config)
        if not phrase:
            break
        if chosen_phrase is None:
            chosen_phrase = phrase

        phrase_events = _load_internal_events_from_midi_path(midi_path=phrase["midi_path"], config=config)
        if not phrase_events:
            t0 += chunk_duration
            continue

        measured = phrase.get("measured") if isinstance(phrase, dict) else None
        if isinstance(measured, dict):
            transform_plan = _transform_plan_from_diff(controls, measured)
            phrase_events = _apply_transform_stack_v0(
                internal_events=phrase_events,
                config=config,
                transform_plan=transform_plan,
            )

        phrase_max_time = max(float(e.get("time_sec", 0.0)) for e in phrase_events)
        phrase_span = max(0.25, phrase_max_time)

        local_time = 0.0
        while local_time < chunk_duration - 1e-6:
            for e in phrase_events:
                te = float(e.get("time_sec", 0.0))
                out_time = t0 + local_time + (te % phrase_span)
                if out_time >= total_duration:
                    continue
                e2 = dict(e)
                e2["time_sec"] = float(out_time)
                out.append(e2)
            local_time += phrase_span

        reseed_prob = float(controls.get("egmd_reseed_probability", 0.85) or 0.85)
        if rng.random() < reseed_prob:
            t0 += chunk_duration
        else:
            t0 += bar_duration

    if chosen_phrase is None:
        chosen_phrase = {"phrase_id": None, "midi_path": None, "audio_path": None, "measured": None}
    out.sort(key=lambda e: float(e.get("time_sec", 0.0)))
    return chosen_phrase, out


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

        if is_ghost and instrument_id == "snare_center":
            instrument_id = "snare_ghost"

        notes.append(
            {
                "id": note_id,
                "barIndex": bar_index,
                "tickInBar": int(note_attr(note, "tickInBar", 0) or 0),
                "tickLength": int(note_attr(note, "tickLength", resolution // 4) or resolution // 4),
                "instrumentId": instrument_id,
                "articulationId": note_attr(note, "articulationId"),
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
    # Apply explicit per-bar directives (absolute bar indices).
    try:
        forced = getattr(config, "force_fill_bars", None) or []
        suppressed = getattr(config, "suppress_fill_bars", None) or []
        for bi in forced:
            try:
                fill_bars.add(int(bi))
            except Exception:
                continue
        for bi in suppressed:
            try:
                b = int(bi)
            except Exception:
                continue
            if b in fill_bars:
                fill_bars.remove(b)
    except Exception:
        pass
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

    # Prefer the existing plugin-aware renderer when available.
    try:
        from backend.render_to_plugin_midi import render_articulated_notes_to_midi
    except Exception:
        render_articulated_notes_to_midi = None

    ppq = int(getattr(dcsm_track, 'resolution_ppq', 480) or 480)
    ppq = max(48, min(ppq, 1000000))
    beats_per_bar = int(config.time_signature[0]) if getattr(config, 'time_signature', None) else 4
    beats_per_bar = max(1, beats_per_bar)
    bar_ticks = beats_per_bar * ppq

    # Decide which articulation map to use.
    midi_map = (getattr(config, 'midi_map_name', None) or 'gm').strip().lower()
    plugin = 'jamstix'
    if 'sd3' in midi_map or 'superior' in midi_map:
        plugin = 'sd3'
    elif 'ssd5' in midi_map or 'ssd' in midi_map:
        plugin = 'ssd5'

    # Build renderer payload. We keep timing in ticks and let the renderer handle
    # mapping to plugin note numbers + emitting any required CCs.
    notes_out = []
    for note in raw_notes:
        bar_index = clamp_int(note_attr(note, 'barIndex', 0), 0, 1_000_000, 0)
        tick_in_bar = clamp_int(note_attr(note, 'tickInBar', 0), 0, 10_000_000, 0)
        tick_len = clamp_int(note_attr(note, 'tickLength', ppq // 4), 1, 10_000_000, ppq // 4)
        channel = clamp_int(note_attr(note, 'channel', 9), 0, 15, 9)
        velocity = clamp_int(note_attr(note, 'velocity', 100), 1, 127, 100)
        midi_pitch = clamp_int(note_attr(note, 'midiPitch', 36), 0, 127, 36)

        t0 = bar_index * bar_ticks + tick_in_bar
        t1 = max(t0 + 1, t0 + tick_len)

        notes_out.append(
            {
                't0': int(t0),
                't1': int(t1),
                'pitch': int(midi_pitch),
                'vel': int(velocity),
                'chan': int(channel),
                'articulationId': note_attr(note, 'articulationId'),
            }
        )

    if render_articulated_notes_to_midi is not None:
        try:
            tempo_bpm = float((getattr(config, "tempos", None) or [120])[0] or 120)
        except Exception:
            tempo_bpm = 120.0
        rendered = render_articulated_notes_to_midi(
            {
                'plugin': plugin,
                'ppq': ppq,
                'tempo_bpm': tempo_bpm,
                'notes': notes_out,
            }
        )
        midi_b64 = rendered.get('midi_base64')
        if midi_b64:
            return str(midi_b64)

    # Fallback: tiny empty MIDI if the renderer isn't available.
    mock_midi = b'MThd\x00\x00\x00\x06\x00\x01\x00\x01\x01\xe0MTrk\x00\x00\x00\x04\x00\xff\x2f\x00'
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
        'midi_base64': export_track_to_midi_base64(None, config),
        'metadata': {
            'drummer_used': config.drummer,
            'style': config.style,
            'mode': 'legacy_fallback',
            'humanized': False,
            'measure_count': config.measure_count,
        }
    }
