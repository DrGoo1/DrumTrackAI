"""REST API for calibration lab."""
from __future__ import annotations

import json
import shutil
from datetime import datetime
import os
import base64
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Literal

from fastapi import FastAPI, APIRouter, Depends, HTTPException, Query, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from admin.services.central_database_service import CentralDatabaseService
from sqlalchemy import create_engine, text  # type: ignore

import requests  # type: ignore
from jose import jwt  # type: ignore

from backend.services.artifact_url_service import ArtifactUrlService
from backend.services.calibration_render_service import CalibrationRenderService, RenderRequest
from backend.services.calibration_candidate_generator import generate_candidate_run
from backend.app.assimilation.api.routes_drummer_generation import (
    router as assimilation_generation_router,
)

if TYPE_CHECKING:
    from admin.services.central_database_service import (
        AudioArtifact,
        CalibrationFeedback,
        CalibrationRun,
        EvaluationItem,
        EvaluationSession,
        RunVersion,
    )

router = APIRouter(prefix="/calibration", tags=["calibration"])

_artifact_url_service = ArtifactUrlService()


def get_db_service() -> CentralDatabaseService:
    svc = CentralDatabaseService.get_instance()
    if svc is None:
        raise RuntimeError("CentralDatabaseService unavailable")
    if not svc.initialize():
        raise RuntimeError("CentralDatabaseService failed to initialize")
    return svc


class CompletionStatusInfo(BaseModel):
    status: str
    completion_ratio: Optional[float] = None


class DrummerListItem(BaseModel):
    slug: str
    displayName: str
    completionStatus: CompletionStatusInfo
    assimilationStatus: Optional[Dict[str, Any]] = None
    latestRunAt: Optional[datetime] = None
    metricsWithin: Optional[int] = None
    metricsCompared: Optional[int] = None


class CalibrationRunPayload(BaseModel):
    id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    outcome: str
    note_count: Optional[int] = None
    fills_per_minute: Optional[float] = None
    delta_summary: Optional[str] = None
    metrics_within: Optional[int] = None
    metrics_compared: Optional[int] = None


class FeedbackEntry(BaseModel):
    id: str
    submitted_at: datetime
    author: Optional[str] = None
    rating: int
    comment: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AdjustmentPayload(BaseModel):
    adjustments: Dict[str, Any]
    metadata: Dict[str, Any] = Field(default_factory=dict)


class GenerateCandidatesRequest(BaseModel):
    base_groove_id: str
    target_drummer_slug: str
    candidate_count: int = Field(default=2, ge=1, le=4)
    include_baseline: bool = True
    render_profile_id: str = "calibration_standard_v1"
    sample_pack_version: str = "default"
    reviewer_id: Optional[str] = None
    seed: Optional[int] = None
    generation_controls: Optional[Dict[str, Any]] = None


class DrummerGenerationControlsPayload(BaseModel):
    target_drummer_id: str
    personality_amount: float = Field(default=0.75, ge=0.0, le=1.0)
    preserve_original_groove: float = Field(default=0.65, ge=0.0, le=1.0)
    fill_aggression: float = Field(default=0.5, ge=0.0, le=1.0)
    ghost_note_detail: float = Field(default=0.6, ge=0.0, le=1.0)
    cymbal_personality: float = Field(default=0.8, ge=0.0, le=1.0)
    timing_personality: float = Field(default=0.7, ge=0.0, le=1.0)
    velocity_personality: float = Field(default=0.75, ge=0.0, le=1.0)
    physical_realism_strictness: float = Field(default=0.9, ge=0.0, le=1.0)
    section_awareness: bool = True


class RunVersionPayload(BaseModel):
    run_id: str
    generator_version: str
    feature_version: str
    rollup_version: str
    sample_pack_version: str
    seed: int
    commit_hash: Optional[str] = None


class AudioArtifactPayload(BaseModel):
    artifact_id: str
    run_id: Optional[str] = None
    artifact_type: str
    storage_uri: str
    public_url: Optional[str] = None
    duration_sec: Optional[float] = None
    loudness_lufs: Optional[float] = None
    sample_pack_version: Optional[str] = None
    render_recipe: Dict[str, Any] = Field(default_factory=dict)


class EvaluationSessionPayload(BaseModel):
    session_id: str
    reviewer_id: str
    target_drummer_slug: str
    assigned_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    app_version: Optional[str] = None
    notes: Optional[str] = None


class EvaluationItemPayload(BaseModel):
    item_id: str
    session_id: str
    target_drummer_slug: str
    base_groove_id: str
    baseline_label: Optional[str] = None
    reference_artifact_id: Optional[str] = None
    baseline_run_id: Optional[str] = None
    candidate_a_run_id: Optional[str] = None
    candidate_b_run_id: Optional[str] = None
    eval_mode: Literal["single", "AB", "ABX"] = "AB"
    ab_mapping: Dict[str, Any] = Field(default_factory=dict)
    artifact_map: Dict[str, List[AudioArtifactPayload]] = Field(default_factory=dict)


class PairwiseJudgmentSubmit(BaseModel):
    preferred_candidate: Literal["A", "B", "tie"]
    closer_to_target: Literal["A", "B", "tie"]
    better_feel: Literal["A", "B", "tie"]
    more_musical: Literal["A", "B", "tie"]
    confidence: int = Field(ge=1, le=5)


class AttributeRatingsSubmit(BaseModel):
    candidate_label: Literal["A", "B", "single"]
    stylistic_authenticity: float = Field(ge=1, le=10)
    groove_feel: float = Field(ge=1, le=10)
    dynamics: float = Field(ge=1, le=10)
    phrasing: float = Field(ge=1, le=10)
    kit_balance: float = Field(ge=1, le=10)
    fill_behavior: float = Field(ge=1, le=10)
    human_realism: float = Field(ge=1, le=10)
    overall_usefulness: float = Field(ge=1, le=10)


class DrummerDetailPayload(BaseModel):
    slug: str
    displayName: str
    adjustments: Dict[str, Any]
    rollupTargets: Dict[str, Any]
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    assimilationStatus: Optional[Dict[str, Any]] = None
    runHistory: Optional[List[CalibrationRunPayload]] = None
    feedbackSamples: Optional[List[FeedbackEntry]] = None
    completionStatus: Optional[CompletionStatusInfo] = None


class CalibrationHealthPayload(BaseModel):
    status: str
    db_path: Optional[str] = None
    db_exists: bool = False
    calibration_tables: Dict[str, bool] = Field(default_factory=dict)
    notes: List[str] = Field(default_factory=list)


class CalibrationTrainingExportPayload(BaseModel):
    exported_at: datetime
    item_count: int
    filters: Dict[str, Any] = Field(default_factory=dict)
    items: List[Dict[str, Any]] = Field(default_factory=list)


class StoragePresignUploadRequest(BaseModel):
    drummer_slug: str
    run_id: Optional[str] = None
    file_name: str
    content_type: Optional[str] = None


class StoragePresignUploadResponse(BaseModel):
    bucket: str
    key: str
    url: str
    fields: Dict[str, Any]
    expires_in: int


class StoragePresignDownloadRequest(BaseModel):
    drummer_slug: str
    key: str


class StoragePresignDownloadResponse(BaseModel):
    bucket: str
    key: str
    url: str
    expires_in: int


class AnalysisJobCreateRequest(BaseModel):
    drummer_slug: str
    input_json: Dict[str, Any] = Field(default_factory=dict)


class AnalysisJobResponse(BaseModel):
    id: str
    drummer_id: str
    status: str
    input_json: Optional[str] = None
    result_json: Optional[str] = None
    error_text: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _bearer_token_from_request(request: Request) -> Optional[str]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def _parse_jwt_sub_unverified(token: str) -> Optional[str]:
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1] + ("=" * ((4 - len(parts[1]) % 4) % 4))
        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode("utf-8"))
        data = json.loads(payload_bytes.decode("utf-8"))
        sub = data.get("sub") or data.get("user_id")
        return str(sub) if sub else None
    except Exception:
        return None


