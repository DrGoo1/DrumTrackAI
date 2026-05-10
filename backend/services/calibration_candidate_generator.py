"""Utilities for generating calibration candidate run events."""
from __future__ import annotations

import logging
import random
import sys
from datetime import datetime
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Dict, List, Optional

from admin.services.central_database_service import CentralDatabaseService
from backend.app.assimilation.models.performance_transformer import apply_personality_transform

logger = logging.getLogger(__name__)


@dataclass
class CandidateRunData:
    event_stream: List[Dict[str, Any]]
    tempo_bpm: Optional[float]
    time_signature: Dict[str, Any]
    bars: int
    kit_id: Optional[str]
    base_groove_path: str
    sections: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    performance_spec: Optional[Dict[str, Any]]
    rollup: Optional[Dict[str, Any]]

    @property
    def note_count(self) -> int:
        return len(self.event_stream)


_HELPERS: Optional[Dict[str, Any]] = None


def _load_helpers() -> Dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    candidates = [
        root / "scripts" / "apply_drummers_to_base_groove.py",
        root / "__drumtrackai_frontend__" / "scripts" / "apply_drummers_to_base_groove.py",
    ]
    script_path = None
    for p in candidates:
        if p.is_file():
            script_path = p
            break
    if script_path is None:
        raise FileNotFoundError(
            f"Missing apply_drummers_to_base_groove at any of: {', '.join(str(p) for p in candidates)}"
        )

    spec = spec_from_file_location("_calibration_apply_drummers", script_path)
    if spec is None or spec.loader is None:
        raise ImportError("Unable to load apply_drummers_to_base_groove helpers")

    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[arg-type]
    except Exception:
        sys.modules.pop(spec.name, None)
        raise

    helpers: Dict[str, Any] = {}
    for name in (
        "load_base_pattern",
        "repeat_events",
        "build_sections",
        "apply_rollup_humanization",
        "fetch_rollup",
        "map_rollup_to_spec",
    ):
        helper = getattr(module, name, None)
        if helper is None:
            raise AttributeError(f"apply_drummers_to_base_groove missing '{name}'")
        helpers[name] = helper
    return helpers


def _helpers() -> Dict[str, Any]:
    global _HELPERS  # noqa: PLW0603
    if _HELPERS is None:
        _HELPERS = _load_helpers()
    return _HELPERS


