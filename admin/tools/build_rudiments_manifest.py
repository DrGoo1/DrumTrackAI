from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def _infer_tags(name: str | None, family: str | None) -> List[str]:
    tags: List[str] = ["rudiment"]
    if family:
        tags.append(str(family).strip().lower())
    n = str(name or "").strip().lower()
    if not n:
        return sorted(set(tags))

    # Simple drummer-term tags
    if "paradiddle" in n:
        tags.append("paradiddle")
    if "flam" in n:
        tags.append("flam")
    if "drag" in n:
        tags.append("drag")
    if "roll" in n:
        tags.append("roll")
    if "ratamacue" in n:
        tags.append("ratamacue")
    if "diddle" in n:
        tags.append("diddle")
    return sorted(set(tags))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(Path("admin") / "data" / "drum_training.db"))
    ap.add_argument(
        "--out",
        default=str(Path("Drum_Education") / "extracted" / "RUDIMENTS_manifest.jsonl"),
    )
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    db_path = Path(args.db)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not db_path.exists():
        raise FileNotFoundError(str(db_path))

    limit = int(args.limit or 0)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        q = (
            "SELECT id, rudiment_name, rudiment_family, midi_path "
            "FROM rudiment_fragments WHERE midi_path IS NOT NULL"
        )
        if limit > 0:
            q += " LIMIT ?"
            cur.execute(q, (limit,))
        else:
            cur.execute(q)
        rows = cur.fetchall() or []

        written = 0
        with out_path.open("w", encoding="utf-8") as f:
            for r in rows:
                rid = int(r["id"])
                name = r["rudiment_name"]
                family = r["rudiment_family"]
                midi_path = r["midi_path"]

                entry: Dict[str, Any] = {
                    "id": f"rudiment:{rid}",
                    "source": "rudiments",
                    "rudiment_id": rid,
                    "name": name,
                    "family": family,
                    "midi_path": midi_path,
                    "tags": _infer_tags(name, family),
                }
                f.write(json.dumps(entry, ensure_ascii=False))
                f.write("\n")
                written += 1

        print(f"Wrote {written} entries")
        print(out_path)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
