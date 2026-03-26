from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("db", type=str)
    ap.add_argument("--filter", type=str, default="")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        raise FileNotFoundError(str(db))

    conn = sqlite3.connect(str(db))
    try:
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        names = [r[0] for r in cur.fetchall()]

        filt = args.filter.strip().lower()
        if filt:
            names = [n for n in names if filt in n.lower()]

        print(f"tables={len(names)}")
        for n in names:
            print(n)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