def _resolve_base_groove_path(base_groove_id: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    candidates = [
        # direct path provided
        Path(base_groove_id),
        # repo-level test assets
        root / "tests" / "assets" / f"{base_groove_id}.json",
        root / "tests" / "assets" / "base_groove.json",
        # frontend test assets (Netlify repo subtree)
        root / "__drumtrackai_frontend__" / "tests" / "assets" / f"{base_groove_id}.json",
        root / "__drumtrackai_frontend__" / "tests" / "assets" / "base_groove.json",
    ]
    for path in candidates:
        if path.is_file():
            return path.resolve()
    raise FileNotFoundError(f"Could not resolve base groove '{base_groove_id}'")


def _parse_time_signature(value: Any) -> Dict[str, Any]:
    if not value:
        return {}
    text = str(value)
    if "/" in text:
        num, denom = text.split("/", 1)
        try:
            return {
                "display": text,
                "numerator": int(num),
                "denominator": int(denom),
            }
        except ValueError:
            logger.debug("Failed to parse time signature '%s'", text)
    return {"display": text}


def _bar_count(events: List[Dict[str, Any]]) -> int:
    max_bar = -1
    for ev in events:
        try:
            max_bar = max(max_bar, int(ev.get("barIndex", 0)))
        except (TypeError, ValueError):
            continue
    return max_bar + 1 if max_bar >= 0 else 0


def _infer_kit_id(rollup: Optional[Dict[str, Any]]) -> Optional[str]:
    if not isinstance(rollup, dict):
        return None
    return (
        rollup.get("kit_id")
        or rollup.get("default_kit")
        or rollup.get("reference_kit")
        or rollup.get("calibration_kit")
    )


def _clamp01(value: Any, default: float) -> float:
    try:
        val = float(value)
    except Exception:
        val = float(default)
    return max(0.0, min(1.0, val))


def _lerp(a: float, b: float, t: float) -> float:
    return float(a + ((b - a) * t))


def _apply_generation_controls_to_spec(
    spec: Optional[Dict[str, Any]],
    *,
    controls: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    if not isinstance(spec, dict):
        return spec
    out = dict(spec)
    personality_amount = _clamp01(controls.get("personality_amount"), 0.75)
    preserve_original = _clamp01(controls.get("preserve_original_groove"), 0.65)
    influence = personality_amount * (1.0 - (preserve_original * 0.85))

    fill_aggr = _clamp01(controls.get("fill_aggression"), 0.5)
    ghost_detail = _clamp01(controls.get("ghost_note_detail"), 0.6)
    cymbal_personality = _clamp01(controls.get("cymbal_personality"), 0.8)
    timing_personality = _clamp01(controls.get("timing_personality"), 0.7)
    velocity_personality = _clamp01(controls.get("velocity_personality"), 0.75)

    if out.get("fillDensity") is not None:
        try:
            base = float(out.get("fillDensity"))
            target = base * (0.75 + (fill_aggr * 0.9))
            out["fillDensity"] = _lerp(base, target, influence)
        except Exception:
            pass

    if out.get("ghostNoteAmount") is not None:
        try:
            base = float(out.get("ghostNoteAmount"))
            target = max(0.0, min(1.0, base * (0.85 + (ghost_detail * 0.7))))
            out["ghostNoteAmount"] = _lerp(base, target, influence)
        except Exception:
            pass

    if out.get("hatOpenness") is not None:
        try:
            base = float(out.get("hatOpenness"))
            target = max(0.0, min(1.0, base * (0.8 + (cymbal_personality * 0.9))))
            out["hatOpenness"] = _lerp(base, target, influence)
        except Exception:
            pass

    if out.get("swing") is not None:
        try:
            base = float(out.get("swing"))
            target = max(0.0, min(1.0, base * (0.85 + (timing_personality * 0.6))))
            out["swing"] = _lerp(base, target, influence)
        except Exception:
            pass

    if out.get("intensity") is not None:
        try:
            base = float(out.get("intensity"))
            target = max(0.0, min(1.0, base * (0.85 + (velocity_personality * 0.8))))
            out["intensity"] = _lerp(base, target, influence)
        except Exception:
            pass

    out["generation_controls"] = dict(controls)
    out["personality_influence"] = float(influence)
    return out


def _blend_events_with_controls(
    base_events: List[Dict[str, Any]],
    styled_events: List[Dict[str, Any]],
    *,
    controls: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not base_events or not styled_events or len(base_events) != len(styled_events):
        return [dict(ev) for ev in styled_events]

    personality_amount = _clamp01(controls.get("personality_amount"), 0.75)
    preserve_original = _clamp01(controls.get("preserve_original_groove"), 0.65)
    timing_personality = _clamp01(controls.get("timing_personality"), 0.7)
    velocity_personality = _clamp01(controls.get("velocity_personality"), 0.75)
    influence = personality_amount * (1.0 - (preserve_original * 0.85))

    time_blend = influence * (0.6 + (0.4 * timing_personality))
    velocity_blend = influence * (0.6 + (0.4 * velocity_personality))

    out: List[Dict[str, Any]] = []
    for base_ev, styled_ev in zip(base_events, styled_events):
        merged = dict(styled_ev)
        for key in ("time_sec", "bar_pos_frac", "timing_offset_ms"):
            if key in base_ev and key in styled_ev:
                try:
                    merged[key] = _lerp(float(base_ev[key]), float(styled_ev[key]), time_blend)
                except Exception:
                    pass

        if "velocity" in base_ev and "velocity" in styled_ev:
            try:
                vel = _lerp(float(base_ev["velocity"]), float(styled_ev["velocity"]), velocity_blend)
                merged["velocity"] = int(max(1, min(127, round(vel))))
            except Exception:
                pass

        out.append(merged)
    return out


def generate_candidate_run(
    *,
    db: CentralDatabaseService,
    base_groove_id: str,
    target_drummer_slug: str | None = None,
    drummer_slug: str | None = None,
    seed: int,
    repeats: int = 4,
    generation_controls: Optional[Dict[str, Any]] = None,
) -> CandidateRunData:
    """Build a candidate run payload by applying the target drummer rollup to a base groove."""

    resolved_slug = target_drummer_slug if target_drummer_slug else drummer_slug
    if not resolved_slug:
        raise ValueError("generate_candidate_run requires drummer_slug or target_drummer_slug")
    slug = resolved_slug.strip().lower()
    helpers = _helpers()
    base_path = _resolve_base_groove_path(base_groove_id)
    pattern = helpers["load_base_pattern"](base_path)
    repeated_events = helpers["repeat_events"](getattr(pattern, "events", []), max(1, repeats))

    rollup: Dict[str, Any] = {}
    try:
        rollup = helpers["fetch_rollup"](db, slug) or {}
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("generate_candidate_run: unable to fetch rollup for %s: %s", slug, exc)
        rollup = {}

    controls: Dict[str, Any] = generation_controls if isinstance(generation_controls, dict) else {}
    rng = random.Random(seed)
    humanized_events = repeated_events
    if rollup:
        try:
            humanized_events = helpers["apply_rollup_humanization"](repeated_events, rollup, slug, rng)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("generate_candidate_run: humanization failed for %s: %s", slug, exc)
            humanized_events = repeated_events

    bars = _bar_count(humanized_events)
    sections = helpers["build_sections"](bars)

    performance_spec: Optional[Dict[str, Any]] = None
    if rollup:
        try:
            performance_spec = helpers["map_rollup_to_spec"](rollup)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("generate_candidate_run: map_rollup_to_spec failed for %s: %s", slug, exc)
            performance_spec = None

    if performance_spec:
        performance_spec = _apply_generation_controls_to_spec(performance_spec, controls=controls)

    if controls:
        humanized_events = _blend_events_with_controls(
            repeated_events,
            humanized_events,
            controls=controls,
        )
        try:
            humanized_events = apply_personality_transform(humanized_events, controls)
        except Exception as exc:  # pragma: no cover
            logger.warning("generate_candidate_run: personality transform failed for %s: %s", slug, exc)

    tempo_bpm = float(getattr(pattern, "tempo_bpm", 110.0))
    time_signature = _parse_time_signature(getattr(pattern, "time_signature", "4/4"))
    kit_id = _infer_kit_id(rollup) or "default_kit"

    metadata = {
        "base_groove_id": base_groove_id,
        "base_groove_path": str(base_path),
        "repeats": repeats,
        "rollup_available": bool(rollup),
        "generator_seed": seed,
        "generation_controls": controls,
    }
    if performance_spec:
        metadata["performance_spec"] = performance_spec
    if sections:
        metadata["sections"] = sections

    return CandidateRunData(
        event_stream=[dict(ev) for ev in humanized_events],
        tempo_bpm=tempo_bpm,
        time_signature=time_signature,
        bars=bars,
        kit_id=kit_id,
        base_groove_path=str(base_path),
        sections=sections,
        metadata=metadata,
        performance_spec=performance_spec,
        rollup=rollup or None,
    )
