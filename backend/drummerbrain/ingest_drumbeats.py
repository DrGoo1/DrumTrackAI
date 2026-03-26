import argparse
import bisect
import hashlib
import math
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from . import db as dtkdb
from .audio_core import analyze, analyze_full


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _song_key_and_variant(p: Path) -> Tuple[str, str]:
    name = p.stem
    lower = name.lower()
    if lower.endswith("_original"):
        return name[: -len("_original")], "original"
    if lower.endswith("_drum"):
        return name[: -len("_drum")], "drum"
    return name, "unknown"


def _iter_wavs(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.wav")
    yield from root.rglob("*.WAV")


def _quantize_onsets_to_events(
    *,
    onsets: List[float],
    beats: List[float],
    subdivisions_per_beat: int,
) -> List[Dict[str, Any]]:
    if not onsets or not beats or len(beats) < 2:
        return []

    beat_times = [float(b) for b in beats]
    beat_times.sort()

    events: List[Dict[str, Any]] = []
    for t in onsets:
        try:
            tt = float(t)
        except Exception:
            continue

        i = bisect.bisect_right(beat_times, tt) - 1
        if i < 0 or i >= (len(beat_times) - 1):
            continue

        b0 = float(beat_times[i])
        b1 = float(beat_times[i + 1])
        dur = b1 - b0
        if not (dur > 0.0) or not math.isfinite(dur):
            continue

        phase = (tt - b0) / dur
        if not math.isfinite(phase):
            continue

        sub = int(round(phase * float(subdivisions_per_beat)))
        if sub < 0:
            sub = 0

        if sub >= subdivisions_per_beat:
            i = i + 1
            sub = 0
            if i >= (len(beat_times) - 1):
                continue
            b0 = float(beat_times[i])
            b1 = float(beat_times[i + 1])
            dur = b1 - b0
            if not (dur > 0.0) or not math.isfinite(dur):
                continue

        q = b0 + (float(sub) / float(subdivisions_per_beat)) * dur
        err = abs(tt - q)
        strength = 1.0 - min(1.0, err / max(1e-9, (dur / float(subdivisions_per_beat))))

        events.append(
            {
                "t": float(q),
                "beat_index": int(i),
                "sub": int(sub),
                "subdiv": int(subdivisions_per_beat),
                "lane": "hit",
                "strength": float(strength),
            }
        )

    events.sort(key=lambda e: (float(e.get("t", 0.0)), int(e.get("beat_index", 0)), int(e.get("sub", 0))))
    return events


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[2] / "DrumBeats"))
    ap.add_argument("--dataset-id", default="drumbeats")
    ap.add_argument("--label", default="DrumBeats")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-bpm", type=float, default=50.0)
    ap.add_argument("--max-bpm", type=float, default=200.0)
    ap.add_argument("--subdiv", type=int, default=4)
    args = ap.parse_args()

    if int(args.subdiv) < 1:
        raise ValueError("--subdiv must be >= 1")

    root = Path(args.root)
    if not root.exists():
        raise FileNotFoundError(str(root))

    conn = dtkdb.connect()
    try:
        dtkdb.ensure_schema(conn)
        dtkdb.upsert_dataset(conn, dataset_id=str(args.dataset_id), label=str(args.label), root_path=str(root), dataset_type="audio_phrase")

        files = list(_iter_wavs(root))
        files.sort(key=lambda p: p.as_posix().lower())
        if int(args.limit or 0) > 0:
            files = files[: int(args.limit)]

        for p in files:
            song_key, variant = _song_key_and_variant(p)
            content_sha = _sha256_file(p)
            asset_id = f"{args.dataset_id}:{content_sha[:16]}"
            try:
                size_bytes = int(p.stat().st_size)
            except Exception:
                size_bytes = None

            dtkdb.upsert_audio_asset(
                conn,
                asset_id=asset_id,
                dataset_id=str(args.dataset_id),
                song_key=str(song_key),
                variant=str(variant),
                source_path=str(p),
                content_sha256=str(content_sha),
                size_bytes=size_bytes,
            )

            songmap = None
            beats = None
            onsets = None
            analysis_error: Optional[str] = None
            try:
                full = analyze_full(audio_path=str(p))
                full_beats = list(full.get("beat_times") or full.get("beatTimes") or full.get("beats") or [])
                full_duration = full.get("duration")
                if full_duration is not None and float(full_duration) <= 0.0:
                    raise RuntimeError("audio-core analyze-full produced non-positive duration")
                if len(full_beats) < 2:
                    raise RuntimeError("audio-core analyze-full produced insufficient beat grid")
                songmap = full
                beats = full_beats
            except Exception as e:
                songmap = None
                beats = None
                analysis_error = f"analyze_full_failed: {type(e).__name__}: {e}".strip()

            try:
                a = analyze(audio_path=str(p), min_bpm=float(args.min_bpm), max_bpm=float(args.max_bpm))
                onsets = list(a.get("onsets") or [])
                if beats is None:
                    b = list(a.get("beats") or [])
                    if len(b) >= 2:
                        beats = b
            except Exception as e:
                onsets = None
                if analysis_error is None:
                    analysis_error = f"analyze_failed: {type(e).__name__}: {e}".strip()

            dtkdb.upsert_audio_analysis(
                conn,
                asset_id=asset_id,
                analyzer="audio-core",
                analyzer_version=None,
                params={"min_bpm": float(args.min_bpm), "max_bpm": float(args.max_bpm)},
                songmap=songmap,
                onsets=onsets,
                beats=beats,
            )

            events = None
            features = None
            confidence = None
            transcription_error: Optional[str] = None
            try:
                if onsets is None or beats is None:
                    raise RuntimeError("missing onsets or beats")

                events = _quantize_onsets_to_events(
                    onsets=list(onsets),
                    beats=list(beats),
                    subdivisions_per_beat=int(args.subdiv),
                )
                if not events:
                    raise RuntimeError("quantization produced 0 events")
                unique_positions = len({(int(e["beat_index"]), int(e["sub"])) for e in events}) if events else 0
                mean_strength = (
                    sum(float(e.get("strength") or 0.0) for e in events) / float(len(events))
                    if events
                    else 0.0
                )
                features = {
                    "subdiv": int(args.subdiv),
                    "event_count": int(len(events)),
                    "unique_positions": int(unique_positions),
                    "mean_strength": float(mean_strength),
                    "variant": str(variant),
                }
                if beats and len(beats) > 1:
                    features["duration_s"] = float(float(beats[-1]) - float(beats[0]))

                base = 0.25
                if variant == "drum":
                    base = 0.6
                if events and beats and len(beats) > 1:
                    confidence = float(max(0.0, min(1.0, base + 0.4 * float(mean_strength))))
                else:
                    confidence = float(max(0.0, min(1.0, base - 0.2)))
            except Exception as e:
                events = None
                features = None
                confidence = 0.0
                transcription_error = f"{type(e).__name__}: {e}".strip()

            prov: Dict[str, Any] = {
                "dataset_id": str(args.dataset_id),
                "source_path": str(p),
                "content_sha256": str(content_sha),
                "analyzer": "audio-core",
                "params": {"min_bpm": float(args.min_bpm), "max_bpm": float(args.max_bpm), "subdiv": int(args.subdiv)},
            }
            if analysis_error is not None:
                prov["analysis_error"] = str(analysis_error)
            if transcription_error is not None:
                prov["error"] = str(transcription_error)

            dtkdb.upsert_transcription_artifact(
                conn,
                asset_id=asset_id,
                transcription_version=f"v1_onset_grid_{int(args.subdiv)}ppb",
                events=events,
                features=features,
                confidence=confidence,
                provenance=prov,
            )

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
