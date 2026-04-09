"""REST API for calibration lab."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from admin.services.central_database_service import CentralDatabaseService

if TYPE_CHECKING:
    from admin.services.central_database_service import CalibrationFeedback, CalibrationRun

router = APIRouter(prefix="/calibration", tags=["calibration"])


def get_db_service() -> CentralDatabaseService:
    svc = CentralDatabaseService.instance()
    if svc is None:
        raise RuntimeError("CentralDatabaseService not initialized")
    return svc


class CompletionStatusInfo(BaseModel):
    status: str
    completion_ratio: Optional[float] = None


class DrummerListItem(BaseModel):
    slug: str
    displayName: str
    completionStatus: CompletionStatusInfo
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


class AdjustmentPayload(BaseModel):
    adjustments: Dict[str, Any]


class DrummerDetailPayload(BaseModel):
    slug: str
    displayName: str
    adjustments: Dict[str, Any]
    rollupTargets: Dict[str, Any]
    metrics: Dict[str, Any]
    metadata: Dict[str, Any]
    runHistory: Optional[List[CalibrationRunPayload]] = None
    feedbackSamples: Optional[List[FeedbackEntry]] = None
    completionStatus: Optional[CompletionStatusInfo] = None


class FeedbackSubmitRequest(BaseModel):
    drummer: str
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
                    latestRunAt=latest_run_at,
                    metricsWithin=metrics_within_int,
                    metricsCompared=metrics_total_int,
                )
            )
        return sorted(results, key=lambda item: item.displayName.lower())
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
        ok = db.upsert_calibration_adjustments(drummer_slug=slug, adjustments=payload.adjustments)
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
        feedback_id = db.log_calibration_feedback(
            drummer_slug=slug,
            rating=payload.rating,
            comment=comment,
            author=(payload.author or "Guest").strip() or "Guest",
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
