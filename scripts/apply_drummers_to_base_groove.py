#!/usr/bin/env python
"""Generate DCSM drum tracks for assimilated drummers using a base groove."""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import random
import sys
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from admin.services.central_database_service import CentralDatabaseService
from backend.jamstix_brain.dcsm_drumtrack_builder import DCSMDrumTrackBuilder


DEFAULT_DRUMMER_ADJUSTMENTS: Dict[str, Dict[str, Any]] = {
    "john_bonham": {
        "timing_scale": 1.0,
        "velocity_std_scale": 1.0,
        "fill_factor": 1.0,
        "snare_share_scale": 1.45,
        "cymbal_share_scale": 0.8,
        "ride_share_scale": 0.75,
        "tom_share_scale": 0.7,
        "kick_share_scale": 0.85,
        "hihat_share_scale": 0.85,
        "hihat_share_floor": 0.22,
        "rebalance_priority": ["snare", "hihat", "ride", "cymbal", "tom"],
        "excess_reassign": {"ride": "hihat_closed", "cymbal": "snare_ghost", "tom": "snare_center"},
        "fill_velocity_scale": 0.85,
        "fill_source_categories": ["hihat", "snare", "ride", "tom", "cymbal"],
        "fill_category_priority": ["snare", "tom", "cymbal", "ride", "hihat", "kick"],
        "fill_source_priority": ["snare", "hihat", "ride", "cymbal", "tom"],
        "max_fills_per_bar_scale": 1.3,
        "donor_priority": ["ride", "cymbal", "tom", "kick", "hihat"],
        "overflow_reassign_priority": ["snare", "hihat", "cymbal", "ride"],
        "max_share_scale": {"kick": 1.05, "tom": 1.4, "ride": 1.25, "cymbal": 1.3, "hihat": 0.95},
        "fill_factor": 1.1,
        "fill_fpm_cap": 5.5,
    },
    "ringo_starr": {
        "timing_scale": 1.2,
        "velocity_std_scale": 0.95,
        "fill_factor": 0.8,
        "snare_share_scale": 1.5,
        "cymbal_share_scale": 0.75,
        "ride_share_scale": 0.8,
        "tom_share_scale": 0.65,
        "kick_share_scale": 0.82,
        "hihat_share_scale": 0.88,
        "hihat_share_floor": 0.26,
        "rebalance_priority": ["snare", "hihat", "ride", "cymbal", "tom"],
        "excess_reassign": {"ride": "hihat_closed", "cymbal": "snare_ghost", "tom": "snare_center"},
        "fill_velocity_scale": 0.8,
        "fill_source_categories": ["hihat", "snare", "ride", "cymbal"],
        "fill_category_priority": ["snare", "ride", "cymbal", "tom", "hihat"],
        "fill_source_priority": ["snare", "hihat", "ride", "cymbal"],
        "max_fills_per_bar_scale": 1.15,
        "donor_priority": ["cymbal", "ride", "tom", "kick", "percussion"],
        "overflow_reassign_priority": ["snare", "ride", "cymbal", "tom", "kick"],
        "max_share_scale": {"hihat": 0.95, "kick": 0.95, "ride": 1.05},
        "fill_fpm_cap": 0.95,
    },
    "clyde_stubblefield": {
        "timing_scale": 0.9,
        "velocity_std_scale": 1.1,
        "fill_factor": 0.25,
        "snare_share_scale": 1.9,
        "cymbal_share_scale": 0.52,
        "ride_share_scale": 0.58,
        "tom_share_scale": 0.6,
        "kick_share_scale": 0.48,
        "hihat_share_scale": 0.82,
        "hihat_share_floor": 0.2,
        "rebalance_priority": ["snare", "hihat", "tom", "cymbal", "ride"],
        "excess_reassign": {"kick": "snare_ghost", "ride": "hihat_closed", "cymbal": "snare_center", "tom": "snare_center"},
        "fill_velocity_scale": 0.85,
        "fill_source_categories": ["snare", "hihat", "ride", "cymbal"],
        "fill_category_priority": ["snare", "cymbal", "ride", "tom", "hihat"],
        "fill_source_priority": ["snare", "ride", "cymbal", "hihat"],
        "max_fills_per_bar_scale": 1.1,
        "donor_priority": ["hihat", "cymbal", "ride", "tom", "percussion", "kick"],
        "overflow_reassign_priority": ["snare", "ride", "cymbal", "tom"],
        "max_share_scale": {"snare": 1.35, "kick": 0.8, "tom": 1.05, "cymbal": 0.9, "hihat": 0.75},
        "fill_fpm_cap": 1.2,
    },
}

ADJUSTMENT_METADATA: Dict[str, Any] = {}
DRUMMER_ADJUSTMENTS: Dict[str, Dict[str, Any]] = deepcopy(DEFAULT_DRUMMER_ADJUSTMENTS)