_JWKS_CACHE: Dict[str, Any] = {"keys": [], "fetched_at": 0.0}


def _load_jwks(force: bool = False) -> Dict[str, Any]:
    import time as _time
    now = _time.time()
    ttl = 600.0
    if not force and _JWKS_CACHE.get("keys") and (now - float(_JWKS_CACHE.get("fetched_at", 0.0))) < ttl:
        return _JWKS_CACHE
    url = os.getenv("SUPABASE_JWKS_URL", "").strip()
    if not url:
        return {"keys": []}
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and isinstance(data.get("keys"), list):
            _JWKS_CACHE["keys"] = data["keys"]
            _JWKS_CACHE["fetched_at"] = now
            return _JWKS_CACHE
    except Exception:
        return {"keys": []}
    return {"keys": []}


def _verify_supabase_jwt(token: str) -> Optional[Dict[str, Any]]:
    audience = os.getenv("SUPABASE_JWT_AUDIENCE", None)
    jwks = _load_jwks()
    headers = jwt.get_unverified_header(token)
    kid = headers.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            try:
                return jwt.decode(token, key, algorithms=[key.get("alg", "RS256")], audience=audience)
            except Exception:
                continue
    # As a fallback, try each key
    for key in jwks.get("keys", []):
        try:
            return jwt.decode(token, key, algorithms=[key.get("alg", "RS256")], audience=audience)
        except Exception:
            continue
    return None


