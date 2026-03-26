import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

from groove_event_extractor import GrooveConfig, GrooveAnalyzer
from groove_style_features import GrooveFeatureExtractor
from groove_stem_analyzer import analyze_from_stems

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "admin" / "drumtrackai.db"


def get_db_path() -> Path:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


BPMS_BY_ARCHETYPE = {
    "ballroom_blitz": 132.0,
    "billion_dollar": 134.0,
    "cissy_strut": 93.0,
    "come_together": 83.0,
    "crazy_train": 138.0,
    "fifty_ways_to_leave_your_lover": 103.0,
    "fool_in_the_rain": 89.0,
    "funky_drummer": 100.0,
    "hot_for_teacher": 94.0,
    "rosanna": 88.0,
    "sing_sing_sing": 110.0,
    "smells_like_teen_spirit": 117.0,
    "sunday_bloody_sunday": 103.0,
    "superstitious": 100.0,
    "take_five": 174.0,
    "tom_sawyer": 88.0,
    "walk_this_way": 108.0,
    "were_not_gonna_take_it": 148.0,
    "we_will_rock_you": 81.0,
    "wipe_out": 160.0,
}


def ensure_analysis_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    # Per-groove aggregate style features
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS groove_style_vectors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archetype_id TEXT UNIQUE NOT NULL,
            bpm REAL,
            swing_amount REAL,
            shuffle_amount REAL,
            backbeat_late_ms REAL,
            hat_open_ratio REAL,
            ghost_snare_ratio REAL,
            kick_density REAL,
            snare_density REAL,
            cymbal_density REAL,
            dynamics_spread REAL,
            ride_density REAL,
            ride_mean_velocity REAL,
            ride_bell_ratio REAL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(archetype_id) REFERENCES groove_archetypes(archetype_id)
        );
        """
    )
    # Backwards-compatible: add new ride_* columns if table already existed
    cur.execute("PRAGMA table_info(groove_style_vectors);")
    existing_cols = {row[1] for row in cur.fetchall()}
    for col_def in [
        ("ride_density", "REAL"),
        ("ride_mean_velocity", "REAL"),
        ("ride_bell_ratio", "REAL"),
    ]:
        name, ctype = col_def
        if name not in existing_cols:
            try:
                cur.execute(f"ALTER TABLE groove_style_vectors ADD COLUMN {name} {ctype};")
            except sqlite3.OperationalError:
                # Column might have been added by a concurrent migration; ignore.
                pass
    # Per-hit event data for each groove archetype
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS groove_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            archetype_id TEXT NOT NULL,
            bar INTEGER,
            step INTEGER,
            time_sec REAL,
            instrument TEXT,
            velocity REAL,
            timing_offset_ms REAL,
            limb TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(archetype_id) REFERENCES groove_archetypes(archetype_id)
        );
        """
    )
    conn.commit()


def list_archetypes(conn: sqlite3.Connection):
    cur = conn.cursor()
    cur.execute(
        "SELECT archetype_id, song_title, drum_path FROM groove_archetypes ORDER BY archetype_id;"
    )
    return cur.fetchall()


def list_missing_archetypes(conn: sqlite3.Connection):
    """Return archetypes that do not yet have a groove_style_vectors row.

    This lets us run analysis only for missing items when using --missing-only.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ga.archetype_id, ga.song_title, ga.drum_path
        FROM groove_archetypes AS ga
        LEFT JOIN groove_style_vectors AS gsv
            ON ga.archetype_id = gsv.archetype_id
        WHERE gsv.archetype_id IS NULL
        ORDER BY ga.archetype_id;
        """
    )
    return cur.fetchall()


def upsert_style_vector(
    conn: sqlite3.Connection,
    archetype_id: str,
    bpm: Optional[float] = None,
    swing_amount: Optional[float] = None,
    shuffle_amount: Optional[float] = None,
    backbeat_late_ms: Optional[float] = None,
    hat_open_ratio: Optional[float] = None,
    ghost_snare_ratio: Optional[float] = None,
    kick_density: Optional[float] = None,
    snare_density: Optional[float] = None,
    cymbal_density: Optional[float] = None,
    dynamics_spread: Optional[float] = None,
    ride_density: Optional[float] = None,
    ride_mean_velocity: Optional[float] = None,
    ride_bell_ratio: Optional[float] = None,
    notes: Optional[str] = None,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO groove_style_vectors (
            archetype_id, bpm, swing_amount, shuffle_amount,
            backbeat_late_ms, hat_open_ratio, ghost_snare_ratio,
            kick_density, snare_density, cymbal_density,
            dynamics_spread, ride_density, ride_mean_velocity, ride_bell_ratio,
            notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(archetype_id) DO UPDATE SET
            bpm=excluded.bpm,
            swing_amount=excluded.swing_amount,
            shuffle_amount=excluded.shuffle_amount,
            backbeat_late_ms=excluded.backbeat_late_ms,
            hat_open_ratio=excluded.hat_open_ratio,
            ghost_snare_ratio=excluded.ghost_snare_ratio,
            kick_density=excluded.kick_density,
            snare_density=excluded.snare_density,
            cymbal_density=excluded.cymbal_density,
            dynamics_spread=excluded.dynamics_spread,
            ride_density=excluded.ride_density,
            ride_mean_velocity=excluded.ride_mean_velocity,
            ride_bell_ratio=excluded.ride_bell_ratio,
            notes=excluded.notes,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            archetype_id,
            bpm,
            swing_amount,
            shuffle_amount,
            backbeat_late_ms,
            hat_open_ratio,
            ghost_snare_ratio,
            kick_density,
            snare_density,
            cymbal_density,
            dynamics_spread,
            ride_density,
            ride_mean_velocity,
            ride_bell_ratio,
            notes,
        ),
    )
    conn.commit()

