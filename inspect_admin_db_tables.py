import sqlite3
from pathlib import Path

def show_tables(db_path: str):
    path = Path(db_path)
    print(f"Opening DB: {path}")
    if not path.exists():
        print("DB file does not exist.")
        return

    conn = sqlite3.connect(path)
    cur = conn.cursor()
    print("\nTables:")
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    rows = cur.fetchall()
    if not rows:
        print("(no tables found)")
    for (name,) in rows:
        print(f"- {name}")
    conn.close()

if __name__ == "__main__":
    show_tables(r"F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db")
