import argparse
import json
import logging
import re
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

from .egmd_midi_extractor import EGMDMIDIExtractor

logger = logging.getLogger(__name__)


DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "drum_training.db"


_EGMD_FILENAME_RE = re.compile(
    r"^(?P<idx>\d+?)_(?P<style>.+?)_(?P<bpm>\d+?)_beat_(?P<meter>\d+-\d+?)_(?P<take>\d+?)$",
    re.IGNORECASE,
)


def _iter_midi_files(midi_root: Path) -> Iterator[Path]:
    yield from midi_root.rglob("*.midi")
    yield from midi_root.rglob("*.mid")


def _paired_audio_path(audio_root: Path, midi_root: Path, midi_path: Path) -> Path:
    rel = midi_path.resolve().relative_to(midi_root.resolve())
    return (audio_root / rel).with_suffix(".wav")


def _parse_from_basename(basename: str) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
    m = _EGMD_FILENAME_RE.match(basename)
    if not m:
        return None, None, None, None

    style_detail = m.group("style")
    style_group = style_detail.split("-")[0].split("_")[0].lower() if style_detail else None

    tempo_bpm: Optional[int]
    try:
        tempo_bpm = int(m.group("bpm"))
    except Exception:
        tempo_bpm = None

    meter_raw = m.group("meter")
    meter = meter_raw.replace("-", "/") if meter_raw else None

    return style_detail, style_group, tempo_bpm, meter


def _infer_drummer_and_session(midi_root: Path, midi_path: Path) -> Tuple[Optional[str], Optional[str], str]:
    rel = midi_path.resolve().relative_to(midi_root.resolve())
    parts = rel.parts
    drummer_id = parts[0] if len(parts) >= 2 else None
    session = parts[1] if len(parts) >= 3 else None
    rel_dir = Path(*parts[:-1]).as_posix() if len(parts) > 1 else ""
    return drummer_id, session, rel_dir


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS egmd_phrases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset TEXT DEFAULT 'E-GMD',
            drummer_id TEXT,
            session TEXT,
            rel_dir TEXT,
            basename TEXT NOT NULL,
            style_detail TEXT,
            style_group TEXT,
            tempo_bpm INTEGER,
            meter TEXT,
            bars INTEGER,
            midi_path TEXT UNIQUE NOT NULL,
            audio_path TEXT,

            total_hits INTEGER,
            duration REAL,
            tempo REAL,
            time_signature TEXT,
            pattern_density REAL,
            swing_amount REAL,
            style_hints_json TEXT,

            feature_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    cur.execute("CREATE INDEX IF NOT EXISTS idx_egmd_phrases_style_group ON egmd_phrases(style_group);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_egmd_phrases_tempo_bpm ON egmd_phrases(tempo_bpm);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_egmd_phrases_meter ON egmd_phrases(meter);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_egmd_phrases_drummer ON egmd_phrases(drummer_id);")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS ingestion_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            progress_key TEXT UNIQUE NOT NULL,
            total_files INTEGER,
            processed_files INTEGER,
            upserted_rows INTEGER,
            last_source_path TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP
        );
        """
    )
    conn.commit()


def _progress_upsert(
    conn: sqlite3.Connection,
    *,
    progress_key: str,
    total_files: int,
    processed_files: int,
    upserted_rows: int,
    last_source_path: Optional[str],
    finished: bool,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO ingestion_progress (
            progress_key, total_files, processed_files, upserted_rows, last_source_path
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(progress_key) DO UPDATE SET
            total_files=excluded.total_files,
            processed_files=excluded.processed_files,
            upserted_rows=excluded.upserted_rows,
            last_source_path=excluded.last_source_path,
            updated_at=CURRENT_TIMESTAMP,
            finished_at=CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE finished_at END;
        """,
        (
            progress_key,
            int(total_files),
            int(processed_files),
            int(upserted_rows),
            last_source_path,
            1 if finished else 0,
        ),
    )


def _features_to_feature_json(features) -> str:
    payload = asdict(features)
    payload["drum_counts"] = features.drum_counts
    payload["velocity_stats"] = features.velocity_stats
    payload["timing_features"] = features.timing_features
    payload["sequential_patterns"] = features.sequential_patterns
    payload["hihat_articulations"] = features.hihat_articulations
    payload["fill_segments"] = features.fill_segments
    payload["velocity_curve"] = features.velocity_curve
    payload["style_hints"] = features.style_hints

    for k in list(payload.keys()):
        if k.endswith("_json"):
            payload.pop(k, None)

    return json.dumps(payload)


def _estimate_bars(duration_seconds: float, tempo_bpm: float, meter: str) -> Optional[int]:
    if not duration_seconds or not tempo_bpm or not meter:
        return None

    try:
        num, den = meter.split("/")
        numerator = int(num)
        denominator = int(den)
    except Exception:
        return None

    if denominator == 0:
        return None

    quarter_notes_per_beat = 4.0 / float(denominator)
    beats_per_bar = float(numerator)

    quarter_notes = (duration_seconds / 60.0) * float(tempo_bpm)
    beats = quarter_notes / quarter_notes_per_beat
    bars = beats / beats_per_bar

    if bars <= 0:
        return None

    return max(1, int(round(bars)))


