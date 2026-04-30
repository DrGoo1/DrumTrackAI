from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from admin.services.central_database_service import CentralDatabaseService
from backend.app.assimilation.evaluation.render_reanalyze_loop import render_reanalyze_loop
from backend.app.assimilation.evaluation.transform_audit import make_transform_audit


router = APIRouter(prefix="/assimilation/generation", tags=["assimilation-generation"])


def get_db_service() -> CentralDatabaseService:
    svc = CentralDatabaseService.get_instance()
    if svc is None:
        raise RuntimeError("CentralDatabaseService unavailable")
    if not svc.initialize():
        raise RuntimeError("CentralDatabaseService failed to initialize")
    return svc


class AssimilationGenerationRequest(BaseModel):
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


@router.post("/preview")
def preview_generation(
    payload: AssimilationGenerationRequest,
    db: CentralDatabaseService = Depends(get_db_service),
) -> Dict[str, Any]:
    slug = (payload.target_drummer_id or "").strip().lower()
    if not slug:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing target drummer id")

    conn = db._get_connection()
    cur = conn.cursor()
    drummer_fk = db._get_drummer_fk_by_slug(cursor=cur, drummer_slug=slug)
    if drummer_fk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drummer not found")
    drummer_fk = int(drummer_fk)

    rollup = db.compute_drummer_profile_rollup(drummer_fk=drummer_fk)
    conf = rollup.get("confidence") if isinstance(rollup.get("confidence"), dict) else {}
    conf_score = float(conf.get("score") or 0.0)

    personality_amount = float(payload.personality_amount)
    preserve = float(payload.preserve_original_groove)
    realism = float(payload.physical_realism_strictness)

    target_similarity = max(0.0, min(1.0, (0.35 * conf_score) + (0.65 * personality_amount)))
    source_similarity = max(0.0, min(1.0, (0.50 + (0.5 * preserve)) * (1.0 - (0.3 * personality_amount))))
    feasibility = max(0.0, min(1.0, (0.6 * realism) + (0.4 * conf_score)))
    groove_preservation = max(0.0, min(1.0, preserve * (0.85 + (0.15 * (1.0 - personality_amount)))))

    loop = render_reanalyze_loop(
        {
            "max_iterations": 4,
            "target_similarity_goal": max(0.7, min(0.98, personality_amount * 0.95)),
            "source_similarity_initial": source_similarity,
            "target_similarity_initial": target_similarity,
            "human_feasibility_initial": feasibility,
            "groove_preservation_initial": groove_preservation,
        }
    )
    final_scores = loop.get("final") if isinstance(loop.get("final"), dict) else {}
    if final_scores:
        target_similarity = float(final_scores.get("target_similarity_score", target_similarity))
        source_similarity = float(final_scores.get("source_similarity_score", source_similarity))
        feasibility = float(final_scores.get("human_feasibility_score", feasibility))
        groove_preservation = float(final_scores.get("groove_preservation_score", groove_preservation))

    before_snapshot = {
        "target_similarity_score": max(0.0, min(1.0, (0.35 * conf_score) + (0.65 * personality_amount))),
        "source_similarity_score": max(0.0, min(1.0, (0.50 + (0.5 * preserve)) * (1.0 - (0.3 * personality_amount)))),
        "human_feasibility_score": max(0.0, min(1.0, (0.6 * realism) + (0.4 * conf_score))),
        "groove_preservation_score": max(0.0, min(1.0, preserve * (0.85 + (0.15 * (1.0 - personality_amount))))),
    }
    after_snapshot = {
        "target_similarity_score": target_similarity,
        "source_similarity_score": source_similarity,
        "human_feasibility_score": feasibility,
        "groove_preservation_score": groove_preservation,
    }
    audit_bundle = make_transform_audit(before_snapshot, after_snapshot)

    audit_id = str(uuid.uuid4())
    db.log_generated_transform_audit(
        audit_id=audit_id,
        target_drummer_fk=drummer_fk,
        generation_run_id=None,
        personality_embedding_id=f"emb_{drummer_fk}",
        source_similarity_score=source_similarity,
        target_similarity_score=target_similarity,
        human_feasibility_score=feasibility,
        groove_preservation_score=groove_preservation,
        before_features={"rollup": rollup, "controls": payload.model_dump(), **before_snapshot},
        after_features={"target_similarity": target_similarity, "source_similarity": source_similarity, **after_snapshot},
        transform_delta={
            **(audit_bundle.get("transform_delta") if isinstance(audit_bundle.get("transform_delta"), dict) else {}),
            "personality_amount": personality_amount,
            "preserve_original_groove": preserve,
            "physical_realism_strictness": realism,
            "reanalyze_status": loop.get("status"),
            "iterations_run": loop.get("iterations_run"),
        },
        source_track_id=None,
    )

    return {
        "status": "preview_ready",
        "target_drummer_id": slug,
        "target_drummer_fk": drummer_fk,
        "audit_id": audit_id,
        "scores": {
            "target_similarity_score": target_similarity,
            "source_similarity_score": source_similarity,
            "human_feasibility_score": feasibility,
            "groove_preservation_score": groove_preservation,
        },
        "render_reanalyze": loop,
        "transform_audit": audit_bundle,
        "confidence": conf,
        "request": payload.model_dump(),
    }
