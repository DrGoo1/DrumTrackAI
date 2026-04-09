from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


DEFAULT_PROFILE_ROOTS = [
    Path("database/drummer_profiles_generated"),
    Path("backend/database/drummer_profiles_generated"),
    Path("admin/database/drummer_profiles_generated"),
]


def _candidate_roots() -> Iterable[Path]:
    env = os.getenv("SENTIENT_PROFILE_ROOTS", "").strip()
    if env:
        for raw in env.split(os.pathsep):
            p = Path(raw).expanduser()
            if p.exists():
                yield p
    for p in DEFAULT_PROFILE_ROOTS:
        if p.exists():
            yield p


def _slug_variants(drummer_id: str) -> Iterable[str]:
    raw = str(drummer_id or "").strip()
    if not raw:
        return []
    variants = {
        raw,
        raw.lower(),
        raw.replace(" ", "_"),
        raw.replace(" ", "-").lower(),
        raw.replace("-", "_").lower(),
    }
    return [v for v in variants if v]


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalize_profile(payload: Dict[str, Any], drummer_id: str) -> Dict[str, Any]:
    out = dict(payload or {})
    out.setdefault("publicDrummerId", drummer_id)
    out.setdefault("drummer_id", drummer_id)
    out.setdefault("source", "phase17_registry")
    out.setdefault("profile_version", "sentient_v1")
    return out


def _resolve_admin_db_path() -> Path:
    env = os.getenv("DRUMTRACKAI_DB_PATH", "").strip()
    if env:
        return Path(env)
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "admin" / "drumtrackai.db"


def _safe_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _avg(values: list[float]) -> Optional[float]:
    vals = [float(v) for v in values if v is not None]
    if not vals:
        return None
    return float(sum(vals) / float(len(vals)))


