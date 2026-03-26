"""Create the drummer_personas table in the admin DB if it doesn't exist.

Schema is intentionally simple and JSON-friendly so it can evolve:

- persona_id      TEXT PRIMARY KEY (e.g. "Porcaro_Shuffle_Persona")
- display_name    TEXT (user-facing label)
- archetypes_json TEXT (JSON list of groove_archetype IDs)
- style_json      TEXT (JSON dict of aggregated_style metrics)
- created_at      TIMESTAMP
- updated_at      TIMESTAMP
"""

import json
import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "admin" / "drumtrackai.db"


def get_db_path() -> Path:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    return Path(env) if env else DEFAULT_DB


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


def main() -> None:
    db_path = get_db_path()
    print(f"Using DB: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        ensure_drummer_personas_schema(conn)
    finally:
        conn.close()
    print("drummer_personas table ensured.")


if __name__ == "__main__":
    main()
