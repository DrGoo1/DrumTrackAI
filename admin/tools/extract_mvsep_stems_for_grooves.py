import asyncio
import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from admin.services.mvsep_service import MVSepService

DEFAULT_DB = PROJECT_ROOT / "admin" / "drumtrackai.db"
OUT_DIR = PROJECT_ROOT / "admin" / "data" / "mvsep_grooves"
INDEX_PATH = OUT_DIR / "mvsep_stems_index.json"


def get_db_path() -> Path:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    return Path(env) if env else DEFAULT_DB


def load_archetypes():
    conn = sqlite3.connect(get_db_path())
    try:
        cur = conn.cursor()
        cur.execute("SELECT archetype_id, song_title, original_path FROM groove_archetypes")
        return cur.fetchall()
    finally:
        conn.close()


async def process_one(service: MVSepService, archetype_id: str, original_path: str) -> Dict[str, str]:
    out_dir = OUT_DIR / archetype_id
    out_dir.mkdir(parents=True, exist_ok=True)

    def progress_cb(p: float, msg: str) -> None:
        pct = int(round(p * 100))
        print(f"[{archetype_id:>20}] {pct:3d}% {msg}")

    result_files = await service.process_audio_file(
        input_file=str(Path(original_path).resolve()),
        output_dir=str(out_dir.resolve()),
        progress_callback=progress_cb,
        skip_stage_1=False,
        keep_original_mix=True,
        keep_drum_stem=True,
    )

    drum_keys = ["drum_stem", "drums", "kick", "snare", "hh", "ride", "crash", "toms", "residual"]
    return {k: v for k, v in result_files.items() if k in drum_keys}


async def main():
    api_key = os.getenv("MVSEP_API_KEY")
    if not api_key:
        raise RuntimeError("MVSEP_API_KEY not set")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    archetypes = load_archetypes()
    print(f"Found {len(archetypes)} archetypes")

    index: Dict[str, Dict[str, str]] = {}
    async with MVSepService(api_key=api_key) as service:
        for archetype_id, song_title, original_path in archetypes:
            if not original_path:
                print(f"[{archetype_id}] No original_path, skipping")
                continue
            print(f"\n=== Processing {archetype_id} | {song_title} ===")
            stems = await process_one(service, archetype_id, original_path)
            index[archetype_id] = stems

    with INDEX_PATH.open("w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"\nSaved MVSEP stems index to {INDEX_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