def _deep_update(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def _load_adjustment_overrides(config_path: Optional[Path]) -> Dict[str, Any]:
    global ADJUSTMENT_METADATA

    path: Optional[Path] = config_path
    if path is None:
        env = os.getenv("DCSM_ADJUSTMENTS_CONFIG") or os.getenv("DRUMTRACKAI_ADJUSTMENTS_CONFIG")
        if env:
            try:
                path = Path(env).expanduser().resolve()
            except Exception:
                path = None
        if path is None:
            default_path = PROJECT_ROOT / "config" / "drummer_adjustments.json"
            if default_path.exists():
                path = default_path
    if path is None:
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:
        print(f"⚠️  Failed to load drummer adjustments from {path}: {exc}", file=sys.stderr)
        return {}

    overrides: Dict[str, Any] = {}
    if isinstance(payload, dict):
        meta = payload.get("metadata")
        if isinstance(meta, dict):
            ADJUSTMENT_METADATA = meta
        if isinstance(payload.get("drummers"), dict):
            overrides = payload["drummers"]
        else:
            overrides = {k: v for k, v in payload.items() if isinstance(v, dict)}
    return overrides


def _apply_adjustment_overrides(overrides: Dict[str, Any]) -> None:
    global DRUMMER_ADJUSTMENTS

    if not overrides:
        return

    merged: Dict[str, Dict[str, Any]] = {}
    for slug, values in overrides.items():
        if not isinstance(values, dict):
            continue
        base = DRUMMER_ADJUSTMENTS.get(slug)
        if base is None:
            base = {}
        merged[slug] = _deep_update(deepcopy(base), values)

    DRUMMER_ADJUSTMENTS.update(merged)


CATEGORY_TO_INSTRUMENTS: Dict[str, List[str]] = {
    "ride": ["ride_bow", "ride_bell"],
    "cymbal": ["crash_1", "crash_2", "splash"],
    "tom": ["tom_high", "tom_mid", "tom_low", "tom_floor"],
    "percussion": ["cowbell", "shaker"],
    "snare": ["snare_center", "snare_rim", "snare_ghost"],
    "hihat": ["hihat_open", "hihat_closed"],
    "kick": ["kick"],
}

FILL_CATEGORY_PRIORITY: List[str] = ["tom", "snare", "cymbal", "ride", "hihat", "kick"]


@dataclass
class PatternAsset:
    tempo_bpm: float
    time_signature: str
    ppqn: int
    events: List[Dict[str, Any]]


def load_base_pattern(path: Path) -> PatternAsset:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return PatternAsset(
        tempo_bpm=float(payload.get("tempo_bpm", 110)),
        time_signature=str(payload.get("time_signature", "4/4")),
        ppqn=int(payload.get("ppqn", 960)),
        events=list(payload.get("pattern_events", [])),
    )


def repeat_events(events: Sequence[Dict[str, Any]], repeats: int) -> List[Dict[str, Any]]:
    if repeats <= 1:
        return [dict(ev) for ev in events]

    bars = sorted({int(ev.get("barIndex", 0)) for ev in events})
    bar_count = len(bars)
    min_start = min(float(ev.get("barStartTime", 0.0)) for ev in events)
    max_end = max(float(ev.get("barEndTime", 0.0)) for ev in events)
    base_duration = max(0.0, max_end - min_start)

    out: List[Dict[str, Any]] = []
    for r in range(repeats):
        bar_shift = r * bar_count
        time_shift = r * base_duration
        for ev in events:
            new_ev = dict(ev)
            new_ev["barIndex"] = int(ev.get("barIndex", 0)) + bar_shift
            new_ev["barStartTime"] = float(ev.get("barStartTime", 0.0)) + time_shift
            new_ev["barEndTime"] = float(ev.get("barEndTime", 0.0)) + time_shift
            new_ev["time_sec"] = float(ev.get("time_sec", 0.0)) + time_shift
            out.append(new_ev)
    return out


def build_sections(total_bars: int) -> List[Dict[str, Any]]:
    if total_bars <= 0:
        return []
    midpoint = max(1, total_bars // 2)
    sections = [
        {"type": "verse", "startBar": 0, "endBar": midpoint},
        {"type": "chorus", "startBar": midpoint, "endBar": total_bars},
    ]
    return [s for s in sections if s["startBar"] < s["endBar"]]


def fetch_rollup(service: CentralDatabaseService, drummer_slug: str) -> Dict[str, Any]:
    conn = service._get_connection()  # pylint: disable=protected-access
    cur = conn.cursor()
    drummer_fk = service._get_drummer_fk_by_slug(cursor=cur, drummer_slug=drummer_slug)  # pylint: disable=protected-access
    if drummer_fk is None:
        raise ValueError(f"Unknown drummer slug: {drummer_slug}")
    rollup = service.compute_drummer_profile_rollup(drummer_fk=int(drummer_fk))
    if not rollup:
        raise RuntimeError(f"No assimilation rollup found for drummer '{drummer_slug}'")
    return rollup


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _normalize_fill_rate(raw_value: Any) -> float | None:
    if raw_value is None:
        return None
    try:
        val = float(raw_value)
    except (TypeError, ValueError):  # pragma: no cover - defensive casting
        return None
    if val <= 0:
        return 0.0
    # Assimilation rollups occasionally store exaggerated values (e.g., per hour).
    # Treat anything above a realistic drummer ceiling (~12 fills/min) as hourly data.
    if val > 12.0:
        val /= 60.0
    return val


def _completion_status(within: int, total: int) -> Dict[str, Any]:
    if total <= 0:
        return {"status": "unknown", "completion_ratio": None}
    ratio = within / float(total)
    if ratio >= 0.8:
        status = "ready"
    elif ratio >= 0.6:
        status = "refine"
    else:
        status = "needs_tuning"
    return {"status": status, "completion_ratio": ratio}


def map_rollup_to_spec(rollup: Dict[str, Any]) -> Dict[str, Any]:
    pocket = float(rollup.get("pocket_tightness") or 0.24)
    timing_std = float(rollup.get("timing_std_ms") or 35.0)
    humanness = float(rollup.get("humanness") or 0.4)
    velocity_mean = float(rollup.get("velocity_mean") or 95.0)
    velocity_std = float(rollup.get("velocity_std") or 18.0)
    fills_per_min = _normalize_fill_rate(rollup.get("fills_per_min"))
    fills_per_min = float(fills_per_min or 0.4)
    shares_raw = rollup.get("instrument_shares") or {}
    if isinstance(shares_raw, str):
        try:
            shares = json.loads(shares_raw)
        except Exception:  # pragma: no cover
            shares = {}
    else:
        shares = shares_raw

    hat_share = float(shares.get("hihat") or shares.get("hihat_closed") or shares.get("hihat_open") or 0.0)
    ride_share = float(shares.get("ride") or shares.get("ride_bow") or shares.get("ride_edge") or 0.0)
    tom_share = float(
        shares.get("tom")
        or shares.get("tom_low")
        or shares.get("tom_mid")
        or shares.get("tom_high")
        or 0.0
    )
    snare_share = float(shares.get("snare") or shares.get("snare_center") or shares.get("snare_rim") or 0.0)

    feel = "on_the_beat" if pocket >= 0.26 else ("pocket" if pocket >= 0.23 else "laid_back")
    swing = _clamp(timing_std / 120.0, 0.0, 0.55)
    intensity = _clamp(velocity_mean / 120.0, 0.2, 1.0)
    hat_open = _clamp(0.1 + hat_share * 0.9, 0.1, 0.85)
    ghost_amount = _clamp(0.3 + humanness * 0.5 + (velocity_std / 90.0), 0.1, 0.95)

    if tom_share >= 0.08:
        fill_style = "tom_run"
    elif snare_share >= hat_share:
        fill_style = "snare_buzz"
    else:
        fill_style = "mixed"
    fill_density = _clamp(fills_per_min / 2.0, 0.05, 0.9)
    accent = "ride_emphasis" if ride_share > hat_share else ("syncopated" if ghost_amount > 0.6 else "2_and_4")

    return {
        "feel": feel,
        "swing": swing,
        "intensity": intensity,
        "hatOpenness": hat_open,
        "ghostNoteAmount": ghost_amount,
        "fillStyle": fill_style,
        "fillDensity": fill_density,
        "accentPattern": accent,
    }


def _instrument_category(instrument: str) -> str:
    if not instrument:
        return "other"
    inst = instrument.lower()
    if "kick" in inst or "bd" in inst:
        return "kick"
    if "snare" in inst or "rim" in inst:
        return "snare"
    if "hat" in inst:
        return "hihat"
    if "ride" in inst:
        return "ride"
    if "tom" in inst:
        return "tom"
    if any(cym in inst for cym in ("crash", "splash", "china")):
        return "cymbal"
    if any(perc in inst for perc in ("perc", "clave", "cowbell", "shaker")):
        return "percussion"
    return "other"


def _rollup_instrument_category(key: str) -> str:
    if not key:
        return "other"
    k = key.lower()
    if "hihat" in k or "hat" in k:
        return "hihat"
    if "snare" in k:
        return "snare"
    if "kick" in k or "bass" in k and "drum" in k:
        return "kick"
    if "ride" in k:
        return "ride"
    if "tom" in k:
        return "tom"
    if "crash" in k or "china" in k or "splash" in k:
        return "cymbal"
    if "cymbal" in k:
        return "cymbal"
    if "percussion" in k or "shaker" in k or "cowbell" in k:
        return "percussion"
    return "other"


def _expected_category_shares(shares: Dict[str, Any]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for inst_key, share in (shares or {}).items():
        try:
            val = float(share)
        except (TypeError, ValueError):
            continue
        category = _rollup_instrument_category(inst_key)
        if category == "other":
            continue
        out[category] = out.get(category, 0.0) + val
    total = sum(out.values())
    if total <= 0:
        return {}
    return {cat: val / total for cat, val in out.items()}


def _adjust_target_shares(shares: Dict[str, float], adjustments: Dict[str, Any]) -> Dict[str, float]:
    if not shares:
        return {}

    adjusted = dict(shares)
    scale_map = {
        "snare": adjustments.get("snare_share_scale"),
        "cymbal": adjustments.get("cymbal_share_scale"),
        "ride": adjustments.get("ride_share_scale"),
        "tom": adjustments.get("tom_share_scale"),
        "kick": adjustments.get("kick_share_scale"),
        "hihat": adjustments.get("hihat_share_scale"),
    }
    for cat, scale in scale_map.items():
        if scale is None or scale == 1.0:
            continue
        if cat in adjusted:
            adjusted[cat] = max(0.0, adjusted[cat] * scale)
        elif scale > 1.0:
            adjusted[cat] = (scale - 1.0) * 0.05

    hihat_floor = adjustments.get("hihat_share_floor")
    if hihat_floor is not None:
        adjusted["hihat"] = max(adjusted.get("hihat", 0.0), float(hihat_floor))

    total = sum(adjusted.values())
    if total <= 0:
        return adjusted
    return {cat: val / total for cat, val in adjusted.items() if val > 0}


def compute_track_metrics(track_dict: Dict[str, Any]) -> Dict[str, Any]:
    bars = track_dict.get("bars", [])
    notes: List[Dict[str, Any]] = []
    for bar in bars:
        notes.extend(bar.get("notes", []))

    total_notes = len(notes)
    velocities = [int(note.get("velocity", 0)) for note in notes]
    micro_timing = [float(note.get("microTimingMs", 0.0)) for note in notes]
    aspects = [note.get("aspect", "groove") for note in notes]

    instrument_counts: Dict[str, int] = {}
    category_counts: Dict[str, int] = {}
    for note in notes:
        inst = note.get("instrument", "unknown")
        instrument_counts[inst] = instrument_counts.get(inst, 0) + 1
        cat = _instrument_category(inst)
        category_counts[cat] = category_counts.get(cat, 0) + 1

    instrument_shares = {k: v / total_notes for k, v in instrument_counts.items()} if total_notes else {}
    category_shares = {k: v / total_notes for k, v in category_counts.items()} if total_notes else {}

    ghost_notes = sum(1 for aspect in aspects if aspect == "ghost")
    fill_notes = sum(1 for aspect in aspects if aspect == "fill")

    velocity_mean_raw = statistics.mean(velocities) if velocities else 0.0
    velocity_std_raw = statistics.pstdev(velocities) if len(velocities) > 1 else 0.0
    velocity_mean = velocity_mean_raw / 127.0
    velocity_std = velocity_std_raw / 127.0
    micro_timing_std = statistics.pstdev(micro_timing) if len(micro_timing) > 1 else 0.0

    total_duration = 0.0
    if bars:
        start_time = min(bar.get("startTime", 0.0) for bar in bars)
        end_time = max(bar.get("endTime", start_time) for bar in bars)
        total_duration = max(0.0, end_time - start_time)
    total_minutes = total_duration / 60.0 if total_duration > 0 else None
    fills_per_minute = (fill_notes / total_minutes) if (total_minutes and total_minutes > 0) else None

    return {
        "note_count": total_notes,
        "velocity_mean": velocity_mean,
        "velocity_std": velocity_std,
        "velocity_mean_raw": velocity_mean_raw,
        "velocity_std_raw": velocity_std_raw,
        "micro_timing_std": micro_timing_std,
        "ghost_ratio": ghost_notes / total_notes if total_notes else 0.0,
        "fill_ratio": fill_notes / total_notes if total_notes else 0.0,
        "fills_per_minute": fills_per_minute,
        "instrument_counts": instrument_counts,
        "instrument_shares": instrument_shares,
        "instrument_category_shares": category_shares,
    }


def compare_metrics_to_rollup(
    rollup: Dict[str, Any],
    metrics: Dict[str, Any],
    tolerance: float = 0.1,
) -> Dict[str, Any]:
    comparisons: List[Dict[str, Any]] = []

    def record(metric: str, actual: float | None, expected: float | None) -> None:
        if expected is None or actual is None:
            return
        pct_diff = None
        within = False
        if expected != 0:
            pct_diff = (actual - expected) / expected
            within = abs(pct_diff) <= tolerance
        else:
            within = abs(actual - expected) <= tolerance
        comparisons.append(
            {
                "metric": metric,
                "actual": actual,
                "expected": expected,
                "pct_diff": pct_diff,
                "within_tolerance": within,
            }
        )

    record("velocity_mean", metrics.get("velocity_mean"), rollup.get("velocity_mean"))
    record("velocity_std", metrics.get("velocity_std"), rollup.get("velocity_std"))
    record("micro_timing_std", metrics.get("micro_timing_std"), rollup.get("timing_std_ms"))
    record("ghost_ratio", metrics.get("ghost_ratio"), rollup.get("ghost_ratio"))
    record("fill_ratio", metrics.get("fill_ratio"), rollup.get("fill_ratio"))
    expected_fpm = _normalize_fill_rate(rollup.get("fills_per_min"))
    record("fills_per_minute", metrics.get("fills_per_minute"), expected_fpm)

    rollup_category_shares = _expected_category_shares(rollup.get("instrument_shares") or {})
    actual_category_shares = metrics.get("instrument_category_shares") or {}
    for category, expected_share in rollup_category_shares.items():
        actual_share = actual_category_shares.get(category)
        record(f"instrument_category_share:{category}", actual_share, expected_share)

    within_count = sum(1 for item in comparisons if item["within_tolerance"])
    total_count = len(comparisons)

    return {
        "comparisons": comparisons,
        "within_tolerance_count": within_count,
        "total_compared": total_count,
        "tolerance": tolerance,
    }


def _clone_events(events: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [dict(ev) for ev in events]


def _retarget_velocities(events: List[Dict[str, Any]], target_mean: float, target_std: float, rng: random.Random) -> None:
    if not events:
        return
    velocities = [float(ev.get("velocity", 80)) for ev in events]
    cur_mean = statistics.mean(velocities)
    cur_std = statistics.pstdev(velocities) if len(velocities) > 1 else 0.0
    for ev, vel in zip(events, velocities):
        if cur_std > 1e-6:
            z = (vel - cur_mean) / cur_std
        else:
            z = rng.uniform(-0.5, 0.5)
        new_vel = target_mean + z * target_std
        jitter = rng.gauss(0.0, target_std * 0.05 if target_std else 0.0)
        new_vel = _clamp(new_vel + jitter, 1.0, 127.0)
        ev["velocity"] = int(round(new_vel))


def _rescale_velocities_to_target(events: List[Dict[str, Any]], target_mean: float, target_std: float) -> None:
    if not events:
        return
    velocities = [float(ev.get("velocity", 0)) for ev in events]
    if not velocities:
        return
    current_mean = statistics.mean(velocities)
    current_std = statistics.pstdev(velocities) if len(velocities) > 1 else 0.0
    scale = (target_std / current_std) if current_std > 1e-6 and target_std > 0 else 0.0
    for ev in events:
        vel = float(ev.get("velocity", 0))
        adjusted = target_mean + (vel - current_mean) * scale if scale > 0 else target_mean
        ev["velocity"] = int(round(_clamp(adjusted, 1.0, 127.0)))

    new_vels = [float(ev.get("velocity", 0)) for ev in events]
    final_mean = statistics.mean(new_vels) if new_vels else 0.0
    mean_delta = target_mean - final_mean
    if abs(mean_delta) > 0.5:
        for ev in events:
            ev["velocity"] = int(round(_clamp(float(ev.get("velocity", 0)) + mean_delta, 1.0, 127.0)))


def _apply_microtiming(events: List[Dict[str, Any]], target_std_ms: float, rng: random.Random) -> None:
    if target_std_ms <= 0:
        return
    for ev in events:
        base_offset = float(ev.get("timing_offset_ms") or 0.0)
        ev["timing_offset_ms"] = base_offset + rng.gauss(0.0, target_std_ms)


def _set_event_instrument(event: Dict[str, Any], instrument_id: str) -> None:
    event["instrument_id"] = instrument_id
    event["instrument"] = instrument_id


def _choose_instrument_for_category(
    category: str,
    adjustments: Dict[str, Any],
    rng: random.Random,
) -> str:
    options = CATEGORY_TO_INSTRUMENTS.get(category)
    if not options:
        return "hihat_closed"
    if category == "snare":
        weighted = [
            "snare_center",
            "snare_center",
            "snare_center",
            "snare_ghost",
            "snare_ghost",
            "snare_rim",
        ]
        return rng.choice(weighted)
    if category == "ride":
        return "ride_bow"
    if category == "cymbal":
        weighted = ["crash_1", "crash_1", "crash_2", "splash"]
        return rng.choice(weighted)
    if category == "tom":
        weighted = ["tom_low", "tom_mid", "tom_high", "tom_floor", "tom_low", "tom_mid"]
        return rng.choice(weighted)
    if category == "kick":
        return "kick"
    return rng.choice(options)


def _assign_index_to_category(
    events: List[Dict[str, Any]],
    idx: int,
    category_or_instrument: str,
    adjustments: Dict[str, Any],
    rng: random.Random,
) -> str:
    if category_or_instrument in CATEGORY_TO_INSTRUMENTS:
        new_inst = _choose_instrument_for_category(category_or_instrument, adjustments, rng)
        new_category = category_or_instrument
    else:
        new_inst = category_or_instrument
        new_category = _instrument_category(new_inst)
    _set_event_instrument(events[idx], new_inst)
    return new_category


def _rebalance_instrument_categories(
    events: List[Dict[str, Any]],
    target_shares: Dict[str, float],
    adjustments: Dict[str, Any],
    rng: random.Random,
) -> None:
    if not events:
        return

    desired_shares = _adjust_target_shares(target_shares, adjustments)
    if not desired_shares:
        return

    total = len(events)
    counts = Counter(_instrument_category(ev.get("instrument_id", "")) for ev in events)
    category_indices: Dict[str, List[int]] = {}
    for idx, ev in enumerate(events):
        cat = _instrument_category(ev.get("instrument_id", ""))
        category_indices.setdefault(cat, []).append(idx)
    snare_times: Set[tuple[int, float]] = set()
    for ev in events:
        if _instrument_category(ev.get("instrument_id", "")) == "snare":
            key = (int(ev.get("barIndex", 0)), round(float(ev.get("time_sec", 0.0)), 4))
            snare_times.add(key)

    hat_slots_free: List[int] = []
    hat_slots_with_snare: List[int] = []
    for idx in category_indices.get("hihat", []):
        ev = events[idx]
        key = (int(ev.get("barIndex", 0)), round(float(ev.get("time_sec", 0.0)), 4))
        if key in snare_times:
            hat_slots_with_snare.append(idx)
        else:
            hat_slots_free.append(idx)

    desired_counts: Dict[str, int] = {}
    fractional: Dict[str, float] = {}
    adjustable = {cat for cat in desired_shares if cat in CATEGORY_TO_INSTRUMENTS}
    base_shares = {cat: float(target_shares.get(cat, desired_shares.get(cat, 0.0))) for cat in adjustable}
    max_share_scale_map = adjustments.get("max_share_scale") or {}
    max_counts: Dict[str, int] = {}

    for cat in adjustable:
        target = desired_shares.get(cat, 0.0) * total
        desired_counts[cat] = math.floor(target)
        fractional[cat] = target - desired_counts[cat]
        scale = max_share_scale_map.get(cat)
        base_share = base_shares.get(cat, 0.0)
        if scale is not None and base_share > 0:
            try:
                max_share = max(0.0, float(scale) * base_share)
            except (TypeError, ValueError):  # pragma: no cover - defensive casting
                max_share = base_share
            max_count = int(math.floor(max_share * total))
            max_counts[cat] = max_count
            if max_count >= 0:
                desired_counts[cat] = min(desired_counts[cat], max_count)

    assigned = sum(desired_counts.values())
    available_hats = len(hat_slots_free) + len(hat_slots_with_snare)
    remaining = max(0, min(available_hats + sum(counts.get(cat, 0) for cat in adjustable), total) - assigned)
    for cat in sorted(adjustable, key=lambda c: fractional.get(c, 0.0), reverse=True):
        if remaining <= 0:
            break
        max_cap = max_counts.get(cat)
        if max_cap is not None and max_cap >= 0 and desired_counts.get(cat, 0) >= max_cap:
            continue
        desired_counts[cat] += 1
        remaining -= 1

    if remaining > 0:
        for cat in sorted(adjustable, key=lambda c: base_shares.get(c, 0.0), reverse=True):
            if remaining <= 0:
                break
            max_cap = max_counts.get(cat)
            if max_cap is not None and max_cap >= 0 and desired_counts.get(cat, 0) >= max_cap:
                continue
            desired_counts[cat] += 1
            remaining -= 1

    donor_priority = adjustments.get("donor_priority") or ["hihat", "ride", "cymbal", "tom", "kick"]

    def take_donor(prefer_snare: bool) -> tuple[int | None, str | None]:
        if prefer_snare and hat_slots_with_snare:
            idx = hat_slots_with_snare.pop()
            if idx in category_indices.get("hihat", []):
                category_indices["hihat"].remove(idx)
            return idx, "hihat"
        if hat_slots_free:
            idx = hat_slots_free.pop()
            if idx in category_indices.get("hihat", []):
                category_indices["hihat"].remove(idx)
            return idx, "hihat"
        if hat_slots_with_snare:
            idx = hat_slots_with_snare.pop()
            if idx in category_indices.get("hihat", []):
                category_indices["hihat"].remove(idx)
            return idx, "hihat"
        for donor_cat in donor_priority:
            if donor_cat == "hihat":
                continue
            indices = category_indices.get(donor_cat)
            if not indices:
                continue
            idx = indices.pop()
            return idx, donor_cat
        return None, None

    def choose_instrument(category: str) -> str:
        return _choose_instrument_for_category(category, adjustments, rng)

    for cat in adjustable:
        if cat == "hihat":
            continue
        desired = desired_counts.get(cat, 0)
        current = counts.get(cat, 0)
        needed = max(0, desired - current)
        prefer_snare = cat == "snare"
        while needed > 0:
            idx, donor_cat = take_donor(prefer_snare)
            if idx is None or donor_cat is None:
                break
            new_inst = choose_instrument(cat)
            _set_event_instrument(events[idx], new_inst)
            counts[cat] = counts.get(cat, 0) + 1
            counts[donor_cat] = counts.get(donor_cat, 0) - 1
            category_indices.setdefault(cat, []).append(idx)
            needed -= 1

    excess_map = adjustments.get("excess_reassign") or {}
    for cat, reassignment in excess_map.items():
        desired = desired_counts.get(cat, 0)
        if desired <= 0:
            continue
        current = counts.get(cat, 0)
        if current <= desired:
            continue
        surplus = current - desired
        donor_list = list(category_indices.get(cat, []))
        while surplus > 0 and donor_list:
            idx = donor_list.pop()
            if idx in category_indices.get(cat, []):
                category_indices[cat].remove(idx)
            new_cat = _assign_index_to_category(events, idx, reassignment, adjustments, rng)
            counts[cat] -= 1
            counts[new_cat] = counts.get(new_cat, 0) + 1
            category_indices.setdefault(new_cat, []).append(idx)
            surplus -= 1

    overflow_priority = adjustments.get("overflow_reassign_priority") or []
    fallback_target = adjustments.get("overflow_default_target")
    if isinstance(fallback_target, str):
        fallback_candidates = [fallback_target]
    elif isinstance(fallback_target, (list, tuple)):
        fallback_candidates = [str(item) for item in fallback_target if isinstance(item, str)]
    else:
        fallback_candidates = []

    def pick_overflow_target(category: str) -> str | None:
        candidates = list(overflow_priority) if overflow_priority else []
        if fallback_candidates:
            candidates.extend(fallback_candidates)
        if not candidates:
            candidates = [c for c in ("snare", "tom", "cymbal", "ride", "hihat") if c != category]
        for cand in candidates:
            if cand == category:
                continue
            if cand not in CATEGORY_TO_INSTRUMENTS:
                continue
            max_cap = max_counts.get(cand)
            if max_cap is not None and max_cap >= 0 and counts.get(cand, 0) >= max_cap:
                continue
            return cand
        return None

    for cat, max_count in max_counts.items():
        if max_count < 0:
            continue
        current = counts.get(cat, 0)
        if current <= max_count:
            continue
        donor_list = list(category_indices.get(cat, []))
        while current > max_count and donor_list:
            idx = donor_list.pop()
            if idx in category_indices.get(cat, []):
                category_indices[cat].remove(idx)
            target_category = pick_overflow_target(cat)
            if target_category is None:
                break
            new_cat = _assign_index_to_category(events, idx, target_category, adjustments, rng)
            counts[cat] -= 1
            counts[new_cat] = counts.get(new_cat, 0) + 1
            category_indices.setdefault(new_cat, []).append(idx)
            current -= 1

def _desired_fill_count(
    events: Sequence[Dict[str, Any]],
    rollup: Dict[str, Any],
    adjustments: Dict[str, float],
) -> int:
    fills_per_min = _normalize_fill_rate(rollup.get("fills_per_min"))
    if fills_per_min is None:
        return 0
    if fills_per_min <= 0:
        return 0
    if not events:
        return 0

    start = min(float(ev.get("barStartTime", ev.get("time_sec", 0.0))) for ev in events)
    end = max(float(ev.get("barEndTime", ev.get("time_sec", 0.0))) for ev in events)
    duration = max(0.0, end - start)
    if duration <= 0:
        return 0

    minutes = duration / 60.0
    fill_factor = float(adjustments.get("fill_factor", 1.0))
    scaled_fpm = fills_per_min * fill_factor
    cap = adjustments.get("fill_fpm_cap")
    try:
        if cap is not None:
            scaled_fpm = min(scaled_fpm, float(cap))
    except (TypeError, ValueError):  # pragma: no cover - defensive casting
        pass

    target = scaled_fpm * minutes
    target = min(target, len(events) * 0.85)
    return int(round(target))


def _ensure_fill_density(
    events: List[Dict[str, Any]],
    desired_fill_notes: int,
    target_mean: float,
    target_std: float,
    adjustments: Dict[str, Any],
    rng: random.Random,
) -> None:
    if desired_fill_notes <= 0 or not events:
        return

    current_fill_indices = [idx for idx, ev in enumerate(events) if ev.get("aspect") == "fill"]
    current_fill_count = len(current_fill_indices)
    bars_present = sorted({int(ev.get("barIndex", 0)) for ev in events})
    if not bars_present:
        return
    fills_per_bar: Dict[int, int] = {bar: 0 for bar in bars_present}
    for idx in current_fill_indices:
        bar_idx = int(events[idx].get("barIndex", 0))
        fills_per_bar[bar_idx] = fills_per_bar.get(bar_idx, 0) + 1

    total_bars = len(bars_present)
    max_scale = float(adjustments.get("max_fills_per_bar_scale") or 1.0)
    max_per_bar = max(1, int(math.ceil(desired_fill_notes / total_bars * max_scale)))

    allowed_sources = adjustments.get("fill_source_categories")
    if not allowed_sources:
        allowed_sources = ["hihat", "snare", "ride", "cymbal", "tom"]
    allowed_sources = [cat for cat in allowed_sources if cat in CATEGORY_TO_INSTRUMENTS or cat in {"kick", "snare", "hihat", "ride", "cymbal", "tom"}]

    total_notes = len(events)
    category_counts = Counter(_instrument_category(ev.get("instrument_id", "")) for ev in events)

    hihat_floor_count = 0
    floor_val = adjustments.get("hihat_share_floor")
    try:
        if floor_val is not None:
            floor_float = float(floor_val)
            if floor_float > 0:
                hihat_floor_count = int(math.ceil(floor_float * total_notes))
    except (TypeError, ValueError):  # pragma: no cover - defensive casting
        hihat_floor_count = 0

    category_sources: Dict[str, List[int]] = {}
    for idx, ev in enumerate(events):
        if ev.get("aspect") == "fill":
            continue
        cat = _instrument_category(ev.get("instrument_id", ""))
        if cat in allowed_sources:
            category_sources.setdefault(cat, []).append(idx)
    for bucket in category_sources.values():
        rng.shuffle(bucket)

    source_priority = adjustments.get("fill_source_priority") or []
    ordered_sources: List[str] = []
    for cat in source_priority:
        if cat in category_sources and cat not in ordered_sources:
            ordered_sources.append(cat)
    for cat in category_sources:
        if cat not in ordered_sources:
            ordered_sources.append(cat)

    def _take_from_category(cat: str) -> int | None:
        bucket = category_sources.get(cat)
        while bucket and events[bucket[-1]].get("aspect") == "fill":
            bucket.pop()
        if not bucket:
            return None
        if cat == "hihat" and hihat_floor_count:
            if category_counts.get("hihat", 0) - 1 < hihat_floor_count:
                return None
        return bucket.pop()

    def _pick_source() -> Tuple[int | None, str | None]:
        for cat in ordered_sources:
            idx_local = _take_from_category(cat)
            if idx_local is not None:
                return idx_local, cat
        for cat in category_sources:
            idx_local = _take_from_category(cat)
            if idx_local is not None:
                return idx_local, cat
        return None, None

    category_priority = adjustments.get("fill_category_priority") or FILL_CATEGORY_PRIORITY
    velocity_scale = float(adjustments.get("fill_velocity_scale") or 1.0)

    def _pick_fill_category() -> str:
        candidates: List[str] = []
        weights: List[float] = []
        total_priority = len(category_priority)
        for rank, cat in enumerate(category_priority):
            options = CATEGORY_TO_INSTRUMENTS.get(cat, [])
            if not options:
                continue
            weight = max(1, len(options)) * max(1, total_priority - rank)
            candidates.append(cat)
            weights.append(weight)
        if not candidates:
            return "snare"
        total_weight = sum(weights)
        pivot = rng.uniform(0.0, total_weight)
        cumulative = 0.0
        for cat, weight in zip(candidates, weights):
            cumulative += weight
            if pivot <= cumulative:
                return cat
        return candidates[-1]

    while current_fill_count < desired_fill_notes:
        idx, source_cat = _pick_source()
        if idx is None or source_cat is None:
            break
        ev = events[idx]
        bar_idx = int(ev.get("barIndex", 0))
        if fills_per_bar.get(bar_idx, 0) >= max_per_bar:
            category_sources.setdefault(source_cat, []).insert(0, idx)
            continue

        category_counts[source_cat] = max(0, category_counts.get(source_cat, 0) - 1)

        fill_category = _pick_fill_category()
        new_instrument = _choose_instrument_for_category(fill_category, adjustments, rng)
        _set_event_instrument(ev, new_instrument)
        category_counts[fill_category] = category_counts.get(fill_category, 0) + 1

        ev["aspect"] = "fill"
        fill_target = target_mean + target_std * rng.uniform(0.4, 0.9) * velocity_scale
        ev["velocity"] = int(round(_clamp(fill_target, 1.0, 127.0)))
        fills_per_bar[bar_idx] = fills_per_bar.get(bar_idx, 0) + 1
        current_fill_count += 1


def apply_rollup_humanization(
    events: Sequence[Dict[str, Any]],
    rollup: Dict[str, Any],
    drummer_slug: str,
    rng: random.Random,
) -> List[Dict[str, Any]]:
    cloned = _clone_events(events)
    adjustments = DRUMMER_ADJUSTMENTS.get(drummer_slug, {})

    target_mean = float(rollup.get("velocity_mean") or 0.3) * 127.0
    target_std = float(rollup.get("velocity_std") or 0.12) * 127.0
    target_std = max(target_std, 2.5)
    target_std *= adjustments.get("velocity_std_scale", 1.0)

    target_shares = _expected_category_shares(rollup.get("instrument_shares") or {})
    if target_shares:
        _rebalance_instrument_categories(cloned, target_shares, adjustments, rng)

    desired_fills = _desired_fill_count(cloned, rollup, adjustments)
    if desired_fills > 0:
        _ensure_fill_density(cloned, desired_fills, target_mean, target_std, adjustments, rng)

    _retarget_velocities(cloned, target_mean, target_std, rng)
    _rescale_velocities_to_target(cloned, target_mean, target_std)

    timing_std = float(rollup.get("timing_std_ms") or 30.0)
    timing_std *= adjustments.get("timing_scale", 1.0)
    _apply_microtiming(cloned, timing_std, rng)

    return cloned


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DCSM tracks for assimilated drummers")
    parser.add_argument("--base-groove", type=Path, default=Path("tests/assets/base_groove.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("tests/output/dcsm"))
    parser.add_argument("--drummers", nargs="*", default=["john_bonham", "ringo_starr", "clyde_stubblefield"])
    parser.add_argument("--repeats", type=int, default=4, help="Number of times to loop the base groove")
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.1,
        help="Allowed relative deviation (±) when comparing generated metrics to rollup values",
    )
    parser.add_argument("--seed", type=int, default=1337, help="Random seed for humanization")
    parser.add_argument(
        "--adjustments-config",
        type=Path,
        default=None,
        help=(
            "Optional path to drummer adjustment overrides (JSON). "
            "Defaults to config/drummer_adjustments.json or environment overrides"
        ),
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    overrides = _load_adjustment_overrides(args.adjustments_config)
    _apply_adjustment_overrides(overrides)

    base = load_base_pattern(args.base_groove)
    repeated_events = repeat_events(base.events, args.repeats)
    total_bars = (max(int(ev.get("barIndex", 0)) for ev in repeated_events) + 1) if repeated_events else 0
    sections = build_sections(total_bars)

    svc = CentralDatabaseService.get_instance()
    svc.initialize()

    builder = DCSMDrumTrackBuilder(tempo=base.tempo_bpm, time_signature=base.time_signature, ppqn=base.ppqn)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    summary: List[Dict[str, Any]] = []

    for drummer in args.drummers:
        print(f"Generating track for {drummer}...")
        try:
            rollup = fetch_rollup(svc, drummer)
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"  ⚠️  Skipping {drummer}: {exc}")
            summary.append({
                "drummer": drummer,
                "status": "error",
                "error": str(exc),
            })
            continue

        perf_spec = map_rollup_to_spec(rollup)
        humanized_events = apply_rollup_humanization(repeated_events, rollup, drummer, rng)

        track = builder.build_from_pattern_and_spec(
            pattern_events=humanized_events,
            sections=sections,
            performance_spec=perf_spec,
        )

        track_path = args.output_dir / f"{drummer}_track.json"
        builder.save_to_json(track, track_path)

        track_dict = track.to_dict()
        metrics = compute_track_metrics(track_dict)
        comparison = compare_metrics_to_rollup(rollup, metrics, tolerance=args.tolerance)

        within = comparison["within_tolerance_count"]
        total = comparison["total_compared"]
        status_info = _completion_status(within, total)

        metrics_payload = {
            "drummer": drummer,
            "performance_spec": perf_spec,
            "metrics": metrics,
            "comparison": comparison,
            "rollup_snapshot": {
                "velocity_mean": rollup.get("velocity_mean"),
                "velocity_std": rollup.get("velocity_std"),
                "timing_std_ms": rollup.get("timing_std_ms"),
                "ghost_ratio": rollup.get("ghost_ratio"),
                "fill_ratio": rollup.get("fill_ratio"),
                "fills_per_min": rollup.get("fills_per_min"),
                "instrument_shares": rollup.get("instrument_shares"),
            },
            "completion_status": status_info,
        }

        metrics_path = args.output_dir / f"{drummer}_metrics.json"
        metrics_path.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")

        print(f"  ✅ Track saved ({track_path}). Metrics within tolerance: {within}/{total}")

        summary.append(
            {
                "drummer": drummer,
                "status": "ok",
                "track_path": str(track_path),
                "metrics_path": str(metrics_path),
                "note_count": metrics.get("note_count"),
                "metrics_within_tolerance": within,
                "metrics_compared": total,
                "completion_status": status_info,
            }
        )

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nSummary written to {summary_path}")


if __name__ == "__main__":
    main()
