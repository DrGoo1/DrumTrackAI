"""Song Mode drum planner.

Expands high-level song sections (intro/verse/chorus/bridge/etc.) into a
bar-by-bar groove + fill plan, expressed as GridEvent objects.

This is a v1 implementation focused on 4/4 pop/rock. It is intentionally
simple but functional, and is kept separate from the existing pattern
layer so it can be integrated and iterated on safely.
"""

from __future__ import annotations

import logging
from typing import Any, List

from .drum_generation_config import (
    DrumGenerationConfig,
    GridEvent,
    SongSection,
    FillControls,
    FillFrequency,
)

logger = logging.getLogger(__name__)


def _canonical_section_name(raw: str) -> str:
    name = str(raw or "").strip().lower()
    if not name:
        return "verse"
    if "chorus" in name:
        return "chorus"
    if "pre" in name and "chorus" in name:
        return "pre"
    if "bridge" in name or "solo" in name or "break" in name:
        return "bridge"
    if "intro" in name:
        return "intro"
    if "outro" in name or "ending" in name or "end" == name:
        return "outro"
    if "verse" in name:
        return "verse"
    return "verse"


def _expand_sections_to_bar_labels(
    num_bars: int,
    song_sections: List[SongSection] | None,
) -> List[str]:
    """Return a list of section labels (one per bar).

    If song_sections is None or empty, we just label everything as the
    config.sectionId, but in Song Mode we expect a small list of
    SongSection entries.
    """

    labels: List[str] = []

    if not song_sections:
        labels = ["section"] * num_bars
        return labels[:num_bars]

    for sec in song_sections:
        bars = max(0, int(sec.bars))
        if bars <= 0:
            continue
        labels.extend([_canonical_section_name(sec.name)] * bars)
        if len(labels) >= num_bars:
            break

    # Pad or trim to exact length
    if len(labels) < num_bars:
        labels.extend([
            _canonical_section_name(song_sections[-1].name)
        ] * (num_bars - len(labels)))
    return labels[:num_bars]


def _compute_fill_bars(
    num_bars: int,
    fill_controls: FillControls | None,
) -> set[int]:
    """Determine which bar indices should be treated as fill bars.

    This is a simple v1 heuristic based on the configured FillFrequency
    and the explicit song sections. More sophisticated logic (e.g. energy
    curves, persona-specific tendencies) can be layered on later.
    """

    if not fill_controls:
        return set()

    freq: FillFrequency = getattr(fill_controls, "frequency", "section_transitions")
    freq = freq or "section_transitions"  # type: ignore[assignment]

    fill_bars: set[int] = set()

    if freq == "none":
        return fill_bars

    if freq in ("every_4_bars", "all_transitions"):
        for i in range(num_bars):
            # End of each 4-bar phrase (3, 7, 11, ... using 0-based indices)
            if (i + 1) % 4 == 0:
                fill_bars.add(i)

    # Note: section-transition-based fills will be added by the caller,
    # once section labels are known. This helper just handles the
    # frequency pattern.

    return fill_bars


