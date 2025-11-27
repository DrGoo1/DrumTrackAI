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
    
    events = []
    
    # Basic rock beat template
    # Kick on 1 and 3
    for beat in [0, 8]:  # Beats 1 and 3 in 16th notes
        events.append(GridEvent(
            bar_index=bar_idx,
            subdivision_index=beat,
            subdivisions_per_bar=subdivisions_per_bar,
            instrument_id="kick",
            is_accent=beat == 0,
        ))
    
    # Snare on 2 and 4
    for beat in [4, 12]:  # Beats 2 and 4 in 16th notes
        events.append(GridEvent(
            bar_index=bar_idx,
            subdivision_index=beat,
            subdivisions_per_bar=subdivisions_per_bar,
            instrument_id="snare_center",
            is_accent=True,
        ))
    
    # Hi-hat on every 8th note
    for beat in range(0, subdivisions_per_bar, 2):
        events.append(GridEvent(
            bar_index=bar_idx,
            subdivision_index=beat,
            subdivisions_per_bar=subdivisions_per_bar,
            instrument_id="hihat_closed",
            is_accent=beat % 4 == 0,
        ))
    
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