def upsert_phrase(
    conn: sqlite3.Connection,
    *,
    dataset: str,
    midi_path: Path,
    audio_path: Path,
    drummer_id: Optional[str],
    session: Optional[str],
    rel_dir: str,
    basename: str,
    style_detail: Optional[str],
    style_group: Optional[str],
    tempo_bpm_from_name: Optional[int],
    meter_from_name: Optional[str],
    features,
) -> None:
    audio_value = str(audio_path) if audio_path.exists() else None

    tempo_from_features = float(getattr(features, "tempo", 0.0) or 0.0)
    meter_from_features = getattr(features, "time_signature", None)

    effective_meter = meter_from_name or meter_from_features
    bars = _estimate_bars(float(features.duration or 0.0), tempo_from_features, effective_meter or "")

    style_hints_json = json.dumps(features.style_hints or [])
    feature_json = _features_to_feature_json(features)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO egmd_phrases (
            dataset, drummer_id, session, rel_dir, basename,
            style_detail, style_group, tempo_bpm, meter, bars,
            midi_path, audio_path,
            total_hits, duration, tempo, time_signature, pattern_density, swing_amount, style_hints_json,
            feature_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(midi_path) DO UPDATE SET
            dataset=excluded.dataset,
            drummer_id=excluded.drummer_id,
            session=excluded.session,
            rel_dir=excluded.rel_dir,
            basename=excluded.basename,
            style_detail=excluded.style_detail,
            style_group=excluded.style_group,
            tempo_bpm=excluded.tempo_bpm,
            meter=excluded.meter,
            bars=excluded.bars,
            audio_path=excluded.audio_path,
            total_hits=excluded.total_hits,
            duration=excluded.duration,
            tempo=excluded.tempo,
            time_signature=excluded.time_signature,
            pattern_density=excluded.pattern_density,
            swing_amount=excluded.swing_amount,
            style_hints_json=excluded.style_hints_json,
            feature_json=excluded.feature_json;
        """,
        (
            dataset,
            drummer_id,
            session,
            rel_dir,
            basename,
            style_detail,
            style_group,
            tempo_bpm_from_name,
            meter_from_name,
            bars,
            str(midi_path),
            audio_value,
            int(features.total_hits or 0),
            float(features.duration or 0.0),
            tempo_from_features,
            meter_from_features,
            float(features.pattern_density or 0.0),
            float(features.swing_amount or 0.0),
            style_hints_json,
            feature_json,
        ),
    )


def ingest_egmd_phrases(
    *,
    db_path: Path,
    midi_root: Path,
    audio_root: Path,
    dataset: str = "E-GMD",
    limit: Optional[int] = None,
    progress_key: str = "egmd_phrases",
    progress_interval: int = 250,
) -> int:
    extractor = EGMDMIDIExtractor(db_path=str(db_path))

    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)

        midi_files = list(_iter_midi_files(midi_root))
        midi_files.sort()
        if limit:
            midi_files = midi_files[:limit]

        total_files = len(midi_files)
        _progress_upsert(
            conn,
            progress_key=progress_key,
            total_files=total_files,
            processed_files=0,
            upserted_rows=0,
            last_source_path=None,
            finished=False,
        )
        conn.commit()

        inserted = 0
        processed = 0
        last_path: Optional[str] = None
        for i, midi_path in enumerate(midi_files, 1):
            processed = i
            last_path = str(midi_path)
            if progress_interval > 0 and i % progress_interval == 0:
                logger.info("Processing %s/%s...", i, len(midi_files))

            try:
                audio_path = _paired_audio_path(audio_root, midi_root, midi_path)
                drummer_id, session, rel_dir = _infer_drummer_and_session(midi_root, midi_path)

                basename = midi_path.stem
                style_detail, style_group, tempo_bpm, meter = _parse_from_basename(basename)

                features = extractor.extract_from_file(midi_path)
                if not features:
                    continue

                upsert_phrase(
                    conn,
                    dataset=dataset,
                    midi_path=midi_path,
                    audio_path=audio_path,
                    drummer_id=drummer_id,
                    session=session,
                    rel_dir=rel_dir,
                    basename=basename,
                    style_detail=style_detail,
                    style_group=style_group,
                    tempo_bpm_from_name=tempo_bpm,
                    meter_from_name=meter,
                    features=features,
                )
                inserted += 1

                if inserted % 200 == 0:
                    conn.commit()

                if progress_interval > 0 and i % progress_interval == 0:
                    _progress_upsert(
                        conn,
                        progress_key=progress_key,
                        total_files=total_files,
                        processed_files=processed,
                        upserted_rows=inserted,
                        last_source_path=last_path,
                        finished=False,
                    )
                    conn.commit()

            except Exception as e:
                logger.exception("Failed ingesting %s: %s", midi_path, e)

        _progress_upsert(
            conn,
            progress_key=progress_key,
            total_files=total_files,
            processed_files=processed,
            upserted_rows=inserted,
            last_source_path=last_path,
            finished=True,
        )
        conn.commit()
        return inserted
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest E-GMD paired MIDI+WAV phrases into drum_training.db")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to admin/data/drum_training.db",
    )
    parser.add_argument(
        "--midi-root",
        type=Path,
        required=True,
        help="Root of E-GMD MIDI folder (e.g. E:/E-GMD Dataset/e-gmd-v1.0.0-midi/e-gmd-v1.0.0)",
    )
    parser.add_argument(
        "--audio-root",
        type=Path,
        required=True,
        help="Root of E-GMD audio folder (e.g. E:/E-GMD Dataset/e-gmd-v1.0.0/e-gmd-v1.0.0)",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--progress-key", default="egmd_phrases")
    parser.add_argument("--progress-interval", type=int, default=250)
    parser.add_argument("--log-level", default="INFO")

    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))

    inserted = ingest_egmd_phrases(
        db_path=args.db,
        midi_root=args.midi_root,
        audio_root=args.audio_root,
        limit=args.limit,
        progress_key=str(args.progress_key),
        progress_interval=int(args.progress_interval),
    )
    logger.info("Done. Upserted %s phrases into %s", inserted, args.db)


if __name__ == "__main__":
    main()
