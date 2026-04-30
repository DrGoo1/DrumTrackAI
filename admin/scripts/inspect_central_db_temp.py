import sqlite3
from pathlib import Path

DB_PATH = Path(r"f:\DrumTracKAI_v1.1.17\admin\drumtrackai.db")

def dump_drummer_summary(cur):
    cur.execute(
        """
        SELECT d.drummer_id, d.display_name, COUNT(DISTINCT spa.analysis_id) AS songs
        FROM drummers d
        LEFT JOIN song_performance_analysis spa ON spa.drummer_id = d.id
        GROUP BY d.id
        ORDER BY songs DESC, d.drummer_id
        """
    )
    rows = cur.fetchall()
    for drummer_id, display_name, songs in rows:
        print(f"{drummer_id}\t{display_name}\t{songs}")


def main():
    if not DB_PATH.exists():
        print(f"DB missing: {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        print("-- DRUMMERS --")
        dump_drummer_summary(cur)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
