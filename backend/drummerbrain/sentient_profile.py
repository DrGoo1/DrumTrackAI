from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SentientProfileBuildOptions:
    max_phrase_windows_per_song: int = 500


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _safe_json_loads(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if not isinstance(value, str):
        return None
    s = value.strip()
    if not s:
        return None
    try:
        return json.loads(s)
    except Exception:
        return None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name})")
        cols = []
        for row in cur.fetchall() or []:
            # row: cid, name, type, notnull, dflt_value, pk
            if row and len(row) >= 2 and row[1] is not None:
                cols.append(str(row[1]))
        return cols
    except Exception:
        return []


def _stats(values: List[float]) -> Dict[str, Any]:
    if not values:
        return {"count": 0, "mean": None, "std": None}
    n = len(values)
    mean = sum(values) / float(n)
    if n <= 1:
        std = 0.0
    else:
        var = sum((v - mean) ** 2 for v in values) / float(n - 1)
        std = var ** 0.5
    return {"count": n, "mean": float(mean), "std": float(std)}


def _resolve_admin_db_path(path: Optional[str]) -> str:
    if path:
        return os.path.abspath(path)
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root / "admin" / "drumtrackai.db"
    return str(candidate)


def _get_drummer_fk(conn: sqlite3.Connection, drummer_slug: str) -> Optional[int]:
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM drummers WHERE drummer_id = ? LIMIT 1", (drummer_slug,))
        row = cur.fetchone()
        if row and row[0] is not None:
            return int(row[0])
    except Exception:
        return None
    return None


