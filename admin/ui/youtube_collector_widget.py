import json
import logging
import os
import re
import time
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPlainTextEdit,
    QPushButton,
    QLineEdit,
    QProgressBar,
    QMessageBox,
    QCheckBox,
)

from admin.services.youtube_service import YouTubeService
from admin.services.central_database_service import CentralDatabaseService
from admin.services.youtube_llm_learning_service import YouTubeLLMLearningPipeline

logger = logging.getLogger(__name__)


class YouTubeCollectorWidget(QWidget):
    pipeline_log = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._download_thread = None
        self._thread = None
        self._queue: List[str] = []
        self._queue_index: int = 0
        self._queue_cancelled: bool = False
        self._queue_context: Dict[str, Any] = {}
        self._profiles: List[Dict[str, Any]] = []
        self._auto_ingest_enabled: bool = True
        self._auto_assimilate_enabled: bool = True

        self._batch_connected: bool = False
        self._auto_ingest_pending: List[Dict[str, str]] = []
        self._auto_ingest_batch: Any = None

        self._db = CentralDatabaseService.get_instance()

        repo_root = Path(__file__).resolve().parents[2]
        self._database_root = repo_root / "database"
        self._download_root = self._database_root / "drummer_songs"

        self._profiles_path = self._database_root / "drummer_profiles.json"
        self._profiles_fallback_paths = [
            repo_root / "admin" / "data" / "drummers" / "profiles.json",
            repo_root / "admin" / "admin" / "data" / "drummers" / "profiles.json",
        ]

        self._download_root.mkdir(parents=True, exist_ok=True)

        self.youtube_service = YouTubeService()
        self._pipeline_thread: Optional[threading.Thread] = None

        self._build_ui()
        self._load_profiles()
        try:
            self.pipeline_log.connect(self._log)
        except Exception:
            pass

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Drummer:"))
        self.drummer_combo = QComboBox()
        self.drummer_combo.setMinimumWidth(320)
        top_row.addWidget(self.drummer_combo, 1)
        layout.addLayout(top_row)

        url_label_row = QHBoxLayout()
        url_label_row.addWidget(QLabel("YouTube URLs (one per line):"))
        layout.addLayout(url_label_row)

        self.urls_edit = QPlainTextEdit()
        self.urls_edit.setPlaceholderText("https://www.youtube.com/watch?v=...\nhttps://youtu.be/...")
        self.urls_edit.setMinimumHeight(120)
        layout.addWidget(self.urls_edit)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Filename label (optional):"))
        self.filename_label_edit = QLineEdit()
        self.filename_label_edit.setPlaceholderText("e.g. Rosanna")
        file_row.addWidget(self.filename_label_edit, 1)
        layout.addLayout(file_row)

        opts_row = QHBoxLayout()
        self.append_timestamp_checkbox = QCheckBox("Append timestamp")
        self.append_timestamp_checkbox.setChecked(True)
        opts_row.addWidget(self.append_timestamp_checkbox)

        self.auto_ingest_checkbox = QCheckBox("Auto-ingest (batch processor)")
        self.auto_ingest_checkbox.setChecked(True)
        opts_row.addWidget(self.auto_ingest_checkbox)

        self.auto_assimilate_checkbox = QCheckBox("Auto-assimilate (DB + phases)")
        self.auto_assimilate_checkbox.setChecked(True)
        opts_row.addWidget(self.auto_assimilate_checkbox)

        opts_row.addStretch(1)
        layout.addLayout(opts_row)

        btn_row = QHBoxLayout()
        self.download_btn = QPushButton("Download")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        btn_row.addWidget(self.download_btn)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        layout.addWidget(QLabel("Activity:"))
        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setMinimumHeight(120)
        layout.addWidget(self.activity)

        self.download_btn.clicked.connect(self._on_download_clicked)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)

    def _log(self, msg: str) -> None:
        try:
            stamp = time.strftime("%H:%M:%S")
            self.activity.appendPlainText(f"[{stamp}] {msg}")
        except Exception:
            pass

    def _sanitize_filename(self, value: str) -> str:
        v = str(value or "").strip()
        v = re.sub(r"\s+", " ", v)
        v = re.sub(r"[^a-zA-Z0-9 _\-\.]+", "", v)
        v = v.replace(" ", "_")
        v = v.strip("._-")
        return v[:120] if len(v) > 120 else v

    def _candidate_profiles_paths(self) -> List[Path]:
        out = [self._profiles_path]
        for p in self._profiles_fallback_paths:
            try:
                out.append(Path(p))
            except Exception:
                pass
        return out

    def _load_profiles(self) -> None:
        self._profiles = []

        chosen: Optional[Path] = None
        for p in self._candidate_profiles_paths():
            try:
                if p and p.exists():
                    chosen = p
                    break
            except Exception:
                continue

        if chosen is None:
            self.drummer_combo.clear()
            self.drummer_combo.addItem("(No drummer profiles found)")
            self._log("No drummer profiles file found.")
            return

        try:
            with open(chosen, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            profiles: List[Dict[str, Any]]
            if isinstance(data, dict) and isinstance(data.get("profiles"), list):
                profiles = data.get("profiles") or []
            elif isinstance(data, list):
                profiles = data
            else:
                profiles = []

            self._profiles = [p for p in profiles if isinstance(p, dict)]

            self.drummer_combo.clear()
            for prof in self._profiles:
                name = str(prof.get("name") or prof.get("display_name") or "Unknown")
                anon_id = str(prof.get("id") or prof.get("anonymized_drummer_id") or "").strip()
                label = f"{name} ({anon_id})" if anon_id else name
                self.drummer_combo.addItem(label, prof)

            self._log(f"Loaded {len(self._profiles)} drummer profiles")
        except Exception as e:
            self._profiles = []
            self.drummer_combo.clear()
            self.drummer_combo.addItem("(Failed to load drummer profiles)")
            self._log(f"Failed to load drummer profiles: {e}")

    def _selected_profile(self) -> Optional[Dict[str, Any]]:
        try:
            prof = self.drummer_combo.currentData(Qt.ItemDataRole.UserRole)
            return prof if isinstance(prof, dict) else None
        except Exception:
            return None

    def _derive_drummer_id(self, prof: Dict[str, Any]) -> str:
        for k in ("id", "anonymized_drummer_id", "drummer_id"):
            v = str(prof.get(k) or "").strip()
            if v:
                return v
        name = str(prof.get("name") or "drummer").strip().lower()
        v = abs(hash(name)) % 10000
        return f"drm_{v:04d}"

    def _extract_urls(self) -> List[str]:
        raw = str(self.urls_edit.toPlainText() or "")
        urls = []
        for line in raw.splitlines():
            u = line.strip()
            if not u:
                continue
            urls.append(u)
        return urls

    def _queue_is_running(self) -> bool:
        try:
            return bool(self._queue) and (self._thread is not None) and getattr(self._thread, "is_alive", lambda: False)()
        except Exception:
            return False

    def _reset_queue_ui(self) -> None:
        self._queue = []
        self._queue_index = 0
        self._queue_cancelled = False
        self._queue_context = {}
        self._thread = None
        self._download_thread = None
        try:
            self.download_btn.setEnabled(True)
            self.cancel_btn.setEnabled(False)
        except Exception:
            pass

    def _start_next_in_queue(self) -> None:
        if self._queue_cancelled:
            self._log("Queue cancelled")
            self._reset_queue_ui()
            return

        if self._queue_index >= len(self._queue):
            self._log("Queue completed")
            self._reset_queue_ui()
            try:
                self.progress.setValue(100)
            except Exception:
                pass

            try:
                if self._auto_ingest_enabled and self._auto_ingest_batch is not None:
                    if not getattr(self._auto_ingest_batch, "is_processing", False):
                        self._log("Starting batch processing...")
                        self._auto_ingest_batch.start_processing()
            except Exception as e:
                self._log(f"ERROR: failed to start batch processing: {e}")
            try:
                self._trigger_full_pipeline()
            except Exception as e:
                self._log(f"ERROR: pipeline trigger failed: {e}")
            return

        prof = self._queue_context.get("profile")
        if not isinstance(prof, dict):
            self._log("Queue error: missing drummer profile")
            self._reset_queue_ui()
            return

        drummer_id = str(self._queue_context.get("drummer_id") or "").strip()
        if not drummer_id:
            drummer_id = self._derive_drummer_id(prof)
            self._queue_context["drummer_id"] = drummer_id

        base_label = str(self._queue_context.get("base_label") or "").strip()
        append_ts = bool(self._queue_context.get("append_ts"))

        url = self._queue[self._queue_index]
        position = self._queue_index + 1
        total = len(self._queue)

        try:
            self.progress.setValue(0)
        except Exception:
            pass

        suffix = f"{position:02d}_of_{total:02d}" if total > 1 else ""
        base = base_label or self._sanitize_filename(str(prof.get("name") or "song"))
        if suffix:
            base = f"{base}_{suffix}"
        if append_ts:
            base = f"{base}_{time.strftime('%Y%m%d_%H%M%S')}"
        filename = f"{drummer_id}_{base}.mp3"
        output_path = str(self._download_root / filename)

        self._log(f"Queue item {position}/{total}")
        self._log(f"URL: {url}")
        self._log(f"Output: {output_path}")

        def on_progress(pct: int) -> None:
            try:
                if pct is None:
                    return
                if int(pct) < 0:
                    self.progress.setValue(0)
                else:
                    self.progress.setValue(max(0, min(100, int(pct))))
            except Exception:
                pass

        def on_complete(path: str) -> None:
            self._log(f"Completed: {path}")
            try:
                self._auto_ingest_enabled = bool(self.auto_ingest_checkbox.isChecked())
                self._auto_assimilate_enabled = bool(self.auto_assimilate_checkbox.isChecked())
            except Exception:
                self._auto_ingest_enabled = False
                self._auto_assimilate_enabled = False

            try:
                if self._auto_ingest_enabled:
                    self._auto_ingest_downloaded_audio(drummer_id=drummer_id, audio_path=str(path), song_label=str(base))
            except Exception as e:
                self._log(f"ERROR: auto-ingest failed: {e}")
            self._thread = None
            self._download_thread = None
            self._queue_index += 1
            self._start_next_in_queue()

        def on_error(err: str) -> None:
            self._log(f"ERROR: {err}")
            self._thread = None
            self._download_thread = None
            self._queue_index += 1
            self._start_next_in_queue()

        try:
            self._download_thread, self._thread = self.youtube_service.download_audio(
                youtube_id=url,
                output_path=output_path,
                progress_callback=on_progress,
                completion_callback=on_complete,
                error_callback=on_error,
                search_query=f"{prof.get('name', '')} {base_label}".strip(),
            )
        except Exception as e:
            self._log(f"ERROR: failed to start download: {e}")
            self._queue_index += 1
            self._start_next_in_queue()

    def _auto_ingest_downloaded_audio(self, *, drummer_id: str, audio_path: str, song_label: str) -> None:
        drummer_id = str(drummer_id or "").strip()
        audio_path = str(audio_path or "").strip()
        song_label = str(song_label or "").strip()
        if not drummer_id or not audio_path:
            return

        if not os.path.exists(audio_path):
            self._log(f"ERROR: downloaded audio missing: {audio_path}")
            return

        safe_song = self._sanitize_filename(song_label) or "song"
        output_dir = str(self._database_root / "processed_stems" / drummer_id / safe_song)
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception:
            pass

        try:
            from admin.ui.batch_processor_widget import get_batch_processor
            batch = get_batch_processor()
        except Exception:
            batch = None

        if batch is None:
            self._log("ERROR: batch processor unavailable; cannot auto-ingest")
            return

        try:
            self._connect_batch_processor(batch)
        except Exception:
            pass

        try:
            self._auto_ingest_batch = batch
        except Exception:
            pass

        metadata = {
            "source": "youtube_collector",
            "analysis_type": "drum_profiling",
            "drummer_id": drummer_id,
            "song_title": safe_song,
        }

        batch.add_to_queue(input_file=audio_path, output_dir=output_dir, metadata=metadata)
        try:
            self._auto_ingest_pending.append(
                {"drummer_id": str(drummer_id), "song_folder": str(output_dir), "song": str(safe_song)}
            )
        except Exception:
            pass
        self._log(f"Auto-ingest queued: drummer_id={drummer_id} song={safe_song}")

    def _connect_batch_processor(self, batch) -> None:
        if self._batch_connected:
            return
        self._batch_connected = True
        try:
            batch.processing_completed.connect(self._on_batch_processing_completed)
        except Exception:
            pass

    def _on_batch_processing_completed(self, batch_id, summary) -> None:
        pending = []
        try:
            pending = list(self._auto_ingest_pending)
            self._auto_ingest_pending = []
        except Exception:
            pending = []

        if not pending:
            return

        by_drummer: Dict[str, List[str]] = {}
        for item in pending:
            try:
                d = str((item or {}).get("drummer_id") or "").strip()
                folder = str((item or {}).get("song_folder") or "").strip()
                if d and folder:
                    by_drummer.setdefault(d, []).append(folder)
            except Exception:
                continue

        for drummer_id, folders in by_drummer.items():
            ingested = 0
            for folder in folders:
                try:
                    if not os.path.exists(os.path.join(folder, "drum_analysis.json")):
                        continue
                    analysis_id = self._db.ingest_processed_stems_song_folder(drummer_id=drummer_id, song_folder=folder)
                    if analysis_id:
                        ingested += 1
                        self._log(f"Ingested: drummer_id={drummer_id} analysis_id={analysis_id}")
                    else:
                        self._log(f"ERROR: ingest failed: {folder}")
                except Exception as e:
                    self._log(f"ERROR: ingest exception: {e}")

            if ingested > 0 and self._auto_assimilate_enabled:
                try:
                    self._log(f"Running phases 2-6 for drummer_id={drummer_id}")
                    self._db.run_phase2_hit_event_extraction_for_drummer(drummer_slug=drummer_id)
                    self._db.run_phase3_fills_and_techniques_for_drummer(drummer_slug=drummer_id)
                    self._db.run_phase4_microtiming_and_dynamics_for_drummer(drummer_slug=drummer_id)
                    self._db.run_phase5_profile_rollup_for_drummer(drummer_slug=drummer_id)
                    self._db.run_phase6_persona_preset_export_for_drummer(drummer_slug=drummer_id)
                    self._log(f"Phases 2-6 complete for drummer_id={drummer_id}")
                except Exception as e:
                    self._log(f"ERROR: phases 2-6 failed: {e}")

    def _on_download_clicked(self) -> None:
        prof = self._selected_profile()
        if not prof:
            QMessageBox.warning(self, "YouTube Collector", "Please select a drummer.")
            return

        urls = self._extract_urls()
        if not urls:
            QMessageBox.warning(self, "YouTube Collector", "Paste at least one YouTube URL.")
            return

        if self._thread is not None and getattr(self._thread, "is_alive", lambda: False)():
            QMessageBox.information(self, "YouTube Collector", "A download is already running.")
            return

        drummer_id = self._derive_drummer_id(prof)
        label = self._sanitize_filename(self.filename_label_edit.text())
        append_ts = bool(self.append_timestamp_checkbox.isChecked())

        self._queue = list(urls)
        self._queue_index = 0
        self._queue_cancelled = False
        self._queue_context = {
            "profile": prof,
            "drummer_id": drummer_id,
            "base_label": label,
            "append_ts": append_ts,
            "urls": list(urls),
        }

        self._log(f"Starting queue: {len(self._queue)} URL(s)")
        self._log(f"Downloading for drummer_id={drummer_id}")

        try:
            self.download_btn.setEnabled(False)
            self.cancel_btn.setEnabled(True)
        except Exception:
            pass

        self._start_next_in_queue()

    def _on_cancel_clicked(self) -> None:
        try:
            self._queue_cancelled = True
            try:
                remaining = max(0, len(self._queue) - self._queue_index)
                self._log(f"Cancel requested (remaining items: {remaining})")
            except Exception:
                self._log("Cancel requested")
            if self._download_thread is not None:
                self._download_thread.cancel()
        except Exception as e:
            self._log(f"Cancel failed: {e}")

    def _trigger_full_pipeline(self) -> None:
        try:
            self._auto_assimilate_enabled = bool(self.auto_assimilate_checkbox.isChecked())
        except Exception:
            self._auto_assimilate_enabled = False
        if not self._auto_assimilate_enabled:
            return
        if self._pipeline_thread is not None and getattr(self._pipeline_thread, "is_alive", lambda: False)():
            return
        ctx = dict(self._queue_context)
        prof = ctx.get("profile")
        urls = list(ctx.get("urls") or [])
        if not prof or not urls:
            return
        drummer_name = str(prof.get("name") or prof.get("display_name") or ctx.get("drummer_id") or "").strip()
        if not drummer_name:
            drummer_name = str(ctx.get("drummer_id") or "drummer").strip()
        raw_style = prof.get("style") or prof.get("default_style") or prof.get("styles")
        style = "rock"
        if isinstance(raw_style, str) and raw_style.strip():
            style = raw_style.strip().lower()
        elif isinstance(raw_style, list) and raw_style:
            style = str(raw_style[0]).strip().lower() or style

        def worker() -> None:
            try:
                self.pipeline_log.emit(f"Starting full pipeline for {drummer_name} ({style})")
                pipeline = YouTubeLLMLearningPipeline()
                result = pipeline.run_complete_pipeline(
                    drummer_name=drummer_name,
                    style=style,
                    max_videos=len(urls),
                    quality_threshold=0.0,
                    start_training=False,
                    ingest_to_drummerbrain=True,
                    drummerbrain_limit=0,
                    urls=urls,
                )
                if result.get("success"):
                    dataset = result.get("dataset_file") or ""
                    ingest = result.get("drummerbrain_ingest") or {}
                    dsid = ingest.get("dataset_id") or ""
                    ok = ingest.get("ok")
                    self.pipeline_log.emit("Full pipeline complete")
                    if dataset:
                        self.pipeline_log.emit(f"Dataset: {dataset}")
                    if dsid:
                        self.pipeline_log.emit(f"DrummerBrain ingest: {'OK' if ok else 'FAILED'} ({dsid})")
                else:
                    self.pipeline_log.emit(f"Pipeline failed: {result.get('error')}")
            except Exception as exc:
                self.pipeline_log.emit(f"Pipeline exception: {exc}")

        self._pipeline_thread = threading.Thread(target=worker, daemon=True)
        self._pipeline_thread.start()
