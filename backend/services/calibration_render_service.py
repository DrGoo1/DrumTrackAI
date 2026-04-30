from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from admin.services.central_database_service import CentralDatabaseService


@dataclass
class RenderRequest:
    run_id: str
    render_profile_id: str
    sample_pack_version: str
    kit_id: str
    seed: int
    render_recipe: Dict[str, Any]


class CalibrationRenderService:
    """Minimal render service stub.

    In production, this would enqueue a render job and later attach produced
    artifacts. For the calibration API bootstrap, we simply mark the run
    metadata to indicate a render was queued successfully so downstream flows
    can proceed.
    """

    def __init__(self, db: CentralDatabaseService) -> None:
        self._db = db

    def render_run(self, request: RenderRequest) -> None:
        # No-op queue: annotate the run's metadata so clients can poll later.
        try:
            run_ref = self._db.get_calibration_run(run_id=request.run_id)
            meta: Dict[str, Any] = {}
            if run_ref and isinstance(run_ref.metadata, dict):
                meta = dict(run_ref.metadata)
            meta.setdefault("render", {})
            meta["render"].update(
                {
                    "status": "queued",
                    "render_profile_id": request.render_profile_id,
                    "sample_pack_version": request.sample_pack_version,
                    "kit_id": request.kit_id,
                    "seed": int(request.seed),
                }
            )
            self._db.log_calibration_run(
                drummer_slug=run_ref.drummer_slug if run_ref else "unknown",
                outcome="queued",
                metadata=meta,
                run_id=request.run_id,
            )
        except Exception:
            # Swallow errors to keep API responsive; callers handle failures upstream.
            pass
