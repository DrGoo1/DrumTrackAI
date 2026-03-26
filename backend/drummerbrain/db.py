import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def resolve_drummerbrain_db_path() -> Path:
    p = os.getenv("DRUMMERBRAIN_DB_PATH")
    if p:
        return Path(p)
    return Path(__file__).resolve().parents[2] / "admin" / "data" / "drummerbrain_clips.db"


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    p = db_path or resolve_drummerbrain_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS datasets (
            dataset_id TEXT PRIMARY KEY,
            label TEXT,
            root_path TEXT,
            dataset_type TEXT,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audio_assets (
            asset_id TEXT PRIMARY KEY,
            dataset_id TEXT NOT NULL,
            song_key TEXT,
            variant TEXT,
            source_path TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            size_bytes INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(dataset_id, source_path),
            UNIQUE(dataset_id, content_sha256)
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS audio_analysis (
            asset_id TEXT PRIMARY KEY,
            analyzer TEXT NOT NULL,
            analyzer_version TEXT,
            params_json TEXT,
            songmap_json TEXT,
            onsets_json TEXT,
            beats_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS transcription_artifacts (
            asset_id TEXT PRIMARY KEY,
            transcription_version TEXT NOT NULL,
            events_json TEXT,
            features_json TEXT,
            confidence REAL,
            provenance_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    # Optional many-to-many mapping between anonymized drummer IDs and
    # public-facing, copyright-safe category IDs.
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS drummers (
            drummer_id TEXT PRIMARY KEY,
            display_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            category_id TEXT PRIMARY KEY,
            label TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS drummer_category_assignments (
            drummer_id TEXT NOT NULL,
            category_id TEXT NOT NULL,
            weight REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (drummer_id, category_id)
        );
        """
    )
    conn.commit()


def upsert_drummer(conn: sqlite3.Connection, *, drummer_id: str, display_name: Optional[str] = None) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO drummers(drummer_id, display_name)
        VALUES(?, ?)
        ON CONFLICT(drummer_id) DO UPDATE SET
            display_name=COALESCE(excluded.display_name, drummers.display_name);
        """,
        (str(drummer_id), str(display_name) if display_name is not None else None),
    )
    conn.commit()


def upsert_category(conn: sqlite3.Connection, *, category_id: str, label: Optional[str] = None) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO categories(category_id, label)
        VALUES(?, ?)
        ON CONFLICT(category_id) DO UPDATE SET
            label=COALESCE(excluded.label, categories.label);
        """,
        (str(category_id), str(label) if label is not None else None),
    )
    conn.commit()


def upsert_drummer_category_assignment(
    conn: sqlite3.Connection,
    *,
    drummer_id: str,
    category_id: str,
    weight: Optional[float] = None,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO drummer_category_assignments(drummer_id, category_id, weight)
        VALUES(?, ?, ?)
        ON CONFLICT(drummer_id, category_id) DO UPDATE SET
            weight=COALESCE(excluded.weight, drummer_category_assignments.weight);
        """,
        (
            str(drummer_id),
            str(category_id),
            float(weight) if weight is not None else None,
        ),
    )
    conn.commit()


def list_categories_for_drummer(conn: sqlite3.Connection, *, drummer_id: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.category_id, c.label, a.weight
        FROM drummer_category_assignments a
        LEFT JOIN categories c ON c.category_id = a.category_id
        WHERE a.drummer_id = ?
        ORDER BY a.category_id
        """,
        (str(drummer_id),),
    )
    rows = cur.fetchall() or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "category_id": str(r["category_id"]),
                "label": str(r["label"] or ""),
                "weight": float(r["weight"]) if r["weight"] is not None else None,
            }
        )
    return out


def list_drummers_for_category(conn: sqlite3.Connection, *, category_id: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT a.drummer_id, d.display_name, a.weight
        FROM drummer_category_assignments a
        LEFT JOIN drummers d ON d.drummer_id = a.drummer_id
        WHERE a.category_id = ?
        ORDER BY a.drummer_id
        """,
        (str(category_id),),
    )
    rows = cur.fetchall() or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "drummer_id": str(r["drummer_id"]),
                "display_name": str(r["display_name"] or ""),
                "weight": float(r["weight"]) if r["weight"] is not None else None,
            }
        )
    return out


def set_dataset_enabled(conn: sqlite3.Connection, *, dataset_id: str, enabled: bool) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE datasets
        SET enabled = ?
        WHERE dataset_id = ?
        """,
        (1 if bool(enabled) else 0, str(dataset_id)),
    )
    conn.commit()


def list_datasets(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT dataset_id, label, dataset_type, root_path, enabled, created_at
        FROM datasets
        ORDER BY dataset_id
        """
    )
    rows = cur.fetchall() or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        try:
            out.append(
                {
                    "dataset_id": str(r["dataset_id"]),
                    "label": str(r["label"] or ""),
                    "dataset_type": str(r["dataset_type"] or ""),
                    "root_path": str(r["root_path"] or ""),
                    "enabled": int(r["enabled"] or 0),
                    "created_at": str(r["created_at"] or ""),
                }
            )
        except Exception:
            continue
    return out


