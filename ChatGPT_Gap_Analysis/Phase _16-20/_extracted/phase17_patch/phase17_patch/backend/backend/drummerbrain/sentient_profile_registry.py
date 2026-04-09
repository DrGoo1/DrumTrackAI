from __future__ import annotations

import json
import os
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
                    return _normalize_profile(payload, drummer_id)

            flat = root / f"{slug}.json"
            if flat.exists():
                payload = _load_json(flat)
                if payload:
                    return _normalize_profile(payload, drummer_id)
    return None


def build_sentient_profile_response(drummer_id: str) -> Dict[str, Any]:
    payload = load_sentient_profile(drummer_id)
    if payload:
        return {"ok": True, "drummer_id": drummer_id, "profile": payload, "found": True}
    return {"ok": True, "drummer_id": drummer_id, "profile": None, "found": False}
