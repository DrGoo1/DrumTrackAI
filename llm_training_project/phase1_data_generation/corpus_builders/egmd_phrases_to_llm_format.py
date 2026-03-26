#!/usr/bin/env python3
"""E-GMD phrases (paired MIDI+WAV) to Admin LLM JSONL.

This exporter reuses the existing Admin JSONL structure:
  {"task": ..., "input": ..., "output": ..., "meta": ...}

It generates paired examples by sampling target controls and selecting the best-matching
phrase from the DB.
"""

import argparse
import json
import math
import random
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class PhraseRow:
    phrase_id: int
    style_group: str
    tempo_bpm_name: Optional[int]
    meter_name: Optional[str]
    bars: Optional[int]
    midi_path: str
    audio_path: Optional[str]
    feature_json: Dict[str, Any]


def _safe_ratio(n: float, d: float) -> float:
    if d <= 0:
        return 0.0
    return float(n) / float(d)


def _derive_phrase_features(p: PhraseRow) -> Dict[str, float]:
    f = p.feature_json

    drum_counts = f.get("drum_counts") or {}
    total_hits = float(f.get("total_hits") or 0)
    duration = float(f.get("duration") or 0.0)
    density = float(f.get("pattern_density") or (total_hits / duration if duration > 0 else 0.0))
    swing = float(f.get("swing_amount") or 0.0)

    hihat_art = f.get("hihat_articulations") or {}
    hihat_hits = float(hihat_art.get("total_hihat_hits") or 0.0)

    ghost_notes = float(f.get("ghost_notes") or 0.0)
    accents = float(f.get("accents") or 0.0)

    fill_segments = f.get("fill_segments") or []
    fill_count = float(len(fill_segments))

    kick = float(drum_counts.get("kick") or 0.0)
    snare = float(drum_counts.get("snare") or 0.0)
    ride = float(drum_counts.get("ride") or 0.0)
    crash = float(drum_counts.get("crash") or 0.0)

    return {
        "tempo": float(f.get("tempo") or 0.0),
        "duration": duration,
        "density": density,
        "swing": swing,
        "kick_ratio": _safe_ratio(kick, total_hits),
        "snare_ratio": _safe_ratio(snare, total_hits),
        "hihat_ratio": _safe_ratio(hihat_hits, total_hits),
        "ride_ratio": _safe_ratio(ride, total_hits),
        "cymbal_ratio": _safe_ratio(ride + crash, total_hits),
        "ghost_ratio": _safe_ratio(ghost_notes, total_hits),
        "accent_ratio": _safe_ratio(accents, total_hits),
        "fill_count": fill_count,
        "fill_rate": _safe_ratio(fill_count, max(duration, 0.001)),
    }


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _score_phrase(target: Dict[str, Any], pf: Dict[str, float]) -> float:
    # Lower is better.
    tempo_target = float(target["tempo_bpm"])
    tempo_tol = float(target.get("tempo_tolerance_bpm", 10.0))
    tempo_err = abs(pf["tempo"] - tempo_target) / max(tempo_tol, 1.0)

    density_target = float(target["density_hps"])
    density_err = abs(pf["density"] - density_target) / max(density_target, 1e-3)

    swing_target = float(target["swing"])
    swing_err = abs(pf["swing"] - swing_target)

    hihat_target = float(target["hihat_ratio"])
    hihat_err = abs(pf["hihat_ratio"] - hihat_target)

    fill_target = float(target["fill_rate"])
    fill_err = abs(pf["fill_rate"] - fill_target) / max(fill_target, 1e-3)

    ghost_target = float(target["ghost_ratio"])
    ghost_err = abs(pf["ghost_ratio"] - ghost_target) / max(ghost_target, 1e-3)

    kick_target = float(target["kick_ratio"])
    kick_err = abs(pf["kick_ratio"] - kick_target) / max(kick_target, 1e-3)

    snare_target = float(target["snare_ratio"])
    snare_err = abs(pf["snare_ratio"] - snare_target) / max(snare_target, 1e-3)

    # Weights tuned for early v0; adjust as we learn.
    return (
        2.5 * tempo_err
        + 1.5 * density_err
        + 1.0 * swing_err
        + 1.0 * hihat_err
        + 0.6 * fill_err
        + 0.6 * ghost_err
        + 0.4 * kick_err
        + 0.4 * snare_err
    )