def clear_events_for_archetype(conn: sqlite3.Connection, archetype_id: str) -> None:
    """Remove any existing events for this archetype so we can re-analyze."""
    cur = conn.cursor()
    cur.execute("DELETE FROM groove_events WHERE archetype_id = ?", (archetype_id,))
    conn.commit()


def insert_events_for_archetype(
    conn: sqlite3.Connection,
    archetype_id: str,
    events,
) -> None:
    """Bulk-insert per-hit events for a groove archetype.

    events is expected to be an iterable of GrooveEvent objects.
    """
    if not events:
        return
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT INTO groove_events (
            archetype_id, bar, step, time_sec,
            instrument, velocity, timing_offset_ms, limb
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                archetype_id,
                e.bar,
                e.subdivision,  # simple v1: store subdivision as step
                e.time_sec,
                e.instrument,
                e.velocity,
                e.timing_offset_ms,
                e.limb,
            )
            for e in events
        ],
    )
    conn.commit()


def analyze_one_groove(archetype_id: str, song_title: str, drum_path: str):
    """Analyze a single groove archetype using MVSEP stems only.

    If stems are missing or stem-based analysis fails, this archetype is
    skipped (no fallback to the raw drum mix).
    """
    print(f"Analyzing groove: {archetype_id} | {song_title}")
    print(f"  drum_path: {drum_path}")

    bpm = BPMS_BY_ARCHETYPE.get(archetype_id)
    if bpm is None:
        print(f"  WARNING: No BPM mapping for archetype_id={archetype_id}, skipping.")
        return [], {}

    cfg = GrooveConfig(bpm=bpm, time_signature=(4, 4), subdivisions_per_beat=4)

    try:
        events = analyze_from_stems(cfg, archetype_id)
        print(f"  Used MVSEP stems for {len(events)} events")
    except Exception as e:
        print(f"  WARNING: stem-based analysis failed or stems missing for {archetype_id}: {e}")
        print("  Skipping this archetype (no raw mix fallback).")
        return [], {}

    feat_extractor = GrooveFeatureExtractor(cfg)
    numeric_features, _text_summary = feat_extractor.analyze(events)

    features = {
        "bpm": numeric_features.get("bpm"),
        "swing_amount": None,
        "shuffle_amount": None,
        "backbeat_late_ms": numeric_features.get("backbeat_mean_offset_ms"),
        "hat_open_ratio": numeric_features.get("hat_open_ratio"),
        "ghost_snare_ratio": numeric_features.get("ghost_snare_fraction"),
        "kick_density": numeric_features.get("kick_hits_per_bar"),
        "snare_density": numeric_features.get("snare_hits_per_bar"),
        "cymbal_density": numeric_features.get("cymbal_hits_per_bar"),
        "dynamics_spread": numeric_features.get("velocity_std"),
        "ride_density": numeric_features.get("ride_hits_per_bar"),
        "ride_mean_velocity": numeric_features.get("ride_velocity_mean"),
        "ride_bell_ratio": numeric_features.get("ride_bell_ratio"),
        "notes": None,
    }
    return events, features


def analyze_all_grooves(missing_only: bool = False) -> None:
    db_path = get_db_path()
    print(f"Using DB: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        ensure_analysis_schema(conn)
        if missing_only:
            rows = list_missing_archetypes(conn)
            mode_label = "missing-only"
        else:
            rows = list_archetypes(conn)
            mode_label = "all"
        if not rows:
            if missing_only:
                print("No missing groove_style_vectors rows; nothing to analyze.")
            else:
                print("No groove_archetypes found. Run import_groove_archetypes first.")
            return

        print(f"Found {len(rows)} groove archetypes to analyze ({mode_label} mode).\n")
        for archetype_id, song_title, drum_path in rows:
            events, features = analyze_one_groove(archetype_id, song_title, drum_path)
            clear_events_for_archetype(conn, archetype_id)
            insert_events_for_archetype(conn, archetype_id, events)
            upsert_style_vector(
                conn,
                archetype_id=archetype_id,
                bpm=features.get("bpm"),
                swing_amount=features.get("swing_amount"),
                shuffle_amount=features.get("shuffle_amount"),
                backbeat_late_ms=features.get("backbeat_late_ms"),
                hat_open_ratio=features.get("hat_open_ratio"),
                ghost_snare_ratio=features.get("ghost_snare_ratio"),
                kick_density=features.get("kick_density"),
                snare_density=features.get("snare_density"),
                cymbal_density=features.get("cymbal_density"),
                dynamics_spread=features.get("dynamics_spread"),
                notes=features.get("notes"),
            )
        print("\nAnalysis pass complete.")
    finally:
        conn.close()

if __name__ == "__main__":
    import sys
    missing_only_flag = "--missing-only"
    missing_only = missing_only_flag in sys.argv[1:]
    if missing_only:
        print("Running in missing-only mode: only archetypes without groove_style_vectors rows will be analyzed.\n")
    analyze_all_grooves(missing_only=missing_only)