def _aggregate_phase32_42_payloads(payloads: list[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not payloads:
        return None

    # Current stored payload shape: {"phase37_42": {...}}
    p3742_list = [p.get("phase37_42") for p in payloads if isinstance(p.get("phase37_42"), dict)]
    if not p3742_list:
        return None

    # ---- microtiming_profile.global aggregation (mean/std across songs) ----
    micro_global_std = []
    micro_global_mean = []
    for p in p3742_list:
        micro = p.get("microtiming_profile")
        g = micro.get("global") if isinstance(micro, dict) else None
        if isinstance(g, dict):
            if g.get("std_ms") is not None:
                micro_global_std.append(_safe_float(g.get("std_ms"), 0.0))
            if g.get("mean_ms") is not None:
                micro_global_mean.append(_safe_float(g.get("mean_ms"), 0.0))

    microtiming_profile = None
    if micro_global_std or micro_global_mean:
        microtiming_profile = {
            "global": {
                "mean_ms": _avg(micro_global_mean),
                "std_ms": _avg(micro_global_std),
            }
        }

    # ---- drummer_personality_profile aggregation (simple average) ----
    personality_fields = [
        "aggressiveness",
        "restraint",
        "consistency",
        "chaos",
        "ghostStyle",
        "kickDrive",
    ]
    personality_values: Dict[str, list[float]] = {k: [] for k in personality_fields}
    crash_bias = []
    accent_bias = []
    for p in p3742_list:
        pers = p.get("drummer_personality_profile")
        if not isinstance(pers, dict):
            continue
        for k in personality_fields:
            if pers.get(k) is not None:
                personality_values[k].append(_safe_float(pers.get(k), 0.0))
        sig = pers.get("signatureHabits")
        if isinstance(sig, dict):
            if sig.get("crashBias") is not None:
                crash_bias.append(_safe_float(sig.get("crashBias"), 0.0))
            if sig.get("accentBias") is not None:
                accent_bias.append(_safe_float(sig.get("accentBias"), 0.0))

    drummer_personality_profile = None
    if any(personality_values[k] for k in personality_fields) or crash_bias or accent_bias:
        drummer_personality_profile = {k: _avg(personality_values[k]) for k in personality_fields}
        drummer_personality_profile["signatureHabits"] = {
            "crashBias": _avg(crash_bias),
            "accentBias": _avg(accent_bias),
        }

    # ---- continuity memory: concatenate and cap ----
    continuity = []
    for p in p3742_list:
        mem = p.get("phrase_continuity_memory")
        if isinstance(mem, list):
            continuity.extend([m for m in mem if isinstance(m, dict)])
    if len(continuity) > 24:
        continuity = continuity[-24:]

    # Limb/dynamics: keep last non-null (these are less well-defined to average)
    limb_profile = None
    dyn_profile = None
    for p in p3742_list:
        if limb_profile is None and isinstance(p.get("limb_interaction_profile"), dict):
            limb_profile = p.get("limb_interaction_profile")
        if dyn_profile is None and isinstance(p.get("dynamic_contour_profile"), dict):
            dyn_profile = p.get("dynamic_contour_profile")

    return {
        "phase37_42": {
            "microtiming_profile": microtiming_profile or {},
            "limb_interaction_profile": limb_profile or {},
            "dynamic_contour_profile": dyn_profile or {},
            "phrase_continuity_memory": continuity,
            "drummer_personality_profile": drummer_personality_profile or {},
        }
    }


def _load_phase32_42_features_from_admin_db(drummer_slug: str) -> Optional[Dict[str, Any]]:
    """Load latest computed Phase 32-42 feature payload for a drummer.

    Option A: features are stored in song_performance_analysis.phase32_42_features_json.
    We return the most recently updated non-null JSON payload.
    """
    drummer_slug = str(drummer_slug or "").strip()
    if not drummer_slug:
        return None

    db_path = _resolve_admin_db_path()
    if not db_path.exists():
        return None

    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id FROM drummers WHERE drummer_id = ? LIMIT 1", (drummer_slug,))
        row = cur.fetchone()
        if not row or row[0] is None:
            return None
        drummer_fk = int(row[0])

        cur.execute(
            """
            SELECT phase32_42_features_json
            FROM song_performance_analysis
            WHERE drummer_id = ?
              AND phase32_42_features_json IS NOT NULL
              AND TRIM(phase32_42_features_json) <> ''
            ORDER BY updated_at DESC
            """,
            (drummer_fk,),
        )
        payloads: list[Dict[str, Any]] = []
        for (raw,) in cur.fetchall() or []:
            if raw is None:
                continue
            try:
                pj = json.loads(str(raw))
            except Exception:
                continue
            if isinstance(pj, dict):
                payloads.append(pj)
        return _aggregate_phase32_42_payloads(payloads)
    except Exception:
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


def load_sentient_profile(drummer_id: str) -> Optional[Dict[str, Any]]:
    """Load an exported sentient profile JSON for a public drummer id.

    Expected export layout from earlier phases:
      database/drummer_profiles_generated/<slug>/drummer_profile.json
    """
    for root in _candidate_roots():
        for slug in _slug_variants(drummer_id):
            direct = root / slug / "drummer_profile.json"
            if direct.exists():
                payload = _load_json(direct)
                if payload:
                    out = _normalize_profile(payload, drummer_id)
                    phase_payload = _load_phase32_42_features_from_admin_db(drummer_id)
                    if phase_payload:
                        out["phase32_42_features"] = phase_payload
                    return out

            flat = root / f"{slug}.json"
            if flat.exists():
                payload = _load_json(flat)
                if payload:
                    out = _normalize_profile(payload, drummer_id)
                    phase_payload = _load_phase32_42_features_from_admin_db(drummer_id)
                    if phase_payload:
                        out["phase32_42_features"] = phase_payload
                    return out
    # Fallback: if no exported profile exists, still expose DB-derived phase32_42 features.
    phase_payload = _load_phase32_42_features_from_admin_db(drummer_id)
    if phase_payload:
        return _normalize_profile({"phase32_42_features": phase_payload}, drummer_id)
    return None


def build_sentient_profile_response(drummer_id: str) -> Dict[str, Any]:
    payload = load_sentient_profile(drummer_id)
    if payload:
        return {"ok": True, "drummer_id": drummer_id, "profile": payload, "found": True}
    return {"ok": True, "drummer_id": drummer_id, "profile": None, "found": False}