def generate_song_grid_events(
    songmap: Any,
    config: DrumGenerationConfig,
) -> List[GridEvent]:
    """Generate a song-length grid of groove events for Song Mode.

    For v1, this assumes 4/4 and focuses on pop/rock semantics. It uses a
    straightforward mapping from sections and fillControls to bar-level
    groove choices.
    """

    bars = getattr(songmap, "bars", [])
    num_bars = len(bars)
    if num_bars <= 0:
        logger.warning("SongDrumPlanner: songmap has no bars; returning empty pattern")
        return []

    # Only support 4/4 in this initial implementation
    if tuple(config.timeSignature) != (4, 4):  # type: ignore[attr-defined]
        logger.info(
            "SongDrumPlanner: non-4/4 time signature %s not yet supported; falling back to simple pattern",
            config.timeSignature,
        )
        return []

    section_labels = _expand_sections_to_bar_labels(num_bars, config.songSections)
    fill_bars = _compute_fill_bars(num_bars, config.fillControls)

    # Apply explicit per-bar directives (absolute bar indices).
    try:
        forced = getattr(config, "forceFillBars", None) or []
        suppressed = getattr(config, "suppressFillBars", None) or []
        for bi in forced:
            try:
                b = int(bi)
            except Exception:
                continue
            if 0 <= b < num_bars:
                fill_bars.add(b)
        for bi in suppressed:
            try:
                b = int(bi)
            except Exception:
                continue
            if b in fill_bars:
                fill_bars.remove(b)
    except Exception:
        pass

    # Also mark the last bar of each section as a fill bar for
    # section_transitions / all_transitions.
    if config.fillControls and config.fillControls.frequency in {  # type: ignore[operator]
        "section_transitions",
        "all_transitions",
    }:
        offset = 0
        for sec in config.songSections or []:
            bars_in_sec = max(0, int(sec.bars))
            if bars_in_sec <= 0:
                continue
            last_bar = offset + bars_in_sec - 1
            if 0 <= last_bar < num_bars:
                fill_bars.add(last_bar)
            offset += bars_in_sec

    grid_events: List[GridEvent] = []
    subdivisions_per_bar = 16  # 16th-note grid

    def section_role(label: str) -> str:
        return _canonical_section_name(label)

    # Core v1 groove: basic rock beat with slight variations by role and fills
    for bar_idx in range(num_bars):
        label = section_labels[bar_idx]
        role = section_role(label)
        is_fill_bar = bar_idx in fill_bars
        bar_role = "fill" if is_fill_bar else "groove"

        # Kick + snare pattern indices for 4/4 on 16th-note grid
        # Beats: 1 = 0, 2 = 4, 3 = 8, 4 = 12
        kick_positions = [0, 8]
        snare_positions = [4, 12]

        # In chorus, add a few more kicks for energy
        if role == "chorus":
            kick_positions = [0, 8, 10]

        # In bridge/outro, slightly busier snare back-half
        if role in {"bridge", "outro"}:
            snare_positions = [4, 12, 14]

        # Hi-hat / cymbal choice: keep it simple for v1; ride bias can be
        # expressed later via articulation / Jamstix enrichment.
        hat_instrument = "hihat_closed"
        if role == "chorus":
            # Still use closed hats in grid; Jamstix + chorusRidePreference
            # can promote these to ride/crashes later.
            hat_instrument = "hihat_closed"

        # --- Kick ---
        for step in kick_positions:
            grid_events.append(
                GridEvent(
                    bar_index=bar_idx,
                    subdivision_index=step,
                    subdivisions_per_bar=subdivisions_per_bar,
                    instrument_id="kick",
                    is_accent=(step == 0),
                    bar_role=bar_role,
                )
            )

        # --- Snare ---
        for step in snare_positions:
            grid_events.append(
                GridEvent(
                    bar_index=bar_idx,
                    subdivision_index=step,
                    subdivisions_per_bar=subdivisions_per_bar,
                    instrument_id="snare_center",
                    is_accent=True,
                    bar_role=bar_role,
                )
            )

        # --- Hi-hats / basic cymbal pattern ---
        for step in range(0, subdivisions_per_bar, 2):  # 8th-note grid
            # On fill bars, push hats slightly at the end of the bar
            is_tail = is_fill_bar and step >= subdivisions_per_bar - 4
            grid_events.append(
                GridEvent(
                    bar_index=bar_idx,
                    subdivision_index=step,
                    subdivisions_per_bar=subdivisions_per_bar,
                    instrument_id=hat_instrument,
                    is_accent=(step % 4 == 0) or is_tail,
                    is_ghost=(step % 4 != 0 and not is_tail),
                    bar_role=bar_role,
                    phrase_marker="fill_tail" if is_tail else None,
                )
            )

        # --- Simple fill embellishments on fill bars ---
        if is_fill_bar:
            # Add a few extra snare hits in the last half of the bar
            for step in [10, 11, 13, 15]:
                grid_events.append(
                    GridEvent(
                        bar_index=bar_idx,
                        subdivision_index=step,
                        subdivisions_per_bar=subdivisions_per_bar,
                        instrument_id="snare_center",
                        is_accent=True,
                        bar_role="fill",
                        phrase_marker="fill_stub",
                    )
                )

    logger.info("SongDrumPlanner: generated %d grid events for %d bars", len(grid_events), num_bars)
    return grid_events