def _transform_plan_from_diff(target: Dict[str, Any], pf: Dict[str, float]) -> Dict[str, Any]:
    density_delta = float(target["density_hps"]) - pf["density"]
    swing_delta = float(target["swing"]) - pf["swing"]

    # Basic policy: multiplicative density, additive swing, and simple per-role adjustments.
    density_multiplier = _clamp(1.0 + (density_delta / max(pf["density"], 1e-3)) * 0.5, 0.4, 2.0)
    ghost_boost = _clamp(float(target["ghost_ratio"]) - pf["ghost_ratio"], -0.3, 0.3)
    fill_inject = _clamp(float(target["fill_rate"]) - pf["fill_rate"], -0.5, 0.5)

    cymbal_preference = float(target.get("cymbal_preference", 0.5))
    # 0 => favor hats, 1 => favor ride
    hats_to_ride = _clamp(cymbal_preference, 0.0, 1.0)

    return {
        "density_multiplier": density_multiplier,
        "swing_delta": _clamp(swing_delta, -0.35, 0.35),
        "ghost_note_boost": ghost_boost,
        "fill_injection": fill_inject,
        "hats_to_ride": hats_to_ride,
        "kick_bias": _clamp(float(target["kick_ratio"]) - pf["kick_ratio"], -0.25, 0.25),
        "snare_bias": _clamp(float(target["snare_ratio"]) - pf["snare_ratio"], -0.25, 0.25),
    }


