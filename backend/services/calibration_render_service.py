from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from pathlib import Path
import math
import wave
import struct
import logging

from admin.services.central_database_service import CentralDatabaseService


logger = logging.getLogger(__name__)


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

            # Synthesize a short preview WAV so the UI has something to play
            # if no external render pipeline is connected yet.
            try:
                preview_path = self._synthesize_preview_audio(
                    run_id=request.run_id,
                    tempo_bpm=float(request.render_recipe.get("tempo_bpm", 110.0) if isinstance(request.render_recipe, dict) else 110.0),
                )
                if preview_path is not None and preview_path.is_file():
                    storage_uri = str(
                        Path("/static/calibration_artifacts")
                        / "candidates"
                        / request.run_id
                        / preview_path.name
                    )
                    self._db.log_audio_artifact(
                        run_id=request.run_id,
                        artifact_type="audio",
                        storage_uri=storage_uri,
                        duration_sec=4.0,
                        loudness_lufs=None,
                        sample_pack_version=request.sample_pack_version,
                        render_recipe={
                            "generated": "synth_preview",
                            "kit_id": request.kit_id,
                            "seed": int(request.seed),
                        },
                    )
            except Exception:
                logger.exception("render_stub_artifact_log_failed run_id=%s", request.run_id)
        except Exception:
            logger.exception("render_run_failed run_id=%s", request.run_id)

    def _synthesize_preview_audio(self, *, run_id: str, tempo_bpm: float) -> Optional[Path]:
        try:
            root = Path(__file__).resolve().parents[1]
            out_dir = root / "artifacts" / "calibration" / "candidates" / run_id
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "preview.wav"

            sample_rate = 44100
            duration_sec = 4.0
            n_frames = int(sample_rate * duration_sec)

            # Simple metronome-like click with a low kick tone
            freq_kick = 60.0  # Hz
            click_every = max(1, int(sample_rate * (60.0 / max(1e-6, tempo_bpm))))

            with wave.open(str(out_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)

                for i in range(n_frames):
                    # Base tone (fade quickly to avoid DC)
                    t = i / float(sample_rate)
                    amp = 0.2 * math.exp(-t * 4.0)
                    sample = amp * math.sin(2.0 * math.pi * freq_kick * t)

                    # Add a short click every beat
                    if i % click_every < 200:  # ~4.5 ms click
                        sample += 0.4 * (1.0 - (i % click_every) / 200.0)

                    # Clip and convert to int16
                    sample = max(-1.0, min(1.0, sample))
                    wf.writeframesraw(struct.pack('<h', int(sample * 32767.0)))

            return out_path
        except Exception:
            return None
