import json
import math
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .weights import load_weights


_DB_DEFAULT = Path(__file__).resolve().parents[2] / "admin" / "data" / "drummerbrain_clips.db"


_POLICY_VERSION = "drummerbrain_v1_mvp_2026_02_11"


def resolve_db_path() -> Path:
    p = os.getenv("DRUMMERBRAIN_DB_PATH")
    if p:
        return Path(p)
    return _DB_DEFAULT


def _connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    p = db_path or resolve_db_path()
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    return conn


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if not math.isfinite(v):
            return float(default)
        return v
    except Exception:
        return float(default)


def _classify_failure(prov: Any) -> str:
    if not isinstance(prov, dict):
        return "unknown"
    et = str(prov.get("error_type") or prov.get("errorType") or "").strip().lower()
    stage = str(prov.get("stage") or "").strip().lower()
    msg = str(prov.get("error") or prov.get("message") or "").strip().lower()

    if et in {"analysis_failed", "analysis", "audio_analysis"} or stage in {"analysis", "audio_analysis"}:
        return "analysis_failed"
    if et in {"transcription_failed", "transcription"} or stage in {"transcription", "quantize", "events"}:
        return "transcription_failed"
    if "analysis" in msg:
        return "analysis_failed"
    if "transcrib" in msg or "quantiz" in msg or "events" in msg:
        return "transcription_failed"
    return "unknown"


