import sqlite3
from pathlib import Path

def list_drummers(db_path: str):
    path = Path(db_path)
    print(f"Opening DB: {path}")
    if not path.exists():
        print("DB file does not exist.")
        return

    conn = sqlite3.connect(path)
    cur = conn.cursor()

    print("\nDrummers:")
    cur.execute("SELECT drummer_id, display_name, real_name FROM drummers ORDER BY display_name;")
    rows = cur.fetchall()
    if not rows:
        print("(no drummers found)")
    for drummer_id, display_name, real_name in rows:
        print(f"- {display_name}  (drummer_id={drummer_id}, real_name={real_name})")

    conn.close()

if __name__ == "__main__":
    list_drummers(r"F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db")
