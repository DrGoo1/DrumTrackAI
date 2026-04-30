import sqlite3
from pathlib import Path

DB_PATH = Path(r"f:\DrumTracKAI_v1.1.17\admin\data\drummerbrain_clips.db")

QUERY = (
    "SELECT dataset_id, label, created_at "
    "FROM datasets "
    "WHERE dataset_id IN ("
    "'sig_travis_barker_rock',"
    "'sig_carter_beauford_fusion',"
    "'sig_steve_gadd_jazz',"
    "'sig_simon_phillips_fusion'"
    ") "
    "ORDER BY dataset_id"
)

def main() -> None:
    if not DB_PATH.exists():
        print(f"DB missing: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(QUERY)
        rows = cur.fetchall()
        if not rows:
            print("NO_ROWS")
            return
        for dataset_id, label, created_at in rows:
            print(f"{dataset_id}\t{label}\t{created_at}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