def _fetch_song_analyses(conn: sqlite3.Connection, drummer_fk: int) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT analysis_id, tempo_bpm, time_signature, duration_sec
        FROM song_performance_analysis
        WHERE drummer_id = ?
        ORDER BY created_at ASC
        """,
        (drummer_fk,),
    )
    out: List[Dict[str, Any]] = []
    for analysis_id, tempo_bpm, time_signature, duration_sec in cur.fetchall() or []:
        out.append(
            {
                "analysis_id": str(analysis_id),
                "tempo_bpm": None if tempo_bpm is None else float(tempo_bpm),
                "time_signature": str(time_signature or ""),
                "duration_sec": None if duration_sec is None else float(duration_sec),
            }
        )
    return out


def _fetch_fills(conn: sqlite3.Connection, analysis_id: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()

    cols = set(_table_columns(conn, "fill_events"))
    select_parts: List[str] = []
    # required
    select_parts.append("start_time_sec")
    select_parts.append("end_time_sec")
    # optional
    if "start_bar_index" in cols:
        select_parts.append("start_bar_index")
    else:
        select_parts.append("NULL AS start_bar_index")
    if "end_bar_index" in cols:
        select_parts.append("end_bar_index")
    else:
        select_parts.append("NULL AS end_bar_index")
    if "hit_count" in cols:
        select_parts.append("hit_count")
    else:
        select_parts.append("NULL AS hit_count")
    if "instruments_json" in cols:
        select_parts.append("instruments_json")
    else:
        select_parts.append("NULL AS instruments_json")
    if "density_per_sec" in cols:
        select_parts.append("density_per_sec")
    else:
        select_parts.append("NULL AS density_per_sec")
    if "classification" in cols:
        select_parts.append("classification")
    else:
        select_parts.append("NULL AS classification")

    cur.execute(
        f"""
        SELECT {', '.join(select_parts)}
        FROM fill_events
        WHERE analysis_id = ?
        ORDER BY start_time_sec ASC
        """,
        (analysis_id,),
    )
    fills: List[Dict[str, Any]] = []
    for row in cur.fetchall() or []:
        instruments = _safe_json_loads(row[5])
        fills.append(
            {
                "start_time_sec": float(row[0] or 0.0),
                "end_time_sec": float(row[1] or 0.0),
                "start_bar_index": None if row[2] is None else int(row[2]),
                "end_bar_index": None if row[3] is None else int(row[3]),
                "hit_count": None if row[4] is None else int(row[4]),
                "instruments": instruments if isinstance(instruments, list) else [],
                "density_per_sec": None if row[6] is None else float(row[6]),
                "classification": str(row[7] or ""),
            }
        )
    return fills


def _fetch_hits(conn: sqlite3.Connection, analysis_id: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()

    cols = set(_table_columns(conn, "drum_hit_events"))
    select_parts: List[str] = []
    select_parts.append("instrument")
    select_parts.append("onset_time_sec")
    if "velocity_est" in cols:
        select_parts.append("velocity_est")
    else:
        select_parts.append("NULL AS velocity_est")
    if "subdivision" in cols:
        select_parts.append("subdivision")
    else:
        select_parts.append("NULL AS subdivision")
    if "timing_offset_ms" in cols:
        select_parts.append("timing_offset_ms")
    else:
        select_parts.append("NULL AS timing_offset_ms")
    if "is_ghost" in cols:
        select_parts.append("is_ghost")
    else:
        select_parts.append("0 AS is_ghost")
    if "is_accent" in cols:
        select_parts.append("is_accent")
    else:
        select_parts.append("0 AS is_accent")

    cur.execute(
        f"""
        SELECT {', '.join(select_parts)}
        FROM drum_hit_events
        WHERE analysis_id = ?
        ORDER BY onset_time_sec ASC
        """,
        (analysis_id,),
    )
    hits: List[Dict[str, Any]] = []
    for instrument, onset_time_sec, velocity_est, subdivision, timing_offset_ms, is_ghost, is_accent in cur.fetchall() or []:
        hits.append(
            {
                "instrument": str(instrument or ""),
                "onset_time_sec": float(onset_time_sec or 0.0),
                "velocity_est": None if velocity_est is None else float(velocity_est),
                "subdivision": str(subdivision or ""),
                "timing_offset_ms": None if timing_offset_ms is None else float(timing_offset_ms),
                "is_ghost": bool(int(is_ghost or 0)),
                "is_accent": bool(int(is_accent or 0)),
            }
        )
    return hits


def _infer_role(hit: Dict[str, Any]) -> str:
    if hit.get("is_ghost"):
        return "ghost"
    if hit.get("is_accent"):
        return "accent"
    return "normal"


def build_phrase_windows(
    *,
    song_duration_sec: Optional[float],
    fills: List[Dict[str, Any]],
    options: SentientProfileBuildOptions,
) -> List[Dict[str, Any]]:
    duration = float(song_duration_sec or 0.0)
    windows: List[Dict[str, Any]] = []

    if duration <= 0.0:
        # Fallback: derive from fill end times
        duration = 0.0
        for f in fills:
            duration = max(duration, float(f.get("end_time_sec") or 0.0))

    t = 0.0
    for f in fills:
        fs = float(f.get("start_time_sec") or 0.0)
        fe = float(f.get("end_time_sec") or fs)
        if fs > t:
            windows.append({"type": "groove", "start_time_sec": t, "end_time_sec": fs})
        windows.append(
            {
                "type": "fill",
                "start_time_sec": fs,
                "end_time_sec": fe,
                "meta": {
                    "hit_count": f.get("hit_count"),
                    "instruments": f.get("instruments") or [],
                    "density_per_sec": f.get("density_per_sec"),
                    "classification": f.get("classification"),
                    "start_bar_index": f.get("start_bar_index"),
                    "end_bar_index": f.get("end_bar_index"),
                },
            }
        )
        t = max(t, fe)
        if len(windows) >= int(options.max_phrase_windows_per_song):
            break

    if duration > t:
        windows.append({"type": "groove", "start_time_sec": t, "end_time_sec": duration})

    # Drop degenerate windows
    windows = [w for w in windows if float(w.get("end_time_sec") or 0.0) - float(w.get("start_time_sec") or 0.0) > 1e-6]
    return windows


def derive_timing_profiles(*, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    # instrument -> subdivision -> stats
    buckets: Dict[Tuple[str, str], List[float]] = {}
    for h in hits:
        off = h.get("timing_offset_ms")
        if off is None:
            continue
        inst = str(h.get("instrument") or "")
        sub = str(h.get("subdivision") or "")
        buckets.setdefault((inst, sub), []).append(float(off))

    profiles: Dict[str, Any] = {}
    for (inst, sub), vals in buckets.items():
        profiles.setdefault(inst, {})[sub] = _stats(vals)
    return profiles


def derive_dynamics_profiles(*, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    # instrument -> role -> stats
    buckets: Dict[Tuple[str, str], List[float]] = {}
    for h in hits:
        v = h.get("velocity_est")
        if v is None:
            continue
        inst = str(h.get("instrument") or "")
        role = _infer_role(h)
        buckets.setdefault((inst, role), []).append(float(v))

    profiles: Dict[str, Any] = {}
    for (inst, role), vals in buckets.items():
        profiles.setdefault(inst, {})[role] = _stats(vals)
    return profiles


def infer_limb_summary(*, hits: List[Dict[str, Any]]) -> Dict[str, Any]:
    # Very conservative heuristic mapping.
    mapping = {
        "kick": "right_foot",
        "snare": "left_hand",
        "hihat": "right_hand",
        "ride": "right_hand",
        "crash": "right_hand",
        "cymbal": "right_hand",
        "tom": "both_hands",
        "perc": "either",
    }

    limb_counts: Dict[str, int] = {}
    inst_counts: Dict[str, int] = {}
    for h in hits:
        inst = str(h.get("instrument") or "")
        limb = mapping.get(inst, "unknown")
        inst_counts[inst] = int(inst_counts.get(inst, 0)) + 1
        limb_counts[limb] = int(limb_counts.get(limb, 0)) + 1

    total = float(sum(limb_counts.values()) or 0)
    limb_shares = {k: (float(v) / total if total > 0 else 0.0) for k, v in limb_counts.items()}

    return {
        "heuristic_mapping": mapping,
        "limb_counts": limb_counts,
        "limb_shares": limb_shares,
        "instrument_counts": inst_counts,
    }


def transition_matrix_from_phrase_windows(*, phrase_windows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, Dict[str, int]] = {}
    for i in range(1, len(phrase_windows)):
        a = str(phrase_windows[i - 1].get("type") or "")
        b = str(phrase_windows[i].get("type") or "")
        if not a or not b:
            continue
        counts.setdefault(a, {})[b] = int(counts.get(a, {}).get(b, 0)) + 1

    probs: Dict[str, Dict[str, float]] = {}
    for a, row in counts.items():
        denom = float(sum(row.values()) or 0)
        probs[a] = {b: (float(n) / denom if denom > 0 else 0.0) for b, n in row.items()}

    return {"counts": counts, "probs": probs}


def build_sentient_profile(
    *,
    admin_db_path: Optional[str] = None,
    drummer_slug: str,
    options: Optional[SentientProfileBuildOptions] = None,
) -> Dict[str, Any]:
    options = options or SentientProfileBuildOptions()
    db_path = _resolve_admin_db_path(admin_db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        drummer_fk = _get_drummer_fk(conn, drummer_slug)
        if drummer_fk is None:
            raise ValueError(f"Drummer slug not found in admin DB: {drummer_slug}")

        analyses = _fetch_song_analyses(conn, drummer_fk)

        all_hits: List[Dict[str, Any]] = []
        phrase_library: List[Dict[str, Any]] = []
        per_song_transitions: List[Dict[str, Any]] = []

        for a in analyses:
            analysis_id = str(a["analysis_id"])
            fills = _fetch_fills(conn, analysis_id)
            hits = _fetch_hits(conn, analysis_id)
            all_hits.extend(hits)

            phrase_windows = build_phrase_windows(
                song_duration_sec=a.get("duration_sec"),
                fills=fills,
                options=options,
            )

            for w in phrase_windows:
                phrase_library.append(
                    {
                        "analysis_id": analysis_id,
                        "type": w.get("type"),
                        "start_time_sec": w.get("start_time_sec"),
                        "end_time_sec": w.get("end_time_sec"),
                        "meta": w.get("meta") or {},
                    }
                )

            per_song_transitions.append(
                {
                    "analysis_id": analysis_id,
                    "transition": transition_matrix_from_phrase_windows(phrase_windows=phrase_windows),
                }
            )

        timing_profiles = derive_timing_profiles(hits=all_hits)
        dynamics_profiles = derive_dynamics_profiles(hits=all_hits)
        limb_summary = infer_limb_summary(hits=all_hits)

        # Aggregate transitions across all phrases (simple global Markov)
        global_transition = transition_matrix_from_phrase_windows(
            phrase_windows=[{"type": p.get("type")} for p in phrase_library]
        )

        return {
            "schema_version": "sentient_profile_v1",
            "generated_at": _utc_now_iso(),
            "source": {
                "admin_db_path": db_path,
                "drummer_slug": drummer_slug,
                "drummer_fk": int(drummer_fk),
            },
            "counts": {
                "songs": int(len(analyses)),
                "phrase_windows": int(len(phrase_library)),
                "hits": int(len(all_hits)),
            },
            "phrase_library": phrase_library,
            "timing_profiles": timing_profiles,
            "dynamics_profiles": dynamics_profiles,
            "limb_summary": limb_summary,
            "phrase_transition": {
                "per_song": per_song_transitions,
                "global": global_transition,
            },
        }
    finally:
        conn.close()


def export_sentient_profile_json(*, profile: Dict[str, Any], out_path: str) -> str:
    out_path = os.path.abspath(out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, sort_keys=True)
    return out_path
