import sqlite3
from pathlib import Path

DB_PATH = Path("admin") / "drumtrackai.db"


def show_event_counts(db_path: Path) -> None:
    print(f"Opening DB: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        # Join groove_events with archetype titles
        cur.execute(
            """
            SELECT ge.archetype_id,
                   ga.song_title,
                   ge.instrument,
                   COUNT(*) as hit_count
            FROM groove_events ge
            JOIN groove_archetypes ga
              ON ge.archetype_id = ga.archetype_id
            GROUP BY ge.archetype_id, ga.song_title, ge.instrument
            ORDER BY ge.archetype_id, ge.instrument
            """
        )
        rows = cur.fetchall()
        if not rows:
            print("No groove_events found. Run analyze_groove_archetypes first.")
            return

        current_id = None
        for archetype_id, song_title, instrument, count in rows:
            if archetype_id != current_id:
                if current_id is not None:
                    print()
                current_id = archetype_id
                print(f"== {archetype_id} | {song_title} ==")
            print(f"  {instrument:15s}: {count}")

    finally:
        conn.close()


if __name__ == "__main__":
    show_event_counts(DB_PATH)