def _require_user(request: Request) -> str:
    token = _bearer_token_from_request(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    # Production: verify against Supabase JWKS
    if str(os.getenv("ALLOW_UNVERIFIED_JWT", "").strip().lower()) in {"1", "true", "yes"}:
        user_id = _parse_jwt_sub_unverified(token)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return user_id
    claims = _verify_supabase_jwt(token)
    if not isinstance(claims, dict):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token verification failed")
    sub = str(claims.get("sub") or claims.get("user_id") or "").strip()
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")
    return sub


class AnalysisDetailPayload(BaseModel):
    analysis_id: str
    drummer_slug: Optional[str] = None
    song_title: Optional[str] = None
    source_file: Optional[str] = None
    tempo_bpm: Optional[float] = None
    time_signature: Optional[str] = None
    duration_sec: Optional[float] = None
    created_at: Optional[str] = None
    hit_event_count: Optional[int] = None


class FeedbackSubmitRequest(BaseModel):
    drummer: str
    run_id: Optional[str] = None
    item_id: Optional[str] = None
    rating: int = Field(..., ge=1, le=5)
    comment: str
    author: Optional[str] = Field(default="Guest")


def _slug_from_row(row: Dict[str, Any]) -> str:
    for key in ("slug", "drummer_slug", "drummer_id", "id"):
        value = row.get(key)
        if value:
            slug = str(value).strip()
            if slug:
                return slug
    return ""


def _display_name_from_row(row: Dict[str, Any], slug: str) -> str:
    for key in ("display_name", "displayName", "name", "drummer_name"):
        value = row.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text
    if not slug:
        return "Unknown Drummer"
    return " ".join(part.capitalize() for part in slug.replace("-", "_").split("_") if part) or slug


def _completion_from_counts(within: Optional[int], total: Optional[int]) -> CompletionStatusInfo:
    if not total or total <= 0 or within is None:
        return CompletionStatusInfo(status="unknown", completion_ratio=None)
    ratio = float(within) / float(total)
    if ratio >= 0.8:
        status = "ready"
    elif ratio >= 0.6:
        status = "refine"
    else:
        status = "needs_tuning"
    return CompletionStatusInfo(status=status, completion_ratio=ratio)


def _completion_from_run(run: Optional["CalibrationRun"]) -> CompletionStatusInfo:
    if not run:
        return CompletionStatusInfo(status="unknown", completion_ratio=None)
    return _completion_from_counts(run.within_tolerance_count, run.total_compared)


def _safe_count(cursor: Any, query: str, params: tuple[Any, ...]) -> int:
    try:
        row = cursor.execute(query, params).fetchone()
        if not row:
            return 0
        value = row[0] if not isinstance(row, dict) else next(iter(row.values()))
        return int(value or 0)
    except Exception:
        return 0


def _assimilation_status_for_slug(db: CentralDatabaseService, slug: str) -> Dict[str, Any]:
    slug = (slug or "").strip()
    status: Dict[str, Any] = {
        "status": "unknown",
        "ready_for_calibration": False,
        "missing_steps": ["ingestion"],
        "counts": {
            "songs": 0,
            "artifacts": 0,
            "stems": 0,
            "hit_events": 0,
            "fills": 0,
            "techniques": 0,
        },
        "metrics": {
            "phase4_enriched_analyses": 0,
            "phase5_rollups": 0,
            "phase6_presets": 0,
        },
    }
    if not slug:
        return status

    try:
        conn = db._get_connection()
        cursor = conn.cursor()
    except Exception:
        return status

    drummer_fk: Optional[int] = None
    try:
        cursor.execute(
            """
            SELECT d.id
            FROM drummers d
            WHERE d.drummer_id = ? OR d.id = ?
            LIMIT 1
            """,
            (slug, slug),
        )
        row = cursor.fetchone()
        if row is not None:
            try:
                drummer_fk = int(row[0])
            except Exception:
                drummer_fk = None
    except Exception:
        drummer_fk = None

    params_fk_or_slug = (drummer_fk if drummer_fk is not None else slug, slug)
    songs = _safe_count(
        cursor,
        """
        SELECT COUNT(DISTINCT analysis_id)
        FROM song_performance_analysis
        WHERE CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
           OR CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
        """,
        params_fk_or_slug,
    )
    artifacts = _safe_count(
        cursor,
        """
        SELECT COUNT(1)
        FROM analysis_artifacts
        WHERE CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
           OR CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
        """,
        params_fk_or_slug,
    )
    stems = _safe_count(
        cursor,
        """
        SELECT COUNT(1)
        FROM stem_artifacts
        WHERE CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
           OR CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
        """,
        params_fk_or_slug,
    )
    hit_events = _safe_count(
        cursor,
        """
        SELECT COUNT(1)
        FROM drum_hit_events
        WHERE CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
           OR CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
        """,
        params_fk_or_slug,
    )
    fills = _safe_count(
        cursor,
        """
        SELECT COUNT(1)
        FROM fill_events
        WHERE CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
           OR CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
        """,
        params_fk_or_slug,
    )
    techniques = _safe_count(
        cursor,
        """
        SELECT COUNT(1)
        FROM technique_events
        WHERE CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
           OR CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
        """,
        params_fk_or_slug,
    )
    phase4_enriched = _safe_count(
        cursor,
        """
        SELECT COUNT(1)
        FROM song_performance_analysis
        WHERE (CAST(drummer_id AS TEXT) = CAST(? AS TEXT)
               OR CAST(drummer_id AS TEXT) = CAST(? AS TEXT))
          AND groove_micro_timing_variance IS NOT NULL
          AND groove_pocket_tightness IS NOT NULL
          AND humanness_score IS NOT NULL
        """,
        params_fk_or_slug,
    )

    rollup_count = 0
    if drummer_fk is not None:
        rollup_count = _safe_count(
            cursor,
            "SELECT COUNT(1) FROM drummer_profile_rollups WHERE drummer_id = ?",
            (drummer_fk,),
        )

    preset_count = 0
    if drummer_fk is not None:
        preset_count = _safe_count(
            cursor,
            "SELECT COUNT(1) FROM drummer_presets WHERE drummer_id = ?",
            (drummer_fk,),
        )

    missing_steps: List[str] = []
    if songs <= 0:
        missing_steps.append("ingestion")
    if hit_events <= 0:
        missing_steps.append("phase2_hit_events")
    if fills <= 0 or techniques <= 0:
        missing_steps.append("phase3_fills_techniques")
    if phase4_enriched <= 0:
        missing_steps.append("phase4_microtiming_dynamics")
    if rollup_count <= 0:
        missing_steps.append("phase5_rollup")
    if preset_count <= 0:
        missing_steps.append("phase6_persona_preset")

    ready = len(missing_steps) == 0
    overall_status = "ready_for_calibration" if ready else "needs_processing"

    status["status"] = overall_status
    status["ready_for_calibration"] = ready
    status["missing_steps"] = missing_steps
    status["counts"] = {
        "songs": songs,
        "artifacts": artifacts,
        "stems": stems,
        "hit_events": hit_events,
        "fills": fills,
        "techniques": techniques,
    }
    status["metrics"] = {
        "phase4_enriched_analyses": phase4_enriched,
        "phase5_rollups": rollup_count,
        "phase6_presets": preset_count,
    }
    return status


def _serialize_run(run: "CalibrationRun") -> CalibrationRunPayload:
    return CalibrationRunPayload(
        id=run.run_id,
        started_at=run.started_at,
        completed_at=run.completed_at,
        outcome=run.outcome,
        note_count=run.note_count,
        fills_per_minute=run.fills_per_minute,
        delta_summary=run.delta_summary,
        metrics_within=run.within_tolerance_count,
        metrics_compared=run.total_compared,
    )


def _serialize_feedback(entry: "CalibrationFeedback") -> FeedbackEntry:
    return FeedbackEntry(
        id=entry.feedback_id,
        submitted_at=entry.submitted_at,
        author=entry.author,
        rating=entry.rating,
        comment=entry.comment,
        metadata=_safe_json_dict(getattr(entry, "metadata", None)),
    )


def _safe_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()  # type: ignore[attr-defined]
    return model.dict()


def _serialize_run_version(version: Optional["RunVersion"]) -> Optional[RunVersionPayload]:
    if not version:
        return None
    return RunVersionPayload(
        run_id=version.run_id,
        generator_version=version.generator_version,
        feature_version=version.feature_version,
        rollup_version=version.rollup_version,
        sample_pack_version=version.sample_pack_version,
        seed=version.seed,
        commit_hash=version.commit_hash,
    )


def _serialize_artifact(artifact: "AudioArtifact") -> AudioArtifactPayload:
    return AudioArtifactPayload(
        artifact_id=artifact.artifact_id,
        run_id=artifact.run_id,
        artifact_type=artifact.artifact_type,
        storage_uri=artifact.storage_uri,
        public_url=_artifact_url_service.build_url(artifact.storage_uri),
        duration_sec=artifact.duration_sec,
        loudness_lufs=artifact.loudness_lufs,
        sample_pack_version=artifact.sample_pack_version,
        render_recipe=getattr(artifact, "render_recipe", {}) or {},
    )


def _serialize_session(session: "EvaluationSession") -> EvaluationSessionPayload:
    return EvaluationSessionPayload(
        session_id=session.session_id,
        reviewer_id=session.reviewer_id,
        target_drummer_slug=session.target_drummer_slug,
        assigned_at=session.assigned_at,
        started_at=session.started_at,
        completed_at=session.completed_at,
        app_version=session.app_version,
        notes=session.notes,
    )


def _serialize_item(
    item: "EvaluationItem",
    artifact_lookup: Dict[str, List[AudioArtifactPayload]],
    *,
    baseline_label: Optional[str] = None,
) -> EvaluationItemPayload:
    eval_mode = item.eval_mode if item.eval_mode in {"single", "AB", "ABX"} else "AB"
    return EvaluationItemPayload(
        item_id=item.item_id,
        session_id=item.session_id,
        target_drummer_slug=item.target_drummer_slug,
        base_groove_id=item.base_groove_id,
        baseline_label=baseline_label,
        reference_artifact_id=item.reference_artifact_id,
        baseline_run_id=item.baseline_run_id,
        candidate_a_run_id=item.candidate_a_run_id,
        candidate_b_run_id=item.candidate_b_run_id,
        eval_mode=eval_mode,
        ab_mapping=item.ab_mapping or {},
        artifact_map=artifact_lookup,
    )


def _pick_reference_artifact_id(
    db: CentralDatabaseService,
    *,
    baseline_run_id: Optional[str],
) -> Optional[str]:
    run_id = (baseline_run_id or "").strip()
    if not run_id:
        return None
    try:
        artifacts = db.get_audio_artifacts_for_run(run_id=run_id)
    except Exception:
        return None
    if not artifacts:
        return None

    preferred = [
        artifact
        for artifact in artifacts
        if str(getattr(artifact, "artifact_type", "")).lower() in {"mix", "preview", "audio"}
    ]
    selected = preferred[0] if preferred else artifacts[0]
    return str(getattr(selected, "artifact_id", "") or "") or None


def _resolve_local_path(value: Any) -> Optional[Path]:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = Path(text)
    if candidate.is_file():
        return candidate.resolve()
    root = Path(__file__).resolve().parents[1]
    alt = (root / candidate).resolve()
    if alt.is_file():
        return alt
    return None


def _song_label_from_path(path: Path) -> str:
    parent = path.parent
    parent_name = parent.name.strip()
    generic_dirs = {"drumsep_components", "components", "stems"}
    if parent_name.lower() in generic_dirs and parent.parent:
        parent_name = parent.parent.name.strip()
    stem = path.stem.strip()
    label = parent_name or stem or "Assimilated Reference"
    return label.replace("_", " ")


def _instrument_id_from_hit(instrument: str, component: str) -> str:
    inst = str(instrument or "").strip().lower()
    comp = str(component or "").strip().lower().replace(" ", "_")
    if comp and comp not in {"none", "null"}:
        if comp.startswith(inst):
            return comp
        if inst:
            return f"{inst}_{comp}"
    mapping = {
        "kick": "kick",
        "snare": "snare_center",
        "hihat": "hihat_closed",
        "hh": "hihat_closed",
        "ride": "ride_bow",
        "crash": "crash",
        "tom": "tom_mid",
        "toms": "tom_mid",
    }
    return mapping.get(inst, inst or "kick")


def _build_assimilation_base_groove(
    db: CentralDatabaseService,
    *,
    drummer_slug: str,
    analysis_id: str,
) -> Optional[Path]:
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT tempo_bpm, time_signature
        FROM song_performance_analysis
        WHERE analysis_id = ?
        LIMIT 1
        """,
        (analysis_id,),
    )
    spa = cursor.fetchone()
    if not spa:
        return None

    try:
        tempo_bpm = float(spa["tempo_bpm"] or 110.0)
    except Exception:
        tempo_bpm = 110.0
    time_signature = str(spa["time_signature"] or "4/4")
    try:
        beats_per_bar = int(time_signature.split("/", 1)[0]) if "/" in time_signature else 4
    except Exception:
        beats_per_bar = 4
    sec_per_bar = (60.0 / max(1e-6, tempo_bpm)) * max(1, beats_per_bar)

    cursor.execute(
        """
        SELECT instrument, component, onset_time_sec, velocity_est, bar_index
        FROM drum_hit_events
        WHERE analysis_id = ?
        ORDER BY onset_time_sec ASC
        """,
        (analysis_id,),
    )
    rows = cursor.fetchall() or []
    if not rows:
        return None

    first_onset = None
    raw_events: List[Dict[str, Any]] = []
    min_bar_idx = None
    for row in rows:
        try:
            onset = float(row["onset_time_sec"])
        except Exception:
            continue
        if first_onset is None:
            first_onset = onset
        try:
            bar_idx = int(row["bar_index"]) if row["bar_index"] is not None else None
        except Exception:
            bar_idx = None
        if bar_idx is not None:
            min_bar_idx = bar_idx if min_bar_idx is None else min(min_bar_idx, bar_idx)
        try:
            velocity = int(round(float(row["velocity_est"] or 90.0)))
        except Exception:
            velocity = 90
        raw_events.append(
            {
                "instrument": str(row["instrument"] or ""),
                "component": str(row["component"] or ""),
                "onset": onset,
                "bar_idx": bar_idx,
                "velocity": max(1, min(127, velocity)),
            }
        )
    if not raw_events or first_onset is None:
        return None

    max_bars = 2
    pattern_events: List[Dict[str, Any]] = []
    for event in raw_events:
        onset_norm = float(event["onset"]) - float(first_onset)
        if event["bar_idx"] is not None and min_bar_idx is not None:
            bar_idx = int(event["bar_idx"]) - int(min_bar_idx)
        else:
            bar_idx = int(onset_norm // sec_per_bar)
        if bar_idx < 0 or bar_idx >= max_bars:
            continue
        bar_start = float(bar_idx) * sec_per_bar
        bar_end = bar_start + sec_per_bar
        bar_pos_frac = (onset_norm - bar_start) / sec_per_bar if sec_per_bar > 0 else 0.0
        bar_pos_frac = max(0.0, min(0.999999, bar_pos_frac))
        pattern_events.append(
            {
                "barIndex": int(bar_idx),
                "barStartTime": round(bar_start, 6),
                "barEndTime": round(bar_end, 6),
                "bar_pos_frac": round(bar_pos_frac, 6),
                "time_sec": round(onset_norm, 6),
                "instrument_id": _instrument_id_from_hit(event["instrument"], event["component"]),
                "velocity": int(event["velocity"]),
            }
        )

    if not pattern_events:
        return None

    root = Path(__file__).resolve().parents[1]
    out_dir = root / "artifacts" / "calibration" / "base_grooves" / drummer_slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{analysis_id}.json"
    payload = {
        "description": f"Assimilated baseline groove from analysis {analysis_id}",
        "tempo_bpm": tempo_bpm,
        "time_signature": time_signature,
        "ppqn": 960,
        "pattern_events": pattern_events,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def _select_assimilation_baseline_source(
    db: CentralDatabaseService,
    *,
    drummer_slug: str,
) -> Optional[Dict[str, Any]]:
    conn = db._get_connection()
    cursor = conn.cursor()
    drummer_fk = db._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=drummer_slug)
    if drummer_fk is None:
        return None

    cursor.execute(
        """
        SELECT spa.analysis_id, spa.created_at, spa.source_file, s.title AS song_title
        FROM song_performance_analysis spa
        LEFT JOIN songs s ON s.id = spa.song_id
        WHERE spa.drummer_id = ?
        ORDER BY spa.created_at DESC
        LIMIT 50
        """,
        (int(drummer_fk),),
    )
    analyses = cursor.fetchall() or []
    if not analyses:
        return None

    preferred_stems = {"drums", "drum"}
    for row in analyses:
        analysis_id = str(row["analysis_id"] or "").strip()
        if not analysis_id:
            continue

        source_path: Optional[Path] = None
        source_song_name: Optional[str] = None

        cursor.execute(
            """
            SELECT stem_name, file_path
            FROM stem_artifacts
            WHERE analysis_id = ?
            """,
            (analysis_id,),
        )
        stem_rows = cursor.fetchall() or []
        best_stem: Optional[Path] = None
        fallback_stem: Optional[Path] = None
        for stem in stem_rows:
            stem_name = str(stem["stem_name"] or "").strip().lower()
            resolved = _resolve_local_path(stem["file_path"])
            if not resolved:
                continue
            if stem_name in preferred_stems:
                best_stem = resolved
                break
            if fallback_stem is None:
                fallback_stem = resolved
        source_path = best_stem or fallback_stem

        if source_path is None:
            source_path = _resolve_local_path(row["source_file"])

        if source_path is None:
            continue

        title = str(row["song_title"] or "").strip()
        source_song_name = title or _song_label_from_path(source_path)
        base_groove_path = _build_assimilation_base_groove(
            db,
            drummer_slug=drummer_slug,
            analysis_id=analysis_id,
        )

        return {
            "analysis_id": analysis_id,
            "source_path": source_path,
            "source_song_name": source_song_name,
            "base_groove_path": str(base_groove_path) if base_groove_path else None,
        }

    return None


def _create_reference_baseline_run(
    db: CentralDatabaseService,
    *,
    drummer_slug: str,
    baseline_source: Dict[str, Any],
    base_groove_id: str,
) -> Optional[Dict[str, Any]]:
    source_path = Path(str(baseline_source.get("source_path") or "")).resolve()
    if not source_path.is_file():
        return None

    analysis_id = str(baseline_source.get("analysis_id") or "").strip() or None
    source_song_name = str(baseline_source.get("source_song_name") or "").strip() or _song_label_from_path(source_path)
    run_id = db.log_calibration_run(
        drummer_slug=drummer_slug,
        outcome="reference",
        note_count=None,
        metadata={
            "requested_via": "generate-candidates",
            "source_type": "assimilated_song",
            "source_song_name": source_song_name,
            "analysis_id": analysis_id,
            "target_drummer_slug": drummer_slug,
            "base_groove_id": base_groove_id,
        },
        metrics={},
        comparison={},
    )
    if not run_id:
        return None

    root = Path(__file__).resolve().parents[1]
    dest_dir = root / "artifacts" / "calibration" / "references" / run_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / source_path.name
    if source_path.resolve() != dest_path.resolve():
        shutil.copy2(source_path, dest_path)

    storage_uri = str(Path("artifacts") / "calibration" / "references" / run_id / source_path.name)
    artifact_id = db.log_audio_artifact(
        run_id=run_id,
        artifact_type="reference_song",
        storage_uri=storage_uri,
        duration_sec=None,
        loudness_lufs=None,
        sample_pack_version=None,
        render_recipe={
            "requested_via": "generate-candidates",
            "source_type": "assimilated_song",
            "source_song_name": source_song_name,
            "analysis_id": analysis_id,
            "target_drummer_slug": drummer_slug,
            "base_groove_id": base_groove_id,
        },
    )
    if not artifact_id:
        return None
    return {
        "run_id": run_id,
        "artifact_id": artifact_id,
        "baseline_label": source_song_name,
    }


def _infer_baseline_label(
    *,
    item: "EvaluationItem",
    artifact_lookup: Dict[str, List[AudioArtifactPayload]],
) -> Optional[str]:
    baseline_artifacts = artifact_lookup.get("baseline") or []
    for artifact in baseline_artifacts:
        recipe = artifact.render_recipe or {}
        source_song = str(recipe.get("source_song_name") or "").strip()
        if source_song:
            return source_song
    return None


def _serialize_run_bundle(db: CentralDatabaseService, run_id: Optional[str]) -> Optional[Dict[str, Any]]:
    run_id_val = (run_id or "").strip()
    if not run_id_val:
        return None

    run = db.get_calibration_run(run_id=run_id_val)
    if not run:
        return None

    version = db.get_run_version(run_id=run_id_val)
    artifacts = db.get_audio_artifacts_for_run(run_id=run_id_val)
    return {
        "run": _model_dump(_serialize_run(run)),
        "run_version": _model_dump(_serialize_run_version(version)) if version else None,
        "artifacts": [_model_dump(_serialize_artifact(item)) for item in artifacts],
    }


def _safe_json_load(value: Any, default: Any) -> Any:
    try:
        if isinstance(value, str):
            parsed = json.loads(value)
            return parsed
    except Exception:
        return default
    return value if value is not None else default


def _fetch_pairwise_judgments(db: CentralDatabaseService, *, item_id: str) -> List[Dict[str, Any]]:
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT judgment_id, item_id, preferred_candidate, closer_to_target,
               better_feel, more_musical, confidence, created_at
        FROM pairwise_judgments
        WHERE item_id = ?
        ORDER BY created_at ASC
        """,
        (item_id,),
    )
    rows = cursor.fetchall() or []
    return [
        {
            "judgment_id": row["judgment_id"],
            "item_id": row["item_id"],
            "preferred_candidate": row["preferred_candidate"],
            "closer_to_target": row["closer_to_target"],
            "better_feel": row["better_feel"],
            "more_musical": row["more_musical"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _fetch_attribute_ratings(db: CentralDatabaseService, *, item_id: str) -> List[Dict[str, Any]]:
    conn = db._get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT rating_id, item_id, candidate_label,
               stylistic_authenticity, groove_feel, dynamics, phrasing,
               kit_balance, fill_behavior, human_realism, overall_usefulness,
               created_at
        FROM attribute_ratings
        WHERE item_id = ?
        ORDER BY created_at ASC
        """,
        (item_id,),
    )
    rows = cursor.fetchall() or []
    return [
        {
            "rating_id": row["rating_id"],
            "item_id": row["item_id"],
            "candidate_label": row["candidate_label"],
            "stylistic_authenticity": row["stylistic_authenticity"],
            "groove_feel": row["groove_feel"],
            "dynamics": row["dynamics"],
            "phrasing": row["phrasing"],
            "kit_balance": row["kit_balance"],
            "fill_behavior": row["fill_behavior"],
            "human_realism": row["human_realism"],
            "overall_usefulness": row["overall_usefulness"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _fetch_item_feedback(db: CentralDatabaseService, *, item_id: str, drummer_slug: str) -> List[Dict[str, Any]]:
    conn = db._get_connection()
    cursor = conn.cursor()
    like_token = f'%"item_id": "{item_id}"%'
    cursor.execute(
        """
        SELECT feedback_id, drummer_slug, rating, comment, author, submitted_at, metadata_json
        FROM calibration_feedback
        WHERE drummer_slug = ? AND metadata_json LIKE ?
        ORDER BY submitted_at ASC
        """,
        (drummer_slug, like_token),
    )
    rows = cursor.fetchall() or []
    output: List[Dict[str, Any]] = []
    for row in rows:
        output.append(
            {
                "feedback_id": row["feedback_id"],
                "drummer_slug": row["drummer_slug"],
                "rating": row["rating"],
                "comment": row["comment"],
                "author": row["author"],
                "submitted_at": row["submitted_at"],
                "metadata": _safe_json_load(row["metadata_json"], {}),
            }
        )
    return output


@router.get("/drummers", response_model=List[DrummerListItem])
async def list_drummers(db: CentralDatabaseService = Depends(get_db_service)) -> List[DrummerListItem]:
    try:
        rows = db.get_drummers() or []
        results: List[DrummerListItem] = []
        for row in rows:
            slug = _slug_from_row(row)
            if not slug:
                continue
            display_name = _display_name_from_row(row, slug)

            completion_info: Optional[CompletionStatusInfo] = None
            within = row.get("metrics_within") or row.get("metrics_within_tolerance")
            total = row.get("metrics_compared") or row.get("metrics_total")
            if within is not None or total is not None:
                try:
                    completion_info = _completion_from_counts(
                        int(within) if within is not None else None,
                        int(total) if total is not None else None,
                    )
                except Exception:
                    completion_info = None

            latest_run: Optional["CalibrationRun"] = None
            try:
                latest_run = db.get_latest_calibration_run(drummer_slug=slug)
            except Exception:
                latest_run = None

            if completion_info is None:
                completion_info = _completion_from_run(latest_run)

            latest_run_at = None
            metrics_within_int: Optional[int] = None
            metrics_total_int: Optional[int] = None
            if latest_run:
                latest_run_at = latest_run.completed_at or latest_run.started_at
                metrics_within_int = latest_run.within_tolerance_count
                metrics_total_int = latest_run.total_compared

            results.append(
                DrummerListItem(
                    slug=slug,
                    displayName=display_name,
                    completionStatus=completion_info,
                    assimilationStatus=_assimilation_status_for_slug(db, slug),
                    latestRunAt=latest_run_at,
                    metricsWithin=metrics_within_int,
                    metricsCompared=metrics_total_int,
                )
            )
        return sorted(results, key=lambda item: item.displayName.lower())
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
# ASGI application factory
app = FastAPI(title="DrumTrackAI Calibration API")

_allowed_origins = [
    "https://drumtrackai.netlify.app",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers are registered at end of file after all routes are defined.


@router.post("/storage/presign-upload", response_model=StoragePresignUploadResponse)
async def presign_upload(
    request: Request,
    payload: StoragePresignUploadRequest,
    db: CentralDatabaseService = Depends(get_db_service),
):
    user_id = _require_user(request)
    slug = (payload.drummer_slug or "").strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing drummer slug")
    if not db.user_has_access_to_drummer(user_id=user_id, drummer_id=slug):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    bucket = os.getenv("AWS_S3_BUCKET", "").strip()
    region = os.getenv("AWS_REGION", "").strip() or os.getenv("AWS_DEFAULT_REGION", "").strip()
    if not bucket or not region:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 not configured")

    try:
        import boto3  # type: ignore
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="boto3 not installed")

    file_name = (payload.file_name or "upload.bin").strip()
    safe_name = file_name.replace("\\", "/").split("/")[-1]
    safe_name = "".join(ch if ch.isalnum() or ch in ("_", ".", "-") else "_" for ch in safe_name)
    run_id = (payload.run_id or str(uuid.uuid4())).strip()
    key = f"drummers/{slug}/runs/{run_id}/audio/{uuid.uuid4()}_{safe_name}"

    s3 = boto3.client("s3", region_name=region)
    fields = {"Content-Type": (payload.content_type or "application/octet-stream").strip()}
    conditions = [["starts-with", "$Content-Type", ""]]
    post = s3.generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=900,
    )

    db.log_calibration_audit(
        actor_user_id=user_id,
        drummer_id=slug,
        run_id=run_id,
        action="storage_presign_upload",
        payload={"key": key},
    )

    return StoragePresignUploadResponse(
        bucket=bucket,
        key=key,
        url=post.get("url", ""),
        fields=post.get("fields", {}),
        expires_in=900,
    )


@router.post("/storage/presign-download", response_model=StoragePresignDownloadResponse)
async def presign_download(
    request: Request,
    payload: StoragePresignDownloadRequest,
    db: CentralDatabaseService = Depends(get_db_service),
):
    user_id = _require_user(request)
    slug = (payload.drummer_slug or "").strip()
    key = (payload.key or "").strip()
    if not slug or not key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing parameters")
    if not db.user_has_access_to_drummer(user_id=user_id, drummer_id=slug):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    bucket = os.getenv("AWS_S3_BUCKET", "").strip()
    region = os.getenv("AWS_REGION", "").strip() or os.getenv("AWS_DEFAULT_REGION", "").strip()
    if not bucket or not region:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="S3 not configured")

    try:
        import boto3  # type: ignore
    except Exception:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="boto3 not installed")

    s3 = boto3.client("s3", region_name=region)
    try:
        url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=600,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    db.log_calibration_audit(
        actor_user_id=user_id,
        drummer_id=slug,
        run_id=None,
        action="storage_presign_download",
        payload={"key": key},
    )

    return StoragePresignDownloadResponse(bucket=bucket, key=key, url=url, expires_in=600)


@router.post("/jobs/analysis", response_model=Dict[str, Any])
async def enqueue_analysis_job(
    request: Request,
    payload: AnalysisJobCreateRequest,
    db: CentralDatabaseService = Depends(get_db_service),
):
    user_id = _require_user(request)
    slug = (payload.drummer_slug or "").strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing drummer slug")
    if not db.user_has_access_to_drummer(user_id=user_id, drummer_id=slug):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    job_id = db.create_analysis_job(drummer_id=slug, input_json=payload.input_json)
    if not job_id:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create job")
    db.log_calibration_audit(
        actor_user_id=user_id,
        drummer_id=slug,
        run_id=None,
        action="analysis_job_enqueued",
        payload={"job_id": job_id, "input_json": payload.input_json},
    )
    return {"status": "queued", "job_id": job_id}


@router.get("/jobs/{job_id}", response_model=AnalysisJobResponse)
async def get_analysis_job(job_id: str, request: Request, db: CentralDatabaseService = Depends(get_db_service)) -> AnalysisJobResponse:
    user_id = _require_user(request)
    ref = db.get_analysis_job(job_id=job_id)
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    drummer_id = str(ref.get("drummer_id") or "").strip()
    if not drummer_id or not db.user_has_access_to_drummer(user_id=user_id, drummer_id=drummer_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return AnalysisJobResponse(**ref)


@router.get("/analysis/{analysis_id}", response_model=AnalysisDetailPayload)
async def get_analysis_detail(analysis_id: str, db: CentralDatabaseService = Depends(get_db_service)) -> AnalysisDetailPayload:
    analysis_id = (analysis_id or "").strip()
    if not analysis_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing analysis id")

    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT spa.analysis_id,
                   spa.source_file,
                   spa.tempo_bpm,
                   spa.time_signature,
                   spa.duration_sec,
                   spa.created_at,
                   d.drummer_id AS drummer_slug,
                   s.title AS song_title
            FROM song_performance_analysis spa
            LEFT JOIN drummers d ON d.id = spa.drummer_id
            LEFT JOIN songs s ON s.id = spa.song_id
            WHERE spa.analysis_id = ?
            LIMIT 1
            """,
            (analysis_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

        hit_event_count: Optional[int] = None
        try:
            cursor.execute(
                "SELECT COUNT(1) FROM drum_hit_events WHERE analysis_id = ?",
                (analysis_id,),
            )
            hit_event_count = int((cursor.fetchone() or [0])[0] or 0)
        except Exception:
            hit_event_count = None

        return AnalysisDetailPayload(
            analysis_id=str(row["analysis_id"]),
            drummer_slug=str(row["drummer_slug"]).strip() if row["drummer_slug"] is not None else None,
            song_title=str(row["song_title"]).strip() if row["song_title"] is not None else None,
            source_file=str(row["source_file"]).strip() if row["source_file"] is not None else None,
            tempo_bpm=float(row["tempo_bpm"]) if row["tempo_bpm"] is not None else None,
            time_signature=str(row["time_signature"]).strip() if row["time_signature"] is not None else None,
            duration_sec=float(row["duration_sec"]) if row["duration_sec"] is not None else None,
            created_at=str(row["created_at"]).strip() if row["created_at"] is not None else None,
            hit_event_count=hit_event_count,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

 
@router.post("/evaluation-items/{item_id}/judgment")
async def submit_pairwise_judgment(
    item_id: str,
    payload: PairwiseJudgmentSubmit,
    db: CentralDatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    item_id = (item_id or "").strip()
    if not item_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing item id")

    try:
        judgment_id = db.log_pairwise_judgment(
            item_id=item_id,
            preferred_candidate=payload.preferred_candidate,
            closer_to_target=payload.closer_to_target,
            better_feel=payload.better_feel,
            more_musical=payload.more_musical,
            confidence=payload.confidence,
        )
        if not judgment_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store pairwise judgment")
        return {"status": "ok", "judgment_id": judgment_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/health", response_model=CalibrationHealthPayload)
async def calibration_health() -> CalibrationHealthPayload:
    db_path = None
    svc = CentralDatabaseService.get_instance()
    try:
        _ = svc.initialize()
        db_path = getattr(svc, "_db_path", None)
    except Exception:
        db_path = None

    calibration_tables = {
        "calibration_adjustments": False,
        "calibration_runs": False,
        "calibration_feedback": False,
        "evaluation_sessions": False,
        "evaluation_items": False,
        "pairwise_judgments": False,
        "attribute_ratings": False,
    }
    notes: List[str] = []
    try:
        engine_active = bool(getattr(svc, "_engine", None) is not None)
        backend_env = str(os.getenv("DB_BACKEND", "")).strip().lower()
        db_url_env = str(os.getenv("DATABASE_URL", "")).strip()
        url_scheme = db_url_env.split("://", 1)[0] if "://" in db_url_env else ""
        notes.append(f"engine_active={engine_active}")
        if backend_env:
            notes.append(f"db_backend={backend_env}")
        if url_scheme:
            notes.append(f"db_url_scheme={url_scheme}")
    except Exception:
        pass
    try:
        if engine_active:
            for table_name in calibration_tables.keys():
                cols = svc._table_columns(table_name)
                calibration_tables[table_name] = bool(cols)
    except Exception as exc:
        notes.append(f"schema_probe_failed: {exc}")

    missing_tables = [name for name, ok in calibration_tables.items() if not ok]
    if missing_tables:
        notes.append("missing_tables=" + ",".join(missing_tables))

    db_exists = False
    if db_path:
        try:
            db_exists = bool(Path(str(db_path)).exists())
        except Exception:
            db_exists = False

    status_text = "ok" if db_exists and not missing_tables else "degraded"
    return CalibrationHealthPayload(
        status=status_text,
        db_path=str(db_path) if db_path else None,
        db_exists=db_exists,
        calibration_tables=calibration_tables,
        notes=notes,
    )


@router.get("/db-diagnostics")
async def db_diagnostics() -> Dict[str, Any]:
    backend_env = str(os.getenv("DB_BACKEND", "")).strip().lower()
    db_url_env = str(os.getenv("DATABASE_URL", "")).strip()
    out: Dict[str, Any] = {
        "db_backend": backend_env or None,
        "has_database_url": bool(db_url_env),
    }
    configured = (backend_env in {"postgres", "postgresql"}) or db_url_env.lower().startswith("postgres")
    out["configured"] = configured
    if not configured:
        return out
    try:
        engine = create_engine(db_url_env, pool_pre_ping=True, future=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            try:
                row = conn.execute(text("SELECT current_user, current_database()"))
                info = row.first()
                if info is not None:
                    out["current_user"] = info[0]
                    out["current_database"] = info[1]
            except Exception:
                pass
        out["connect_ok"] = True
    except Exception as e:
        out["connect_ok"] = False
        out["error"] = str(e)
    return out


@router.get("/training-export", response_model=CalibrationTrainingExportPayload)
async def export_training_dataset(
    drummer_slug: Optional[str] = Query(default=None),
    limit: int = Query(default=200, ge=1, le=5000),
    db: CentralDatabaseService = Depends(get_db_service),
) -> CalibrationTrainingExportPayload:
    slug_filter = (drummer_slug or "").strip()
    items: List[Dict[str, Any]] = []

    try:
        conn = db._get_connection()
        cursor = conn.cursor()

        query = (
            "SELECT * FROM evaluation_items "
            + ("WHERE target_drummer_slug = ? " if slug_filter else "")
            + "ORDER BY created_at DESC LIMIT ?"
        )
        params: tuple[Any, ...] = ((slug_filter, int(limit)) if slug_filter else (int(limit),))
        cursor.execute(query, params)
        rows = cursor.fetchall() or []

        for row in rows:
            item = db._row_to_evaluation_item(row)
            if not item:
                continue

            item_payload: Dict[str, Any] = {
                "item": {
                    "item_id": item.item_id,
                    "session_id": item.session_id,
                    "target_drummer_slug": item.target_drummer_slug,
                    "base_groove_id": item.base_groove_id,
                    "reference_artifact_id": item.reference_artifact_id,
                    "baseline_run_id": item.baseline_run_id,
                    "candidate_a_run_id": item.candidate_a_run_id,
                    "candidate_b_run_id": item.candidate_b_run_id,
                    "eval_mode": item.eval_mode,
                    "ab_mapping": item.ab_mapping,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                },
                "assimilation_status": _assimilation_status_for_slug(db, item.target_drummer_slug),
                "pairwise_judgments": _fetch_pairwise_judgments(db, item_id=item.item_id),
                "attribute_ratings": _fetch_attribute_ratings(db, item_id=item.item_id),
                "feedback": _fetch_item_feedback(
                    db,
                    item_id=item.item_id,
                    drummer_slug=item.target_drummer_slug,
                ),
                "runs": {
                    "baseline": _serialize_run_bundle(db, item.baseline_run_id),
                    "A": _serialize_run_bundle(db, item.candidate_a_run_id),
                    "B": _serialize_run_bundle(db, item.candidate_b_run_id),
                },
            }
            items.append(item_payload)

        return CalibrationTrainingExportPayload(
            exported_at=datetime.utcnow(),
            item_count=len(items),
            filters={"drummer_slug": slug_filter or None, "limit": int(limit)},
            items=items,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/evaluation-items/{item_id}/ratings")
async def submit_attribute_ratings(
    item_id: str,
    payload: AttributeRatingsSubmit,
    db: CentralDatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    item_id = (item_id or "").strip()
    if not item_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing item id")

    try:
        rating_id = db.log_attribute_rating(item_id=item_id, **_model_dump(payload))
        if not rating_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to store ratings")
        return {"status": "ok", "rating_id": rating_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/evaluation-items/{item_id}", response_model=EvaluationItemPayload)
async def get_evaluation_item(item_id: str, db: CentralDatabaseService = Depends(get_db_service)) -> EvaluationItemPayload:
    item_id = (item_id or "").strip()
    if not item_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing item id")

    try:
        item = db.get_evaluation_item(item_id=item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation item not found")

        artifact_map: Dict[str, List[AudioArtifactPayload]] = {}
        for label, run_id in (
            ("baseline", item.baseline_run_id),
            ("A", item.candidate_a_run_id),
            ("B", item.candidate_b_run_id),
        ):
            run_id_val = (run_id or "").strip() if run_id else ""
            if not run_id_val:
                continue
            artifacts = db.get_audio_artifacts_for_run(run_id=run_id_val)
            artifact_map[label] = [_serialize_artifact(artifact) for artifact in artifacts]

        baseline_label = _infer_baseline_label(item=item, artifact_lookup=artifact_map)
        return _serialize_item(item, artifact_map, baseline_label=baseline_label)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/sessions/next", response_model=Optional[EvaluationSessionPayload])
async def get_next_session(
    reviewer_id: Optional[str] = Query(default=None),
    target_drummer_slug: Optional[str] = Query(default=None),
    db: CentralDatabaseService = Depends(get_db_service),
) -> Optional[EvaluationSessionPayload]:
    try:
        session = db.get_next_evaluation_session(
            reviewer_id=(reviewer_id or None),
            target_drummer_slug=(target_drummer_slug or None),
        )
        if not session:
            return None
        return _serialize_session(session)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/sessions/{session_id}/start")
async def start_session(session_id: str, db: CentralDatabaseService = Depends(get_db_service)) -> Dict[str, Any]:
    session_id = (session_id or "").strip()
    if not session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing session id")

    try:
        ok = db.start_evaluation_session(session_id=session_id)
        if not ok:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return {"status": "ok", "session_id": session_id}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/runs/{run_id}")
async def get_run(run_id: str, db: CentralDatabaseService = Depends(get_db_service)) -> Dict[str, Any]:
    run_id = (run_id or "").strip()
    if not run_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing run id")

    try:
        run = db.get_calibration_run(run_id=run_id)
        if not run:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")

        version = db.get_run_version(run_id=run_id)
        artifacts = db.get_audio_artifacts_for_run(run_id=run_id)

        payload: Dict[str, Any] = {
            "run": _model_dump(_serialize_run(run)),
            "artifacts": [_model_dump(_serialize_artifact(item)) for item in artifacts],
        }
        serialized_version = _serialize_run_version(version)
        if serialized_version:
            payload["run_version"] = _model_dump(serialized_version)

        return payload
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/runs/{run_id}/artifacts", response_model=List[AudioArtifactPayload])
async def list_run_artifacts(run_id: str, db: CentralDatabaseService = Depends(get_db_service)) -> List[AudioArtifactPayload]:
    run_id = (run_id or "").strip()
    if not run_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing run id")

    try:
        artifacts = db.get_audio_artifacts_for_run(run_id=run_id)
        return [_serialize_artifact(item) for item in artifacts]
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/generate-candidates")
async def generate_candidates(
    payload: GenerateCandidatesRequest,
    db: CentralDatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    base_groove_id = (payload.base_groove_id or "").strip()
    target_slug = (payload.target_drummer_slug or "").strip()
    if not base_groove_id or not target_slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing base groove or drummer")

    try:
        render_service = CalibrationRenderService(db)
        session_id: Optional[str] = None
        reviewer_id = (payload.reviewer_id or "").strip()
        if reviewer_id:
            db.upsert_reviewer_profile(reviewer_id=reviewer_id, display_name=reviewer_id)
            session_id = db.create_evaluation_session(
                reviewer_id=reviewer_id,
                target_drummer_slug=target_slug,
                app_version="calibration_phase2",
            )

        created_run_ids: List[str] = []
        generation_controls = payload.generation_controls if isinstance(payload.generation_controls, dict) else {}
        effective_base_groove_id = base_groove_id
        item_base_groove_id = base_groove_id
        baseline_analysis_id: Optional[str] = None
        baseline_run_id: Optional[str] = None
        reference_artifact_id: Optional[str] = None

        if payload.include_baseline:
            baseline_source = _select_assimilation_baseline_source(db, drummer_slug=target_slug)
            if baseline_source:
                source_groove_path = str(baseline_source.get("base_groove_path") or "").strip()
                if source_groove_path:
                    effective_base_groove_id = source_groove_path
                analysis_id = str(baseline_source.get("analysis_id") or "").strip()
                if analysis_id:
                    baseline_analysis_id = analysis_id
                    item_base_groove_id = f"assimilation:{analysis_id}"
                baseline_ref = _create_reference_baseline_run(
                    db,
                    drummer_slug=target_slug,
                    baseline_source=baseline_source,
                    base_groove_id=item_base_groove_id,
                )
                if baseline_ref:
                    baseline_run_id = str(baseline_ref.get("run_id") or "").strip() or None
                    reference_artifact_id = str(baseline_ref.get("artifact_id") or "").strip() or None

        generate_baseline = bool(payload.include_baseline and not baseline_run_id)
        requested = payload.candidate_count + (1 if generate_baseline else 0)
        for idx in range(requested):
            seed_offset = idx + (1 if baseline_run_id else 0)
            seed_value = payload.seed if payload.seed is not None else (1000 + seed_offset)
            run_data = generate_candidate_run(
                db=db,
                base_groove_id=effective_base_groove_id,
                drummer_slug=target_slug,
                seed=int(seed_value),
                generation_controls=generation_controls,
            )

            run_metadata = {
                "requested_via": "generate-candidates",
                "candidate_index": idx,
                "render_profile_id": payload.render_profile_id,
                "sample_pack_version": payload.sample_pack_version,
                "target_drummer_slug": target_slug,
                "tempo_bpm": run_data.tempo_bpm,
                "time_signature": run_data.time_signature,
                "kit_id": run_data.kit_id,
                "base_groove_path": run_data.base_groove_path,
                "generation_base_groove_id": effective_base_groove_id,
                "source_analysis_id": baseline_analysis_id,
                "generation_controls": generation_controls,
                **run_data.metadata,
            }

            run_id = db.log_calibration_run(
                drummer_slug=target_slug,
                outcome="queued",
                note_count=run_data.note_count,
                metadata=run_metadata,
                metrics={},
                comparison={},
            )
            if not run_id:
                continue
            created_run_ids.append(run_id)
            db.upsert_run_version(
                run_id=run_id,
                generator_version="candidate_generator_v1",
                feature_version="metrics_v1",
                rollup_version="phase5",
                sample_pack_version=payload.sample_pack_version,
                seed=int(seed_value),
                commit_hash=None,
            )

            # Store event stream placeholder so render pipeline has context.
            db.upsert_calibration_run_events(
                run_id=run_id,
                drummer_slug=target_slug,
                event_stream=run_data.event_stream,
                tempo_bpm=run_data.tempo_bpm,
                time_signature=run_data.time_signature,
                bars=run_data.bars,
                source_type="generate_candidates_autogen",
            )

            # Trigger render pipeline immediately.
            render_request = RenderRequest(
                run_id=run_id,
                render_profile_id=payload.render_profile_id,
                sample_pack_version=payload.sample_pack_version,
                kit_id=run_data.kit_id or "default_kit",
                seed=int(seed_value),
                render_recipe={
                    "base_groove_id": effective_base_groove_id,
                    "target_drummer_slug": target_slug,
                    "render_profile_id": payload.render_profile_id,
                    "requested_via": "generate-candidates",
                    "source_analysis_id": baseline_analysis_id,
                    "generation_controls": generation_controls,
                    "performance_spec": run_data.performance_spec,
                    "sections": run_data.sections,
                    "tempo_bpm": run_data.tempo_bpm,
                },
            )
            try:
                render_service.render_run(render_request)
            except Exception as render_exc:
                db.log_calibration_render_job(
                    run_id=run_id,
                    render_profile_id=payload.render_profile_id,
                    sample_pack_version=payload.sample_pack_version,
                    status="failed",
                    error_text=str(render_exc),
                )

        item_id: Optional[str] = None
        if session_id and (created_run_ids or baseline_run_id):
            created = created_run_ids.copy()
            generated_baseline_id: Optional[str] = created.pop(0) if generate_baseline and created else None
            if not baseline_run_id:
                baseline_run_id = generated_baseline_id
            candidate_a_run_id: Optional[str] = created.pop(0) if created else None
            candidate_b_run_id: Optional[str] = created.pop(0) if created else None
            if not reference_artifact_id:
                reference_artifact_id = _pick_reference_artifact_id(db, baseline_run_id=baseline_run_id)

            item_id = db.create_evaluation_item(
                session_id=session_id,
                base_groove_id=item_base_groove_id,
                target_drummer_slug=target_slug,
                reference_artifact_id=reference_artifact_id,
                baseline_run_id=baseline_run_id,
                candidate_a_run_id=candidate_a_run_id,
                candidate_b_run_id=candidate_b_run_id,
                eval_mode="AB",
                ab_mapping={"A": candidate_a_run_id, "B": candidate_b_run_id},
            )

        return {
            "status": "queued",
            "run_ids": created_run_ids,
            "session_id": session_id,
            "item_id": item_id,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

@router.get("/drummers/{slug}", response_model=DrummerDetailPayload)
async def get_drummer(slug: str, db: CentralDatabaseService = Depends(get_db_service)) -> DrummerDetailPayload:
    slug = (slug or "").strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing drummer slug")

    try:
        drummer_row = db.get_drummer(slug) or {"id": slug, "display_name": slug}
        display_name = _display_name_from_row(drummer_row, slug)

        adjustments_record = db.get_calibration_adjustments(slug) or {}
        adjustments = _safe_json_dict(adjustments_record.get("adjustments"))
        metadata = _safe_json_dict(adjustments_record.get("metadata"))

        rollup_result = db.run_phase5_profile_rollup_for_drummer(drummer_slug=slug) or {}
        rollup_targets = rollup_result.get("rollup")
        if not isinstance(rollup_targets, dict):
            rollup_targets = {}

        latest_run = db.get_latest_calibration_run(drummer_slug=slug)
        metrics = latest_run.metrics if latest_run and isinstance(latest_run.metrics, dict) else {}

        runs = db.get_calibration_runs(drummer_slug=slug, limit=10)
        run_history = [_serialize_run(run) for run in runs]

        feedback_entries = db.get_calibration_feedback(drummer_slug=slug, limit=25)
        feedback_samples = [_serialize_feedback(item) for item in feedback_entries]

        completion_status = _completion_from_run(latest_run)

        return DrummerDetailPayload(
            slug=slug,
            displayName=display_name,
            adjustments=adjustments,
            rollupTargets=rollup_targets,
            metrics=metrics,
            metadata=metadata,
            assimilationStatus=_assimilation_status_for_slug(db, slug),
            runHistory=run_history,
            feedbackSamples=feedback_samples,
            completionStatus=completion_status,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/drummers/{slug}/adjustments")
async def update_adjustments(
    slug: str,
    payload: AdjustmentPayload,
    db: CentralDatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    slug = (slug or "").strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing drummer slug")

    try:
        ok = db.upsert_calibration_adjustments(
            drummer_slug=slug,
            adjustments=payload.adjustments,
            metadata=payload.metadata,
        )
        if not ok:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save adjustments")

        record = db.get_calibration_adjustments(slug) or {}
        adjustments = _safe_json_dict(record.get("adjustments"))
        metadata = _safe_json_dict(record.get("metadata"))

        return {
            "status": "ok",
            "adjustments": adjustments,
            "metadata": metadata,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/drummers/{slug}/generate")
async def trigger_generation(slug: str, db: CentralDatabaseService = Depends(get_db_service)) -> Dict[str, Any]:
    slug = (slug or "").strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing drummer slug")

    try:
        rollup_result = db.run_phase5_profile_rollup_for_drummer(drummer_slug=slug) or {}
        rollup_payload = rollup_result.get("rollup") if isinstance(rollup_result, dict) else {}
        if not isinstance(rollup_payload, dict):
            rollup_payload = {}

        comparison = rollup_result.get("comparison") if isinstance(rollup_result, dict) else None
        if not isinstance(comparison, dict):
            comparison = rollup_payload.get("comparison") if isinstance(rollup_payload, dict) else None
        if not isinstance(comparison, dict):
            comparison = None

        metrics = rollup_result.get("metrics") if isinstance(rollup_result, dict) else None
        if not isinstance(metrics, dict):
            metrics = rollup_payload.get("metrics") if isinstance(rollup_payload, dict) else None
        if not isinstance(metrics, dict):
            metrics = None

        run_id = db.log_calibration_run(
            drummer_slug=slug,
            outcome="pending",
            metadata=rollup_payload,
            metrics=metrics,
            comparison=comparison,
            note_count=rollup_payload.get("note_count") if isinstance(rollup_payload, dict) else None,
            fills_per_minute=rollup_payload.get("fills_per_min") if isinstance(rollup_payload, dict) else None,
            within_tolerance_count=(comparison.get("within_tolerance_count") if isinstance(comparison, dict) else None),
            total_compared=(comparison.get("total_compared") if isinstance(comparison, dict) else None),
        )

        return {
            "status": "queued",
            "run_id": run_id,
            "rollupSaved": bool(rollup_result.get("saved")) if isinstance(rollup_result, dict) else False,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/feedback")
async def submit_feedback(
    payload: FeedbackSubmitRequest,
    db: CentralDatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    slug = (payload.drummer or "").strip()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing drummer slug")

    comment = (payload.comment or "").strip()
    if not comment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Feedback comment required")

    try:
        metadata: Dict[str, Any] = {}
        if payload.run_id:
            metadata["run_id"] = payload.run_id.strip()
        if payload.item_id:
            metadata["item_id"] = payload.item_id.strip()

        feedback_id = db.log_calibration_feedback(
            drummer_slug=slug,
            rating=payload.rating,
            comment=comment,
            author=(payload.author or "Guest").strip() or "Guest",
            metadata=metadata if metadata else None,
        )

        if not feedback_id:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record feedback")

        latest = db.get_calibration_feedback(drummer_slug=slug, limit=25)
        return {
            "status": "ok",
            "feedback_id": feedback_id,
            "feedback": [_serialize_feedback(item) for item in latest],
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

app.include_router(router)
app.include_router(assimilation_generation_router)
