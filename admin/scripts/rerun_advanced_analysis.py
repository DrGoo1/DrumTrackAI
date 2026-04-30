import argparse
import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import librosa  # type: ignore
import numpy as np  # type: ignore

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from admin.services.advanced_drummer_analysis import AdvancedDrummerAnalysis  # noqa: E402

logger = logging.getLogger("rerun_advanced_analysis")

COMPONENT_ALIASES: Dict[str, Iterable[str]] = {
    "drums": ("drums", "drum_stem", "drumsep_drums"),
    "kick": ("kick", "bd", "bass_drum", "kickdrum", "kik", "drumsep_kick"),
    "snare": ("snare", "sd", "sn", "drumsep_snare"),
    "hihat": ("hihat", "hh", "hi_hat", "hat", "drumsep_hh"),
    "toms": ("tom", "toms", "rack_tom", "floor_tom", "drumsep_toms"),
    "ride": ("ride", "drumsep_ride"),
    "crash": ("crash", "drumsep_crash"),
    "percussion": ("perc", "percussion"),
}


@dataclass
class TrackContext:
    track_dir: Path
    result_files: Dict[str, str]
    component_map: Dict[str, str]
    previous_payload: Dict[str, object]


def _build_result_files(track_dir: Path) -> Dict[str, str]:
    result: Dict[str, str] = {}

    for pattern in ("*.wav", "*.mp3", "*.flac"):
        for file_path in track_dir.glob(pattern):
            if file_path.is_file():
                result[file_path.stem.lower()] = str(file_path)

    drumsep_dir = track_dir / "drumsep_components"
    if drumsep_dir.exists():
        for file_path in drumsep_dir.glob("*.wav"):
            if file_path.is_file():
                result[file_path.stem.lower()] = str(file_path)

    logger.debug("Result files collected: %s", sorted(result.keys()))
    return result


def _build_component_map(result_files: Dict[str, str]) -> Dict[str, str]:
    normalized: Dict[str, str] = {}

    skip_prefixes = ("bass", "vocals", "other", "instrumental")

    for name, path in result_files.items():
        key = name.lower()
        logger.debug("Evaluating stem '%s' (%s)", key, path)

        if Path(path).suffix.lower() == ".mp3" or key.startswith(skip_prefixes):
            logger.debug("Skipping '%s' due to skip rules", key)
            continue

        matched = False

        if key.startswith("drumsep_"):
            suffix = key[len("drumsep_"):]
            suffix_map = {
                "drums": "drums",
                "kick": "kick",
                "snare": "snare",
                "hh": "hihat",
                "hihat": "hihat",
                "ride": "ride",
                "crash": "crash",
                "toms": "toms",
                "perc": "percussion",
            }
            canonical = suffix_map.get(suffix)
            if canonical:
                normalized[canonical] = path
                matched = True
                logger.debug("Mapped drumsep stem '%s' to '%s'", key, canonical)
            else:
                logger.debug("Unhandled drumsep stem '%s'", key)

        if not matched:
            for canonical, aliases in COMPONENT_ALIASES.items():
                if any(alias == key for alias in aliases):
                    normalized[canonical] = path
                    matched = True
                    logger.debug("Matched '%s' exactly to component '%s'", key, canonical)
                    break
                if any(key.startswith(alias) or alias in key for alias in aliases):
                    normalized.setdefault(canonical, path)
                    matched = True
                    logger.debug("Matched '%s' loosely to component '%s'", key, canonical)
                    break

        if not matched:
            normalized.setdefault(key, path)
            logger.debug("No alias match for '%s'; keeping as '%s'", key, key)

    logger.debug("Component map normalized keys: %s", sorted(normalized.keys()))
    return normalized


def _estimate_tempo(audio_path: str) -> Tuple[float, List[float]]:
    try:
        y, sr = librosa.load(audio_path, sr=22050, mono=True)
        if y.size == 0:
            return 0.0, []
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        return float(tempo), beat_times
    except Exception as exc:  # pragma: no cover
        logger.warning("Tempo estimation failed for %s: %s", audio_path, exc)
        return 0.0, []


def _load_track_context(track_dir: Path) -> TrackContext:
    if not track_dir.is_dir():
        raise FileNotFoundError(f"Track directory not found: {track_dir}")

    result_files = _build_result_files(track_dir)
    if not result_files:
        raise RuntimeError(f"No audio stems found in {track_dir}")

    component_map = _build_component_map(result_files)
    if not component_map:
        raise RuntimeError(f"Unable to map drum components for {track_dir}")

    previous_payload: Dict[str, object] = {}
    payload_path = track_dir / "drum_analysis.json"
    if payload_path.exists():
        try:
            previous_payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            logger.warning("Existing drum_analysis.json is invalid JSON: %s", exc)

    return TrackContext(
        track_dir=track_dir,
        result_files=result_files,
        component_map=component_map,
        previous_payload=previous_payload,
    )


def _pick_reference_stem(component_map: Dict[str, str]) -> str:
    for key in ("drums", "drumsep_drums"):
        path = component_map.get(key)
        if path and os.path.exists(path):
            return path

    for path in component_map.values():
        if path and os.path.exists(path):
            return path

    raise RuntimeError("No valid stem available for tempo estimation")


def _resolve_style(style_arg: str | None, payload: Dict[str, object]) -> str:
    if style_arg:
        return style_arg

    for key in ("style", "default_style", "styles"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, list) and value:
            return str(value[0])

    return "rock"


def _resolve_key(key_arg: str | None, payload: Dict[str, object]) -> str:
    if key_arg:
        return key_arg

    key_val = payload.get("key")
    if isinstance(key_val, str) and key_val.strip():
        return key_val

    return "C"


