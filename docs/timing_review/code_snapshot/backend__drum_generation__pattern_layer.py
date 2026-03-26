"""
Pattern Layer - Grid Generation
===============================
Generates grid-level drum events (WHAT notes, not HOW they're played).

This is a placeholder/adapter for your existing pattern generation logic.
"""

import logging
from typing import List, Dict, Any
from .drum_generation_config import GridEvent, DrumGenerationConfig

logger = logging.getLogger(__name__)


_MUST_KNOW_BEATS: Dict[str, Dict[str, List[int]]] = {
    # Notes are 16th-subdivision indices (0..15) within a 4/4 bar.
    # Instrument ids use DrumTracKAI canonical ids where possible.
    # These are intentionally simple 1-bar archetypes; refinements can be applied later.
    "beat_01_four_on_floor": {
        "kick": [0, 4, 8, 12],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_02_dance": {
        "kick": [0, 4, 8, 12],
        "snare_center": [4, 12],
        "hihat_closed": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    },
    "beat_03_first_beat": {
        "kick": [0, 8],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_04_second_beat": {
        "kick": [0, 6, 8],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_05_classic_rock": {
        "kick": [0, 6, 8],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_06_classic_rock_2": {
        "kick": [0, 6, 10],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_07_halftime": {
        "kick": [0, 8],
        "snare_center": [8],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_08_halftime_16ths": {
        "kick": [0, 8],
        "snare_center": [8],
        "hihat_closed": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    },
    "beat_09_halftime_turned_normal": {
        "kick": [0, 8],
        "snare_center": [4, 12],
        "hihat_closed": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    },
    "beat_10_change_things_up": {
        "kick": [0, 6, 10, 12],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_11_bieber": {
        "kick": [0, 6, 8, 14],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
        "hihat_open": [15],
    },
    "beat_12_bieber_on_toms": {
        "kick": [0, 6, 8, 14],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
        "tom_mid": [10],
        "tom_floor": [15],
    },
    "beat_13_pop_country": {
        "kick": [0, 6, 8],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_14_pop_country_chorus": {
        "kick": [0, 6, 8, 10],
        "snare_center": [4, 12],
        "hihat_closed": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
        "crash_1": [0],
    },
    "beat_15_double_time": {
        "kick": [0, 8],
        "snare_center": [4, 12],
        "hihat_closed": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
    },
    "beat_16_jungle": {
        "kick": [0, 7, 10],
        "snare_center": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_17_cross_stick": {
        "kick": [0, 8],
        "snare_rim": [4, 12],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_18_four_on_floor_halftime": {
        "kick": [0, 4, 8, 12],
        "snare_center": [8],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_19_first_ghost_note": {
        "kick": [0, 8],
        "snare_center": [4, 12],
        "snare_ghost": [3, 7, 11, 15],
        "hihat_closed": [0, 2, 4, 6, 8, 10, 12, 14],
    },
    "beat_20_anthem_toms": {
        "kick": [0, 8],
        "snare_center": [4, 12],
        "crash_1": [0],
        "tom_high": [10],
        "tom_mid": [14],
        "tom_floor": [15],
        "hihat_closed": [0, 4, 8, 12],
    },
}


def _choose_must_know_template_id(config: DrumGenerationConfig) -> str:
    style = str(getattr(config, "songStyle", None) or getattr(config, "style", "") or "").strip().lower()
    if style in {"edm", "dance"}:
        return "beat_02_dance"
    if style in {"pop"}:
        return "beat_03_first_beat"
    if style in {"metal"}:
        return "beat_15_double_time"
    if style in {"funk"}:
        return "beat_10_change_things_up"
    if style in {"blues"}:
        return "beat_05_classic_rock"
    if style in {"rock"}:
        return "beat_05_classic_rock"
    # Default: classic rock archetype
    return "beat_05_classic_rock"


def _append_16th_hits(
    out: List[GridEvent],
    *,
    bar_idx: int,
    subdivisions_per_bar: int,
    instrument_id: str,
    hit_subdivisions: List[int],
) -> None:
    for s in hit_subdivisions:
        ss = int(s)
        if ss < 0 or ss >= subdivisions_per_bar:
            continue
        out.append(
            GridEvent(
                bar_index=bar_idx,
                subdivision_index=ss,
                subdivisions_per_bar=subdivisions_per_bar,
                instrument_id=instrument_id,
                is_accent=(ss == 0),
            )
        )


