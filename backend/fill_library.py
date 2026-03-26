from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class FillPattern:
    # 16th-grid steps in a single 4/4 bar
    # instrument_id -> list of subdivision indices (0..15)
    steps: Dict[str, List[int]]


_BANG_STARTER: Dict[str, FillPattern] = {
    # These are pragmatic starter transcriptions (not perfect optical transcription).
    # They provide useful, musical fills that are associated with the lick ids.
    "Nasty-Lick-34": FillPattern(
        steps={
            "crash_1": [0],
            "kick": [0, 6, 10, 12],
            "snare_center": [2, 4, 6, 8, 10, 12, 14],
            "tom_high": [1, 3],
            "tom_mid": [9, 11],
            "tom_floor": [13, 15],
        }
    ),
    "Nasty-Lick-39": FillPattern(
        steps={
            "crash_1": [0],
            "kick": [0, 8, 12],
            "snare_center": [2, 4, 6, 10, 14],
            "tom_mid": [8, 9, 12, 13],
            "tom_floor": [15],
            "hihat_closed": [0, 4, 8, 12],
        }
    ),
    "Nasty-Lick-24": FillPattern(
        steps={
            "crash_1": [0],
            "kick": [0, 8],
            "snare_center": [1, 2, 4, 6, 8, 10, 12, 14],
            "tom_high": [3, 7, 11],
            "tom_floor": [15],
        }
    ),
}


def _rudiment_fill_from_id(rudiment_id: str) -> Optional[FillPattern]:
    rid = str(rudiment_id or "").strip().lower()
    if not rid:
        return None

    # Extract the stem after the prefix.
    stem = rid
    if stem.startswith("rudiment_midi:"):
        stem = stem.split(":", 1)[1]
    stem = stem.replace("-", "_").strip("_")

    # Basic family heuristics from the filename stem.
    # Use 16th grid by default; use a triplet-ish feel via denser 16ths for now.
    if "paradiddle" in stem:
        # RLRR LRLL as accents/ghosts across the bar
        return FillPattern(steps={"snare_center": [0, 2, 4, 6, 8, 10, 12, 14], "snare_ghost": [1, 3, 5, 7, 9, 11, 13, 15]})
    if "flam" in stem:
        # Flam feel: ghosted grace before accented hits
        return FillPattern(steps={"snare_ghost": [0, 4, 8, 12], "snare_center": [1, 5, 9, 13]})
    if "drag" in stem or "ruff" in stem:
        # Two soft notes into a main accent
        return FillPattern(steps={"snare_ghost": [0, 1, 4, 5, 8, 9, 12, 13], "snare_center": [2, 6, 10, 14]})
    if "roll" in stem:
        # Continuous 16ths on snare, accent downbeats
        return FillPattern(steps={"snare_center": [0, 4, 8, 12], "snare_ghost": [1, 2, 3, 5, 6, 7, 9, 10, 11, 13, 14, 15]})

    # Generic rudiment fill
    return FillPattern(steps={"snare_center": [0, 4, 8, 12], "snare_ghost": [2, 6, 10, 14]})


def _fallback_fill(seed: int) -> FillPattern:
    # Deterministic, musical 1-bar fill.
    if seed % 3 == 0:
        return FillPattern(
            steps={
                "crash_1": [0],
                "kick": [0, 8, 12],
                "snare_center": [4, 6, 10, 12, 14],
                "tom_mid": [9, 11],
                "tom_floor": [15],
            }
        )
    if seed % 3 == 1:
        return FillPattern(
            steps={
                "crash_1": [0],
                "kick": [0, 7, 8, 15],
                "snare_center": [4, 12],
                "tom_high": [10],
                "tom_mid": [11, 14],
                "tom_floor": [15],
            }
        )
    return FillPattern(
        steps={
            "crash_1": [0],
            "kick": [0, 8],
            "snare_center": [3, 7, 11, 15],
            "tom_mid": [12, 13, 14],
            "tom_floor": [15],
        }
    )


def get_fill_pattern(fill_groove_id: str | None) -> Tuple[FillPattern, str]:
    gid = str(fill_groove_id or "").strip()
    if gid in _BANG_STARTER:
        return _BANG_STARTER[gid], gid

    if gid.lower().startswith("rudiment_midi:"):
        rp = _rudiment_fill_from_id(gid)
        if rp:
            return rp, gid

    if gid.lower().startswith("egmd:"):
        # EGMD phrases are generally grooves; for fills we use a deterministic tom/snare fill.
        seed = sum(ord(c) for c in gid)
        return _fallback_fill(seed), gid

    if gid.lower().startswith("pattern:"):
        # drum_patterns entries vary; treat as a deterministic fill for now.
        seed = sum(ord(c) for c in gid) + 1337
        return _fallback_fill(seed), gid

    # If caller passes the full source id (e.g. bangthedrumschool entry id)
    # try a normalized match.
    normalized = gid.replace(".pdf", "").strip()
    if normalized in _BANG_STARTER:
        return _BANG_STARTER[normalized], normalized

    seed = sum(ord(c) for c in gid) if gid else 0
    return _fallback_fill(seed), "fallback"