def _resolve_tempo(payload: Dict[str, object]) -> float | None:
    tempo_val = payload.get("tempo")
    if isinstance(tempo_val, (int, float)) and tempo_val > 0:
        return float(tempo_val)

    return None


def _resolve_beats(payload: Dict[str, object]) -> List[float] | None:
    beats = payload.get("beats")
    if isinstance(beats, list) and beats and all(isinstance(b, (int, float)) for b in beats):
        return [float(b) for b in beats]

    return None


def _run_analysis(
    ctx: TrackContext,
    *,
    tempo: float,
    beats: List[float] | None,
    style: str,
    key: str,
) -> Dict[str, object]:
    analyzer = AdvancedDrummerAnalysis(sample_rate=22050)
    logger.info("Component map keys: %s", sorted(ctx.component_map.keys()))
    profile = analyzer.analyze_drummer_performance(
        stem_files=ctx.component_map,
        tempo=tempo,
        style=style,
        key=key,
    )

    profile_path = ctx.track_dir / "drummer_profile.json"
    try:
        analyzer.save_profile(profile, str(profile_path))
    except Exception as exc:
        logger.warning("Failed to persist drummer profile: %s", exc)

    total_hits = sum(len(comp.hits) for comp in profile.components.values())
    groove = profile.groove

    components_serialized = {
        name: {
            "audio_file": comp.audio_file,
            "hit_count": len(comp.hits),
            "hits": list(comp.hits),
            "velocities": list(comp.velocities),
            "timing_deviations": list(comp.timing_deviations),
            "spectral_features": comp.spectral_features,
        }
        for name, comp in profile.components.items()
    }

    tempo_std = _tempo_std_from_beats(beats)

    payload = {
        "source": ctx.previous_payload.get("source", "advanced_reanalysis"),
        "source_file": ctx.previous_payload.get("source_file"),
        "output_directory": str(ctx.track_dir),
        "created_at": datetime.utcnow().isoformat(),
        "analysis_method": "advanced_drummer_analysis",
        "profile_file": str(profile_path),
        "tempo": float(profile.tempo or tempo),
        "tempo_variability_bpm_std": tempo_std
        if tempo_std is not None
        else ctx.previous_payload.get("tempo_variability_bpm_std"),
        "beats": list(beats or []),
        "style": profile.style or style,
        "key": profile.key or key,
        "duration": float(profile.duration or 0.0),
        "total_hits": int(total_hits),
        "components_analyzed": list(profile.components.keys()),
        "components": components_serialized,
        "groove_analysis": {
            "swing_factor": groove.swing_factor,
            "pocket_tightness": groove.pocket_tightness,
            "rhythmic_complexity": groove.rhythmic_complexity,
            "syncopation_level": groove.syncopation_level,
            "micro_timing_variance": groove.micro_timing_variance,
            "humanness_score": groove.humanness_score,
        },
        "personality_traits": profile.personality_traits,
        "technical_metrics": profile.technical_metrics,
        "component_interactions": profile.interaction_matrix,
        "signature_patterns": profile.signature_patterns,
        "stem_files_used": ctx.component_map,
    }

    return payload


def _tempo_std_from_beats(beats: List[float] | None) -> float | None:
    if not beats or len(beats) < 3:
        return None

    intervals = np.diff(np.array(beats, dtype=float))
    safe = intervals[intervals > 1e-3]
    if safe.size == 0:
        return None

    tempos = 60.0 / safe
    return float(np.std(tempos)) if tempos.size else None


def _write_payload(track_dir: Path, payload: Dict[str, object]) -> None:
    output_path = track_dir / "drum_analysis.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote updated drum_analysis.json to %s", output_path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-run AdvancedDrummerAnalysis on existing stems"
    )
    parser.add_argument(
        "track_dir",
        type=Path,
        help="Directory containing processed stems (e.g. processed_stems/drummer/song)",
    )
    parser.add_argument(
        "--style",
        help="Override style value (defaults to previous payload or 'rock')",
    )
    parser.add_argument(
        "--key",
        help="Override musical key (defaults to previous payload or 'C')",
    )
    parser.add_argument(
        "--tempo",
        type=float,
        help="Override tempo in BPM (defaults to previous payload or re-estimated)",
    )
    parser.add_argument(
        "--beats-json",
        type=Path,
        help="Optional path to JSON file containing beat times (seconds)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def _load_beats_override(beats_json: Path | None) -> List[float] | None:
    if not beats_json:
        return None

    data = json.loads(beats_json.read_text(encoding="utf-8"))
    if isinstance(data, list) and all(isinstance(b, (int, float)) for b in data):
        return [float(b) for b in data]

    raise ValueError("Beats JSON must be an array of numbers")


def main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    ctx = _load_track_context(args.track_dir)

    style = _resolve_style(args.style, ctx.previous_payload)
    key = _resolve_key(args.key, ctx.previous_payload)

    beats = _load_beats_override(args.beats_json) or _resolve_beats(ctx.previous_payload)

    if args.tempo and args.tempo > 0:
        tempo = float(args.tempo)
    else:
        tempo = _resolve_tempo(ctx.previous_payload) or 0.0
        if tempo <= 0:
            ref_stem = _pick_reference_stem(ctx.component_map)
            tempo, beats_auto = _estimate_tempo(ref_stem)
            if tempo <= 0:
                tempo = 120.0
            if beats is None and beats_auto:
                beats = beats_auto

    payload = _run_analysis(
        ctx,
        tempo=tempo,
        beats=beats,
        style=style,
        key=key,
    )

    _write_payload(ctx.track_dir, payload)


if __name__ == "__main__":
    main()