def _load_phrases(conn: sqlite3.Connection) -> List[PhraseRow]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, style_group, tempo_bpm, meter, bars, midi_path, audio_path, feature_json
        FROM egmd_phrases
        WHERE feature_json IS NOT NULL
          AND style_group IS NOT NULL
          AND style_group != ''
        """
    )

    rows: List[PhraseRow] = []
    for (pid, style_group, tempo_bpm, meter, bars, midi_path, audio_path, feature_json) in cur.fetchall():
        try:
            fj = json.loads(feature_json) if feature_json else {}
        except Exception:
            continue

        rows.append(
            PhraseRow(
                phrase_id=int(pid),
                style_group=str(style_group),
                tempo_bpm_name=int(tempo_bpm) if tempo_bpm is not None else None,
                meter_name=str(meter) if meter else None,
                bars=int(bars) if bars is not None else None,
                midi_path=str(midi_path),
                audio_path=str(audio_path) if audio_path else None,
                feature_json=fj,
            )
        )

    return rows


def _group_by_style(phrases: Iterable[PhraseRow]) -> Dict[str, List[PhraseRow]]:
    buckets: Dict[str, List[PhraseRow]] = {}
    for p in phrases:
        buckets.setdefault(p.style_group, []).append(p)
    return buckets


def _sample_target_controls(style_group: str, rng: random.Random) -> Dict[str, Any]:
    # Tempo ranges are intentionally broad; meter defaults to 4/4 for v0.
    tempo = rng.choice([70, 80, 90, 100, 110, 120, 130, 140, 160, 180])

    # density in hits/sec: typical groove ranges ~4-14
    density = rng.uniform(4.0, 14.0)

    # swing is 0..~0.65 in our current extractor scale
    swing = rng.uniform(0.0, 0.65)

    # ratios: these are not strict; they act as a soft preference.
    hihat_ratio = rng.uniform(0.05, 0.45)
    kick_ratio = rng.uniform(0.05, 0.25)
    snare_ratio = rng.uniform(0.05, 0.25)

    # fill_rate in segments/sec (very low)
    fill_rate = rng.uniform(0.0, 0.15)
    ghost_ratio = rng.uniform(0.0, 0.25)

    cymbal_pref = rng.uniform(0.0, 1.0)

    return {
        "style_group": style_group,
        "meter": "4/4",
        "tempo_bpm": tempo,
        "tempo_tolerance_bpm": rng.choice([6, 8, 10, 12, 15]),
        "density_hps": density,
        "swing": swing,
        "hihat_ratio": hihat_ratio,
        "kick_ratio": kick_ratio,
        "snare_ratio": snare_ratio,
        "fill_rate": fill_rate,
        "ghost_ratio": ghost_ratio,
        "cymbal_preference": cymbal_pref,
    }


def export_phrases_to_jsonl(
    *,
    db_path: Path,
    output_file: Path,
    num_examples: int,
    seed: int,
    candidate_pool_per_style: int,
) -> None:
    rng = random.Random(seed)

    if not db_path.exists():
        raise FileNotFoundError(f"DB not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        phrases = _load_phrases(conn)
        if not phrases:
            raise RuntimeError("No phrases loaded from egmd_phrases")

        by_style = _group_by_style(phrases)
        styles = sorted(by_style.keys())

        output_file.parent.mkdir(parents=True, exist_ok=True)

        with output_file.open("w", encoding="utf-8") as f_out:
            for i in range(num_examples):
                style = rng.choice(styles)
                candidates = by_style[style]

                if candidate_pool_per_style and len(candidates) > candidate_pool_per_style:
                    candidates = rng.sample(candidates, candidate_pool_per_style)

                target = _sample_target_controls(style, rng)

                best: Optional[Tuple[PhraseRow, Dict[str, float], float]] = None
                for p in candidates:
                    pf = _derive_phrase_features(p)
                    s = _score_phrase(target, pf)
                    if best is None or s < best[2]:
                        best = (p, pf, s)

                if best is None:
                    continue

                chosen, chosen_pf, score = best

                # Task 1: phrase selection
                select_record = {
                    "task": "select_phrase",
                    "input": target,
                    "output": {
                        "phrase_id": chosen.phrase_id,
                        "midi_path": chosen.midi_path,
                        "audio_path": chosen.audio_path,
                        "measured": chosen_pf,
                        "match_score": score,
                    },
                    "meta": {
                        "source": "egmd_phrases",
                        "db": str(db_path),
                        "seed": seed,
                        "example_index": i,
                    },
                }
                f_out.write(json.dumps(select_record) + "\n")

                # Task 2: transform planning (synthetic)
                plan = _transform_plan_from_diff(target, chosen_pf)
                plan_record = {
                    "task": "plan_transforms",
                    "input": {
                        "target": target,
                        "phrase": {
                            "phrase_id": chosen.phrase_id,
                            "measured": chosen_pf,
                        },
                    },
                    "output": plan,
                    "meta": {
                        "source": "egmd_phrases",
                        "db": str(db_path),
                        "seed": seed,
                        "example_index": i,
                    },
                }
                f_out.write(json.dumps(plan_record) + "\n")

    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Export egmd_phrases to Admin LLM JSONL (paired control targets -> best phrase)")
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("admin/data/drum_training.db"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("llm_training_project/training_datasets/egmd_phrase_select_train.jsonl"),
    )
    parser.add_argument("--num-examples", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--candidate-pool-per-style", type=int, default=4000)

    args = parser.parse_args()

    export_phrases_to_jsonl(
        db_path=args.db,
        output_file=args.out,
        num_examples=int(args.num_examples),
        seed=int(args.seed),
        candidate_pool_per_style=int(args.candidate_pool_per_style),
    )

    print(f"Wrote: {args.out}")


if __name__ == "__main__":
    main()
