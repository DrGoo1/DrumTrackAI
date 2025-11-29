import sqlite3
from pathlib import Path

def show_drummers_schema(db_path: str):
    path = Path(db_path)
    print(f"Opening DB: {path}")
    if not path.exists():
        print("DB file does not exist.")
        return

    conn = sqlite3.connect(path)
    cur = conn.cursor()

    print("\nSchema for drummers table:")
    cur.execute("PRAGMA table_info(drummers);")
    rows = cur.fetchall()
    if not rows:
        print("(no drummers table or no columns)")
    else:
        for cid, name, col_type, notnull, dflt, pk in rows:
            print(f"- {name} {col_type} (pk={pk})")
    conn.close()

if __name__ == "__main__":
    show_drummers_schema(r"F:\DrumTracKAI_v1.1.17\admin\drumtrackai.db")