def upsert_dataset(conn: sqlite3.Connection, *, dataset_id: str, label: str, root_path: str, dataset_type: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO datasets(dataset_id, label, root_path, dataset_type)
        VALUES(?, ?, ?, ?)
        ON CONFLICT(dataset_id) DO UPDATE SET
            label=excluded.label,
            root_path=excluded.root_path,
            dataset_type=excluded.dataset_type;
        """,
        (dataset_id, label, root_path, dataset_type),
    )
    conn.commit()


def upsert_audio_asset(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    dataset_id: str,
    song_key: Optional[str],
    variant: Optional[str],
    source_path: str,
    content_sha256: str,
    size_bytes: Optional[int],
) -> None:
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO audio_assets(asset_id, dataset_id, song_key, variant, source_path, content_sha256, size_bytes)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dataset_id, source_path) DO UPDATE SET
                asset_id=excluded.asset_id,
                song_key=excluded.song_key,
                variant=excluded.variant,
                content_sha256=excluded.content_sha256,
                size_bytes=excluded.size_bytes;
            """,
            (asset_id, dataset_id, song_key, variant, source_path, content_sha256, size_bytes),
        )
    except sqlite3.IntegrityError as e:
        # If two files in the same dataset are byte-identical, the UNIQUE(dataset_id, content_sha256)
        # constraint will be hit. For ingestion purposes, it's safe to ignore the duplicate.
        msg = str(e).lower()
        if "content_sha256" in msg or "content_sha" in msg:
            return
        raise
    conn.commit()


def upsert_audio_analysis(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    analyzer: str,
    analyzer_version: Optional[str],
    params: Dict[str, Any],
    songmap: Optional[Dict[str, Any]],
    onsets: Optional[List[float]],
    beats: Optional[List[float]],
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO audio_analysis(asset_id, analyzer, analyzer_version, params_json, songmap_json, onsets_json, beats_json)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
            analyzer=excluded.analyzer,
            analyzer_version=excluded.analyzer_version,
            params_json=excluded.params_json,
            songmap_json=excluded.songmap_json,
            onsets_json=excluded.onsets_json,
            beats_json=excluded.beats_json,
            created_at=CURRENT_TIMESTAMP;
        """,
        (
            asset_id,
            analyzer,
            analyzer_version,
            json.dumps(params or {}, ensure_ascii=False),
            json.dumps(songmap or {}, ensure_ascii=False) if songmap is not None else None,
            json.dumps(onsets or [], ensure_ascii=False) if onsets is not None else None,
            json.dumps(beats or [], ensure_ascii=False) if beats is not None else None,
        ),
    )
    conn.commit()


def upsert_transcription_artifact(
    conn: sqlite3.Connection,
    *,
    asset_id: str,
    transcription_version: str,
    events: Optional[List[Dict[str, Any]]],
    features: Optional[Dict[str, Any]],
    confidence: Optional[float],
    provenance: Dict[str, Any],
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO transcription_artifacts(asset_id, transcription_version, events_json, features_json, confidence, provenance_json)
        VALUES(?, ?, ?, ?, ?, ?)
        ON CONFLICT(asset_id) DO UPDATE SET
            transcription_version=excluded.transcription_version,
            events_json=excluded.events_json,
            features_json=excluded.features_json,
            confidence=excluded.confidence,
            provenance_json=excluded.provenance_json,
            created_at=CURRENT_TIMESTAMP;
        """,
        (
            asset_id,
            transcription_version,
            json.dumps(events or [], ensure_ascii=False) if events is not None else None,
            json.dumps(features or {}, ensure_ascii=False) if features is not None else None,
            float(confidence) if confidence is not None else None,
            json.dumps(provenance or {}, ensure_ascii=False),
        ),
    )
    conn.commit()
