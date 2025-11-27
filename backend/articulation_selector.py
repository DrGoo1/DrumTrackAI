from typing import Dict, Any, Optional


def _get_strategy_for_instrument(performance_spec: Dict[str, Any], inst: str) -> Optional[Dict[str, Any]]:
    """Given the full performance_spec, find the articulationStrategy for a specific instrument.

    This mirrors the schema used by the LLM PerformanceSpec where:
    performance_spec = {
        "phrases": [
            {"profiles": [{"instrumentId": "hihat", "articulationStrategy": {...}}, ...]},
            ...
        ]
    }
    """
    for phrase in performance_spec.get("phrases", []):
        for prof in phrase.get("profiles", []):
            if prof.get("instrumentId") == inst:
                strat = prof.get("articulationStrategy")
                if strat:
                    return strat
    return None


def select_hat_articulation(note: Dict[str, Any], strat: Dict[str, Any], section_label: str) -> str:
    """Hi-hat articulation logic based on strategy + basic note context.

    Strategy keys (all optional):
      base: default articulationId (e.g. "hh_closed")
      accent: articulationId for accents
      maxOpen: articulationId for maximum openness
      openOn: list of section labels where openness is allowed
      neverOpenOn: list of section labels where hats must stay closed
    """
    art = strat.get("base", "hh_closed")

    if note.get("isAccent") and strat.get("accent"):
        art = strat["accent"]

    if section_label in strat.get("neverOpenOn", []):
        return "hh_closed"

    if section_label in strat.get("openOn", []):
        max_open = strat.get("maxOpen")
        if max_open:
            if int(note.get("velocity", 0)) > 90:
                art = max_open

    return art


def select_ride_articulation(note: Dict[str, Any], strat: Dict[str, Any], section_label: str) -> str:
    """Ride bow vs bell vs edge selection."""
    art = strat.get("base") or strat.get("rideMain") or "ride_bow_tip"

    if note.get("isAccent") and strat.get("accent"):
        art = strat["accent"]

    if section_label in strat.get("openOn", []) and strat.get("rideBellOn"):
        if note.get("isAccent"):
            art = "ride_bell"

    return art


def select_snare_articulation(note: Dict[str, Any], strat: Dict[str, Any]) -> str:
    """Snare ghosts, rimshots, sidestick selection."""
    if note.get("isGhost"):
        return "snare_ghost"

    if note.get("isAccent") and strat.get("accent"):
        return strat["accent"]

    return strat.get("base", "snare_center")


def select_articulation_for_note(
    note: Dict[str, Any],
    performance_spec: Dict[str, Any],
    section_label: str,
) -> str:
    """Main entry point – return an articulationId string for a logical drum note.

    The caller is expected to pass a lightweight logical note context, e.g.:
      note = {
        "instrumentId": "hihat" | "snare" | "ride" | ...,
        "velocity": int,
        "isGhost": bool,
        "isAccent": bool,
      }

    If no strategy is found, we fall back to simple instrument-based defaults.
    """
    inst = note.get("instrumentId") or ""
    if not inst:
        return "unknown"

    strat = _get_strategy_for_instrument(performance_spec, inst)
    if not strat:
        if inst.startswith("hihat"):
            return "hh_closed"
        if inst.startswith("ride"):
            return "ride_bow_tip"
        if inst.startswith("snare"):
            return "snare_center"
        if inst.startswith("tom"):
            return "tom_center"
        if inst.startswith("crash"):
            return "crash_normal"
        return "unknown"

    if inst.startswith("hihat"):
        return select_hat_articulation(note, strat, section_label)

    if inst.startswith("ride"):
        return select_ride_articulation(note, strat, section_label)

    if inst.startswith("snare"):
        return select_snare_articulation(note, strat)

    return strat.get("base", "unknown")
