from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_float(x: Any) -> Optional[float]:
    try:
        v = float(x)
        if not math.isfinite(v):
            return None
        return v
    except Exception:
        return None


def _beats_per_bar(ts: str) -> float:
    try:
        num, den = str(ts or "4/4").split("/")
        denom = int(den) or 4
        return float(int(num)) * (4.0 / float(denom))
    except Exception:
        return 4.0


def _estimate_bars(duration_sec: Optional[float], tempo_bpm: Optional[float], ts: str) -> Optional[float]:
    if not duration_sec or not tempo_bpm or duration_sec <= 0 or tempo_bpm <= 0:
        return None
    bpb = _beats_per_bar(ts)
    beats = (duration_sec / 60.0) * tempo_bpm
    return beats / max(bpb, 1e-6)


def _infer_drummer_terms(features: Dict[str, Any], *, tempo_bpm: Optional[float], meter: str) -> List[str]:
    tags: List[str] = []

    drum_counts: Dict[str, Any] = features.get("drum_counts") or {}
    kick = int(drum_counts.get("kick") or 0)
    snare = int(drum_counts.get("snare") or 0)
    hat = int(drum_counts.get("hihat_closed") or 0)
    ride = int(drum_counts.get("ride") or drum_counts.get("ride_bow") or 0)

    duration = _safe_float(features.get("duration"))
    tempo = tempo_bpm or _safe_float(features.get("tempo"))
    ts = str(features.get("time_signature") or meter or "4/4")

    bars = _estimate_bars(duration, tempo, ts)
    if bars and bars > 0:
        kick_per_bar = kick / bars
        snare_per_bar = snare / bars
        hat_per_bar = hat / bars

        # Drummer-term style tags
        if abs(kick_per_bar - 4.0) <= 1.0:
            tags.append("four_on_floor")
        if abs(snare_per_bar - 2.0) <= 0.75:
            tags.append("backbeat_2_4")
        if abs(snare_per_bar - 1.0) <= 0.6:
            tags.append("halftime")

        # Hat density heuristics
        if hat_per_bar >= 14:
            tags.append("sixteenth_note_hats")
        elif hat_per_bar >= 7:
            tags.append("eighth_note_hats")

    swing = _safe_float(features.get("swing_amount"))
    if swing is not None:
        if swing >= 0.35:
            tags.append("shuffle")
        elif swing >= 0.2:
            tags.append("swing")

    density = _safe_float(features.get("pattern_density"))
    if density is not None:
        if density >= 10:
            tags.append("busy")
        elif density <= 4:
            tags.append("simple")

    # Instrument presence
    if ride > 0:
        tags.append("ride")

    return sorted(set(tags))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(Path("admin") / "data" / "drum_training.db"))
    ap.add_argument(
        "--out",
        default=str(Path("Drum_Education") / "extracted" / "EGMD_manifest.jsonl"),
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
            "SELECT id, basename, style_group, style_detail, tempo_bpm, tempo, meter, time_signature, bars, midi_path, audio_path, feature_json "
            "FROM egmd_phrases WHERE midi_path IS NOT NULL AND feature_json IS NOT NULL"
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
                try:
                    features = json.loads(r["feature_json"] or "{}")
                except Exception:
                    features = {}

                meter = str(r["meter"] or r["time_signature"] or features.get("time_signature") or "4/4")
                tempo_bpm = _safe_float(r["tempo_bpm"]) or _safe_float(r["tempo"]) or _safe_float(features.get("tempo"))

                tags: List[str] = []
                if r["style_group"]:
                    tags.append(str(r["style_group"]).strip().lower())
                tags.extend(_infer_drummer_terms(features, tempo_bpm=tempo_bpm, meter=meter))

                entry = {
                    "id": f"egmd:{int(r['id'])}",
                    "source": "egmd",
                    "phrase_id": int(r["id"]),
                    "basename": r["basename"],
                    "style_group": (r["style_group"] or "").strip().lower() if r["style_group"] else None,
                    "style_detail": r["style_detail"],
                    "tempo_bpm": tempo_bpm,
                    "meter": meter,
                    "bars": int(r["bars"]) if r["bars"] is not None else None,
                    "midi_path": r["midi_path"],
                    "audio_path": r["audio_path"],
                    "tags": sorted({t for t in tags if t}),
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
