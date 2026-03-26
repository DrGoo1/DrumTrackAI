from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple, Optional

import numpy as np

from groove_event_extractor import GrooveConfig, GrooveEvent


@dataclass
class GrooveNumericFeatures:
    """Container for numeric style features.

    Use .as_dict() to flatten for storage.
    """

    bpm: float
    time_sig_num: int
    time_sig_den: int
    subdivisions_per_beat: int
    bars: int

    backbeat_mean_offset_ms: float
    backbeat_std_offset_ms: float
    global_timing_std_ms: float
    hat_timing_std_ms: float
    swing_offbeat_mean_offset_ms: float
    swing_offbeat_ratio: float

    hits_per_bar: float
    kick_hits_per_bar: float
    snare_hits_per_bar: float
    hat_hits_per_bar: float
    cymbal_hits_per_bar: float
    ride_hits_per_bar: float
    ghost_snare_fraction: float

    velocity_mean: float
    velocity_std: float
    snare_velocity_mean: float
    snare_velocity_std: float
    hat_velocity_mean: float
    hat_velocity_std: float
    ride_velocity_mean: float
    ride_velocity_std: float

    hat_open_ratio: float
    ride_vs_hat_ratio: float
    ride_bell_ratio: float
    crash_per_bar: float

    complexity_index: float

    def as_dict(self) -> Dict[str, float]:
        return {
            "bpm": self.bpm,
            "time_sig_num": self.time_sig_num,
            "time_sig_den": self.time_sig_den,
            "subdivisions_per_beat": self.subdivisions_per_beat,
            "bars": self.bars,
            "backbeat_mean_offset_ms": self.backbeat_mean_offset_ms,
            "backbeat_std_offset_ms": self.backbeat_std_offset_ms,
            "global_timing_std_ms": self.global_timing_std_ms,
            "hat_timing_std_ms": self.hat_timing_std_ms,
            "swing_offbeat_mean_offset_ms": self.swing_offbeat_mean_offset_ms,
            "swing_offbeat_ratio": self.swing_offbeat_ratio,
            "hits_per_bar": self.hits_per_bar,
            "kick_hits_per_bar": self.kick_hits_per_bar,
            "snare_hits_per_bar": self.snare_hits_per_bar,
            "hat_hits_per_bar": self.hat_hits_per_bar,
            "cymbal_hits_per_bar": self.cymbal_hits_per_bar,
            "ghost_snare_fraction": self.ghost_snare_fraction,
            "velocity_mean": self.velocity_mean,
            "velocity_std": self.velocity_std,
            "snare_velocity_mean": self.snare_velocity_mean,
            "snare_velocity_std": self.snare_velocity_std,
            "hat_velocity_mean": self.hat_velocity_mean,
            "hat_velocity_std": self.hat_velocity_std,
            "ride_velocity_mean": self.ride_velocity_mean,
            "ride_velocity_std": self.ride_velocity_std,
            "hat_open_ratio": self.hat_open_ratio,
            "ride_vs_hat_ratio": self.ride_vs_hat_ratio,
            "ride_bell_ratio": self.ride_bell_ratio,
            "crash_per_bar": self.crash_per_bar,
            "complexity_index": self.complexity_index,
        }


