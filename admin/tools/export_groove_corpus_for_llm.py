import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "admin" / "drumtrackai.db"
DEFAULT_OUT_PATH = PROJECT_ROOT / "llm_training_project" / "groove_corpus" / "llm_groove_corpus.jsonl"


def get_db_path() -> Path:
    env = os.getenv("DRUMTRACKAI_DB_PATH")
    if env:
        return Path(env)
    return DEFAULT_DB_PATH


def export_groove_corpus(out_path: Path = DEFAULT_OUT_PATH) -> None:
    db_path = get_db_path()
    print(f"Using DB: {db_path}")

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()

        # Load archetype metadata
        cur.execute(
            """
            SELECT archetype_id, song_title, drum_path, original_path
            FROM groove_archetypes
            ORDER BY archetype_id
            """
        )
        archetypes = cur.fetchall()
        if not archetypes:
            print("No groove_archetypes found. Nothing to export.")
            return

        # Load style vectors into a dict
        cur.execute(
            """
            SELECT archetype_id, bpm, swing_amount, shuffle_amount,
                   backbeat_late_ms, hat_open_ratio, ghost_snare_ratio,
                   kick_density, snare_density, cymbal_density,
                   dynamics_spread, ride_density, ride_mean_velocity,
                   ride_bell_ratio, notes
            FROM groove_style_vectors
            """
        )
        style_rows = cur.fetchall()
        style_by_id: Dict[str, Dict[str, Any]] = {}
        for row in style_rows:
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
            ) = row
            style_by_id[archetype_id] = {
                "bpm": bpm,
                "swing_amount": swing_amount,
                "shuffle_amount": shuffle_amount,
                "backbeat_late_ms": backbeat_late_ms,
                "hat_open_ratio": hat_open_ratio,
                "ghost_snare_ratio": ghost_snare_ratio,
                "kick_density": kick_density,
                "snare_density": snare_density,
                "cymbal_density": cymbal_density,
                "dynamics_spread": dynamics_spread,
                "ride_density": ride_density,
                "ride_mean_velocity": ride_mean_velocity,
                "ride_bell_ratio": ride_bell_ratio,
                "notes": notes,
            }

        # Ensure output directory
        out_path.parent.mkdir(parents=True, exist_ok=True)

        num_written = 0
        with out_path.open("w", encoding="utf-8") as f_out:
            for archetype_id, song_title, drum_path, original_path in archetypes:
                # Fetch events for this archetype
                cur.execute(
                    """
                    SELECT bar, step, time_sec, instrument, velocity, timing_offset_ms, limb
                    FROM groove_events
                    WHERE archetype_id = ?
                    ORDER BY bar, step, time_sec
                    """,
                    (archetype_id,),
                )
                event_rows = cur.fetchall()
                events: List[Dict[str, Any]] = []
                for bar, step, time_sec, instrument, velocity, timing_offset_ms, limb in event_rows:
                    events.append(
                        {
                            "bar": bar,
                            "step": step,
                            "time_sec": time_sec,
                            "instrument": instrument,
                            "velocity": velocity,
                            "timing_offset_ms": timing_offset_ms,
                            "limb": limb,
                        }
                    )

                style_features = style_by_id.get(archetype_id) or {}

                record = {
                    "archetype_id": archetype_id,
                    "song_title": song_title,
                    "drum_path": drum_path,
                    "original_path": original_path,
                    "style_features": style_features,
                    "events": events,
                }

                f_out.write(json.dumps(record))
                f_out.write("\n")
                num_written += 1

        print(f"Exported {num_written} groove records to {out_path}")

    finally:
        conn.close()


if __name__ == "__main__":
    export_groove_corpus()
