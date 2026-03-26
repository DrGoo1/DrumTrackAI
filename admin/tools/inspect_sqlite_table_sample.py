from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db", type=str)
    ap.add_argument("table", type=str)
    ap.add_argument("--limit", type=int, default=3)
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        raise FileNotFoundError(str(db))

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({args.table})")
        cols = [dict(r) for r in cur.fetchall()]
        print("columns:")
        print(json.dumps(cols, indent=2))

        cur.execute(f"SELECT * FROM {args.table} LIMIT ?", (int(args.limit),))
        rows = [dict(r) for r in cur.fetchall()]
        print("rows:")
        print(json.dumps(rows, indent=2, ensure_ascii=False)[:4000])
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
