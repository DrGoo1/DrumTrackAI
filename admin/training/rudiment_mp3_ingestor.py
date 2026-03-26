import argparse
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "drum_training.db"


@dataclass(frozen=True)
class RudimentAsset:
    rudiment_name: str
    rudiment_family: str
    audio_path: str
    rel_dir: str
    file_size: int


def _infer_family_from_name(name: str) -> str:
    n = name.lower().strip()
    if "flam" in n:
        return "flam"
    if "drag" in n or "ruff" in n:
        return "drag"
    if "paradiddle" in n:
        return "paradiddle"
    if "ratamacue" in n:
        return "ratamacue"
    if "stroke roll" in n or "bounce roll" in n or "roll" in n:
        return "roll"
    if "tap" in n:
        return "tap"
    return "other"


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS rudiment_fragments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT DEFAULT 'snare_rudiments',
            rudiment_name TEXT NOT NULL,
            rudiment_family TEXT,
            audio_path TEXT UNIQUE NOT NULL,
            rel_dir TEXT,
            format TEXT,
            file_size INTEGER,
            duration REAL,
            midi_path TEXT,
            midi_generated_at TIMESTAMP,
            tags_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    # Backwards-compatible migrations (SQLite supports ADD COLUMN)
    try:
        cur.execute("ALTER TABLE rudiment_fragments ADD COLUMN midi_path TEXT;")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE rudiment_fragments ADD COLUMN midi_generated_at TIMESTAMP;")
    except Exception:
        pass
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rudiment_fragments_name ON rudiment_fragments(rudiment_name);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_rudiment_fragments_family ON rudiment_fragments(rudiment_family);")
    conn.commit()


def _iter_mp3_files(root: Path) -> Iterable[Path]:
    yield from root.rglob("*.mp3")


def _extract_rudiment_name(path: Path) -> str:
    # Prefer parent folder name (matches your dataset layout)
    folder = path.parent.name
    if folder and folder.lower() not in {"new folder", "new folder (2)"}:
        return folder
    return path.stem


def _build_asset(root: Path, file_path: Path) -> RudimentAsset:
    rudiment_name = _extract_rudiment_name(file_path)
    rudiment_family = _infer_family_from_name(rudiment_name)
    rel_dir = file_path.resolve().relative_to(root.resolve()).parent.as_posix()
    stat = file_path.stat()
    return RudimentAsset(
        rudiment_name=rudiment_name,
        rudiment_family=rudiment_family,
        audio_path=str(file_path),
        rel_dir=rel_dir,
        file_size=int(stat.st_size),
    )


def ingest_rudiment_mp3s(*, db_path: Path, rudiments_root: Path, limit: Optional[int] = None) -> int:
    if not rudiments_root.exists():
        raise FileNotFoundError(f"Rudiments root not found: {rudiments_root}")

    conn = sqlite3.connect(str(db_path))
    try:
        ensure_schema(conn)

        files = list(_iter_mp3_files(rudiments_root))
        files.sort()
        if limit:
            files = files[:limit]

        cur = conn.cursor()
        inserted = 0
        for idx, f in enumerate(files, 1):
            asset = _build_asset(rudiments_root, f)
            cur.execute(
                """
                INSERT INTO rudiment_fragments (
                    source, rudiment_name, rudiment_family, audio_path, rel_dir, format, file_size, duration, tags_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(audio_path) DO UPDATE SET
                    rudiment_name=excluded.rudiment_name,
                    rudiment_family=excluded.rudiment_family,
                    rel_dir=excluded.rel_dir,
                    file_size=excluded.file_size;
                """,
                (
                    "snare_rudiments",
                    asset.rudiment_name,
                    asset.rudiment_family,
                    asset.audio_path,
                    asset.rel_dir,
                    "mp3",
                    asset.file_size,
                    None,
                    None,
                ),
            )
            inserted += 1

            if idx % 200 == 0:
                conn.commit()
                logger.info("Ingested %s/%s rudiment MP3s", idx, len(files))

        conn.commit()
        return inserted
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Snare Rudiments MP3 assets into drum_training.db")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--rudiments-root", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO))
    count = ingest_rudiment_mp3s(db_path=args.db, rudiments_root=args.rudiments_root, limit=args.limit)
    logger.info("Done. Upserted %s rudiment assets into %s", count, args.db)


if __name__ == "__main__":
    main()
