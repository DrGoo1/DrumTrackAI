# backend/drum_generation/jamstix_attributes.py

from typing import List, Dict, Any
import math

"""
This module enriches your internal drum events with Jamstix-style attributes:
- limbId: "LH" | "RH" | "LF" | "RF"
- priority: 0..1 (importance)
- aspect: "groove" | "accent" | "fill"
- hitStyle: "single" | "double" | "bounce"
- hatOpenLevel: 0..1
- timingOffsetMs: per-note offset (optional)
"""

LIMBS_BY_INSTRUMENT = {
    "kick": "RF",
    "snare_center": "RH",
    "snare_rim": "RH",
    "snare_ghost": "RH",
    "hihat_closed": "LH",
    "hihat_open": "LH",
    "hihat_pedal": "LF",
    "ride_bow": "RH",
    "ride_bell": "RH",
    "ride_edge": "RH",
    "tom_high": "RH",
    "tom_mid": "RH",
    "tom_floor": "RH",
    "crash_1": "RH",
    "crash_2": "RH",
}

def assign_limb(instrument_id: str) -> str:
    return LIMBS_BY_INSTRUMENT.get(instrument_id, "other")


def compute_priority(ev: Dict[str, Any]) -> float:
    """
    Rough heuristic:
    - Backbeat snares and kicks on 1/3/2/4 are highest
    - Fills and crashes very high
    - Ghosts low
    - Hats mid
    Internal event expected keys:
      - instrument_id, isGhost, isAccent, isFill, bar_pos_frac
    """
    inst = ev["instrument_id"]
    base = 0.5

    if ev.get("isFill", False):
        base = 0.9
    elif inst.startswith("crash"):
        base = 0.85
    elif inst.startswith("snare") and ev.get("isAccent", False):
        base = 0.8
    elif inst == "kick":
        base = 0.7
    elif inst.startswith("hihat"):
        base = 0.6

    if ev.get("isGhost", False):
        base *= 0.4

    # Slightly bump if near strong beat
    frac = ev.get("bar_pos_frac", 0.0)
    if abs(frac - 0.0) < 1e-3 or abs(frac - 0.5) < 1e-3:
        base += 0.05

    return max(0.0, min(1.0, base))


def assign_aspect(ev: Dict[str, Any]) -> str:
    """
    Decide GROOVE vs ACCENT vs FILL.
    """
    if ev.get("isFill", False):
        return "fill"
    if ev.get("isAccent", False):
        return "accent"
    return "groove"


def assign_hit_style(ev: Dict[str, Any]) -> str:
    """
    Basic rule:
    - Ghost snares & fast rolls → "bounce"
    - Normal hits → "single"
    - Optionally "double" for some fill tom notes (not implemented deeply here)
    """
    inst = ev["instrument_id"]
    if ev.get("isGhost", False) and inst.startswith("snare"):
        return "bounce"
    if ev.get("isFill", False) and inst.startswith("tom"):
        return "double"
    return "single"


def assign_hat_open_level(ev: Dict[str, Any], global_openness: float = 0.0) -> float:
    """
    If this is a hat, set an openness level:
    - Use global_openness as base and maybe raise a bit on accents.
    """
    inst = ev["instrument_id"]
    if not inst.startswith("hihat"):
        return 0.0
    lvl = global_openness
    if ev.get("isAccent", False):
        lvl += 0.2
    return float(max(0.0, min(1.0, lvl)))


def compute_timing_offset_ms(ev: Dict[str, Any], laid_back_amount: float) -> float:
    """
    Use the global laid-back (or pushed) feel to adjust timing.
    - laid_back_amount: -1 (pushed) .. +1 (laid back)
    - We add a small offset around the beat
    """
    base_range = 10.0  # ms
    frac = ev.get("bar_pos_frac", 0.0)
    inst = ev["instrument_id"]

    # Only slightly move kicks; snare & hats more
    if inst == "kick":
        amt = 0.3
    elif inst.startswith("snare") or inst.startswith("hihat") or inst.startswith("ride"):
        amt = 1.0
    else:
        amt = 0.5

    # Negative laid_back_amount pushes earlier, positive delays later
    offset = base_range * laid_back_amount * amt
    # we can add some shaped randomness later if necessary
    return float(offset)


def enrich_internal_events_with_jamstix_attrs(
    internal_events: List[Dict[str, Any]],
    laid_back_amount: float,
    global_hat_openness: float,
    ride_bell_bias: float = 0.0,
    ride_velocity_bias: float = 0.0,
    ride_density_bias: float = 0.0,
    drum_config: Any = None,
) -> List[Dict[str, Any]]:
    """
    internal_events: list of dicts, each with at least:
      - time_sec
      - length_sec
      - instrument_id
      - midi_pitch
      - velocity
      - isGhost (bool)
      - isAccent (bool)
      - isFill (bool)
      - barIndex
      - barStartTime
      - barEndTime

        Returns the same list with extra keys:
      - limbId
      - priority
      - aspect
      - hitStyle
      - hatOpenLevel
      - timingOffsetMs
      - bar_pos_frac
        drum_config is accepted for API compatibility (unused currently).
    """
    for ev in internal_events:
        inst = ev["instrument_id"]
        bar_index = ev.get("barIndex", 0)
        bar_start = ev.get("barStartTime", 0.0)
        bar_end = ev.get("barEndTime", bar_start + 1.0)
        t_sec = ev["time_sec"]
        bar_len = max(bar_end - bar_start, 1e-6)
        frac = (t_sec - bar_start) / bar_len
        frac = max(0.0, min(0.999999, frac))

        ev["bar_pos_frac"] = frac
        ev["limbId"] = assign_limb(inst)
        ev["priority"] = compute_priority(ev)
        ev["aspect"] = assign_aspect(ev)
        ev["hitStyle"] = assign_hit_style(ev)
        ev["hatOpenLevel"] = assign_hat_open_level(ev, global_hat_openness)
        ev["timingOffsetMs"] = compute_timing_offset_ms(ev, laid_back_amount)

        # --- Ride-specific customization ---------------------------------
        if inst.startswith("ride"):
            # Density: nudge priority for ride hits
            if ride_density_bias != 0.0:
                scale = 1.0 + 0.5 * ride_density_bias
                ev["priority"] = max(0.0, min(1.0, ev["priority"] * scale))

            # Velocity: scale ride velocities
            if ride_velocity_bias != 0.0:
                vel_scale = 1.0 + ride_velocity_bias
                vel_scale = max(0.5, min(1.5, vel_scale))
                new_vel = int(round(ev["velocity"] * vel_scale))
                ev["velocity"] = max(1, min(127, new_vel))

            # Bow vs Bell: if bias > 0, favor bell on accents; if < 0, favor bow
            if ride_bell_bias != 0.0:
                if ride_bell_bias > 0:
                    if inst == "ride_bow" and ev.get("isAccent", False):
                        ev["instrument_id"] = "ride_bell"
                else:
                    if inst == "ride_bell" and not ev.get("isAccent", False):
                        ev["instrument_id"] = "ride_bow"

    return internal_events
