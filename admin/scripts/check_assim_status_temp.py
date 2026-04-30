import sqlite3
from pathlib import Path

DB_PATH = Path(r"f:\DrumTracKAI_v1.1.17\admin\drumtrackai.db")

QUERY = (
    "SELECT d.drummer_id, COUNT(DISTINCT spa.analysis_id) AS songs, "
    "COALESCE((SELECT COUNT(1) FROM analysis_artifacts aa WHERE aa.drummer_id = spa.drummer_id), 0) AS artifacts, "
    "COALESCE((SELECT COUNT(1) FROM stem_artifacts sa WHERE sa.drummer_id = spa.drummer_id), 0) AS stems, "
    "COALESCE((SELECT COUNT(1) FROM drum_hit_events he WHERE he.drummer_id = spa.drummer_id), 0) AS hit_events "
    "FROM song_performance_analysis spa "
    "LEFT JOIN drummers d ON d.id = spa.drummer_id "
    "WHERE d.drummer_id IN (?, ?, ?, ?, ?) "
    "GROUP BY spa.drummer_id"
)

def main() -> None:
    if not DB_PATH.exists():
        print(f"DB missing: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            QUERY,
            (
                'stewart_copeland',
                'travis_barker',
                'carter_beauford',
                'steve_gadd',
                'simon_phillips',
            ),
        )
        rows = cur.fetchall()
        if not rows:
            print("NO_ROWS")
            return
        for row in rows:
            print("|".join(str(col) for col in row))
    finally:
        conn.close()


if __name__ == "__main__":
    main()
