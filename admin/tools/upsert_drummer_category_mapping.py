"""Admin tool to upsert a mapping from a public DrumTracKAI drummer category
(e.g. "studio_rock") to a drummer persona (e.g. "porcaro_shuffle") plus
optional default knob settings.

Usage (from project root, with venv + DRUMTRACKAI_DB_PATH set):

    python admin\tools\upsert_drummer_category_mapping.py \
        studio_rock "Studio Rock" porcaro_shuffle \
        --backup_personas cissy_strut_groove \
        --default_humanize 0.7 \
        --default_swing 0.1 \
        --default_chorus_ride 0.6
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from services.central_database_service import get_database_service


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "admin" / "drumtrackai.db"


def get_db_path() -> str:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    return env or str(DEFAULT_DB)


def main() -> None:
    parser = argparse.ArgumentParser(description="Upsert drummer category mapping -> persona")
    parser.add_argument("category_id", help="Public DrumTracKAI drummer category id (e.g. studio_rock)")
    parser.add_argument("display_name", help="Human-friendly name for this category")
    parser.add_argument("primary_persona_id", help="Persona id from drummer_personas to use as primary source")
    parser.add_argument("--backup_personas", nargs="*", default=[], help="Optional backup persona_ids")
    parser.add_argument("--default_humanize", type=float, default=None, help="Default humanizeAmount (0..1) for this category")
    parser.add_argument("--default_swing", type=float, default=None, help="Default swingAmount (0..1) for this category")
    parser.add_argument("--default_chorus_ride", type=float, default=None, help="Default chorusRidePreference (0..1) for this category")

    args = parser.parse_args()

    # Ensure DB path is set for CentralDatabaseService
    db_path = get_db_path()
    os.environ.setdefault("DRUMTRACKAI_DB_PATH", db_path)

    db = get_database_service()
    if not db.initialize(db_path):
        raise SystemExit("Failed to initialize database")

    ok = db.upsert_drummer_category_mapping(
        category_id=args.category_id,
        display_name=args.display_name,
        primary_persona_id=args.primary_persona_id,
        backup_persona_ids=args.backup_personas or [],
        default_humanize=args.default_humanize,
        default_swing=args.default_swing,
        default_chorus_ride_pref=args.default_chorus_ride,
    )
    if not ok:
        raise SystemExit("Failed to upsert mapping")

    mapping = db.get_drummer_category_mapping(args.category_id)
    print("Upserted mapping:\n")
    print(mapping)


if __name__ == "__main__":
    main()
