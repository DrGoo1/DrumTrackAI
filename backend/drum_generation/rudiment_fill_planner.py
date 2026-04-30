"""Rudiment-aware fill planner that upgrades SongDrumPlanner grid events.

The planner sits between the SongDrumPlanner (which produces basic groove +
fill placeholders) and the internal event conversion step. It inspects bars
that were marked as fills and swaps their coarse snare spam with curated
rudiment phrases from :mod:`rudiment_library`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .drum_generation_config import (
    DrumGenerationConfig,
    GridEvent,
    RudimentBlock,
    RudimentControls,
)
from .rudiment_library import RudimentPattern, get_rudiment_catalogue


@dataclass
class RudimentPlannerSettings:
    """Derived preferences steering which rudiments are selected."""

    density: float = 0.7
    allowed_families: Optional[List[str]] = None
    keep_kick_on_one: bool = True
    carry_hat_tail: bool = True
    preferred_rudiments: List[str] = field(default_factory=list)
    bar_blocks: Dict[int, RudimentBlock] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: DrumGenerationConfig) -> "RudimentPlannerSettings":
        fill_controls = getattr(config, "fillControls", None)
        rudiment_controls: Optional[RudimentControls] = getattr(config, "rudimentControls", None)

        density = getattr(config, "fillDensity", 0.7)
        if fill_controls and getattr(fill_controls, "density", None) is not None:
            density = fill_controls.density
        if rudiment_controls and getattr(rudiment_controls, "density", None) is not None:
            density = rudiment_controls.density

        fill_type = getattr(fill_controls, "fillType", None) or getattr(config, "fillType", "auto")
        families = _families_from_fill_type(fill_type)
        if rudiment_controls and rudiment_controls.preferredFamilies:
            families = list(rudiment_controls.preferredFamilies)

        keep_kick = True
        carry_hat_tail = True
        preferred_rudiments: List[str] = []
        if rudiment_controls:
            keep_kick = rudiment_controls.ensureDownbeatKick
            carry_hat_tail = rudiment_controls.preserveHatTail
            preferred_rudiments = list(rudiment_controls.preferredRudiments)

        bar_blocks: Dict[int, RudimentBlock] = {}
        for block in getattr(config, "rudimentBlocks", None) or []:
            if not isinstance(block, RudimentBlock):
                continue
            length = max(0, block.lengthBars)
            for offset in range(length):
                bar_idx = block.startBar + offset
                bar_blocks.setdefault(bar_idx, block)

        return cls(
            density=_clamp(density, 0.0, 1.0),
            allowed_families=families,
            keep_kick_on_one=keep_kick,
            carry_hat_tail=carry_hat_tail,
            preferred_rudiments=preferred_rudiments,
            bar_blocks=bar_blocks,
        )


def enrich_grid_with_rudiments(
    *,
    grid_events: Sequence[GridEvent],
    config: DrumGenerationConfig,
    rng: Optional[random.Random] = None,
) -> List[GridEvent]:
    """Replace naive fill bars with curated rudiment phrases."""

    if not grid_events:
        return list(grid_events)

    fill_controls = getattr(config, "fillControls", None)
    rudiment_controls: Optional[RudimentControls] = getattr(config, "rudimentControls", None)
    if not fill_controls and not rudiment_controls:
        # Song Mode not active or user disabled fills; leave grid untouched.
        return list(grid_events)
    if rudiment_controls and not rudiment_controls.enabled:
        return list(grid_events)

    fill_bars = _detect_fill_bars(grid_events)
    if not fill_bars:
        return list(grid_events)

    settings = RudimentPlannerSettings.from_config(config)
    catalogue = get_rudiment_catalogue()
    rng = rng or _build_rng(config)

    events_by_bar: Dict[int, List[GridEvent]] = {}
    bar_order: List[int] = []
    for event in grid_events:
        events_by_bar.setdefault(event.bar_index, []).append(event)
        if event.bar_index not in bar_order:
            bar_order.append(event.bar_index)

    for bar_idx in fill_bars:
        if bar_idx not in events_by_bar:
            continue

        block_override = settings.bar_blocks.get(bar_idx)
        pattern = _select_pattern(
            catalogue,
            settings,
            rng,
            block=block_override,
        )
        if not pattern:
            continue

        original_events = events_by_bar[bar_idx]
        subdivisions = original_events[0].subdivisions_per_bar if original_events else 16
        surface_overrides = _surface_overrides_for_config(config)
        rudiment_events = pattern.materialize(
            bar_index=bar_idx,
            subdivisions_per_bar=subdivisions,
            surface_overrides=surface_overrides,
        )

        if not rudiment_events:
            continue

        keep_kick = settings.keep_kick_on_one
        carry_hat_tail = settings.carry_hat_tail
        if block_override:
            if block_override.ensureDownbeatKick is not None:
                keep_kick = block_override.ensureDownbeatKick
            if block_override.preserveHatTail is not None:
                carry_hat_tail = block_override.preserveHatTail

        if keep_kick:
            rudiment_events = _merge_downbeat_kick(original_events, rudiment_events)

        if carry_hat_tail:
            rudiment_events = _merge_hat_tail(original_events, rudiment_events, subdivisions)

        events_by_bar[bar_idx] = rudiment_events

    enriched: List[GridEvent] = []
    for bar_idx in bar_order:
        events = events_by_bar.get(bar_idx, [])
        events.sort(key=lambda e: (e.subdivision_index, e.instrument_id))
        enriched.extend(events)

    return enriched


def _detect_fill_bars(grid_events: Sequence[GridEvent]) -> List[int]:
    bars = {event.bar_index for event in grid_events if getattr(event, "bar_role", None) == "fill"}
    return sorted(bars)


def _select_pattern(
    catalogue: Dict[str, RudimentPattern],
    settings: RudimentPlannerSettings,
    rng: random.Random,
    *,
    block: Optional[RudimentBlock],
) -> Optional[RudimentPattern]:
    if block and block.rudimentId:
        pinned = catalogue.get(block.rudimentId)
        if pinned:
            return pinned

    families = block.families if block and block.families else settings.allowed_families

    preferred_ids: List[str] = []
    if block and block.rudimentId:
        preferred_ids.append(block.rudimentId)
    preferred_ids.extend(settings.preferred_rudiments)
    for rid in preferred_ids:
        pattern = catalogue.get(rid)
        if not pattern:
            continue
        if families and pattern.family not in families:
            continue
        return pattern

    candidates = [
        pattern
        for pattern in catalogue.values()
        if not families or pattern.family in families
    ]
    if not candidates:
        candidates = list(catalogue.values())
    if not candidates:
        return None

    target_density = block.density if block and block.density is not None else settings.density
    candidates.sort(key=lambda p: p.complexity)
    idx = int(round(target_density * (len(candidates) - 1))) if len(candidates) > 1 else 0
    if len(candidates) > 2:
        idx += rng.choice([-1, 0, 1])
    idx = max(0, min(len(candidates) - 1, idx))
    return candidates[idx]


def _surface_overrides_for_config(config: DrumGenerationConfig) -> Dict[str, str]:
    intensity = _clamp(getattr(config, "intensity", 0.7), 0.0, 1.0)
    overrides: Dict[str, str] = {}
    if intensity >= 0.65:
        overrides["snare_accent"] = "snare_rimshot"
        overrides["cymbal"] = "crash_heavy"
    if intensity >= 0.85:
        overrides["stack"] = "china"
    if getattr(config, "style", "").lower() in {"jazz", "fusion"}:
        overrides["cymbal"] = "ride_bow"
    return overrides


def _merge_downbeat_kick(original: Sequence[GridEvent], new_events: List[GridEvent]) -> List[GridEvent]:
    has_downbeat_kick = any(
        e.instrument_id.startswith("kick") and e.subdivision_index == 0 for e in new_events
    )
    if has_downbeat_kick:
        return new_events

    downbeat_kicks = [
        e for e in original if e.instrument_id.startswith("kick") and e.subdivision_index == 0
    ]
    if not downbeat_kicks:
        return new_events

    # Reuse the first kick event verbatim to retain any metadata that may exist.
    new_events.append(downbeat_kicks[0])
    return new_events


def _merge_hat_tail(
    original: Sequence[GridEvent],
    new_events: List[GridEvent],
    subdivisions_per_bar: int,
) -> List[GridEvent]:
    tail_threshold = subdivisions_per_bar - 4
    hat_tail = [
        e
        for e in original
        if e.instrument_id.startswith("hihat") and e.subdivision_index >= tail_threshold
    ]
    if not hat_tail:
        return new_events

    new_events.extend(hat_tail)
    return new_events


def _families_from_fill_type(fill_type: Optional[str]) -> Optional[List[str]]:
    if not fill_type or fill_type == "auto":
        return None
    mapping = {
        "tom_run": ["tom_run", "linear"],
        "crash_buildup": ["hybrid"],
        "snare_rudiment": ["snare"],
        "hybrid": ["hybrid"],
        "linear": ["linear"],
    }
    return mapping.get(fill_type.lower())


def _build_rng(config: DrumGenerationConfig) -> random.Random:
    seed = None
    brain_config = getattr(config, "brainConfig", None)
    if brain_config and getattr(brain_config, "randomizeSeed", None) is not None:
        seed = int(brain_config.randomizeSeed)
    return random.Random(seed)


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, float(value)))
