import os
import re
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DRUM_BEATS_DIR = PROJECT_ROOT / "DrumBeats"
# Canonical admin/analysis DB
DEFAULT_DB_PATH = PROJECT_ROOT / "admin" / "drumtrackai.db"


def get_db_path() -> Path:
    """Resolve the DB path, honoring DRUMTRACKAI_DB_PATH if set."""
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Ensure tables for groove archetypes exist."""
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS groove_archetypes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archetype_id TEXT UNIQUE NOT NULL,
            song_title TEXT NOT NULL,
            drum_path TEXT NOT NULL,
            original_path TEXT,
            public_persona_id TEXT,
            drummer_display_name TEXT,
            bpm REAL,
            time_signature TEXT,
            bars INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def slugify(name: str) -> str:
    s = name.strip().lower()
    s = s.replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def parse_groove_key(filename: str) -> Tuple[str, str]:
    """Return (base_key, kind) where kind is 'drum' or 'original'."""
    name = filename
    lower = name.lower()
    if lower.endswith("_drum.wav"):
        base = name[: -len("_drum.wav")]
        return base, "drum"
    # handle several original variants
    for suffix in ("_original.wav", "_orig.wav", "_origianl.wav"):
        if lower.endswith(suffix):
            base = name[: -len(suffix)]
            return base, "original"
    # default: treat as original clip
    base = os.path.splitext(name)[0]
    return base, "original"


def scan_drum_beats() -> Dict[str, Dict[str, Path]]:
    """Scan DrumBeats dir and group files by base key.

    Returns: { base_key: {"drum": Path, "original": Path} }
    """
    if not DRUM_BEATS_DIR.exists():
        raise FileNotFoundError(f"DrumBeats folder not found at {DRUM_BEATS_DIR}")

    groups: Dict[str, Dict[str, Path]] = {}
    for entry in DRUM_BEATS_DIR.iterdir():
        if not entry.is_file():
            continue
        if not entry.name.lower().endswith(".wav"):
            continue
        base_key, kind = parse_groove_key(entry.name)
        group = groups.setdefault(base_key, {})
        # Prefer explicit drum/original naming; last one wins if duplicates
        group[kind] = entry
    return groups


def upsert_groove(conn: sqlite3.Connection, base_key: str, drum_path: Path, original_path: Optional[Path]) -> None:
    song_title = base_key.replace("_", " ").strip()
    archetype_id = slugify(base_key)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO groove_archetypes (archetype_id, song_title, drum_path, original_path)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(archetype_id) DO UPDATE SET
            song_title=excluded.song_title,
            drum_path=excluded.drum_path,
            original_path=excluded.original_path,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            archetype_id,
            song_title,
            str(drum_path),
            str(original_path) if original_path is not None else None,
        ),
    )
    conn.commit()


def import_grooves() -> None:
    db_path = get_db_path()
    print(f"Using DB: {db_path}")
    print(f"Scanning grooves in: {DRUM_BEATS_DIR}")

    conn = sqlite3.connect(db_path)
    try:
        ensure_schema(conn)
        groups = scan_drum_beats()
        if not groups:
            print("No WAV files found in DrumBeats folder.")
            return

        count = 0
        for base_key, files in sorted(groups.items()):
            drum = files.get("drum")
            if drum is None:
                # only keep entries that have a drum-only file
                continue
            original = files.get("original")
            upsert_groove(conn, base_key, drum, original)
            print(f"Registered groove: {base_key} (archetype_id={slugify(base_key)})")
            count += 1

        print(f"\nImported/updated {count} groove archetypes.")
    finally:
        conn.close()


if __name__ == "__main__":
    import_grooves()
