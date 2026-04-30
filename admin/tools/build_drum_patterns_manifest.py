from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def _infer_tags(row: Dict[str, Any]) -> List[str]:
    tags = set()
    src = str(row.get("dataset_source") or "").strip().lower()
    if src:
        tags.add(src)
    style = str(row.get("style") or "").strip().lower()
    genre = str(row.get("genre") or "").strip().lower()
    section_type = str(row.get("section_type") or "").strip().lower()
    if style:
        tags.add(style)
    if genre:
        tags.add(genre)
    if section_type:
        tags.add(section_type)

    # drummer-term heuristics
    try:
        kick = int(row.get("kick_count") or 0)
        snare = int(row.get("snare_count") or 0)
        hats = int(row.get("hihat_count") or 0)
        bars = int(row.get("duration_bars") or 0) or 0
    except Exception:
        kick = snare = hats = 0
        bars = 0

    if bars > 0:
        kick_per_bar = kick / bars
        snare_per_bar = snare / bars
        hat_per_bar = hats / bars
        if abs(kick_per_bar - 4.0) <= 1.0:
            tags.add("four_on_floor")
        if abs(snare_per_bar - 2.0) <= 0.75:
            tags.add("backbeat_2_4")
        if abs(snare_per_bar - 1.0) <= 0.6:
            tags.add("halftime")
        if hat_per_bar >= 14:
            tags.add("sixteenth_note_hats")
        elif hat_per_bar >= 7:
            tags.add("eighth_note_hats")

    return sorted(t for t in tags if t)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(Path("admin") / "drumtrackai.db"))
    ap.add_argument(
        "--out",
        default=str(Path("Drum_Education") / "extracted" / "DRUM_PATTERNS_manifest.jsonl"),
    )
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    db = Path(args.db)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not db.exists():
        raise FileNotFoundError(str(db))

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        q = "SELECT * FROM drum_patterns"
        limit = int(args.limit or 0)
        if limit > 0:
            q += " LIMIT ?"
            cur.execute(q, (limit,))
        else:
            cur.execute(q)
        rows = cur.fetchall() or []

        written = 0
        with out.open("w", encoding="utf-8") as f:
            for r in rows:
                row = dict(r)
                pid = int(row.get("id") or 0)
                entry: Dict[str, Any] = {
                    "id": f"pattern:{pid}",
                    "source": "drum_patterns",
                    "pattern_id": pid,
                    "dataset_source": row.get("dataset_source"),
                    "file_path": row.get("file_path"),
                    "tempo_bpm": row.get("tempo_bpm"),
                    "meter": row.get("time_signature"),
                    "duration_bars": row.get("duration_bars"),
                    "section_type": row.get("section_type"),
                    "style": row.get("style"),
                    "genre": row.get("genre"),
                    "tags": _infer_tags(row),
                }
                f.write(json.dumps(entry, ensure_ascii=False))
                f.write("\n")
                written += 1

        print(f"Wrote {written} entries")
        print(out)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
