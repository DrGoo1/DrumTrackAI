import os
import re
import sqlite3
import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


AUDIO_EXTS = {".wav", ".aif", ".aiff", ".flac", ".mp3"}


@dataclass(frozen=True)
class CollectionSpec:
    collection_name: str
    folder_path: Path
    category: Optional[str] = None
    manufacturer: Optional[str] = None
    description: Optional[str] = None


def _as_posix_relpath(path: Path, root: Path) -> str:
    # Always store portable DB paths with POSIX separators
    return path.resolve().relative_to(root.resolve()).as_posix()


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _identify_drum_type_from_path(path: Path) -> str:
    parts = [p.lower() for p in path.parts]
    name = path.stem.lower()

    def has_any(haystack: str, needles: Iterable[str]) -> bool:
        return any(n in haystack for n in needles)

    folder_blob = " ".join(parts)
    if has_any(folder_blob, ["kick"]):
        return "kick"
    if has_any(folder_blob, ["snare"]):
        return "snare"
    if has_any(folder_blob, ["hihat", "hi hat", "hat", "hh"]):
        return "hihat"
    if has_any(folder_blob, ["ride"]):
        return "ride"
    if has_any(folder_blob, ["crash", "cymbal", "splash", "china", "stack"]):
        return "cymbal"
    if has_any(folder_blob, ["tom", "rack", "floor"]):
        return "tom"

    if has_any(name, ["kick", "bd", "bassdrum", "bass_drum", "bass-drum"]):
        return "kick"
    if has_any(name, ["snare", "sd"]):
        return "snare"
    if has_any(name, ["hihat", "hi_hat", "hi-hat", "hh", "hat"]):
        return "hihat"
    if "ride" in name:
        return "ride"
    if has_any(name, ["crash", "cymbal", "splash", "china", "stack"]):
        return "cymbal"
    if has_any(name, ["tom", "rack", "floor"]):
        return "tom"

    return "unknown"


def _extract_variation(path: Path) -> Optional[str]:
    m = re.search(r"(?:vel|velocity)[ _-]?(\d{1,3})", path.stem, flags=re.IGNORECASE)
    if m:
        return f"vel{m.group(1)}"
    m = re.search(r"\b(rr|roundrobin)[ _-]?(\d{1,2})\b", path.stem, flags=re.IGNORECASE)
    if m:
        return f"rr{m.group(2)}"
    return None


def _list_audio_files(root: Path) -> List[Path]:
    files: List[Path] = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            p = Path(dirpath) / fn
            if p.suffix.lower() in AUDIO_EXTS:
                files.append(p)
    files.sort(key=lambda x: str(x).lower())
    return files