class GrooveFeatureExtractor:
    """Compute numeric groove metrics and a text summary from GrooveEvents."""

    def __init__(self, config: GrooveConfig, ghost_velocity_threshold: int = 48) -> None:
        self.cfg = config
        self.ghost_velocity_threshold = ghost_velocity_threshold

    def analyze(self, events: List[GrooveEvent]) -> Tuple[Dict[str, float], Dict[str, Any]]:
        if not events:
            raise ValueError("No events provided to GrooveFeatureExtractor.analyze().")

        numeric = self._compute_numeric_features(events)
        summary = self._build_text_summary(numeric)
        return numeric.as_dict(), summary

    # --- numeric features -------------------------------------------------

    def _compute_numeric_features(self, events: List[GrooveEvent]) -> GrooveNumericFeatures:
        cfg = self.cfg
        bpm = cfg.bpm
        ts_num, ts_den = cfg.time_signature
        spb = cfg.subdivisions_per_beat

        max_bar = max(e.bar for e in events)
        bars = max_bar if max_bar > 0 else 1

        offsets = np.array([e.timing_offset_ms for e in events], dtype=float)
        global_timing_std_ms = float(np.std(offsets))

        def inst_filter(substrs: List[str]) -> List[GrooveEvent]:
            return [e for e in events if any(s in e.instrument for s in substrs)]

        snares = inst_filter(["snare"])
        kicks = inst_filter(["kick"])
        hats = inst_filter(["hat"])
        rides = inst_filter(["ride"])
        crashes = inst_filter(["crash"])
        cymbals = rides + crashes

        backbeats = self._select_backbeats(snares, ts_num)
        if backbeats:
            bb_offsets = np.array([e.timing_offset_ms for e in backbeats], dtype=float)
            backbeat_mean_offset_ms = float(np.mean(bb_offsets))
            backbeat_std_offset_ms = float(np.std(bb_offsets))
        else:
            backbeat_mean_offset_ms = 0.0
            backbeat_std_offset_ms = global_timing_std_ms

        if hats:
            hat_offsets = np.array([e.timing_offset_ms for e in hats], dtype=float)
            hat_timing_std_ms = float(np.std(hat_offsets))
        else:
            hat_timing_std_ms = global_timing_std_ms

        swing_offbeat_events, offbeat_ratio = self._select_offbeat_events(events)
        if swing_offbeat_events:
            swing_offsets = np.array([e.timing_offset_ms for e in swing_offbeat_events], dtype=float)
            swing_offbeat_mean_offset_ms = float(np.mean(swing_offsets))
        else:
            swing_offbeat_mean_offset_ms = 0.0

        swing_offbeat_ratio = float(offbeat_ratio)

        total_hits = len(events)
        hits_per_bar = total_hits / bars

        def hits_per_bar_for(inst_events: List[GrooveEvent]) -> float:
            return len(inst_events) / bars if bars > 0 else 0.0

        kick_hits_per_bar = hits_per_bar_for(kicks)
        snare_hits_per_bar = hits_per_bar_for(snares)
        hat_hits_per_bar = hits_per_bar_for(hats)
        cymbal_hits_per_bar = hits_per_bar_for(cymbals)
        ride_hits_per_bar = hits_per_bar_for(rides)
        crash_per_bar = hits_per_bar_for(crashes)

        ghost_snare_fraction = self._ghost_snare_fraction(snares)

        vel_all = np.array([e.velocity for e in events], dtype=float)
        velocity_mean = float(np.mean(vel_all))
        velocity_std = float(np.std(vel_all))

        def vel_stats(inst_events: List[GrooveEvent]) -> Tuple[float, float]:
            if not inst_events:
                return velocity_mean, velocity_std
            v = np.array([e.velocity for e in inst_events], dtype=float)
            return float(np.mean(v)), float(np.std(v))

        snare_velocity_mean, snare_velocity_std = vel_stats(snares)
        hat_velocity_mean, hat_velocity_std = vel_stats(hats)
        ride_velocity_mean, ride_velocity_std = vel_stats(rides)

        open_hats = [e for e in hats if "open" in e.instrument]
        closed_hats = [e for e in hats if "closed" in e.instrument]
        hat_open_ratio = len(open_hats) / len(hats) if hats else 0.0

        if hats or rides:
            ride_vs_hat_ratio = len(rides) / (len(hats) + len(rides))
        else:
            ride_vs_hat_ratio = 0.0

        # Ratio of ride bell vs all ride hits
        bell_rides = [e for e in rides if "bell" in e.instrument]
        ride_bell_ratio = len(bell_rides) / len(rides) if rides else 0.0

        density_norm = min(hits_per_bar / 24.0, 1.5)
        looseness_norm = min(global_timing_std_ms / 25.0, 1.5)
        complexity_index = float(0.6 * density_norm + 0.4 * looseness_norm)

        return GrooveNumericFeatures(
            bpm=bpm,
            time_sig_num=ts_num,
            time_sig_den=ts_den,
            subdivisions_per_beat=spb,
            bars=bars,
            backbeat_mean_offset_ms=backbeat_mean_offset_ms,
            backbeat_std_offset_ms=backbeat_std_offset_ms,
            global_timing_std_ms=global_timing_std_ms,
            hat_timing_std_ms=hat_timing_std_ms,
            swing_offbeat_mean_offset_ms=swing_offbeat_mean_offset_ms,
            swing_offbeat_ratio=swing_offbeat_ratio,
            hits_per_bar=hits_per_bar,
            kick_hits_per_bar=kick_hits_per_bar,
            snare_hits_per_bar=snare_hits_per_bar,
            hat_hits_per_bar=hat_hits_per_bar,
            cymbal_hits_per_bar=cymbal_hits_per_bar,
            ride_hits_per_bar=ride_hits_per_bar,
            ghost_snare_fraction=ghost_snare_fraction,
            velocity_mean=velocity_mean,
            velocity_std=velocity_std,
            snare_velocity_mean=snare_velocity_mean,
            snare_velocity_std=snare_velocity_std,
            hat_velocity_mean=hat_velocity_mean,
            hat_velocity_std=hat_velocity_std,
            ride_velocity_mean=ride_velocity_mean,
            ride_velocity_std=ride_velocity_std,
            hat_open_ratio=hat_open_ratio,
            ride_vs_hat_ratio=ride_vs_hat_ratio,
            ride_bell_ratio=ride_bell_ratio,
            crash_per_bar=crash_per_bar,
            complexity_index=complexity_index,
        )

    def _select_backbeats(self, snares: List[GrooveEvent], ts_num: int) -> List[GrooveEvent]:
        if not snares:
            return []
        if ts_num == 4:
            target_beats = {2, 4}
        elif ts_num == 3:
            target_beats = {2}
        else:
            mid = ts_num // 2
            target_beats = {mid} if mid > 1 else {2}
        return [e for e in snares if e.beat in target_beats]

    def _select_offbeat_events(self, events: List[GrooveEvent]) -> Tuple[List[GrooveEvent], float]:
        spb = self.cfg.subdivisions_per_beat
        if spb == 4:
            offbeat_subs = {2}
        elif spb == 3:
            offbeat_subs = {1}
        else:
            mid = spb // 2
            offbeat_subs = {mid}

        hats_or_snares = [e for e in events if ("hat" in e.instrument or "snare" in e.instrument)]
        if not hats_or_snares:
            return [], 0.0

        offbeat_events = [e for e in hats_or_snares if e.subdivision in offbeat_subs]
        offbeat_ratio = len(offbeat_events) / len(hats_or_snares)
        return offbeat_events, float(offbeat_ratio)

    def _ghost_snare_fraction(self, snares: List[GrooveEvent]) -> float:
        if not snares:
            return 0.0
        ghosts = [e for e in snares if e.velocity <= self.ghost_velocity_threshold]
        return len(ghosts) / len(snares)

    # --- text summary ------------------------------------------------------

    def _build_text_summary(self, numeric: GrooveNumericFeatures) -> Dict[str, Any]:
        n = numeric.as_dict()
        descriptors: List[str] = []

        descriptors.append(self._timing_description(numeric))
        hat_desc = self._hat_cymbal_description(numeric)
        if hat_desc:
            descriptors.append(hat_desc)
        ghost_desc = self._ghost_dynamic_description(numeric)
        if ghost_desc:
            descriptors.append(ghost_desc)
        descriptors.append(self._density_description(numeric))

        labels: List[str] = []
        if numeric.backbeat_mean_offset_ms > 8:
            labels.append("deep pocket, behind the beat")
        elif numeric.backbeat_mean_offset_ms < -8:
            labels.append("forward-leaning backbeat")
        else:
            labels.append("centered backbeat")

        if numeric.swing_offbeat_ratio > 0.4 and numeric.swing_offbeat_mean_offset_ms > 6:
            labels.append("shuffly / swung offbeats")
        elif numeric.swing_offbeat_ratio > 0.3:
            labels.append("lightly swung")
        else:
            labels.append("straight feel")

        if numeric.ghost_snare_fraction > 0.35:
            labels.append("ghost-heavy funk")
        elif numeric.ghost_snare_fraction > 0.15:
            labels.append("subtle ghost work")
        else:
            labels.append("minimal ghost notes")

        if numeric.complexity_index > 1.2:
            labels.append("dense, busy groove")
        elif numeric.complexity_index < 0.7:
            labels.append("spacious, minimal pattern")
        else:
            labels.append("moderate complexity")

        one_liner = ", ".join(labels)

        return {
            "one_liner": one_liner,
            "details": descriptors,
            "raw_features": n,
        }

    def _timing_description(self, numeric: GrooveNumericFeatures) -> str:
        bb = numeric.backbeat_mean_offset_ms
        std = numeric.global_timing_std_ms

        if bb > 8:
            pocket = "backbeat sits behind the grid"
        elif bb < -8:
            pocket = "backbeat leans ahead of the grid"
        else:
            pocket = "backbeat centers closely on the grid"

        if std < 8:
            tightness = "with very tight overall timing"
        elif std < 16:
            tightness = "with moderate looseness"
        else:
            tightness = "with a loose, human feel"

        swing = numeric.swing_offbeat_mean_offset_ms
        offbeat_ratio = numeric.swing_offbeat_ratio

        if offbeat_ratio > 0.4 and swing > 6:
            swing_desc = "Offbeat hats/snare suggest a clear shuffle or swing."
        elif offbeat_ratio > 0.3:
            swing_desc = "Offbeats are present but swing is subtle."
        else:
            swing_desc = "Pattern leans towards a straight subdivision feel."

        return f"Timing: {pocket} ({bb:+.1f} ms), {tightness}. {swing_desc}"

    def _hat_cymbal_description(self, numeric: GrooveNumericFeatures) -> Optional[str]:
        hat_hits = numeric.hat_hits_per_bar
        cym_hits = numeric.cymbal_hits_per_bar
        open_ratio = numeric.hat_open_ratio
        ride_ratio = numeric.ride_vs_hat_ratio
        crash_pb = numeric.crash_per_bar

        parts: List[str] = []

        if hat_hits > 0.1:
            if open_ratio > 0.4:
                parts.append("Hi-hats are often open, giving a washy texture.")
            elif open_ratio > 0.15:
                parts.append("Hi-hats mix closed strokes with occasional opens.")
            else:
                parts.append("Hi-hats are mostly tight and closed.")
        if cym_hits > 0.1:
            if ride_ratio > 0.6:
                parts.append("Ride cymbal is favored over hats.")
            elif ride_ratio < 0.3 and hat_hits > 0.1:
                parts.append("Hats lead the pattern, with ride used sparingly.")
        if crash_pb > 0.5:
            parts.append("Crashes are used frequently.")
        elif crash_pb > 0.1:
            parts.append("Crashes accent transitions.")
        else:
            parts.append("Crash usage is restrained.")

        if not parts:
            return None
        return "Cymbal behavior: " + " ".join(parts)

    def _ghost_dynamic_description(self, numeric: GrooveNumericFeatures) -> Optional[str]:
        ghost_frac = numeric.ghost_snare_fraction
        vel_std = numeric.velocity_std

        parts: List[str] = []
        if ghost_frac > 0.4:
            parts.append("Snare work is heavily ghosted, with many quiet inner strokes.")
        elif ghost_frac > 0.2:
            parts.append("Ghost notes add subtle inner detail to the snare pattern.")
        else:
            parts.append("Snare pattern uses few ghost notes.")

        if vel_std < 10:
            parts.append("Dynamics are fairly controlled and even.")
        elif vel_std < 20:
            parts.append("Dynamics show moderate variation.")
        else:
            parts.append("Dynamics are highly expressive with strong contrasts.")

        return "Dynamics & ghosts: " + " ".join(parts)

    def _density_description(self, numeric: GrooveNumericFeatures) -> str:
        hpbar = numeric.hits_per_bar
        kicks = numeric.kick_hits_per_bar
        snares = numeric.snare_hits_per_bar
        hats = numeric.hat_hits_per_bar

        if hpbar < 12:
            density = "sparse, leaving plenty of space."
        elif hpbar < 20:
            density = "medium-dense, balanced between space and activity."
        else:
            density = "dense, with many hits per bar."

        return (
            f"Density: approximately {hpbar:.1f} hits per bar "
            f"({kicks:.1f} kicks, {snares:.1f} snares, {hats:.1f} hats); "
            f"overall the groove feels {density}"
        )
