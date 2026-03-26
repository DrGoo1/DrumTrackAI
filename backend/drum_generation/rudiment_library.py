"""Rudiment pattern catalogue used by the fill planner.

The library keeps the definitions small and declarative so that new patterns
can be added (or sourced from Jamstix analysis) without touching the planner
logic itself. Patterns are expressed on a generic 16-step grid and scaled to
whatever subdivision resolution the SongDrumPlanner is using (currently 16th
notes).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .drum_generation_config import GridEvent


@dataclass(frozen=True)
class RudimentStroke:
    """Single hit inside a rudiment phrase."""

    step: int
    voice: str
    accent: bool = False
    ghost: bool = False
    flam: bool = False
    drag: bool = False


@dataclass(frozen=True)
class RudimentPattern:
    """Declarative definition of a Jamstix-style rudiment phrase."""

    rudiment_id: str
    label: str
    family: str
    length_subdivisions: int
    complexity: float
    sticking: str
    description: str
    strokes: List[RudimentStroke]
    default_surface_map: Dict[str, str]

    def materialize(
        self,
        *,
        bar_index: int,
        subdivisions_per_bar: int,
        surface_overrides: Optional[Dict[str, str]] = None,
        phrase_marker: str = "rudiment_fill",
    ) -> List[GridEvent]:
        """Expand the rudiment into concrete GridEvent entries."""

        if not self.strokes or subdivisions_per_bar <= 0:
            return []

        surfaces = dict(self.default_surface_map)
        if surface_overrides:
            surfaces.update(surface_overrides)

        # Avoid division-by-zero when a pattern is defined with a single step.
        denom = max(1, self.length_subdivisions - 1)
        scale = (subdivisions_per_bar - 1) / denom if subdivisions_per_bar > 1 else 0

        events: List[GridEvent] = []
        for stroke in self.strokes:
            # Scale the pattern step to the target subdivision resolution.
            target_step = int(round(stroke.step * scale)) if scale else 0
            target_step = max(0, min(subdivisions_per_bar - 1, target_step))
            instrument_id = surfaces.get(stroke.voice) or surfaces.get("snare") or "snare_center"

            events.append(
                GridEvent(
                    bar_index=bar_index,
                    subdivision_index=target_step,
                    subdivisions_per_bar=subdivisions_per_bar,
                    instrument_id=instrument_id,
                    is_accent=stroke.accent,
                    is_ghost=stroke.ghost,
                    is_flam=stroke.flam,
                    is_drag=stroke.drag,
                    bar_role="fill",
                    phrase_marker=phrase_marker,
                    rudiment_id=self.rudiment_id,
                )
            )

        return events


_DEFAULT_SURFACES: Dict[str, str] = {
    "snare": "snare_center",
    "snare_accent": "snare_rimshot",
    "snare_ghost": "snare_ghost",
    "tom1": "tom_mid_high",
    "tom2": "tom_mid_low",
    "floor": "tom_floor",
    "kick": "kick",
    "cymbal": "crash_medium",
    "stack": "stacker",
}


def _pattern(
    rudiment_id: str,
    label: str,
    family: str,
    complexity: float,
    sticking: str,
    description: str,
    strokes: List[RudimentStroke],
    *,
    length_subdivisions: int = 16,
    surface_overrides: Optional[Dict[str, str]] = None,
) -> RudimentPattern:
    surfaces = dict(_DEFAULT_SURFACES)
    if surface_overrides:
        surfaces.update(surface_overrides)
    return RudimentPattern(
        rudiment_id=rudiment_id,
        label=label,
        family=family,
        length_subdivisions=length_subdivisions,
        complexity=complexity,
        sticking=sticking,
        description=description,
        strokes=strokes,
        default_surface_map=surfaces,
    )


_RUDIMENT_LIBRARY: Dict[str, RudimentPattern] = {
    "paradiddle_migration": _pattern(
        "paradiddle_migration",
        label="Paradiddle Migration",
        family="snare",
        complexity=0.35,
        sticking="RLRR LRLL",
        description="Classic paradiddle that migrates to high toms on the last beat",
        strokes=[
            RudimentStroke(0, "snare_accent", accent=True),
            RudimentStroke(1, "snare"),
            RudimentStroke(2, "snare"),
            RudimentStroke(3, "snare"),
            RudimentStroke(4, "snare_accent", accent=True),
            RudimentStroke(5, "snare"),
            RudimentStroke(6, "snare"),
            RudimentStroke(7, "snare"),
            RudimentStroke(8, "snare_accent", accent=True),
            RudimentStroke(9, "snare"),
            RudimentStroke(10, "tom1"),
            RudimentStroke(11, "tom1"),
            RudimentStroke(12, "tom2", accent=True),
            RudimentStroke(13, "tom2"),
            RudimentStroke(14, "floor", accent=True),
            RudimentStroke(15, "floor"),
        ],
    ),
    "swiss_triplet_stack": _pattern(
        "swiss_triplet_stack",
        label="Swiss Triplet Stack",
        family="hybrid",
        complexity=0.55,
        sticking="RLL RRL",
        description="Swiss Army triplet that ends with a stack shot for extra bite",
        strokes=[
            RudimentStroke(0, "snare_accent", accent=True, flam=True),
            RudimentStroke(2, "snare"),
            RudimentStroke(3, "snare"),
            RudimentStroke(4, "snare"),
            RudimentStroke(6, "snare_accent", accent=True, flam=True),
            RudimentStroke(8, "snare"),
            RudimentStroke(9, "snare"),
            RudimentStroke(10, "tom1"),
            RudimentStroke(12, "stack", accent=True),
            RudimentStroke(14, "stack", accent=True),
        ],
    ),
    "flam_tap_cascade": _pattern(
        "flam_tap_cascade",
        label="Flam Tap Cascade",
        family="snare",
        complexity=0.65,
        sticking="R lR L rL",
        description="Alternating flam taps that tumble into the mid toms",
        strokes=[
            RudimentStroke(0, "snare_accent", accent=True, flam=True),
            RudimentStroke(1, "snare"),
            RudimentStroke(2, "snare"),
            RudimentStroke(3, "snare"),
            RudimentStroke(4, "snare_accent", accent=True, flam=True),
            RudimentStroke(5, "snare"),
            RudimentStroke(6, "tom1"),
            RudimentStroke(7, "tom1"),
            RudimentStroke(8, "tom2", accent=True),
            RudimentStroke(9, "tom2"),
            RudimentStroke(10, "floor", accent=True),
            RudimentStroke(11, "floor"),
            RudimentStroke(14, "cymbal", accent=True),
        ],
    ),
    "six_stroke_run": _pattern(
        "six_stroke_run",
        label="Six-Stroke Run",
        family="linear",
        complexity=0.75,
        sticking="RR LL RR",
        description="Six-stroke roll voiced across snare-to-floor for wide stereo motion",
        strokes=[
            RudimentStroke(0, "snare_accent", accent=True),
            RudimentStroke(1, "snare", ghost=True, drag=True),
            RudimentStroke(2, "snare", ghost=True, drag=True),
            RudimentStroke(4, "tom1", accent=True),
            RudimentStroke(5, "tom1"),
            RudimentStroke(6, "tom2", accent=True),
            RudimentStroke(7, "tom2"),
            RudimentStroke(8, "floor", accent=True),
            RudimentStroke(9, "floor"),
            RudimentStroke(12, "cymbal", accent=True),
            RudimentStroke(14, "cymbal", accent=True),
        ],
    ),
    "tom_run_exploder": _pattern(
        "tom_run_exploder",
        label="Tom Run Exploder",
        family="tom_run",
        complexity=0.9,
        sticking="R L R L triplet",
        description="Dense linear tom run that ends with a cymbal/kick unison",
        strokes=[
            RudimentStroke(0, "snare_accent", accent=True),
            RudimentStroke(1, "tom1"),
            RudimentStroke(2, "tom2"),
            RudimentStroke(3, "floor"),
            RudimentStroke(4, "tom1", accent=True),
            RudimentStroke(5, "tom2"),
            RudimentStroke(6, "floor"),
            RudimentStroke(7, "floor"),
            RudimentStroke(8, "tom1", accent=True),
            RudimentStroke(9, "tom2"),
            RudimentStroke(10, "floor", accent=True),
            RudimentStroke(11, "kick", accent=True),
            RudimentStroke(12, "cymbal", accent=True),
            RudimentStroke(14, "cymbal", accent=True),
        ],
    ),
}


def get_rudiment_catalogue() -> Dict[str, RudimentPattern]:
    """Return the entire rudiment dictionary."""

    return _RUDIMENT_LIBRARY


def get_rudiment(pattern_id: str) -> Optional[RudimentPattern]:
    """Convenience accessor for a single rudiment."""

    return _RUDIMENT_LIBRARY.get(pattern_id)


def list_rudiments() -> List[RudimentPattern]:
    """Return the patterns as a list (useful for UI serialization)."""

    return list(_RUDIMENT_LIBRARY.values())