def generate_grid_pattern_events(
    songmap: Any,
    config: DrumGenerationConfig,
    pattern_model: Any = None,
) -> List[GridEvent]:
    """
    Generate grid-level drum events (pattern layer).
    
    This function is a placeholder that wraps your existing pattern generation.
    Replace with your actual pattern generation logic.
    
    Args:
        songmap: SongMap with bars, sections, tempo
        config: Complete drum generation config
        pattern_model: Your existing pattern model (GrooVAE, templates, etc.)
    
    Returns:
        List of GridEvent (grid-level, no micro-timing)
    """
    
    logger.info(f"Generating pattern for {config.generationMode} mode")
    
    grid_events: List[GridEvent] = []
    subdivisions_per_bar = 16  # 16th note grid
    
    # For each bar in the range
    for bar_idx in range(config.startMeasure, config.endMeasure + 1):
        if bar_idx >= len(songmap.bars):
            break
        
        bar = songmap.bars[bar_idx]
        
        # Generate bar pattern based on mode
        if config.generationMode == "template":
            bar_events = generate_template_bar(
                bar_idx, bar, config, subdivisions_per_bar
            )
        elif config.generationMode == "ai_variation":
            bar_events = generate_ai_variation_bar(
                bar_idx, bar, config, subdivisions_per_bar, pattern_model
            )
        else:  # full_ai
            bar_events = generate_full_ai_bar(
                bar_idx, bar, config, subdivisions_per_bar, pattern_model
            )
        
        grid_events.extend(bar_events)
    
    logger.info(f"Generated {len(grid_events)} grid events")
    return grid_events


def generate_template_bar(
    bar_idx: int,
    bar: Any,
    config: DrumGenerationConfig,
    subdivisions_per_bar: int,
) -> List[GridEvent]:
    """
    Generate template-based bar pattern.
    
    Replace with your actual template logic.
    """
    
    events: List[GridEvent] = []

    template_id = _choose_must_know_template_id(config)
    template = _MUST_KNOW_BEATS.get(template_id) or _MUST_KNOW_BEATS["beat_05_classic_rock"]

    for inst_id, steps in template.items():
        _append_16th_hits(
            events,
            bar_idx=bar_idx,
            subdivisions_per_bar=subdivisions_per_bar,
            instrument_id=inst_id,
            hit_subdivisions=list(steps or []),
        )

    return events


def generate_ai_variation_bar(
    bar_idx: int,
    bar: Any,
    config: DrumGenerationConfig,
    subdivisions_per_bar: int,
    pattern_model: Any,
) -> List[GridEvent]:
    """
    Generate AI variation bar pattern.
    
    Replace with your actual AI variation logic.
    """
    
    # Placeholder: Use template as base
    events = generate_template_bar(bar_idx, bar, config, subdivisions_per_bar)
    
    # TODO: Add variations using your pattern model
    # - Vary hi-hat pattern
    # - Add ghost notes based on config.ghostNoteAmount
    # - Add syncopation based on config.variation
    
    return events


def generate_full_ai_bar(
    bar_idx: int,
    bar: Any,
    config: DrumGenerationConfig,
    subdivisions_per_bar: int,
    pattern_model: Any,
) -> List[GridEvent]:
    """
    Generate fully AI-generated bar pattern.
    
    Replace with your actual full AI logic (GrooVAE, etc.).
    """
    
    # Placeholder: Use template as base
    events = generate_template_bar(bar_idx, bar, config, subdivisions_per_bar)
    
    # TODO: Replace with your full AI generation
    # - Use GrooVAE or similar
    # - Consider style, drummer profile, intensity
    # - Add complexity based on config.variation
    
    return events


def convert_internal_events_to_grid_events(
    internal_events: List[Dict[str, Any]],
    songmap: Any,
    resolution_ppq: int = 960,
    subdivisions_per_bar: int = 16,
) -> List[GridEvent]:
    """
    Convert your existing internal drum events to GridEvent format.
    
    Use this adapter if you already have a working pattern generator
    that outputs events with time_sec, instrument_id, etc.
    
    Args:
        internal_events: Your existing event format
        songmap: SongMap for time->bar mapping
        resolution_ppq: MIDI resolution
        subdivisions_per_bar: Grid resolution
    
    Returns:
        List of GridEvent
    """
    
    grid_events = []
    
    # Build bar timing lookup
    bar_start_times = [b.start_time for b in songmap.bars]
    bar_end_times = [b.end_time for b in songmap.bars]
    
    for ev in internal_events:
        time_sec = ev["time_sec"]
        inst_id = ev["instrument_id"]
        is_ghost = ev.get("isGhost", False)
        is_accent = ev.get("isAccent", False)
        is_flam = ev.get("isFlam", False)
        is_drag = ev.get("isDrag", False)
        
        # Find bar
        bar_idx = None
        for i, (start, end) in enumerate(zip(bar_start_times, bar_end_times)):
            if start <= time_sec < end:
                bar_idx = i
                break
        
        if bar_idx is None:
            continue
        
        # Calculate subdivision
        bar = songmap.bars[bar_idx]
        bar_len_sec = bar.end_time - bar.start_time
        frac = (time_sec - bar.start_time) / max(bar_len_sec, 1e-6)
        subdivision_idx = int(round(frac * subdivisions_per_bar))
        subdivision_idx = max(0, min(subdivisions_per_bar - 1, subdivision_idx))
        
        grid_events.append(GridEvent(
            bar_index=bar_idx,
            subdivision_index=subdivision_idx,
            subdivisions_per_bar=subdivisions_per_bar,
            instrument_id=inst_id,
            is_ghost=is_ghost,
            is_accent=is_accent,
            is_flam=is_flam,
            is_drag=is_drag,
        ))
    
    return grid_events
