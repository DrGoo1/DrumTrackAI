"""Upsert a drummer persona into the admin DB from groove_style_vectors.

Usage (from project root):

    python admin/tools/upsert_drummer_persona.py \
        porcaro_shuffle "Porcaro Shuffle" rosanna fool_in_the_rain

This will:
- Read groove_style_vectors for the given archetypes.
- Aggregate core metrics (timing, densities, dynamics).
- Upsert a row into drummer_personas.
"""

import argparse
import json
import os
import sqlite3
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "admin" / "drumtrackai.db"

METRIC_COLUMNS = [
    "bpm",
    "backbeat_late_ms",
    "hat_open_ratio",
    "ghost_snare_ratio",
    "kick_density",
    "snare_density",
    "cymbal_density",
    "dynamics_spread",
    "ride_density",
    "ride_mean_velocity",
    "ride_bell_ratio",
]


def get_db_path() -> Path:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    return Path(env) if env else DEFAULT_DB


def fetch_vectors(conn: sqlite3.Connection, archetype_ids: List[str]):
    cur = conn.cursor()
    placeholders = ",".join(["?"] * len(archetype_ids))
    cur.execute(
        f"""
        SELECT archetype_id,
               bpm,
               backbeat_late_ms,
               hat_open_ratio,
               ghost_snare_ratio,
               kick_density,
               snare_density,
               cymbal_density,
               dynamics_spread
        FROM groove_style_vectors
        WHERE archetype_id IN ({placeholders})
        ORDER BY archetype_id
        """,
        archetype_ids,
    )
    return cur.fetchall()


def aggregate_metrics(rows):
    if not rows:
        return None

    sums = {col: 0.0 for col in METRIC_COLUMNS}
    counts = {col: 0 for col in METRIC_COLUMNS}

    for _archetype_id, *metric_vals in rows:
        for col, val in zip(METRIC_COLUMNS, metric_vals):
            if val is None:
                continue
            sums[col] += float(val)
            counts[col] += 1

    means = {}
    for col in METRIC_COLUMNS:
        if counts[col] > 0:
            means[col] = sums[col] / counts[col]
        else:
            means[col] = None
    return means


def ensure_drummer_personas_schema(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS drummer_personas (
            persona_id TEXT PRIMARY KEY,
            display_name TEXT NOT NULL,
            archetypes_json TEXT NOT NULL,
            style_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()


def upsert_persona(
    conn: sqlite3.Connection,
    persona_id: str,
    display_name: str,
    archetypes: List[str],
    style: dict,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO drummer_personas (
            persona_id, display_name, archetypes_json, style_json
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(persona_id) DO UPDATE SET
            display_name=excluded.display_name,
            archetypes_json=excluded.archetypes_json,
            style_json=excluded.style_json,
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            persona_id,
            display_name,
            json.dumps(archetypes),
            json.dumps(style),
        ),
    )
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Upsert a drummer persona from groove_style_vectors.",
    )
    parser.add_argument("persona_id", type=str, help="Internal ID, e.g. porcaro_shuffle")
    parser.add_argument(
        "display_name",
        type=str,
        help="User-facing label, e.g. 'Porcaro Shuffle'",
    )
    parser.add_argument(
        "archetypes",
        nargs="+",
        help="One or more groove archetype_ids (e.g. rosanna fool_in_the_rain)",
    )
    args = parser.parse_args()

    db_path = get_db_path()
    print(f"Using DB: {db_path}")
    print(f"Persona ID: {args.persona_id}")
    print(f"Display name: {args.display_name}")
    print(f"Archetypes: {', '.join(args.archetypes)}")

    conn = sqlite3.connect(db_path)
    try:
        ensure_drummer_personas_schema(conn)
        rows = fetch_vectors(conn, args.archetypes)
        if not rows:
            print("No groove_style_vectors found for the given archetype_ids.")
            return
        style = aggregate_metrics(rows)
        if style is None:
            print("No numeric metrics to aggregate; aborting.")
            return
        upsert_persona(conn, args.persona_id, args.display_name, args.archetypes, style)
    finally:
        conn.close()

    print("Persona upserted successfully.")


if __name__ == "__main__":
    main()
