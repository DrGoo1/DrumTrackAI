"""Create controlled, blinded calibration trials around the production engine."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
import random
from typing import Any, Dict, Optional
import uuid

from admin.services.central_database_service import CentralDatabaseService
from backend.services.calibration_production_engine import (
    CalibrationProductionEngine,
    ProductionCandidate,
)
from backend.services.calibration_render_service import CalibrationRenderService, RenderRequest
from backend.services.calibration_v2_repository import CalibrationV2Repository


@dataclass(frozen=True)
class TrialCreateInput:
    reviewer_id: str
    drummer_slug: str
    base_groove_id: str
    challenger_treatment_id: str
    paired_seed: int
    assignment_seed: int
    repeats: int = 4
    render_profile_id: str = "calibration_standard_v2"
    sample_pack_version: str = "default"
    kit_id: str = "default_kit"


class CalibrationTrialService:
    def __init__(
        self,
        db: CentralDatabaseService,
        *,
        repository: Optional[CalibrationV2Repository] = None,
        engine: Optional[CalibrationProductionEngine] = None,
        render_service: Optional[CalibrationRenderService] = None,
    ) -> None:
        self._db = db
        self._repo = repository or CalibrationV2Repository(db)
        self._engine = engine or CalibrationProductionEngine(db)
        self._render = render_service or CalibrationRenderService(db)

    def create_trial(self, request: TrialCreateInput) -> Dict[str, Any]:
        treatment = self._repo.get_treatment(request.challenger_treatment_id)
        if treatment["drummer_slug"] != request.drummer_slug:
            raise ValueError("Treatment drummer does not match trial drummer")
        if treatment["status"] not in {"draft", "active"}:
            raise ValueError("Treatment must be draft or active")

        neutral = self._engine.generate_neutral(
            base_groove_id=request.base_groove_id,
            repeats=request.repeats,
            seed=request.paired_seed,
            kit_id=request.kit_id,
        )
        control = self._engine.generate_candidate(
            role="control",
            base_groove_id=request.base_groove_id,
            drummer_slug=request.drummer_slug,
            seed=request.paired_seed,
            repeats=request.repeats,
            cfg_overrides={},
            profile_overrides={},
            treatment_id=None,
            kit_id=request.kit_id,
        )
        challenger = self._engine.generate_candidate(
            role="challenger",
            base_groove_id=request.base_groove_id,
            drummer_slug=request.drummer_slug,
            seed=request.paired_seed,
            repeats=request.repeats,
            cfg_overrides=treatment.get("cfg_overrides") or {},
            profile_overrides=treatment.get("profile_overrides") or {},
            treatment_id=request.challenger_treatment_id,
            kit_id=request.kit_id,
        )

        if control.metadata["base_pattern_hash"] != challenger.metadata["base_pattern_hash"]:
            raise RuntimeError("Control/challenger base-pattern hashes differ")
        if control.metadata["paired_seed"] != challenger.metadata["paired_seed"]:
            raise RuntimeError("Control/challenger paired seeds differ")
        if control.metadata["event_stream_hash"] == challenger.metadata["event_stream_hash"]:
            raise RuntimeError(
                "Challenger produced no audible event change. Refuse to create a meaningless trial."
            )

        created_runs: Dict[str, str] = {}
        try:
            for candidate in (neutral, control, challenger):
                created_runs[candidate.role] = self._persist_and_queue_candidate(
                    candidate=candidate,
                    drummer_slug=request.drummer_slug,
                    render_profile_id=request.render_profile_id,
                    sample_pack_version=request.sample_pack_version,
                    seed=request.paired_seed,
                )

            lane_pairs = [
                ("control", created_runs["control"]),
                ("challenger", created_runs["challenger"]),
            ]
            assignment_rng = random.Random(int(request.assignment_seed))
            assignment_rng.shuffle(lane_pairs)
            lane_a_role, lane_a_run = lane_pairs[0]
            lane_b_role, lane_b_run = lane_pairs[1]

            session_id = self._db.create_evaluation_session(
                reviewer_id=request.reviewer_id,
                target_drummer_slug=request.drummer_slug,
                app_version="calibration_v2",
                notes="production-engine controlled trial",
            )
            if not session_id:
                raise RuntimeError("Failed to create evaluation session")

            item_id = self._db.create_evaluation_item(
                session_id=session_id,
                base_groove_id=request.base_groove_id,
                target_drummer_slug=request.drummer_slug,
                reference_artifact_id=None,
                baseline_run_id=created_runs["neutral"],
                candidate_a_run_id=lane_a_run,
                candidate_b_run_id=lane_b_run,
                eval_mode="AB",
                ab_mapping={
                    "schema": "calibration_v2_internal_only",
                    "A": {"role": lane_a_role, "run_id": lane_a_run},
                    "B": {"role": lane_b_role, "run_id": lane_b_run},
                },
            )
            if not item_id:
                raise RuntimeError("Failed to create evaluation item")

            trial_id = f"trial_{uuid.uuid4().hex[:16]}"
            self._repo.create_trial_record(
                {
                    "trial_id": trial_id,
                    "item_id": item_id,
                    "session_id": session_id,
                    "reviewer_id": request.reviewer_id,
                    "drummer_slug": request.drummer_slug,
                    "base_groove_id": request.base_groove_id,
                    "neutral_run_id": created_runs["neutral"],
                    "control_run_id": created_runs["control"],
                    "challenger_run_id": created_runs["challenger"],
                    "visible_a_run_id": lane_a_run,
                    "visible_b_run_id": lane_b_run,
                    "challenger_treatment_id": request.challenger_treatment_id,
                    "paired_seed": int(request.paired_seed),
                    "assignment_seed": int(request.assignment_seed),
                    "control_profile_hash": control.metadata.get("profile_snapshot_hash"),
                    "challenger_profile_hash": challenger.metadata.get("profile_snapshot_hash"),
                    "control_profile_snapshot": control.profile_snapshot or {},
                    "challenger_profile_snapshot": challenger.profile_snapshot or {},
                    "assignment_json": {
                        "A": {"role": lane_a_role, "run_id": lane_a_run},
                        "B": {"role": lane_b_role, "run_id": lane_b_run},
                    },
                    "generation_metadata": {
                        "neutral": neutral.metadata,
                        "control": control.metadata,
                        "challenger": challenger.metadata,
                    },
                    "model_version": str(
                        challenger.metadata.get("production_metadata", {}).get("model_version")
                        or os.getenv("DRUMTRACKAI_MODEL_VERSION", "unknown")
                    ),
                    "renderer_version": str(os.getenv("CALIBRATION_RENDERER_VERSION", "unknown")),
                    "sample_pack_version": request.sample_pack_version,
                    "status": "queued",
                }
            )
            return {
                "trial_id": trial_id,
                "session_id": session_id,
                "item_id": item_id,
                "run_ids": created_runs,
                "status": "queued",
            }
        except Exception as exc:
            for role, run_id in created_runs.items():
                try:
                    candidate = {"neutral": neutral, "control": control, "challenger": challenger}[role]
                    self._db.log_calibration_run(
                        run_id=run_id,
                        drummer_slug=request.drummer_slug,
                        outcome="failure",
                        completed_at=datetime.utcnow(),
                        note_count=candidate.note_count,
                        metadata={**candidate.metadata, "trial_create_error": str(exc)},
                    )
                except Exception:
                    pass
            raise

    def _persist_and_queue_candidate(
        self,
        *,
        candidate: ProductionCandidate,
        drummer_slug: str,
        render_profile_id: str,
        sample_pack_version: str,
        seed: int,
    ) -> str:
        run_id = f"calv2_{uuid.uuid4().hex[:24]}"
        commit_hash = str(
            os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("GIT_COMMIT")
            or os.getenv("SOURCE_VERSION")
            or ""
        ).strip() or None
        run_metadata = {
            **candidate.metadata,
            "requested_via": "calibration_v2_trial_service",
            "render_profile_id": render_profile_id,
            "sample_pack_version": sample_pack_version,
            "kit_id": candidate.kit_id,
            "tempo_bpm": candidate.tempo_bpm,
            "time_signature": candidate.time_signature,
            "base_groove_path": candidate.base_groove_path,
        }
        result = self._db.log_calibration_run(
            run_id=run_id,
            drummer_slug=drummer_slug,
            outcome="queued",
            note_count=candidate.note_count,
            metadata=run_metadata,
            metrics={},
            comparison={},
        )
        if not result:
            raise RuntimeError(f"Could not persist {candidate.role} run")
        if not self._db.upsert_run_version(
            run_id=run_id,
            generator_version="production_performance_spec_v2",
            feature_version="calibration_v2",
            rollup_version=str(candidate.metadata.get("rollup_version") or "neutral"),
            sample_pack_version=sample_pack_version,
            seed=int(seed),
            commit_hash=commit_hash,
        ):
            raise RuntimeError(f"Could not persist run version for {run_id}")
        if not self._db.upsert_calibration_run_events(
            run_id=run_id,
            drummer_slug=drummer_slug,
            event_stream=candidate.event_stream,
            source_type="production_performance_spec_v2",
            tempo_bpm=candidate.tempo_bpm,
            time_signature=candidate.time_signature,
            bars=candidate.bars,
        ):
            raise RuntimeError(f"Could not persist event stream for {run_id}")

        self._render.render_run(
            RenderRequest(
                run_id=run_id,
                render_profile_id=render_profile_id,
                sample_pack_version=sample_pack_version,
                kit_id=candidate.kit_id,
                seed=int(seed),
                render_recipe={
                    "schema": "calibration_render_recipe_v2",
                    # Never expose control/challenger in renderer-facing filenames or URLs.
                    "render_class": "neutral" if candidate.role == "neutral" else "candidate",
                    "base_groove_path": candidate.base_groove_path,
                    "performance_spec": candidate.performance_spec,
                    "tempo_bpm": candidate.tempo_bpm,
                    "time_signature": candidate.time_signature,
                    "event_stream_hash": candidate.metadata.get("event_stream_hash"),
                    "profile_snapshot_hash": candidate.metadata.get("profile_snapshot_hash"),
                },
            )
        )
        return run_id