def _ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sample_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_name TEXT NOT NULL,
            description TEXT,
            manufacturer TEXT,
            category TEXT,
            folder_path TEXT,
            sample_count INTEGER,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS drum_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            file_name TEXT,
            file_size INTEGER,
            drum_type TEXT,
            variation TEXT,
            sample_rate INTEGER,
            bit_depth INTEGER,
            duration_ms REAL,
            format TEXT,
            category TEXT,
            genre TEXT,
            style TEXT,
            manufacturer TEXT,
            kit_name TEXT,
            peak_amplitude REAL,
            rms_level REAL,
            frequency_range TEXT,
            transient_sharpness REAL,
            quality_rating INTEGER,
            usage_count INTEGER,
            tags TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS collection_samples (
            collection_id INTEGER,
            sample_id INTEGER
        )
        """
    )
    conn.commit()


def _get_table_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [r[1] for r in cur.fetchall()]


def _upsert_collection(conn: sqlite3.Connection, spec: CollectionSpec) -> int:
    cols = _get_table_columns(conn, "sample_collections")
    now = _now_iso()

    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM sample_collections WHERE folder_path = ?",
        (spec.folder_path.as_posix(),),
    )
    row = cur.fetchone()

    if row:
        collection_id = int(row[0])
        updates: Dict[str, Optional[str]] = {
            "collection_name": spec.collection_name,
            "description": spec.description,
            "manufacturer": spec.manufacturer,
            "category": spec.category,
        }
        set_pairs = []
        params: List[object] = []
        for k, v in updates.items():
            if k in cols:
                set_pairs.append(f"{k} = ?")
                params.append(v)
        if "created_at" in cols:
            set_pairs.append("created_at = COALESCE(created_at, ?)")
            params.append(now)
        if set_pairs:
            params.append(collection_id)
            cur.execute(
                f"UPDATE sample_collections SET {', '.join(set_pairs)} WHERE id = ?",
                params,
            )
        conn.commit()
        return collection_id

    insert_cols: List[str] = []
    insert_vals: List[object] = []

    def add(k: str, v: object) -> None:
        if k in cols:
            insert_cols.append(k)
            insert_vals.append(v)

    add("collection_name", spec.collection_name)
    add("description", spec.description)
    add("manufacturer", spec.manufacturer)
    add("category", spec.category)
    add("folder_path", spec.folder_path.as_posix())
    add("sample_count", 0)
    add("created_at", now)

    cur.execute(
        f"INSERT INTO sample_collections ({', '.join(insert_cols)}) VALUES ({', '.join(['?']*len(insert_cols))})",
        insert_vals,
    )
    conn.commit()
    return int(cur.lastrowid)


def _insert_sample(
    conn: sqlite3.Connection,
    file_path: Path,
    spec: CollectionSpec,
    *,
    file_name: Optional[str] = None,
    file_size: Optional[int] = None,
    file_format: Optional[str] = None,
) -> int:
    cols = _get_table_columns(conn, "drum_samples")
    now = _now_iso()

    db_file_path = file_path.as_posix()

    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM drum_samples WHERE file_path = ?",
        (db_file_path,),
    )
    row = cur.fetchone()
    if row:
        return int(row[0])

    if file_name is None:
        file_name = file_path.name
    if file_format is None:
        file_format = file_path.suffix.lower().lstrip(".")

    insert_cols: List[str] = []
    insert_vals: List[object] = []

    def add(k: str, v: object) -> None:
        if k in cols:
            insert_cols.append(k)
            insert_vals.append(v)

    add("file_path", db_file_path)
    add("file_name", file_name)
    if file_size is not None:
        add("file_size", int(file_size))
    add("drum_type", _identify_drum_type_from_path(file_path))
    add("variation", _extract_variation(file_path))
    add("format", file_format)
    add("category", spec.category)
    add("manufacturer", spec.manufacturer)
    add("kit_name", spec.collection_name)
    add("created_at", now)
    add("updated_at", now)

    cur.execute(
        f"INSERT INTO drum_samples ({', '.join(insert_cols)}) VALUES ({', '.join(['?']*len(insert_cols))})",
        insert_vals,
    )
    conn.commit()
    return int(cur.lastrowid)


def _link_collection_sample(conn: sqlite3.Connection, collection_id: int, sample_id: int) -> None:
    cols = _get_table_columns(conn, "collection_samples")
    if not ("collection_id" in cols and "sample_id" in cols):
        return
    cur = conn.cursor()
    cur.execute(
        "SELECT 1 FROM collection_samples WHERE collection_id = ? AND sample_id = ? LIMIT 1",
        (collection_id, sample_id),
    )
    if cur.fetchone():
        return
    cur.execute(
        "INSERT INTO collection_samples (collection_id, sample_id) VALUES (?, ?)",
        (collection_id, sample_id),
    )
    conn.commit()


def _update_collection_sample_count(conn: sqlite3.Connection, collection_id: int) -> None:
    cols = _get_table_columns(conn, "sample_collections")
    if "sample_count" not in cols:
        return
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM collection_samples WHERE collection_id = ?",
        (collection_id,),
    )
    count = int(cur.fetchone()[0])
    cur.execute(
        "UPDATE sample_collections SET sample_count = ? WHERE id = ?",
        (count, collection_id),
    )
    conn.commit()


def import_collections(db_path: Path, collections: List[CollectionSpec], *, samples_root: Optional[Path] = None) -> Tuple[int, int]:
    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema(conn)
        total_collections = 0
        total_samples = 0
        for spec in collections:
            if not spec.folder_path.exists() or not spec.folder_path.is_dir():
                continue

            if samples_root is not None:
                rel_folder = _as_posix_relpath(spec.folder_path, samples_root)
                spec = CollectionSpec(
                    collection_name=spec.collection_name,
                    folder_path=Path(rel_folder),
                    category=spec.category,
                    manufacturer=spec.manufacturer,
                    description=spec.description,
                )

            collection_id = _upsert_collection(conn, spec)
            total_collections += 1

            scan_root = spec.folder_path
            if samples_root is not None:
                scan_root = samples_root / Path(str(spec.folder_path))

            files = _list_audio_files(scan_root)
            for fp in files:
                fp_for_db = fp
                if samples_root is not None:
                    fp_for_db = Path(_as_posix_relpath(fp, samples_root))

                stat = fp.stat()
                sample_id = _insert_sample(
                    conn,
                    fp_for_db,
                    spec,
                    file_name=fp.name,
                    file_size=int(stat.st_size),
                    file_format=fp.suffix.lower().lstrip("."),
                )
                _link_collection_sample(conn, collection_id, sample_id)
                total_samples += 1

            _update_collection_sample_count(conn, collection_id)

        return total_collections, total_samples
    finally:
        conn.close()


def reset_samples(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute("DELETE FROM collection_samples")
    cur.execute("DELETE FROM drum_samples")
    cur.execute("DELETE FROM sample_collections")
    conn.commit()


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=os.getenv("SAMPLE_DB_PATH") or str(project_root / "admin" / "drumtrackai.db"))
    parser.add_argument("--samples-root", default=os.getenv("SAMPLES_HOST_ROOT") or r"E:\\Drum Samples")
    parser.add_argument("--extra-root", action="append", default=None)
    parser.add_argument("--store-absolute-paths", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    db_path = Path(args.db)
    samples_root = Path(args.samples_root)

    roots: Dict[str, Path] = {
        "Drum Samples": samples_root,
        "Kick Samples": samples_root / "Kick Samples",
        "Snare Samples": samples_root / "Snare Samples",
        "Effect Cymbal Samples": samples_root / "Effect Cymbal Samples",
        "Tom1": samples_root / "Tom1 (very high)",
        "Tom2": samples_root / "Tom2 (high)",
        "Tom3": samples_root / "Tom3 (medium)",
        "Tom4": samples_root / "Tom4 (low)",
    }

    if args.extra_root:
        for extra in args.extra_root:
            p = Path(str(extra))
            roots[p.name] = p

    collections = [CollectionSpec(collection_name=name, folder_path=path, category="local") for name, path in roots.items()]

    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema(conn)
        if args.reset:
            reset_samples(conn)
    finally:
        conn.close()

    rel_root = samples_root
    if args.store_absolute_paths:
        rel_root = None
    imported_collections, imported_samples = import_collections(db_path, collections, samples_root=rel_root)
    print(f"Imported collections: {imported_collections}")
    print(f"Imported samples: {imported_samples}")
    print(f"DB: {db_path}")
    print(f"Samples root: {samples_root}")


if __name__ == "__main__":
    main()