def build_internal_events_from_asset(
    *,
    config: Any,
    asset_id: str,
    dataset_id: str,
    song_key: Optional[str],
    variant: Optional[str],
    confidence: float,
    events: List[Dict[str, Any]],
    features: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    beats_per_bar = int(getattr(config, "time_signature", (4, 4))[0] or 4)
    beats_per_bar = max(1, beats_per_bar)
    tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)
    tempo = max(1e-3, tempo)

    bar_dur = (60.0 / tempo) * float(beats_per_bar)
    section_len = float(getattr(config, "measure_count", 1) or 1) * bar_dur

    beat_dur = 60.0 / tempo

    pattern_len = _safe_float(features.get("duration_s"), 0.0)
    if not (pattern_len > 1e-3):
        dur_beats = _safe_float(features.get("duration_beats"), 0.0)
        if dur_beats > 1e-6:
            pattern_len = float(dur_beats) * float(beat_dur)
    if not (pattern_len > 1e-3):
        last_t = 0.0
        for e in events:
            last_t = max(last_t, _safe_float(e.get("t"), 0.0))
        pattern_len = max(last_t + beat_dur, beat_dur)

    out: List[Dict[str, Any]] = []
    if not events:
        return out, {
            "used": False,
            "reason": "empty_events",
            "asset_id": asset_id,
            "dataset_id": dataset_id,
        }

    max_tiles = int(math.ceil(section_len / max(pattern_len, 1e-3)))
    max_tiles = max(1, min(max_tiles, 512))

    for tile in range(max_tiles):
        offset = float(tile) * float(pattern_len)
        for ev in events:
            if "t" in ev and ev.get("t") is not None:
                t0 = _safe_float(ev.get("t"), 0.0)
            else:
                bi = int(ev.get("beat_index") or 0)
                sub = int(ev.get("sub") or 0)
                subdiv = int(ev.get("subdiv") or features.get("subdiv") or 4)
                subdiv = max(1, subdiv)
                t0 = (float(bi) + (float(sub) / float(subdiv))) * float(beat_dur)

            t = offset + float(t0)
            if t < 0.0 or t >= section_len:
                continue

            beat_index = int(ev.get("beat_index") or 0)
            sub = int(ev.get("sub") or 0)

            if sub == 0 and (beat_index % beats_per_bar) == 0:
                inst = "kick"
            elif sub == 0:
                inst = "snare_center"
            else:
                inst = "hihat_closed"

            strength = _safe_float(ev.get("strength"), 0.5)
            vel = int(max(1, min(127, round(50 + 70 * max(0.0, min(1.0, strength))))))

            bar_index = int(t // max(bar_dur, 1e-6))
            out.append(
                {
                    "time_sec": float(t),
                    "length_sec": 0.12,
                    "instrument_id": inst,
                    "velocity": int(vel),
                    "barIndex": int(bar_index),
                    "barRole": "groove",
                    "isGhost": False,
                    "isAccent": bool(vel >= 110),
                    "isFlam": False,
                    "isDrag": False,
                }
            )

    out.sort(key=lambda e: (float(e.get("time_sec", 0.0)), str(e.get("instrument_id", "")), int(e.get("velocity", 0))))
    prov = {
        "used": True,
        "reason": "selected",
        "asset_id": asset_id,
        "dataset_id": dataset_id,
        "song_key": song_key,
        "variant": variant,
        "confidence": float(confidence),
        "pattern_len_s": float(pattern_len),
        "section_len_s": float(section_len),
        "event_count_source": int(len(events)),
        "event_count_tiled": int(len(out)),
        "features": features,
    }
    return out, prov


def try_build_internal_events(config: Any) -> Tuple[Optional[List[Dict[str, Any]]], Dict[str, Any]]:
    db_path = resolve_db_path()
    tempo = float((getattr(config, "tempos", None) or [120])[0] or 120)

    weights = load_weights()

    max_candidates = int(os.getenv("DRUMMERBRAIN_SEARCH_BUDGET", "250") or 250)
    max_candidates = max(10, min(max_candidates, 5000))
    tempo_window_bpm = _safe_float(os.getenv("DRUMMERBRAIN_TEMPO_WINDOW_BPM", "40"), 40.0)
    tempo_window_bpm = max(5.0, min(tempo_window_bpm, 200.0))

    def _base_prov(*, used: bool, reason: str) -> Dict[str, Any]:
        return {
            "used": bool(used),
            "reason": str(reason),
            "db_path": str(db_path),
            "policy_version": _POLICY_VERSION,
            "weights": weights,
            "search_budget": {
                "max_candidates": int(max_candidates),
                "tempo_window_bpm": float(tempo_window_bpm),
            },
        }

    if not db_path.exists():
        return None, _base_prov(used=False, reason="db_missing")

    beats_per_bar = int(getattr(config, "time_signature", (4, 4))[0] or 4)
    beats_per_bar = max(1, beats_per_bar)
    bar_dur = (60.0 / max(1e-3, tempo)) * float(beats_per_bar)
    section_len = float(getattr(config, "measure_count", 1) or 1) * bar_dur

    conn = _connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                aa.asset_id,
                aa.dataset_id,
                aa.song_key,
                aa.variant,
                ta.transcription_version,
                ta.confidence,
                ta.events_json,
                ta.features_json,
                ta.provenance_json,
                an.songmap_json
            FROM transcription_artifacts ta
            JOIN audio_assets aa ON aa.asset_id = ta.asset_id
            JOIN datasets ds ON ds.dataset_id = aa.dataset_id
            LEFT JOIN audio_analysis an ON an.asset_id = aa.asset_id
            WHERE ta.events_json IS NOT NULL
              AND ta.confidence IS NOT NULL
              AND ta.confidence > 0
              AND ds.enabled = 1
            """
        )
        rows: List[sqlite3.Row] = cur.fetchall() or []
    except Exception as e:
        prov = _base_prov(used=False, reason=f"query_failed: {type(e).__name__}: {e}")
        return None, prov
    finally:
        conn.close()

    if not rows:
        try:
            conn2 = _connect(db_path)
            cur2 = conn2.cursor()
            cur2.execute(
                """
                SELECT ta.provenance_json
                FROM transcription_artifacts ta
                JOIN audio_assets aa ON aa.asset_id = ta.asset_id
                JOIN datasets ds ON ds.dataset_id = aa.dataset_id
                WHERE ds.enabled = 1
                """
            )
            prov_rows = cur2.fetchall() or []
        except Exception:
            prov_rows = []
        finally:
            try:
                conn2.close()
            except Exception:
                pass

        counts = {"analysis_failed": 0, "transcription_failed": 0, "unknown": 0}
        for pr in prov_rows:
            try:
                pj = json.loads(pr["provenance_json"] or "{}") if pr["provenance_json"] is not None else {}
            except Exception:
                pj = {}
            cls = _classify_failure(pj)
            counts[cls] = int(counts.get(cls, 0)) + 1

        prov = _base_prov(used=False, reason="no_candidates")
        prov["failure_counts"] = counts
        return None, prov

    target_bpm = float(tempo)

    scored: List[Tuple[float, str, sqlite3.Row]] = []
    for r in rows:
        try:
            conf = _safe_float(r["confidence"], 0.0)
            variant = str(r["variant"] or "")
            songmap = json.loads(r["songmap_json"] or "{}") if r["songmap_json"] is not None else {}
            src_bpm = _safe_float(songmap.get("global_bpm_estimate"), 0.0)

            feats = json.loads(r["features_json"] or "{}") if r["features_json"] is not None else {}
            tempo_adaptive = bool(feats.get("tempo_adaptive"))
            if src_bpm <= 1e-3:
                src_bpm = _safe_float(feats.get("tempo_bpm"), 0.0)

            if (not tempo_adaptive) and src_bpm > 1e-3 and abs(src_bpm - target_bpm) > tempo_window_bpm:
                continue

            pat_len = _safe_float(feats.get("duration_s"), 0.0)
            if not (pat_len > 1e-3):
                dur_beats = _safe_float(feats.get("duration_beats"), 0.0)
                if tempo_adaptive and dur_beats > 1e-6:
                    pat_len = float(dur_beats) * (60.0 / max(1e-3, target_bpm))
                else:
                    pat_len = 0.0

            bar_multiple_err = 1.0
            loop_fit_err = 1.0
            if pat_len > 1e-3:
                bars = pat_len / max(bar_dur, 1e-6)
                bar_multiple_err = abs(bars - round(bars))
                tiles = section_len / max(pat_len, 1e-6)
                loop_fit_err = abs(tiles - round(tiles))

            tempo_err = abs(src_bpm - target_bpm) if (not tempo_adaptive and src_bpm > 1e-3) else 0.0

            # Deterministic content terms (features_json contract).
            has_kick = bool(feats.get("has_kick"))
            has_snare = bool(feats.get("has_snare"))
            backbeat_ratio = _safe_float(feats.get("backbeat_ratio"), 0.0)
            sync_ratio = _safe_float(feats.get("syncopation_ratio"), 0.0)
            hits_per_beat = _safe_float(feats.get("hits_per_beat"), 0.0)

            skeleton_penalty = 0.0
            if not has_kick:
                skeleton_penalty += _safe_float((weights.get("skeleton_penalty") or {}).get("missing_kick"), 0.35)
            if not has_snare:
                skeleton_penalty += _safe_float((weights.get("skeleton_penalty") or {}).get("missing_snare"), 0.45)

            # Prefer a clear backbeat when available.
            bb_target = _safe_float((weights.get("backbeat") or {}).get("target"), 0.8)
            bb_w = _safe_float((weights.get("backbeat") or {}).get("w"), 0.20)
            backbeat_term = abs(backbeat_ratio - bb_target) * bb_w
            # Prefer moderate syncopation; avoid extremely offbeat/noisy patterns.
            syn_target = _safe_float((weights.get("syncopation") or {}).get("target"), 0.25)
            syn_w = _safe_float((weights.get("syncopation") or {}).get("w"), 0.15)
            sync_term = abs(sync_ratio - syn_target) * syn_w
            # Prefer moderate density.
            dens_target = _safe_float((weights.get("density") or {}).get("target"), 2.0)
            dens_w = _safe_float((weights.get("density") or {}).get("w"), 0.05)
            density_term = abs(hits_per_beat - dens_target) * dens_w
            variant_bonus = 0.0
            if variant == "drum":
                variant_bonus = _safe_float((weights.get("variant_bonus") or {}).get("drum"), -0.25)
            elif variant == "original":
                variant_bonus = _safe_float((weights.get("variant_bonus") or {}).get("original"), 0.10)

            t_div = max(1e-6, _safe_float(weights.get("tempo_div"), 25.0))
            t_term = (tempo_err / t_div)

            bar_w = _safe_float(weights.get("bar_multiple_w"), 0.35)
            bar_term = (bar_multiple_err * bar_w)

            loop_w = _safe_float(weights.get("loop_fit_w"), 0.75)
            loop_term = (loop_fit_err * loop_w)

            conf_w = _safe_float(weights.get("confidence_w"), 1.25)
            conf_term = -(conf * conf_w)
            score = (t_term + bar_term + loop_term + conf_term + variant_bonus + skeleton_penalty + backbeat_term + sync_term + density_term)
            scored.append((float(score), str(r["asset_id"]), r))
        except Exception:
            continue

    if not scored:
        return None, _base_prov(used=False, reason="no_scored_candidates")

    if len(scored) > max_candidates:
        try:
            tmp = []
            for sc, aid, row in scored:
                tmp.append((float(_safe_float(row["confidence"], 0.0)), float(sc), str(aid), row))
            tmp.sort(key=lambda t: (-t[0], t[1], t[2]))
            scored = [(t[1], t[2], t[3]) for t in tmp[:max_candidates]]
        except Exception:
            scored = scored[:max_candidates]

    scored.sort(key=lambda t: (float(t[0]), t[1]))
    best_score, best_id, best_row = scored[0]

    try:
        events = json.loads(best_row["events_json"] or "[]")
        features = json.loads(best_row["features_json"] or "{}") if best_row["features_json"] is not None else {}
        provenance = json.loads(best_row["provenance_json"] or "{}") if best_row["provenance_json"] is not None else {}
        if not isinstance(events, list):
            events = []
        if not isinstance(features, dict):
            features = {}
        if not isinstance(provenance, dict):
            provenance = {}
    except Exception as e:
        prov = _base_prov(used=False, reason=f"parse_failed: {type(e).__name__}: {e}")
        prov["asset_id"] = best_id
        return None, prov

    internal, prov = build_internal_events_from_asset(
        config=config,
        asset_id=str(best_row["asset_id"]),
        dataset_id=str(best_row["dataset_id"]),
        song_key=str(best_row["song_key"]) if best_row["song_key"] is not None else None,
        variant=str(best_row["variant"]) if best_row["variant"] is not None else None,
        confidence=_safe_float(best_row["confidence"], 0.0),
        events=events,
        features=features,
    )

    prov["candidate_count"] = int(len(scored))
    prov["best_score"] = float(best_score)
    prov["target_bpm"] = float(target_bpm)
    prov["db_path"] = str(db_path)
    prov["policy_version"] = _POLICY_VERSION
    prov["search_budget"] = {
        "max_candidates": int(max_candidates),
        "tempo_window_bpm": float(tempo_window_bpm),
    }
    prov["weights"] = weights
    prov["source_provenance"] = provenance
    prov["constraints"] = {
        "time_signature": list(getattr(config, "time_signature", (4, 4)) or (4, 4)),
        "measure_count": int(getattr(config, "measure_count", 1) or 1),
        "bar_dur_s": float(bar_dur),
        "section_len_s": float(section_len),
    }

    try:
        src_bpm_best = None
        try:
            songmap_best = json.loads(best_row["songmap_json"] or "{}") if best_row["songmap_json"] is not None else {}
            src_bpm_best = _safe_float(songmap_best.get("global_bpm_estimate"), 0.0)
        except Exception:
            src_bpm_best = None
        if not (src_bpm_best and src_bpm_best > 1e-3):
            src_bpm_best = _safe_float(features.get("tempo_bpm"), 0.0)

        tempo_err_best = abs(float(src_bpm_best) - float(target_bpm)) if src_bpm_best and src_bpm_best > 1e-3 else None
        pat_len_best = _safe_float(features.get("duration_s"), 0.0)
        bar_multiple_err_best = None
        loop_fit_err_best = None
        if pat_len_best and pat_len_best > 1e-3:
            bars_best = pat_len_best / max(bar_dur, 1e-6)
            bar_multiple_err_best = abs(bars_best - round(bars_best))
            tiles_best = section_len / max(pat_len_best, 1e-6)
            loop_fit_err_best = abs(tiles_best - round(tiles_best))
        prov["score_terms"] = {
            "src_bpm": float(src_bpm_best) if src_bpm_best is not None else None,
            "tempo_err_bpm": float(tempo_err_best) if tempo_err_best is not None else None,
            "pattern_len_s": float(pat_len_best) if pat_len_best is not None else None,
            "bar_multiple_err": float(bar_multiple_err_best) if bar_multiple_err_best is not None else None,
            "loop_fit_err": float(loop_fit_err_best) if loop_fit_err_best is not None else None,
            "confidence": float(_safe_float(best_row["confidence"], 0.0)),
            "has_kick": bool(features.get("has_kick")) if isinstance(features, dict) else None,
            "has_snare": bool(features.get("has_snare")) if isinstance(features, dict) else None,
            "backbeat_ratio": float(_safe_float((features or {}).get("backbeat_ratio"), 0.0)) if isinstance(features, dict) else None,
            "syncopation_ratio": float(_safe_float((features or {}).get("syncopation_ratio"), 0.0)) if isinstance(features, dict) else None,
            "hits_per_beat": float(_safe_float((features or {}).get("hits_per_beat"), 0.0)) if isinstance(features, dict) else None,
        }
    except Exception:
        pass

    if internal:
        return internal, prov
    prov2 = _base_prov(used=False, reason="built_no_events")
    prov2["asset_id"] = best_id
    return None, prov2
