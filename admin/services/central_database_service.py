"""
Central Database Service
=======================
Provides centralized database access for DrumBeats and other database operations.
Handles SQLite connection, CRUD operations, and connection pooling.
"""
import hashlib
import json
import logging
import os
import random
import sqlite3
import statistics
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


_MISSING = object()


@dataclass
class CalibrationRun:
    run_id: str
    drummer_slug: str
    started_at: datetime
    completed_at: Optional[datetime]
    outcome: str
    note_count: Optional[int]
    fills_per_minute: Optional[float]
    within_tolerance_count: Optional[int]
    total_compared: Optional[int]
    delta_summary: Optional[str]
    metadata: Optional[Dict[str, Any]]
    metrics: Optional[Dict[str, Any]]
    comparison: Optional[Dict[str, Any]]
    log_path: Optional[str]


@dataclass
class CalibrationFeedback:
    feedback_id: str
    drummer_slug: str
    rating: int
    comment: Optional[str]
    author: Optional[str]
    submitted_at: datetime


class CentralDatabaseService(QObject):
    """
    Central database service for DrumTracKAI.
    Provides thread-safe database access and CRUD operations.
    """
    # Define signals for database operations
    database_connected = Signal(str)  # db_path
    database_error = Signal(str)  # error_message
    data_changed = Signal(str, str)  # table_name, operation (insert, update, delete)

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        super().__init__()
        self._db_path = None
        self._connection = None
        self._connections = {}  # Thread-local connections
        self._initialized = False
        self._tables_created = False
        self._schema_cache: Dict[str, set] = {}
        self._write_lock = threading.RLock()
        self._last_ingest_error: str = ""
        logger.info("CentralDatabaseService initialized")

    def _set_last_ingest_error(self, msg: str) -> None:
        try:
            self._last_ingest_error = str(msg or "")
        except Exception:
            self._last_ingest_error = ""

    def get_last_ingest_error(self) -> str:
        try:
            return str(self._last_ingest_error or "")
        except Exception:
            return ""

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            text = str(value).strip()
            if not text:
                return None
            if text.endswith("Z"):
                text = text[:-1]
            return datetime.fromisoformat(text)
        except Exception:
            return None

    @staticmethod
    def _json_loads(value: Any, *, default: Any = None) -> Any:
        if value is None or value is _MISSING:
            return default
        if isinstance(value, (dict, list)):
            return value
        try:
            text = str(value)
        except Exception:
            text = ""
        if not text:
            return default
        try:
            return json.loads(text)
        except Exception:
            return default

    @staticmethod
    def _json_dumps(value: Any) -> Optional[str]:
        if value is None:
            return None
        try:
            return json.dumps(value, default=str)
        except Exception:
            return None

    def _ensure_phase32_42_columns(self) -> None:
        """Additive migration: add Phase 32-42 derived-feature columns if missing."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cols = self._table_columns("song_performance_analysis")
            if not cols:
                return

            if "phase32_42_features_json" not in cols:
                cursor.execute("ALTER TABLE song_performance_analysis ADD COLUMN phase32_42_features_json TEXT")
            if "phase32_42_features_version" not in cols:
                cursor.execute("ALTER TABLE song_performance_analysis ADD COLUMN phase32_42_features_version TEXT")

            conn.commit()
        except Exception as e:
            logger.warning(f"Phase32-42 schema migration skipped/failed: {e}")
            try:
                conn = self._get_connection()
                conn.rollback()
            except Exception:
                pass

    def _is_locked_error(self, e: BaseException) -> bool:
        try:
            s = str(e).lower()
            return "database is locked" in s or "database schema is locked" in s or "locked" in s
        except Exception:
            return False

    def _with_write_lock_retry(self, fn, *, attempts: int = 6, base_sleep_s: float = 0.15):
        last_err = None
        with self._write_lock:
            for i in range(int(attempts)):
                try:
                    return fn()
                except sqlite3.OperationalError as e:
                    last_err = e
                    if not self._is_locked_error(e):
                        raise
                    # backoff with jitter
                    sleep_s = float(base_sleep_s) * (1.8 ** i) + (random.random() * 0.05)
                    time.sleep(min(sleep_s, 2.0))
        if last_err is not None:
            raise last_err
        return None

    def _ensure_drummer_exists(self, *, cursor: sqlite3.Cursor, drummer_id: str):
        """Ensure a drummer row exists and return the FK value to store in song_performance_analysis.

        Important: in the shipped admin DB, `drummers.id` is INTEGER primary key and
        `song_performance_analysis.drummer_id` has an FK to `drummers.id`. That means we
        must store the INTEGER PK (as a value) in song_performance_analysis.drummer_id.
        """
        drummer_id = (drummer_id or "").strip()
        if not drummer_id:
            raise ValueError("Missing drummer_id")

        cols = self._table_columns("drummers")
        display_name = drummer_id.replace("_", " ").strip() or drummer_id
        now = datetime.utcnow().isoformat()

        # Canonical admin schema: INTEGER id PK + TEXT drummer_id/display_name
        if "id" in cols and "drummer_id" in cols:
            cursor.execute("SELECT id FROM drummers WHERE drummer_id = ? LIMIT 1", (drummer_id,))
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])

            insert_fields = ["drummer_id"]
            insert_values = [drummer_id]
            if "display_name" in cols:
                insert_fields.append("display_name")
                insert_values.append(display_name)
            if "created_at" in cols:
                insert_fields.append("created_at")
                insert_values.append(now)
            if "updated_at" in cols:
                insert_fields.append("updated_at")
                insert_values.append(now)

            cursor.execute(
                f"INSERT INTO drummers ({', '.join(insert_fields)}) VALUES ({', '.join(['?'] * len(insert_values))})",
                tuple(insert_values),
            )
            cursor.execute("SELECT id FROM drummers WHERE drummer_id = ? LIMIT 1", (drummer_id,))
            row = cursor.fetchone()
            if row and row[0] is not None:
                return int(row[0])
            raise RuntimeError("Failed to create drummer row")

        # Legacy schema used by some older tools: TEXT PK id + name
        if "name" in cols:
            cursor.execute(
                """
                INSERT INTO drummers (id, name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING
                """,
                (drummer_id, display_name, None, now, now),
            )
            return drummer_id

        if "display_name" in cols and "drummer_id" in cols:
            cursor.execute(
                """
                INSERT INTO drummers (drummer_id, display_name)
                VALUES (?, ?)
                ON CONFLICT(drummer_id) DO NOTHING
                """,
                (drummer_id, display_name),
            )
            return drummer_id

        raise RuntimeError("Unsupported drummers table schema")

    def _get_drummer_fk_by_slug(self, *, cursor: sqlite3.Cursor, drummer_slug: str) -> Optional[int]:
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return None
            cols = self._table_columns("drummers")
            if "id" in cols and "drummer_id" in cols:
                cursor.execute("SELECT id FROM drummers WHERE drummer_id = ? LIMIT 1", (drummer_slug,))
                row = cursor.fetchone()
                if row and row[0] is not None:
                    return int(row[0])
                return None
            return None
        except Exception:
            return None

    def extract_hit_events_for_analysis(
        self,
        *,
        analysis_id: str,
        max_events_per_stem: int = 5000,
    ) -> int:
        """Phase 2: create drum_hit_events rows by running onset detection on each stem wav.

        Returns number of events inserted.
        """
        try:
            self._set_last_ingest_error("")
            analysis_id = (analysis_id or "").strip()
            if not analysis_id:
                return 0

            try:
                import numpy as np  # type: ignore
                import librosa  # type: ignore
            except Exception as e:
                msg = f"Phase 2 requires librosa/numpy: {e}"
                logger.error(msg)
                self._set_last_ingest_error(msg)
                self.database_error.emit(msg)
                return 0

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT analysis_id, drummer_id, mvsep_output_dir, tempo_bpm, time_signature
                FROM song_performance_analysis
                WHERE analysis_id = ?
                LIMIT 1
                """,
                (analysis_id,),
            )
            spa = cursor.fetchone()
            if not spa:
                return 0

            drummer_fk = spa[1]
            mvsep_output_dir = spa[2] or ""
            tempo_bpm = spa[3]
            time_signature = spa[4] or ""

            try:
                tempo_bpm = float(tempo_bpm) if isinstance(tempo_bpm, (int, float)) else None
            except Exception:
                tempo_bpm = None

            beats_per_bar = 4
            try:
                if isinstance(time_signature, str) and "/" in time_signature:
                    beats_per_bar = int(str(time_signature).split("/")[0].strip() or "4")
            except Exception:
                beats_per_bar = 4

            if not tempo_bpm or tempo_bpm <= 0:
                # Reasonable fallback: prevents division by zero and keeps grid fields usable.
                tempo_bpm = 120.0

            sec_per_beat = 60.0 / float(tempo_bpm)

            def _map_stem_to_instrument(stem: str) -> str:
                s = str(stem or "").lower()
                if any(k in s for k in ["kick", "bd", "bassdrum", "bass_drum", "kik"]):
                    return "kick"
                if any(k in s for k in ["snare", "sd", "snr"]):
                    return "snare"
                if any(k in s for k in ["hihat", "hi_hat", "hat", "hh"]):
                    return "hihat"
                if "ride" in s:
                    return "ride"
                if "crash" in s:
                    return "crash"
                if "tom" in s:
                    return "tom"
                if any(k in s for k in ["cym", "cymbal", "oh", "overhead"]):
                    return "cymbal"
                if any(k in s for k in ["perc", "shaker", "tamb", "clap", "fx"]):
                    return "perc"
                return str(stem or "stem")

            def _subdivision_from_fraction(frac: float) -> str:
                # Nearest 16th note grid
                targets = [0.0, 0.25, 0.5, 0.75]
                labels = ["1", "e", "&", "a"]
                best_i = 0
                best_d = 999.0
                for i, t in enumerate(targets):
                    d = abs(float(frac) - float(t))
                    if d < best_d:
                        best_d = d
                        best_i = i
                return labels[best_i]

            cursor.execute(
                "SELECT stem_name, file_path FROM stem_artifacts WHERE analysis_id = ?",
                (analysis_id,),
            )
            stems = cursor.fetchall() or []
            if not stems and mvsep_output_dir and os.path.isdir(str(mvsep_output_dir)):
                try:
                    candidates = [p for p in os.listdir(str(mvsep_output_dir)) if p.lower().endswith(".wav")]
                    stems = [(os.path.splitext(p)[0], os.path.join(str(mvsep_output_dir), p)) for p in candidates]
                except Exception:
                    stems = []

            now = datetime.utcnow().isoformat()

            def _do_write() -> int:
                # De-dupe: remove any previous extracted events for this analysis
                cursor.execute("DELETE FROM drum_hit_events WHERE analysis_id = ?", (analysis_id,))

                inserted = 0
                for stem_name, wav_path in stems:
                    wav_path = str(wav_path or "")
                    if not wav_path or not os.path.exists(wav_path):
                        continue

                    try:
                        y, sr = librosa.load(wav_path, sr=22050, mono=True)
                        if y is None or len(y) < 2048:
                            continue
                        hop_length = 512
                        o_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
                        onset_frames = librosa.onset.onset_detect(
                            onset_envelope=o_env,
                            sr=sr,
                            hop_length=hop_length,
                            backtrack=False,
                            units="frames",
                        )
                        if onset_frames is None:
                            continue
                        onset_frames = np.asarray(onset_frames, dtype=int)
                        if onset_frames.size == 0:
                            continue
                        if int(max_events_per_stem) > 0 and onset_frames.size > int(max_events_per_stem):
                            onset_frames = onset_frames[: int(max_events_per_stem)]

                        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=hop_length)
                        onset_times = np.asarray(onset_times, dtype=float)

                        # strength + normalized velocity (per stem)
                        o_env = np.asarray(o_env, dtype=float) if o_env is not None else np.asarray([], dtype=float)
                        max_env = float(np.max(o_env)) if o_env.size else 0.0
                        instrument = _map_stem_to_instrument(stem_name)

                        for idx, t in enumerate(onset_times):
                            frame = int(onset_frames[idx]) if idx < onset_frames.size else None
                            strength = None
                            vel = None
                            try:
                                if frame is not None and o_env.size and 0 <= frame < int(o_env.size):
                                    strength = float(o_env[frame])
                                    if max_env > 0:
                                        vel = float(strength / max_env)
                            except Exception:
                                strength = None
                                vel = None

                            beat_pos = float(t) / float(sec_per_beat) if sec_per_beat > 0 else 0.0
                            beat_index = int(beat_pos) if beat_pos >= 0 else 0
                            bar_index = int(beat_index // int(beats_per_bar)) if int(beats_per_bar) > 0 else 0
                            frac = beat_pos - float(beat_index)
                            subdiv = _subdivision_from_fraction(frac)

                            # timing offset vs nearest 16th grid
                            grid_16 = round(beat_pos * 4.0) / 4.0
                            grid_t = float(grid_16) * float(sec_per_beat)
                            timing_offset_ms = (float(t) - float(grid_t)) * 1000.0

                            cursor.execute(
                                """
                                INSERT INTO drum_hit_events (
                                    event_id, analysis_id, drummer_id, song_id,
                                    instrument, component,
                                    onset_time_sec, onset_strength, velocity_est,
                                    beat_index, bar_index, subdivision, timing_offset_ms,
                                    is_ghost, is_accent, is_flams_like, is_roll_like,
                                    created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    str(uuid.uuid4()),
                                    analysis_id,
                                    drummer_fk,
                                    None,
                                    instrument,
                                    None,
                                    float(t),
                                    strength,
                                    vel,
                                    int(beat_index),
                                    int(bar_index),
                                    str(subdiv),
                                    float(timing_offset_ms),
                                    None,
                                    None,
                                    None,
                                    None,
                                    now,
                                ),
                            )
                            inserted += 1
                    except Exception:
                        continue

                conn.commit()
                return inserted

            inserted = int(self._with_write_lock_retry(_do_write) or 0)
            if inserted > 0:
                self.data_changed.emit("drum_hit_events", "insert")
            return inserted
        except Exception as e:
            msg = f"Phase 2 hit event extraction failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return 0

    def run_phase2_hit_event_extraction_for_drummer(
        self,
        *,
        drummer_slug: str,
        max_events_per_stem: int = 5000,
    ) -> Dict[str, Any]:
        """Run Phase 2 for all ingested analyses of a drummer identified by folder slug (e.g., stewart_copeland)."""
        out = {"drummer_slug": drummer_slug, "analyses": 0, "events": 0}
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return out

            conn = self._get_connection()
            cursor = conn.cursor()
            drummer_fk = self._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=drummer_slug)
            if drummer_fk is None:
                # Ensure row exists then look up again
                self._ensure_drummer_exists(cursor=cursor, drummer_id=drummer_slug)
                conn.commit()
                drummer_fk = self._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=drummer_slug)
            if drummer_fk is None:
                return out

            cursor.execute(
                "SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ? ORDER BY created_at DESC",
                (drummer_fk,),
            )
            rows = cursor.fetchall() or []
            out["analyses"] = len(rows)
            total_events = 0
            for r in rows:
                aid = r[0]
                total_events += int(
                    self.extract_hit_events_for_analysis(analysis_id=aid, max_events_per_stem=max_events_per_stem) or 0
                )
            out["events"] = total_events
            return out
        except Exception as e:
            msg = f"Phase 2 run failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def compute_phase32_42_features_for_analysis(self, *, analysis_id: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {"analysis_id": analysis_id, "updated": False}
        try:
            analysis_id = (analysis_id or "").strip()
            if not analysis_id:
                return out

            conn = self._get_connection()
            cur = conn.cursor()

            cur.execute(
                "SELECT drummer_id FROM song_performance_analysis WHERE analysis_id = ? LIMIT 1",
                (analysis_id,),
            )
            row = cur.fetchone()
            drummer_fk = row[0] if row else None

            rollup: Dict[str, Any] = {}
            try:
                if drummer_fk is not None:
                    rollup = self.compute_drummer_profile_rollup(drummer_fk=int(drummer_fk))
            except Exception:
                rollup = {}

            cur.execute(
                """
                SELECT onset_time_sec, instrument, timing_offset_ms, velocity_est, onset_strength,
                       is_ghost, is_accent, component
                FROM drum_hit_events
                WHERE analysis_id = ?
                ORDER BY onset_time_sec ASC
                """,
                (analysis_id,),
            )
            event_rows = cur.fetchall() or []

            from admin.services.phase32_42_feature_extractor import build_phase32_42_features_json

            payload_json = build_phase32_42_features_json(event_rows=event_rows, rollup=rollup)
            version = "phase32_42_offline_v1"
            now = datetime.utcnow().isoformat()

            def _do_write() -> None:
                cur.execute(
                    """
                    UPDATE song_performance_analysis
                    SET phase32_42_features_json = ?,
                        phase32_42_features_version = ?,
                        updated_at = ?
                    WHERE analysis_id = ?
                    """,
                    (payload_json, version, now, analysis_id),
                )
                conn.commit()

            self._with_write_lock_retry(_do_write)
            out["updated"] = True
            out["phase32_42_features_version"] = version
            self.data_changed.emit("song_performance_analysis", "update")
            return out
        except Exception as e:
            msg = f"Phase32-42 feature recompute failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def run_phase32_42_features_for_drummer(self, *, drummer_slug: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {"drummer_slug": drummer_slug, "analyses": 0, "updated": 0}
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return out

            conn = self._get_connection()
            cur = conn.cursor()
            drummer_fk = self._get_drummer_fk_by_slug(cursor=cur, drummer_slug=drummer_slug)
            if drummer_fk is None:
                self._ensure_drummer_exists(cursor=cur, drummer_id=drummer_slug)
                conn.commit()
                drummer_fk = self._get_drummer_fk_by_slug(cursor=cur, drummer_slug=drummer_slug)
            if drummer_fk is None:
                return out

            cur.execute(
                "SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ? ORDER BY created_at DESC",
                (drummer_fk,),
            )
            rows = cur.fetchall() or []
            out["analyses"] = len(rows)

            updated = 0
            for (aid,) in rows:
                res = self.compute_phase32_42_features_for_analysis(analysis_id=str(aid))
                if res.get("updated"):
                    updated += 1

            out["updated"] = int(updated)
            return out
        except Exception as e:
            msg = f"Phase32-42 run failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def _get_drummer_slug_by_fk(self, *, cursor: sqlite3.Cursor, drummer_fk: int) -> str:
        try:
            cols = self._table_columns("drummers")
            if "id" in cols and "drummer_id" in cols:
                cursor.execute("SELECT drummer_id FROM drummers WHERE id = ? LIMIT 1", (int(drummer_fk),))
                row = cursor.fetchone()
                if row and row[0]:
                    return str(row[0]).strip()
        except Exception:
            pass
        return str(drummer_fk)

    def infer_persona_from_rollup(self, *, rollup: Dict[str, Any]) -> Dict[str, Any]:
        try:
            pocket = rollup.get("pocket_tightness")
            human = rollup.get("humanness")
            fills_per_min = rollup.get("fills_per_min")
            inst_shares = rollup.get("instrument_shares") or {}

            tags: List[str] = []
            if pocket is not None:
                try:
                    p = float(pocket)
                    if p >= 0.70:
                        tags.append("tight")
                    elif p <= 0.35:
                        tags.append("loose")
                    else:
                        tags.append("balanced")
                except Exception:
                    pass

            if human is not None:
                try:
                    h = float(human)
                    if h >= 0.65:
                        tags.append("human")
                    elif h <= 0.35:
                        tags.append("machine")
                except Exception:
                    pass

            if fills_per_min is not None:
                try:
                    fpm = float(fills_per_min)
                    if fpm >= 1.25:
                        tags.append("fill_heavy")
                    elif fpm <= 0.35:
                        tags.append("fill_light")
                except Exception:
                    pass

            try:
                ride_share = float(inst_shares.get("ride") or 0.0) if isinstance(inst_shares, dict) else 0.0
                if ride_share >= 0.18:
                    tags.append("ride_led")
            except Exception:
                pass
            try:
                hat_share = float(inst_shares.get("hihat") or 0.0) if isinstance(inst_shares, dict) else 0.0
                if hat_share >= 0.22:
                    tags.append("hat_led")
            except Exception:
                pass

            if not tags:
                tags = ["balanced"]

            label = "_".join(tags[:4])
            confidence = 0.55 + (0.1 * min(3, max(0, len(tags) - 1)))
            confidence = max(0.0, min(0.95, float(confidence)))

            return {"label": label, "confidence": confidence, "tags": tags}
        except Exception:
            return {"label": "balanced", "confidence": 0.5, "tags": ["balanced"]}

    def generate_preset_from_rollup(self, *, drummer_slug: str, rollup: Dict[str, Any], persona: Dict[str, Any]) -> Dict[str, Any]:
        deltas: Dict[str, Any] = {}
        policies: Dict[str, Any] = {"source": "phase6", "persona": persona}

        pocket = rollup.get("pocket_tightness")
        human = rollup.get("humanness")
        fills_per_min = rollup.get("fills_per_min")

        humanize = 0.5
        try:
            if pocket is not None:
                humanize = 0.2 + (1.0 - max(0.0, min(1.0, float(pocket)))) * 0.8
        except Exception:
            humanize = 0.5
        humanize = max(0.0, min(1.0, float(humanize)))

        ghost = 0.35
        try:
            if human is not None:
                ghost = 0.15 + max(0.0, min(1.0, float(human))) * 0.55
        except Exception:
            ghost = 0.35
        ghost = max(0.0, min(1.0, float(ghost)))

        fill_density = 0.35
        try:
            if fills_per_min is not None:
                fill_density = max(0.0, min(1.0, float(fills_per_min) / 2.0))
        except Exception:
            fill_density = 0.35

        swing = 0.15

        deltas["humanizeAmount"] = float(humanize)
        deltas["ghostNoteAmount"] = float(ghost)
        deltas["swingAmount"] = float(swing)
        deltas["fillDensity"] = float(fill_density)

        preset_id = f"phase6_{drummer_slug}".lower()
        name = f"{drummer_slug} (Phase 6)"

        return {
            "preset_id": preset_id,
            "profile_type": "drummer",
            "name": name,
            "tier": "generated",
            "deltas": deltas,
            "policies": policies,
            "source_type": "phase6_rollup",
            "source_song_name": None,
            "source_ref": drummer_slug,
        }

    def export_drummer_profile_json(
        self,
        *,
        drummer_slug: str,
        rollup: Dict[str, Any],
        persona: Dict[str, Any],
        preset: Dict[str, Any],
    ) -> str:
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return ""

            project_root = Path(__file__).resolve().parents[2]
            out_dir = project_root / "database" / "drummer_profiles_generated" / drummer_slug
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / "drummer_profile.json"

            payload = {
                "drummer_id": drummer_slug,
                "generated_at": datetime.utcnow().isoformat(),
                "persona": persona,
                "preset": {
                    "preset_id": preset.get("preset_id"),
                    "profile_type": preset.get("profile_type"),
                    "tier": preset.get("tier"),
                    "deltas": preset.get("deltas") or {},
                    "policies": preset.get("policies") or {},
                },
                "rollup": rollup,
            }
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            return str(out_path)
        except Exception:
            return ""

    def run_phase6_persona_preset_export_for_drummer(self, *, drummer_slug: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "drummer_slug": drummer_slug,
            "saved_rollup": False,
            "persona": {},
            "preset_saved": False,
            "preset_id": None,
            "export_path": "",
        }
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return out

            conn = self._get_connection()
            cur = conn.cursor()
            drummer_fk = self._get_drummer_fk_by_slug(cursor=cur, drummer_slug=drummer_slug)
            if drummer_fk is None:
                self._ensure_drummer_exists(cursor=cur, drummer_id=drummer_slug)
                conn.commit()
                drummer_fk = self._get_drummer_fk_by_slug(cursor=cur, drummer_slug=drummer_slug)
            if drummer_fk is None:
                return out

            rollup = self.compute_drummer_profile_rollup(drummer_fk=int(drummer_fk))
            persona = self.infer_persona_from_rollup(rollup=rollup)
            preset = self.generate_preset_from_rollup(drummer_slug=drummer_slug, rollup=rollup, persona=persona)

            preset_saved = self.upsert_drummer_preset(
                preset_id=str(preset.get("preset_id") or ""),
                profile_type=str(preset.get("profile_type") or "drummer"),
                name=str(preset.get("name") or ""),
                tier=str(preset.get("tier") or "generated"),
                deltas=preset.get("deltas") if isinstance(preset.get("deltas"), dict) else {},
                policies=preset.get("policies") if isinstance(preset.get("policies"), dict) else {},
                source_type=str(preset.get("source_type") or "phase6_rollup"),
                source_song_name=None,
                source_ref=str(preset.get("source_ref") or drummer_slug),
            )

            export_path = self.export_drummer_profile_json(
                drummer_slug=drummer_slug,
                rollup=rollup,
                persona=persona,
                preset=preset,
            )

            rollup = dict(rollup or {})
            rollup["persona"] = persona
            rollup["preset_id"] = preset.get("preset_id")
            rollup["export_path"] = export_path
            rollup_saved = self.upsert_drummer_profile_rollup(drummer_fk=int(drummer_fk), rollup=rollup, rollup_version="phase6_v1")

            out["saved_rollup"] = bool(rollup_saved)
            out["persona"] = persona
            out["preset_saved"] = bool(preset_saved)
            out["preset_id"] = preset.get("preset_id")
            out["export_path"] = export_path
            return out
        except Exception as e:
            msg = f"Phase 6 run failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def compute_drummer_profile_rollup(self, *, drummer_fk: int) -> Dict[str, Any]:
        rollup: Dict[str, Any] = {
            "drummer_id": int(drummer_fk),
            "songs": 0,
            "hits": 0,
            "instrument_counts": {},
            "instrument_shares": {},
            "fills": 0,
            "fills_per_min": None,
            "techniques": 0,
            "technique_breakdown": {},
            "timing_std_ms": None,
            "pocket_tightness": None,
            "humanness": None,
            "velocity_mean": None,
            "velocity_std": None,
        }
        conn = self._get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT COUNT(DISTINCT analysis_id) FROM song_performance_analysis WHERE drummer_id = ?",
            (drummer_fk,),
        )
        rollup["songs"] = int((cur.fetchone() or [0])[0] or 0)

        cur.execute(
            """
            SELECT COUNT(1)
            FROM drum_hit_events
            WHERE analysis_id IN (
                SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ?
            )
            """,
            (drummer_fk,),
        )
        rollup["hits"] = int((cur.fetchone() or [0])[0] or 0)

        cur.execute(
            """
            SELECT instrument, COUNT(1)
            FROM drum_hit_events
            WHERE analysis_id IN (
                SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ?
            )
            GROUP BY instrument
            ORDER BY COUNT(1) DESC
            """,
            (drummer_fk,),
        )
        inst_counts: Dict[str, int] = {}
        for inst, n in cur.fetchall() or []:
            inst_counts[str(inst or "")] = int(n or 0)
        rollup["instrument_counts"] = inst_counts
        total_inst = float(sum(inst_counts.values()) or 0)
        if total_inst > 0:
            rollup["instrument_shares"] = {k: float(v) / total_inst for k, v in inst_counts.items()}

        cur.execute(
            """
            SELECT COUNT(1)
            FROM fill_events
            WHERE analysis_id IN (
                SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ?
            )
            """,
            (drummer_fk,),
        )
        rollup["fills"] = int((cur.fetchone() or [0])[0] or 0)

        cur.execute(
            """
            SELECT COUNT(1)
            FROM technique_events
            WHERE analysis_id IN (
                SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ?
            )
            """,
            (drummer_fk,),
        )
        rollup["techniques"] = int((cur.fetchone() or [0])[0] or 0)

        cur.execute(
            """
            SELECT technique_name, COUNT(1)
            FROM technique_events
            WHERE analysis_id IN (
                SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ?
            )
            GROUP BY technique_name
            ORDER BY COUNT(1) DESC
            """,
            (drummer_fk,),
        )
        tb: Dict[str, int] = {}
        for name, n in cur.fetchall() or []:
            tb[str(name or "")] = int(n or 0)
        rollup["technique_breakdown"] = tb

        cur.execute(
            """
            SELECT
                AVG(groove_micro_timing_variance),
                AVG(groove_pocket_tightness),
                AVG(humanness_score)
            FROM song_performance_analysis
            WHERE drummer_id = ?
            """,
            (drummer_fk,),
        )
        row = cur.fetchone() or (None, None, None)
        try:
            rollup["timing_std_ms"] = None if row[0] is None else float(row[0])
        except Exception:
            rollup["timing_std_ms"] = None
        try:
            rollup["pocket_tightness"] = None if row[1] is None else float(row[1])
        except Exception:
            rollup["pocket_tightness"] = None
        try:
            rollup["humanness"] = None if row[2] is None else float(row[2])
        except Exception:
            rollup["humanness"] = None

        cur.execute(
            "SELECT dynamics_json FROM song_performance_analysis WHERE drummer_id = ?",
            (drummer_fk,),
        )
        vel_means: List[float] = []
        vel_stds: List[float] = []
        for (dj,) in cur.fetchall() or []:
            try:
                d = json.loads(dj) if isinstance(dj, str) and dj.strip() else None
                if isinstance(d, dict):
                    if d.get("velocity_mean") is not None:
                        vel_means.append(float(d.get("velocity_mean")))
                    if d.get("velocity_std") is not None:
                        vel_stds.append(float(d.get("velocity_std")))
            except Exception:
                continue
        if vel_means:
            rollup["velocity_mean"] = float(sum(vel_means) / float(len(vel_means)))
        if vel_stds:
            rollup["velocity_std"] = float(sum(vel_stds) / float(len(vel_stds)))

        cur.execute(
            "SELECT duration_sec FROM song_performance_analysis WHERE drummer_id = ?",
            (drummer_fk,),
        )
        total_min = 0.0
        for (dur,) in cur.fetchall() or []:
            try:
                if dur is not None and float(dur) > 0:
                    total_min += float(dur) / 60.0
            except Exception:
                continue
        if total_min > 0:
            rollup["fills_per_min"] = float(rollup["fills"]) / total_min

        return rollup

    def upsert_drummer_profile_rollup(
        self,
        *,
        drummer_fk: int,
        rollup: Dict[str, Any],
        rollup_version: str = "phase5_v1",
    ) -> bool:
        try:
            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            cur = conn.cursor()

            def _do_write() -> None:
                cur.execute(
                    """
                    INSERT INTO drummer_profile_rollups (
                        rollup_id, drummer_id, rollup_version, rollup_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(drummer_id) DO UPDATE SET
                        rollup_version=excluded.rollup_version,
                        rollup_json=excluded.rollup_json,
                        updated_at=excluded.updated_at
                    """,
                    (
                        str(uuid.uuid4()),
                        int(drummer_fk),
                        (rollup_version or "").strip() or None,
                        json.dumps(rollup or {}, default=str),
                        now,
                        now,
                    ),
                )
                conn.commit()

            self._with_write_lock_retry(_do_write)
            self.data_changed.emit("drummer_profile_rollups", "upsert")
            return True
        except Exception as e:
            msg = f"Phase 5 rollup upsert failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return False

    def run_phase5_profile_rollup_for_drummer(self, *, drummer_slug: str) -> Dict[str, Any]:
        out: Dict[str, Any] = {"drummer_slug": drummer_slug, "saved": False, "rollup": {}}
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return out

            conn = self._get_connection()
            cur = conn.cursor()
            drummer_fk = self._get_drummer_fk_by_slug(cursor=cur, drummer_slug=drummer_slug)
            if drummer_fk is None:
                self._ensure_drummer_exists(cursor=cur, drummer_id=drummer_slug)
                conn.commit()
                drummer_fk = self._get_drummer_fk_by_slug(cursor=cur, drummer_slug=drummer_slug)
            if drummer_fk is None:
                return out

            rollup = self.compute_drummer_profile_rollup(drummer_fk=int(drummer_fk))
            saved = self.upsert_drummer_profile_rollup(drummer_fk=int(drummer_fk), rollup=rollup)
            out["saved"] = bool(saved)
            out["rollup"] = rollup
            return out
        except Exception as e:
            msg = f"Phase 5 run failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def extract_fills_and_techniques_for_analysis(
        self,
        *,
        analysis_id: str,
        fill_window_sec: float = 0.75,
        fill_min_hits: int = 12,
        flam_max_gap_ms: float = 70.0,
        roll_max_gap_ms: float = 110.0,
        roll_min_hits: int = 5,
    ) -> Dict[str, Any]:
        """Phase 3 (baseline): derive fill_events and technique_events from hit-event sequences."""
        out = {"analysis_id": analysis_id, "fills": 0, "techniques": 0}
        try:
            self._set_last_ingest_error("")
            analysis_id = (analysis_id or "").strip()
            if not analysis_id:
                return out

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT analysis_id, drummer_id, tempo_bpm, time_signature FROM song_performance_analysis WHERE analysis_id = ? LIMIT 1",
                (analysis_id,),
            )
            spa = cursor.fetchone()
            if not spa:
                return out

            drummer_fk = spa[1]
            tempo_bpm = spa[2]
            time_signature = spa[3] or ""
            try:
                tempo_bpm = float(tempo_bpm) if isinstance(tempo_bpm, (int, float)) else None
            except Exception:
                tempo_bpm = None
            if not tempo_bpm or tempo_bpm <= 0:
                tempo_bpm = 120.0
            sec_per_beat = 60.0 / float(tempo_bpm)

            beats_per_bar = 4
            try:
                if isinstance(time_signature, str) and "/" in time_signature:
                    beats_per_bar = int(str(time_signature).split("/")[0].strip() or "4")
            except Exception:
                beats_per_bar = 4

            cursor.execute(
                """
                SELECT instrument, onset_time_sec, velocity_est
                FROM drum_hit_events
                WHERE analysis_id = ?
                ORDER BY onset_time_sec ASC
                """,
                (analysis_id,),
            )
            rows = cursor.fetchall() or []
            if not rows:
                return out

            hits = []
            for r in rows:
                inst = str(r[0] or "")
                try:
                    t = float(r[1])
                except Exception:
                    continue
                vel = r[2]
                try:
                    vel = float(vel) if isinstance(vel, (int, float)) else None
                except Exception:
                    vel = None
                hits.append((inst, t, vel))

            song_len_sec = 0.0
            try:
                song_len_sec = float(hits[-1][1]) - float(hits[0][1])
                if song_len_sec < 0:
                    song_len_sec = 0.0
            except Exception:
                song_len_sec = 0.0

            now = datetime.utcnow().isoformat()

            def _do_write() -> Dict[str, Any]:
                # De-dupe baseline extraction
                cursor.execute("DELETE FROM fill_events WHERE analysis_id = ?", (analysis_id,))
                cursor.execute("DELETE FROM technique_events WHERE analysis_id = ?", (analysis_id,))

                fills_inserted = 0
                tech_inserted = 0

                # -------- FILL detection (simple density heuristic) --------
                # Identify windows with many hits, biased toward tom/snare activity.
                n = len(hits)
                i = 0
                in_fill = False
                fill_start = None
                fill_end = None
                fill_hit_count = 0
                fill_instruments = set()

                while i < n:
                    t0 = hits[i][1]
                    j = i
                    tom_snare = 0
                    insts = set()
                    while j < n and (hits[j][1] - t0) <= float(fill_window_sec):
                        inst = hits[j][0]
                        insts.add(inst)
                        if inst in ("tom", "snare"):
                            tom_snare += 1
                        j += 1

                    window_hits = j - i
                    # Stricter fill rule:
                    # - must be dense
                    # - must have meaningful tom/snare presence
                    # - skip overlapping windows by jumping i->j when a fill is started
                    looks_like_fill = window_hits >= int(fill_min_hits) and (tom_snare >= 3 or ("tom" in insts and tom_snare >= 2))
                    if looks_like_fill:
                        fs = float(t0)
                        fe = float(hits[j - 1][1]) if j - 1 >= i else fs
                        # Minimum duration prevents ultra-short spikes from being recorded as a fill.
                        if (fe - fs) >= 0.25:
                            beat_index = int(fs / sec_per_beat) if sec_per_beat > 0 else None
                            bar_index = int((beat_index or 0) // int(beats_per_bar)) if beats_per_bar > 0 else None
                            cursor.execute(
                                """
                                INSERT INTO fill_events (
                                    fill_id, analysis_id, drummer_id, song_id,
                                    start_time_sec, end_time_sec,
                                    start_bar_index, end_bar_index,
                                    hit_count, instruments_json,
                                    density_per_sec, classification,
                                    created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    str(uuid.uuid4()),
                                    analysis_id,
                                    drummer_fk,
                                    None,
                                    fs,
                                    fe,
                                    bar_index,
                                    bar_index,
                                    int(window_hits),
                                    json.dumps(sorted(list(insts))),
                                    float(window_hits) / max(0.001, (fe - fs)),
                                    "density_fill",
                                    now,
                                ),
                            )
                            fills_inserted += 1
                        i = max(i + 1, j)
                    else:
                        i += 1

                # -------- Technique detection (baseline heuristics) --------
                # Flam: two snare hits within flam_max_gap_ms
                # Roll: >= roll_min_hits snare hits where each gap <= roll_max_gap_ms
                snare_times = [t for inst, t, _ in hits if inst == "snare"]
                snare_times.sort()

                technique_breakdown: Dict[str, int] = {}

                # Flams
                for k in range(1, len(snare_times)):
                    gap_ms = (float(snare_times[k]) - float(snare_times[k - 1])) * 1000.0
                    if 0.0 < gap_ms <= float(flam_max_gap_ms):
                        cursor.execute(
                            """
                            INSERT INTO technique_events (
                                technique_event_id, analysis_id, drummer_id, song_id,
                                start_time_sec, end_time_sec,
                                technique_type, technique_name,
                                confidence, details_json,
                                created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                str(uuid.uuid4()),
                                analysis_id,
                                drummer_fk,
                                None,
                                float(snare_times[k - 1]),
                                float(snare_times[k]),
                                "rudiment",
                                "flam_like",
                                0.55,
                                json.dumps({"gap_ms": gap_ms}),
                                now,
                            ),
                        )
                        tech_inserted += 1
                        technique_breakdown["flam_like"] = int(technique_breakdown.get("flam_like") or 0) + 1

                # Rolls
                run_start = 0
                for k in range(1, len(snare_times) + 1):
                    if k == len(snare_times):
                        end_run = k
                    else:
                        gap_ms = (float(snare_times[k]) - float(snare_times[k - 1])) * 1000.0
                        end_run = None if gap_ms <= float(roll_max_gap_ms) else k

                    if end_run is not None:
                        run_len = end_run - run_start
                        if run_len >= int(roll_min_hits):
                            s = float(snare_times[run_start])
                            e = float(snare_times[end_run - 1])
                            cursor.execute(
                                """
                                INSERT INTO technique_events (
                                    technique_event_id, analysis_id, drummer_id, song_id,
                                    start_time_sec, end_time_sec,
                                    technique_type, technique_name,
                                    confidence, details_json,
                                    created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    str(uuid.uuid4()),
                                    analysis_id,
                                    drummer_fk,
                                    None,
                                    s,
                                    e,
                                    "rudiment",
                                    "roll_like",
                                    0.6,
                                    json.dumps({"hit_count": int(run_len)}),
                                    now,
                                ),
                            )
                            tech_inserted += 1
                            technique_breakdown["roll_like"] = int(technique_breakdown.get("roll_like") or 0) + 1
                        run_start = end_run

                conn.commit()
                fills_per_min = 0.0
                try:
                    denom = max(1e-6, float(song_len_sec) / 60.0)
                    fills_per_min = float(fills_inserted) / denom
                except Exception:
                    fills_per_min = 0.0

                return {
                    "fills": int(fills_inserted),
                    "techniques": int(tech_inserted),
                    "fills_per_min": float(fills_per_min),
                    "technique_breakdown": technique_breakdown,
                }

            res = self._with_write_lock_retry(_do_write) or {}
            out["fills"] = int(res.get("fills") or 0)
            out["techniques"] = int(res.get("techniques") or 0)
            if out["fills"] > 0:
                self.data_changed.emit("fill_events", "insert")
            if out["techniques"] > 0:
                self.data_changed.emit("technique_events", "insert")
            return out
        except Exception as e:
            msg = f"Phase 3 extraction failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def run_phase3_fills_and_techniques_for_drummer(
        self,
        *,
        drummer_slug: str,
    ) -> Dict[str, Any]:
        out = {
            "drummer_slug": drummer_slug,
            "analyses": 0,
            "fills": 0,
            "techniques": 0,
            "avg_fills_per_min": 0.0,
            "technique_breakdown": {},
        }
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return out

            conn = self._get_connection()
            cursor = conn.cursor()
            drummer_fk = self._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=drummer_slug)
            if drummer_fk is None:
                self._ensure_drummer_exists(cursor=cursor, drummer_id=drummer_slug)
                conn.commit()
                drummer_fk = self._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=drummer_slug)
            if drummer_fk is None:
                return out

            cursor.execute(
                "SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ? ORDER BY created_at DESC",
                (drummer_fk,),
            )
            rows = cursor.fetchall() or []
            out["analyses"] = len(rows)
            fills = 0
            tech = 0
            fills_per_min_vals: List[float] = []
            breakdown: Dict[str, int] = {}
            for r in rows:
                aid = r[0]
                res = self.extract_fills_and_techniques_for_analysis(analysis_id=aid)
                fills += int((res or {}).get("fills") or 0)
                tech += int((res or {}).get("techniques") or 0)

                try:
                    fpm = float((res or {}).get("fills_per_min") or 0.0)
                    if fpm > 0:
                        fills_per_min_vals.append(fpm)
                except Exception:
                    pass

                try:
                    tb = (res or {}).get("technique_breakdown") or {}
                    if isinstance(tb, dict):
                        for k, v in tb.items():
                            try:
                                breakdown[str(k)] = int(breakdown.get(str(k)) or 0) + int(v or 0)
                            except Exception:
                                continue
                except Exception:
                    pass
            out["fills"] = fills
            out["techniques"] = tech

            if fills_per_min_vals:
                out["avg_fills_per_min"] = float(sum(fills_per_min_vals) / float(len(fills_per_min_vals)))
            out["technique_breakdown"] = breakdown
            return out
        except Exception as e:
            msg = f"Phase 3 run failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def extract_microtiming_and_dynamics_for_analysis(
        self,
        *,
        analysis_id: str,
    ) -> Dict[str, Any]:
        """Phase 4 (baseline): derive microtiming + dynamics summaries from drum_hit_events.

        Writes into song_performance_analysis:
        - groove_micro_timing_variance
        - groove_pocket_tightness
        - groove_swing_factor (currently None unless a reliable estimate exists)
        - humanness_score
        - hit_counts_json
        - hit_density_json
        - dynamics_json
        """

        out: Dict[str, Any] = {
            "analysis_id": analysis_id,
            "updated": False,
            "total_hits": 0,
            "timing_std_ms": None,
            "timing_mean_ms": None,
            "velocity_mean": None,
            "velocity_std": None,
            "pocket_tightness": None,
            "micro_timing_variance": None,
            "humanness_score": None,
        }
        try:
            self._set_last_ingest_error("")
            analysis_id = (analysis_id or "").strip()
            if not analysis_id:
                return out

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT tempo_bpm, duration_sec FROM song_performance_analysis WHERE analysis_id = ? LIMIT 1",
                (analysis_id,),
            )
            spa = cursor.fetchone()
            if not spa:
                return out

            tempo_bpm = spa[0]
            duration_sec = spa[1]
            try:
                tempo_bpm = float(tempo_bpm) if isinstance(tempo_bpm, (int, float)) else None
            except Exception:
                tempo_bpm = None
            try:
                duration_sec = float(duration_sec) if isinstance(duration_sec, (int, float)) else None
            except Exception:
                duration_sec = None

            cursor.execute(
                """
                SELECT instrument, onset_time_sec, timing_offset_ms, velocity_est
                FROM drum_hit_events
                WHERE analysis_id = ?
                ORDER BY onset_time_sec ASC
                """,
                (analysis_id,),
            )
            rows = cursor.fetchall() or []
            if not rows:
                return out

            offsets: List[float] = []
            velocities: List[float] = []
            hit_counts: Dict[str, int] = {}
            first_t = None
            last_t = None

            for inst, t, off_ms, vel in rows:
                inst_s = str(inst or "")
                hit_counts[inst_s] = int(hit_counts.get(inst_s) or 0) + 1

                try:
                    t = float(t)
                    if first_t is None:
                        first_t = t
                    last_t = t
                except Exception:
                    pass

                try:
                    if off_ms is not None:
                        offsets.append(float(off_ms))
                except Exception:
                    pass

                try:
                    if vel is not None:
                        velocities.append(float(vel))
                except Exception:
                    pass

            total_hits = int(sum(hit_counts.values()))
            out["total_hits"] = total_hits

            if duration_sec is None:
                try:
                    if first_t is not None and last_t is not None and float(last_t) > float(first_t):
                        duration_sec = float(last_t) - float(first_t)
                except Exception:
                    duration_sec = None

            # ---- microtiming stats ----
            timing_mean_ms = None
            timing_std_ms = None
            if offsets:
                try:
                    timing_mean_ms = float(statistics.fmean(offsets))
                except Exception:
                    timing_mean_ms = None
                try:
                    timing_std_ms = float(statistics.pstdev(offsets)) if len(offsets) >= 2 else 0.0
                except Exception:
                    timing_std_ms = None

            # ---- dynamics stats ----
            vel_mean = None
            vel_std = None
            if velocities:
                try:
                    vel_mean = float(statistics.fmean(velocities))
                except Exception:
                    vel_mean = None
                try:
                    vel_std = float(statistics.pstdev(velocities)) if len(velocities) >= 2 else 0.0
                except Exception:
                    vel_std = None

            # Pocket tightness in [0, 1], decreasing with timing std.
            pocket_tightness = None
            micro_var = None
            if timing_std_ms is not None:
                micro_var = float(timing_std_ms)
                # Smooth decay so values remain informative above ~30ms.
                # 0ms => 1.0, ~20ms => 0.45, ~36ms => 0.23, ~60ms => 0.09
                try:
                    pocket_tightness = float(2.718281828459045 ** (-float(timing_std_ms) / 25.0))
                except Exception:
                    pocket_tightness = None
                if pocket_tightness is not None:
                    pocket_tightness = max(0.0, min(1.0, pocket_tightness))

            # Humanness is a simple composite of timing variation + dynamics variation.
            # (This is intentionally lightweight; can be refined later.)
            humanness = None
            try:
                t_component = 0.0
                if timing_std_ms is not None:
                    # Favor some variation, penalize too-tight and too-loose.
                    # Peak around ~12ms.
                    t_component = max(0.0, 1.0 - (abs(float(timing_std_ms) - 12.0) / 28.0))
                v_component = 0.0
                if vel_std is not None:
                    # Peak around ~0.18 assuming velocity_est is ~0..1.
                    v_component = max(0.0, 1.0 - (abs(float(vel_std) - 0.18) / 0.30))
                humanness = max(0.0, min(1.0, (0.65 * t_component) + (0.35 * v_component)))
            except Exception:
                humanness = None

            # Basic hit density: hits per second and per beat (if tempo exists).
            hits_per_sec = None
            hits_per_beat = None
            try:
                if duration_sec and duration_sec > 0:
                    hits_per_sec = float(total_hits) / float(duration_sec)
            except Exception:
                hits_per_sec = None
            try:
                if duration_sec and duration_sec > 0 and tempo_bpm and tempo_bpm > 0:
                    beats = float(duration_sec) / (60.0 / float(tempo_bpm))
                    if beats > 0:
                        hits_per_beat = float(total_hits) / beats
            except Exception:
                hits_per_beat = None

            now = datetime.utcnow().isoformat()

            def _do_write() -> None:
                cursor.execute(
                    """
                    UPDATE song_performance_analysis
                    SET
                        groove_swing_factor = COALESCE(groove_swing_factor, NULL),
                        groove_pocket_tightness = ?,
                        groove_micro_timing_variance = ?,
                        humanness_score = ?,
                        total_hits = ?,
                        hit_counts_json = ?,
                        hit_density_json = ?,
                        dynamics_json = ?,
                        updated_at = ?
                    WHERE analysis_id = ?
                    """,
                    (
                        float(pocket_tightness) if pocket_tightness is not None else None,
                        float(micro_var) if micro_var is not None else None,
                        float(humanness) if humanness is not None else None,
                        int(total_hits),
                        json.dumps(hit_counts, default=str),
                        json.dumps(
                            {
                                "duration_sec": float(duration_sec) if isinstance(duration_sec, (int, float)) else None,
                                "hits_per_sec": hits_per_sec,
                                "hits_per_beat": hits_per_beat,
                            },
                            default=str,
                        ),
                        json.dumps(
                            {
                                "velocity_mean": vel_mean,
                                "velocity_std": vel_std,
                                "timing_mean_ms": timing_mean_ms,
                                "timing_std_ms": timing_std_ms,
                            },
                            default=str,
                        ),
                        now,
                        analysis_id,
                    ),
                )
                conn.commit()

            self._with_write_lock_retry(_do_write)
            out["updated"] = True
            out["timing_std_ms"] = timing_std_ms
            out["timing_mean_ms"] = timing_mean_ms
            out["velocity_mean"] = vel_mean
            out["velocity_std"] = vel_std
            out["pocket_tightness"] = pocket_tightness
            out["micro_timing_variance"] = micro_var
            out["humanness_score"] = humanness
            self.data_changed.emit("song_performance_analysis", "update")
            return out
        except Exception as e:
            msg = f"Phase 4 extraction failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def run_phase4_microtiming_and_dynamics_for_drummer(
        self,
        *,
        drummer_slug: str,
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "drummer_slug": drummer_slug,
            "analyses": 0,
            "updated": 0,
            "avg_timing_std_ms": None,
            "avg_pocket_tightness": None,
            "avg_humanness_score": None,
        }
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return out

            conn = self._get_connection()
            cursor = conn.cursor()
            drummer_fk = self._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=drummer_slug)
            if drummer_fk is None:
                self._ensure_drummer_exists(cursor=cursor, drummer_id=drummer_slug)
                conn.commit()
                drummer_fk = self._get_drummer_fk_by_slug(cursor=cursor, drummer_slug=drummer_slug)
            if drummer_fk is None:
                return out

            cursor.execute(
                "SELECT analysis_id FROM song_performance_analysis WHERE drummer_id = ? ORDER BY created_at DESC",
                (drummer_fk,),
            )
            rows = cursor.fetchall() or []
            out["analyses"] = len(rows)

            updated = 0
            stds: List[float] = []
            pockets: List[float] = []
            humans: List[float] = []
            for (aid,) in rows:
                res = self.extract_microtiming_and_dynamics_for_analysis(analysis_id=aid)
                if res.get("updated"):
                    updated += 1
                try:
                    v = res.get("timing_std_ms")
                    if v is not None:
                        stds.append(float(v))
                except Exception:
                    pass
                try:
                    v = res.get("pocket_tightness")
                    if v is not None:
                        pockets.append(float(v))
                except Exception:
                    pass
                try:
                    v = res.get("humanness_score")
                    if v is not None:
                        humans.append(float(v))
                except Exception:
                    pass

            out["updated"] = int(updated)
            if stds:
                out["avg_timing_std_ms"] = float(sum(stds) / float(len(stds)))
            if pockets:
                out["avg_pocket_tightness"] = float(sum(pockets) / float(len(pockets)))
            if humans:
                out["avg_humanness_score"] = float(sum(humans) / float(len(humans)))
            return out
        except Exception as e:
            msg = f"Phase 4 run failed: {e}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return out

    def _table_columns(self, table_name: str) -> set:
        if table_name in self._schema_cache:
            return self._schema_cache[table_name]
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            rows = cursor.execute(f"PRAGMA table_info({table_name})").fetchall()
            cols = {row[1] for row in rows} if rows else set()
            self._schema_cache[table_name] = cols
            return cols
        except Exception:
            self._schema_cache[table_name] = set()
            return set()

    @classmethod
    def get_instance(cls):
        """Get the singleton instance"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, db_path=None) -> bool:
        """
        Initialize the database connection.
        
        Args:
            db_path: Path to SQLite database. If None, uses default path.
            
        Returns:
            bool: True if successful
        """
        try:
            if self._initialized:
                logger.warning("Database already initialized")
                return True
                
            # Set default path if not provided
            if db_path is None:
                # First, honor an explicit environment override so backend
                # services and the admin GUI can share the same canonical DB
                # (e.g. the rich admin/analysis DB at admin/drumtrackai.db).
                env_path = os.getenv("DRUMTRACKAI_DB_PATH")
                if env_path:
                    db_path = env_path
                else:
                    # Prefer project-local DBs when running from a repo checkout.
                    # This prevents the admin UI from silently connecting to a
                    # fresh per-user DB with no drummers/beats.
                    try:
                        project_root = Path(__file__).resolve().parents[2]
                    except Exception:
                        project_root = None

                    candidates: List[Path] = []
                    if project_root:
                        candidates.extend([
                            project_root / "admin" / "drumtrackai.db",
                            project_root / "admin" / "admin" / "drumtrackai.db",
                            project_root / "admin" / "data" / "drum_training.db",
                            project_root / "admin" / "admin" / "data" / "drum_training.db",
                        ])

                    selected = None
                    for candidate in candidates:
                        try:
                            if candidate.exists() and candidate.is_file() and candidate.stat().st_size > 0:
                                selected = candidate
                                break
                        except Exception:
                            continue

                    if selected is not None:
                        db_path = str(selected)
                    else:
                        # Fallback to the original per-user location.
                        home = Path.home()
                        db_dir = home / "DrumTracKAI" / "database"
                        db_dir.mkdir(parents=True, exist_ok=True)
                        db_path = str(db_dir / "drum_tracks.db")
                
            logger.info(f"Initializing database at: {db_path}")
            self._db_path = db_path
            
            # Create initial connection
            self._get_connection()
            
            # Create tables if they don't exist
            self._create_tables()

            # Schema migrations / compatibility
            self._ensure_phase32_42_columns()
            
            self._initialized = True
            self.database_connected.emit(db_path)
            logger.info(f"Database initialized successfully at {db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}")
            self.database_error.emit(f"Failed to initialize database: {str(e)}")
            return False

    def _sha256_file(self, file_path: str, max_bytes: int = 0) -> str:
        try:
            p = str(file_path)
            h = hashlib.sha256()
            with open(p, "rb") as f:
                if max_bytes and int(max_bytes) > 0:
                    h.update(f.read(int(max_bytes)))
                else:
                    for chunk in iter(lambda: f.read(1024 * 1024), b""):
                        h.update(chunk)
            return h.hexdigest()
        except Exception:
            return ""

    def upsert_song_performance_analysis(
        self,
        *,
        analysis_id: str,
        drummer_id: str,
        song_id: Optional[str] = None,
        source_file: str = "",
        mvsep_output_dir: str = "",
        analysis_json: Optional[Dict[str, Any]] = None,
        stem_files_used: Optional[Dict[str, Any]] = None,
        analysis_version: str = "",
    ) -> bool:
        try:
            self._set_last_ingest_error("")
            analysis_id = (analysis_id or "").strip()
            drummer_id = (drummer_id or "").strip()
            if not analysis_id or not drummer_id:
                return False

            now = datetime.utcnow().isoformat()
            analysis_json = analysis_json if isinstance(analysis_json, dict) else {}
            stem_files_used = stem_files_used if isinstance(stem_files_used, dict) else {}

            tempo_bpm = analysis_json.get("tempo")
            tempo_confidence = analysis_json.get("tempo_confidence")
            duration_sec = analysis_json.get("duration")
            total_hits = analysis_json.get("total_hits")

            groove = analysis_json.get("groove_analysis") if isinstance(analysis_json.get("groove_analysis"), dict) else {}
            swing_factor = groove.get("swing_factor")
            pocket_tightness = groove.get("pocket_tightness")
            micro_var = groove.get("micro_timing_variance")
            rhythmic_complexity = groove.get("rhythmic_complexity")
            syncopation_level = groove.get("syncopation_level")
            humanness_score = groove.get("humanness_score")

            raw_analysis_json = json.dumps(analysis_json, default=str)
            stem_files_used_json = json.dumps(stem_files_used, default=str)

            conn = self._get_connection()
            cursor = conn.cursor()

            def _do_write():
                # Ensure FK target exists (song_performance_analysis.drummer_id -> drummers.*)
                drummer_fk = self._ensure_drummer_exists(cursor=cursor, drummer_id=drummer_id)

                cursor.execute(
                    """
                INSERT INTO song_performance_analysis (
                    analysis_id, song_id, drummer_id, source_file, mvsep_output_dir,
                    tempo_bpm, tempo_confidence, duration_sec,
                    groove_swing_factor, groove_pocket_tightness, groove_micro_timing_variance,
                    rhythmic_complexity, syncopation_level, humanness_score,
                    total_hits,
                    stem_files_used_json, raw_analysis_json,
                    analysis_version,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(analysis_id) DO UPDATE SET
                    song_id=excluded.song_id,
                    drummer_id=excluded.drummer_id,
                    source_file=excluded.source_file,
                    mvsep_output_dir=excluded.mvsep_output_dir,
                    tempo_bpm=excluded.tempo_bpm,
                    tempo_confidence=excluded.tempo_confidence,
                    duration_sec=excluded.duration_sec,
                    groove_swing_factor=excluded.groove_swing_factor,
                    groove_pocket_tightness=excluded.groove_pocket_tightness,
                    groove_micro_timing_variance=excluded.groove_micro_timing_variance,
                    rhythmic_complexity=excluded.rhythmic_complexity,
                    syncopation_level=excluded.syncopation_level,
                    humanness_score=excluded.humanness_score,
                    total_hits=excluded.total_hits,
                    stem_files_used_json=excluded.stem_files_used_json,
                    raw_analysis_json=excluded.raw_analysis_json,
                    analysis_version=excluded.analysis_version,
                    updated_at=excluded.updated_at
                """,
                    (
                    analysis_id,
                    song_id,
                    drummer_fk,
                    source_file,
                    mvsep_output_dir,
                    float(tempo_bpm) if isinstance(tempo_bpm, (int, float)) else None,
                    float(tempo_confidence) if isinstance(tempo_confidence, (int, float)) else None,
                    float(duration_sec) if isinstance(duration_sec, (int, float)) else None,
                    float(swing_factor) if isinstance(swing_factor, (int, float)) else None,
                    float(pocket_tightness) if isinstance(pocket_tightness, (int, float)) else None,
                    float(micro_var) if isinstance(micro_var, (int, float)) else None,
                    float(rhythmic_complexity) if isinstance(rhythmic_complexity, (int, float)) else None,
                    float(syncopation_level) if isinstance(syncopation_level, (int, float)) else None,
                    float(humanness_score) if isinstance(humanness_score, (int, float)) else None,
                    int(total_hits) if isinstance(total_hits, int) else None,
                    stem_files_used_json,
                    raw_analysis_json,
                    (analysis_version or "").strip() or None,
                    now,
                    now,
                    ),
                )
                conn.commit()

            self._with_write_lock_retry(_do_write)
            self.data_changed.emit("song_performance_analysis", "upsert")
            return True
        except sqlite3.OperationalError as e:
            msg = f"Error upserting song_performance_analysis: {str(e)}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return False
        except Exception as e:
            msg = f"Error upserting song_performance_analysis: {str(e)}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return False

    def ingest_processed_stems_song_folder(
        self,
        *,
        drummer_id: str,
        song_folder: str,
        compute_hashes: bool = False,
        hash_max_bytes: int = 0,
        analysis_version: str = "baseline_v1",
    ) -> Optional[str]:
        try:
            self._set_last_ingest_error("")
            drummer_id = (drummer_id or "").strip()
            song_folder = str(song_folder or "").strip()
            if not drummer_id or not song_folder:
                self._set_last_ingest_error("Missing drummer_id or song_folder")
                return None
            if not os.path.isdir(song_folder):
                self._set_last_ingest_error(f"Not a directory: {song_folder}")
                return None

            drum_analysis_path = os.path.join(song_folder, "drum_analysis.json")
            if not os.path.exists(drum_analysis_path):
                self._set_last_ingest_error(f"Missing drum_analysis.json: {song_folder}")
                return None

            analysis_json = {}
            try:
                with open(drum_analysis_path, "r", encoding="utf-8") as f:
                    analysis_json = json.load(f)
            except Exception:
                analysis_json = {}

            stem_files_used = {}
            try:
                stem_files_used = analysis_json.get("stem_files_used") if isinstance(analysis_json, dict) else {}
            except Exception:
                stem_files_used = {}
            if not isinstance(stem_files_used, dict):
                stem_files_used = {}

            analysis_id = str(uuid.uuid4())
            source_file = ""
            try:
                candidates = [p for p in os.listdir(song_folder) if p.lower().endswith((".mp3", ".wav", ".flac", ".m4a"))]
                if candidates:
                    source_file = os.path.join(song_folder, sorted(candidates)[0])
            except Exception:
                source_file = ""

            # Pre-ensure drummer and get FK value (INTEGER id in the admin DB)
            conn = self._get_connection()
            cursor = conn.cursor()
            drummer_fk = self._ensure_drummer_exists(cursor=cursor, drummer_id=drummer_id)
            conn.commit()

            ok = self.upsert_song_performance_analysis(
                analysis_id=analysis_id,
                drummer_id=drummer_id,
                song_id=None,
                source_file=source_file,
                mvsep_output_dir=song_folder,
                analysis_json=analysis_json,
                stem_files_used=stem_files_used,
                analysis_version=analysis_version,
            )
            if not ok:
                return None

            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            cursor = conn.cursor()

            def _insert_artifact(role: str, path: str, fmt: str = ""):
                try:
                    if not path or not os.path.exists(path):
                        return
                    stat = os.stat(path)
                    sha = ""
                    if compute_hashes:
                        sha = self._sha256_file(path, max_bytes=hash_max_bytes)
                    cursor.execute(
                        """
                        INSERT INTO analysis_artifacts (
                            artifact_id, analysis_id, drummer_id, song_id,
                            artifact_role, file_path, file_format,
                            file_size_bytes, file_mtime_epoch, sha256,
                            extractor_name, extractor_version,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            analysis_id,
                            drummer_fk,
                            None,
                            role,
                            str(path),
                            (fmt or "").strip() or None,
                            int(stat.st_size),
                            float(stat.st_mtime),
                            sha or None,
                            "processed_stems_ingest",
                            (analysis_version or "").strip() or None,
                            now,
                        ),
                    )
                except Exception:
                    return

            _insert_artifact("drum_analysis_json", drum_analysis_path, "json")
            prof = os.path.join(song_folder, "drummer_profile.json")
            _insert_artifact("drummer_profile_json", prof, "json")

            for stem_name, path in stem_files_used.items():
                try:
                    if not path or not os.path.exists(path):
                        continue
                    stat = os.stat(path)
                    sha = ""
                    if compute_hashes:
                        sha = self._sha256_file(path, max_bytes=hash_max_bytes)
                    cursor.execute(
                        """
                        INSERT INTO stem_artifacts (
                            stem_id, analysis_id, drummer_id, song_id,
                            stem_name, file_path,
                            file_size_bytes, file_mtime_epoch, sha256,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            analysis_id,
                            drummer_fk,
                            None,
                            str(stem_name),
                            str(path),
                            int(stat.st_size),
                            float(stat.st_mtime),
                            sha or None,
                            now,
                        ),
                    )
                except Exception:
                    continue

            def _commit_all():
                conn.commit()

            self._with_write_lock_retry(_commit_all)
            self.data_changed.emit("analysis_artifacts", "insert")
            self.data_changed.emit("stem_artifacts", "insert")
            return analysis_id
        except sqlite3.OperationalError as e:
            msg = f"Error ingesting processed stems folder: {str(e)}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return None
        except Exception as e:
            msg = f"Error ingesting processed stems folder: {str(e)}"
            logger.error(msg)
            self._set_last_ingest_error(msg)
            self.database_error.emit(msg)
            return None

    def list_drummer_presets(self, profile_type: str) -> List[Dict[str, Any]]:
        try:
            profile_type = (profile_type or "").strip().lower()
            if not profile_type:
                return []

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT preset_id, profile_type, name, tier,
                       deltas_json, policies_json,
                       source_type, source_song_name, source_ref
                FROM drummer_presets
                WHERE profile_type = ?
                ORDER BY tier DESC, name
                """,
                (profile_type,),
            )
            rows = cursor.fetchall()
            out: List[Dict[str, Any]] = []
            for row in rows:
                deltas = {}
                policies = {}
                try:
                    deltas = json.loads(row[4]) if row[4] else {}
                except Exception:
                    deltas = {}
                try:
                    policies = json.loads(row[5]) if row[5] else {}
                except Exception:
                    policies = {}
                out.append(
                    {
                        "preset_id": row[0],
                        "profile_type": row[1],
                        "name": row[2],
                        "tier": row[3],
                        "deltas": deltas,
                        "policies": policies,
                        "source_type": row[6],
                        "source_song_name": row[7],
                        "source_ref": row[8],
                    }
                )
            return out
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_presets table not available: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing drummer presets: {str(e)}")
            self.database_error.emit(f"Error listing drummer presets: {str(e)}")
            return []

    def get_drummer_preset(self, preset_id: str) -> Optional[Dict[str, Any]]:
        try:
            preset_id = (preset_id or "").strip()
            if not preset_id:
                return None

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT preset_id, profile_type, name, tier,
                       deltas_json, policies_json,
                       source_type, source_song_name, source_ref
                FROM drummer_presets
                WHERE preset_id = ?
                LIMIT 1
                """,
                (preset_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            deltas = {}
            policies = {}
            try:
                deltas = json.loads(row[4]) if row[4] else {}
            except Exception:
                deltas = {}
            try:
                policies = json.loads(row[5]) if row[5] else {}
            except Exception:
                policies = {}

            return {
                "preset_id": row[0],
                "profile_type": row[1],
                "name": row[2],
                "tier": row[3],
                "deltas": deltas,
                "policies": policies,
                "source_type": row[6],
                "source_song_name": row[7],
                "source_ref": row[8],
            }
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_presets table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting drummer preset {preset_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer preset: {str(e)}")
            return None

    def upsert_drummer_preset(
        self,
        preset_id: str,
        profile_type: str,
        name: str,
        tier: str,
        deltas: Optional[Dict[str, Any]] = None,
        policies: Optional[Dict[str, Any]] = None,
        source_type: Optional[str] = None,
        source_song_name: Optional[str] = None,
        source_ref: Optional[str] = None,
    ) -> bool:
        try:
            preset_id = (preset_id or "").strip()
            profile_type = (profile_type or "").strip().lower()
            name = (name or "").strip()
            tier = (tier or "").strip().lower()

            if not preset_id or not profile_type or not name or not tier:
                return False

            deltas_json = json.dumps(deltas or {})
            policies_json = json.dumps(policies or {})

            now = datetime.utcnow().isoformat()
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO drummer_presets (
                    preset_id, profile_type, name, tier,
                    deltas_json, policies_json,
                    source_type, source_song_name, source_ref,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(preset_id) DO UPDATE SET
                    profile_type=excluded.profile_type,
                    name=excluded.name,
                    tier=excluded.tier,
                    deltas_json=excluded.deltas_json,
                    policies_json=excluded.policies_json,
                    source_type=excluded.source_type,
                    source_song_name=excluded.source_song_name,
                    source_ref=excluded.source_ref,
                    updated_at=excluded.updated_at
                """,
                (
                    preset_id,
                    profile_type,
                    name,
                    tier,
                    deltas_json,
                    policies_json,
                    source_type,
                    source_song_name,
                    source_ref,
                    now,
                    now,
                ),
            )
            conn.commit()
            return True
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_presets table not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error upserting drummer preset: {str(e)}")
            self.database_error.emit(f"Error upserting drummer preset: {str(e)}")
            return False

    def _get_connection(self) -> sqlite3.Connection:
        """
        Get a thread-local database connection.
        
        Returns:
            sqlite3.Connection: SQLite connection object
        """
        thread_id = threading.get_ident()
        if thread_id not in self._connections or self._connections[thread_id] is None:
            if self._db_path is None:
                raise ValueError("Database path not set. Call initialize() first.")
                
            conn = sqlite3.connect(self._db_path, timeout=10.0, check_same_thread=False)
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            # Make the GUI more robust against concurrent access.
            # WAL allows concurrent readers while a writer is active.
            # busy_timeout makes SQLite wait a bit instead of raising 'database is locked'.
            try:
                conn.execute("PRAGMA journal_mode = WAL")
            except Exception:
                pass
            try:
                conn.execute("PRAGMA busy_timeout = 5000")
            except Exception:
                pass
            # Configure for dictionary results
            conn.row_factory = sqlite3.Row
            self._connections[thread_id] = conn
            
        return self._connections[thread_id]

    def _create_tables(self) -> None:
        """Create database tables if they don't exist"""
        if self._tables_created:
            return
            
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Create drummers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drummers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            
            # Create songs table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS songs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                artist TEXT,
                album TEXT,
                year INTEGER,
                genre TEXT,
                duration REAL,
                file_path TEXT,
                drummer_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (drummer_id) REFERENCES drummers(id) ON DELETE CASCADE
            )
            ''')
            
            # Create drum_beats table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drum_beats (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                file_path TEXT,
                song_id TEXT,
                drummer_id TEXT,
                bpm REAL,
                time_signature TEXT,
                complexity REAL,
                energy REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
                FOREIGN KEY (drummer_id) REFERENCES drummers(id) ON DELETE CASCADE
            )
            ''')
            
            # Create processing_metadata table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS processing_metadata (
                id TEXT PRIMARY KEY,
                entity_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                process_type TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata TEXT,  -- JSON string
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')
            # Note: drummer_personas lives in the admin DB and is created by
            # admin/tools/init_drummer_personas_table.py. We don't create it
            # here to avoid surprising frontends that use a different DB
            # layout, but we *do* provide read helpers below if it exists.

            # Admin-only mapping of public DrumTracKAI drummer categories to
            # analysis personas & default knob settings. This lives in the same
            # DB so both the admin tools and backend can share it.
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drummer_category_mappings (
                category_id TEXT PRIMARY KEY,
                display_name TEXT,
                primary_persona_id TEXT,
                backup_persona_ids_json TEXT,
                default_humanize REAL,
                default_swing REAL,
                default_chorus_ride_pref REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drummer_presets (
                preset_id TEXT PRIMARY KEY,
                profile_type TEXT NOT NULL,
                name TEXT NOT NULL,
                tier TEXT NOT NULL,
                deltas_json TEXT,
                policies_json TEXT,
                source_type TEXT,
                source_song_name TEXT,
                source_ref TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS song_performance_analysis (
                analysis_id TEXT PRIMARY KEY,
                song_id TEXT,
                drummer_id TEXT,
                source_file TEXT,
                mvsep_output_dir TEXT,
                tempo_bpm REAL,
                tempo_confidence REAL,
                time_signature TEXT,
                duration_sec REAL,
                groove_swing_factor REAL,
                groove_pocket_tightness REAL,
                groove_micro_timing_variance REAL,
                rhythmic_complexity REAL,
                syncopation_level REAL,
                humanness_score REAL,
                total_hits INTEGER,
                hit_counts_json TEXT,
                hit_density_json TEXT,
                dynamics_json TEXT,
                fills_summary_json TEXT,
                rudiments_summary_json TEXT,
                techniques_json TEXT,
                stem_files_used_json TEXT,
                raw_analysis_json TEXT,
                analysis_version TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE SET NULL,
                FOREIGN KEY (drummer_id) REFERENCES drummers(id) ON DELETE SET NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drum_hit_events (
                event_id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                drummer_id TEXT,
                song_id TEXT,
                instrument TEXT NOT NULL,
                component TEXT,
                onset_time_sec REAL NOT NULL,
                onset_strength REAL,
                velocity_est REAL,
                beat_index INTEGER,
                bar_index INTEGER,
                subdivision TEXT,
                timing_offset_ms REAL,
                is_ghost INTEGER,
                is_accent INTEGER,
                is_flams_like INTEGER,
                is_roll_like INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES song_performance_analysis(analysis_id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS fill_events (
                fill_id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                drummer_id TEXT,
                song_id TEXT,
                start_time_sec REAL NOT NULL,
                end_time_sec REAL NOT NULL,
                start_bar_index INTEGER,
                end_bar_index INTEGER,
                hit_count INTEGER,
                instruments_json TEXT,
                density_per_sec REAL,
                classification TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES song_performance_analysis(analysis_id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS technique_events (
                technique_event_id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                drummer_id TEXT,
                song_id TEXT,
                start_time_sec REAL,
                end_time_sec REAL,
                technique_type TEXT NOT NULL,
                technique_name TEXT,
                confidence REAL,
                details_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES song_performance_analysis(analysis_id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS drummer_profile_rollups (
                rollup_id TEXT PRIMARY KEY,
                drummer_id INTEGER NOT NULL UNIQUE,
                rollup_version TEXT,
                rollup_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (drummer_id) REFERENCES drummers(id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_artifacts (
                artifact_id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                drummer_id TEXT,
                song_id TEXT,
                artifact_role TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_format TEXT,
                file_size_bytes INTEGER,
                file_mtime_epoch REAL,
                sha256 TEXT,
                extractor_name TEXT,
                extractor_version TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES song_performance_analysis(analysis_id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS stem_artifacts (
                stem_id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                drummer_id TEXT,
                song_id TEXT,
                stem_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER,
                file_mtime_epoch REAL,
                sha256 TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES song_performance_analysis(analysis_id) ON DELETE CASCADE
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS calibration_adjustments (
                drummer_slug TEXT PRIMARY KEY,
                adjustments_json TEXT NOT NULL,
                metadata_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS calibration_runs (
                run_id TEXT PRIMARY KEY,
                drummer_slug TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                outcome TEXT NOT NULL,
                note_count INTEGER,
                fills_per_minute REAL,
                within_tolerance_count INTEGER,
                total_compared INTEGER,
                delta_summary TEXT,
                metadata_json TEXT,
                metrics_json TEXT,
                comparison_json TEXT,
                log_path TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            ''')

            cursor.execute('''
            CREATE TABLE IF NOT EXISTS calibration_feedback (
                feedback_id TEXT PRIMARY KEY,
                drummer_slug TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                author TEXT,
                submitted_at TEXT NOT NULL,
                metadata_json TEXT
            )
            ''')

            cursor.execute('CREATE INDEX IF NOT EXISTS idx_spa_drummer_id ON song_performance_analysis(drummer_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_spa_song_id ON song_performance_analysis(song_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hit_analysis_time ON drum_hit_events(analysis_id, onset_time_sec)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_hit_drummer_instrument_time ON drum_hit_events(drummer_id, instrument, onset_time_sec)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_fill_analysis_time ON fill_events(analysis_id, start_time_sec)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_tech_analysis_type ON technique_events(analysis_id, technique_type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_rollups_drummer_id ON drummer_profile_rollups(drummer_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_artifacts_analysis_role ON analysis_artifacts(analysis_id, artifact_role)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stems_analysis_name ON stem_artifacts(analysis_id, stem_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_calibration_runs_slug ON calibration_runs(drummer_slug)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_calibration_runs_start ON calibration_runs(started_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_calibration_feedback_slug ON calibration_feedback(drummer_slug)')

            conn.commit()
            self._tables_created = True
            logger.info("Database tables created successfully")
            
        except Exception as e:
            logger.error(f"Failed to create database tables: {str(e)}")
            self.database_error.emit(f"Failed to create database tables: {str(e)}")
            raise

    # CRUD operations for drummers
    def get_drummers(self) -> List[Dict]:
        """
        Get all drummers from the database.
        
        Returns:
            List[Dict]: List of drummer records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cols = self._table_columns("drummers")
            if "display_name" in cols:
                cursor.execute('SELECT * FROM drummers ORDER BY display_name')
            elif "name" in cols:
                cursor.execute('SELECT * FROM drummers ORDER BY name')
            else:
                cursor.execute('SELECT * FROM drummers ORDER BY id')
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            if results:
                return results

            # Prefer real drummers derived from style-vector ingestion.
            # This is the authoritative "real drummers" list in v1.1.17.
            try:
                vec_cols = self._table_columns("drummer_style_vectors")
                if vec_cols and "drummer_id" in vec_cols and "drummer_name" in vec_cols:
                    cursor.execute(
                        'SELECT DISTINCT drummer_id, drummer_name FROM drummer_style_vectors '
                        'WHERE drummer_name IS NOT NULL AND TRIM(drummer_name) != "" '
                        'ORDER BY drummer_name'
                    )
                    vec_rows = cursor.fetchall()
                    if vec_rows:
                        return [
                            {
                                "id": row[0],
                                "drummer_id": row[0],
                                "display_name": row[1],
                                "name": row[1],
                                "source": "drummer_style_vectors",
                            }
                            for row in vec_rows
                        ]
            except Exception:
                pass

            # Fallback: many v1.1.x admin DBs use drummer_personas/drummer_profiles
            # instead of the simple drummers table.
            try:
                persona_cols = self._table_columns("drummer_personas")
                if persona_cols:
                    cursor.execute('SELECT persona_id, display_name, archetypes_json, style_json, created_at, updated_at FROM drummer_personas ORDER BY display_name')
                    persona_rows = cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "drummer_id": row[0],
                            "display_name": row[1],
                            "name": row[1],
                            "archetypes_json": row[2],
                            "style_json": row[3],
                            "created_at": row[4],
                            "updated_at": row[5],
                            "source": "drummer_personas",
                        }
                        for row in persona_rows
                    ]
            except Exception:
                pass

            try:
                profile_cols = self._table_columns("drummer_profiles")
                if profile_cols:
                    cursor.execute('SELECT drummer_id, COALESCE(display_name, name) as display_name, category, era FROM drummer_profiles ORDER BY display_name')
                    profile_rows = cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "drummer_id": row[0],
                            "display_name": row[1],
                            "name": row[1],
                            "category": row[2],
                            "era": row[3],
                            "source": "drummer_profiles",
                        }
                        for row in profile_rows
                    ]
            except Exception:
                pass

            return []
        except Exception as e:
            logger.error(f"Error getting drummers: {str(e)}")
            self.database_error.emit(f"Error getting drummers: {str(e)}")
            return []

    def get_drummer(self, drummer_id: str) -> Optional[Dict]:
        """
        Get a drummer by ID.
        
        Args:
            drummer_id: The ID of the drummer
            
        Returns:
            Dict or None: Drummer record or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cols = self._table_columns("drummers")
            if "drummer_id" in cols:
                cursor.execute('SELECT * FROM drummers WHERE drummer_id = ?', (drummer_id,))
            else:
                cursor.execute('SELECT * FROM drummers WHERE id = ?', (drummer_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)

            vec_cols = self._table_columns("drummer_style_vectors")
            if vec_cols and "drummer_id" in vec_cols and "drummer_name" in vec_cols:
                cursor.execute(
                    'SELECT DISTINCT drummer_id, drummer_name FROM drummer_style_vectors WHERE drummer_id = ? LIMIT 1',
                    (drummer_id,),
                )
                vrow = cursor.fetchone()
                if vrow:
                    return {
                        "id": vrow[0],
                        "drummer_id": vrow[0],
                        "display_name": vrow[1],
                        "name": vrow[1],
                        "source": "drummer_style_vectors",
                    }

            persona_cols = self._table_columns("drummer_personas")
            if persona_cols:
                cursor.execute(
                    'SELECT persona_id, display_name, archetypes_json, style_json, created_at, updated_at FROM drummer_personas WHERE persona_id = ?',
                    (drummer_id,),
                )
                prow = cursor.fetchone()
                if prow:
                    return {
                        "id": prow[0],
                        "drummer_id": prow[0],
                        "display_name": prow[1],
                        "name": prow[1],
                        "archetypes_json": prow[2],
                        "style_json": prow[3],
                        "created_at": prow[4],
                        "updated_at": prow[5],
                        "source": "drummer_personas",
                    }

            profile_cols = self._table_columns("drummer_profiles")
            if profile_cols:
                cursor.execute(
                    'SELECT drummer_id, COALESCE(display_name, name) as display_name, category, era, styles FROM drummer_profiles WHERE drummer_id = ?',
                    (drummer_id,),
                )
                pr = cursor.fetchone()
                if pr:
                    return {
                        "id": pr[0],
                        "drummer_id": pr[0],
                        "display_name": pr[1],
                        "name": pr[1],
                        "category": pr[2],
                        "era": pr[3],
                        "styles": pr[4],
                        "source": "drummer_profiles",
                    }

            return None
        except Exception as e:
            logger.error(f"Error getting drummer {drummer_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer: {str(e)}")
            return None

    # ---- Calibration persistence helpers ---------------------------------

    def get_calibration_adjustments(self, drummer_slug: str) -> Optional[Dict[str, Any]]:
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return None

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT drummer_slug, adjustments_json, metadata_json, created_at, updated_at
                FROM calibration_adjustments
                WHERE drummer_slug = ?
                LIMIT 1
                """,
                (drummer_slug,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "drummer_slug": row["drummer_slug"],
                "adjustments": self._json_loads(row["adjustments_json"], default={}) or {},
                "metadata": self._json_loads(row["metadata_json"], default={}),
                "created_at": self._parse_datetime(row["created_at"]),
                "updated_at": self._parse_datetime(row["updated_at"]),
            }
        except sqlite3.OperationalError as e:
            logger.warning(f"calibration_adjustments table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting calibration adjustments for {drummer_slug}: {str(e)}")
            self.database_error.emit(f"Error getting calibration adjustments: {str(e)}")
            return None

    def upsert_calibration_adjustments(
        self,
        *,
        drummer_slug: str,
        adjustments: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return False

            conn = self._get_connection()
            cursor = conn.cursor()
            now = datetime.utcnow().isoformat()
            adjustments_json = self._json_dumps(adjustments or {}) or "{}"
            metadata_json = self._json_dumps(metadata or {})

            def _do_write() -> bool:
                cursor.execute(
                    """
                    INSERT INTO calibration_adjustments (
                        drummer_slug, adjustments_json, metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(drummer_slug) DO UPDATE SET
                        adjustments_json = excluded.adjustments_json,
                        metadata_json = excluded.metadata_json,
                        updated_at = excluded.updated_at
                    """,
                    (drummer_slug, adjustments_json, metadata_json, now, now),
                )
                conn.commit()
                return True

            self._with_write_lock_retry(_do_write)
            self.data_changed.emit("calibration_adjustments", "upsert")
            return True
        except sqlite3.OperationalError as e:
            logger.warning(f"calibration_adjustments table not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error upserting calibration adjustments for {drummer_slug}: {str(e)}")
            self.database_error.emit(f"Error upserting calibration adjustments: {str(e)}")
            return False

    def _row_to_calibration_run(self, row: sqlite3.Row) -> Optional[CalibrationRun]:
        if not row:
            return None

        def _to_int(value: Any) -> Optional[int]:
            try:
                return int(value)
            except Exception:
                return None

        def _to_float(value: Any) -> Optional[float]:
            try:
                return float(value)
            except Exception:
                return None

        try:
            row_dict = {key: row[key] for key in row.keys()}
        except Exception:
            try:
                row_dict = dict(row)
            except Exception:
                row_dict = {}

        metadata_json = row_dict.get("metadata_json", _MISSING)
        metrics_json = row_dict.get("metrics_json", _MISSING)
        comparison_json = row_dict.get("comparison_json", _MISSING)

        return CalibrationRun(
            run_id=str(row_dict.get("run_id", "")),
            drummer_slug=str(row_dict.get("drummer_slug", "")),
            started_at=self._parse_datetime(row_dict.get("started_at")) or datetime.utcnow(),
            completed_at=self._parse_datetime(row_dict.get("completed_at")),
            outcome=str(row_dict.get("outcome", "unknown") or "unknown"),
            note_count=_to_int(row_dict.get("note_count")),
            fills_per_minute=_to_float(row_dict.get("fills_per_minute")),
            within_tolerance_count=_to_int(row_dict.get("within_tolerance_count")),
            total_compared=_to_int(row_dict.get("total_compared")),
            delta_summary=row_dict.get("delta_summary"),
            metadata=(self._json_loads(metadata_json, default={}) or {}) if metadata_json is not _MISSING else None,
            metrics=(self._json_loads(metrics_json, default={}) or {}) if metrics_json is not _MISSING else None,
            comparison=(self._json_loads(comparison_json, default={}) or {}) if comparison_json is not _MISSING else None,
            log_path=row_dict.get("log_path"),
        )

    def _row_to_calibration_feedback(self, row: sqlite3.Row) -> Optional[CalibrationFeedback]:
        if not row:
            return None

        try:
            row_dict = {key: row[key] for key in row.keys()}
        except Exception:
            try:
                row_dict = dict(row)
            except Exception:
                row_dict = {}

        submitted_at = self._parse_datetime(row_dict.get("submitted_at")) or datetime.utcnow()
        metadata_json = row_dict.get("metadata_json", _MISSING)

        return CalibrationFeedback(
            feedback_id=str(row_dict.get("feedback_id", "")),
            drummer_slug=str(row_dict.get("drummer_slug", "")),
            rating=int(row_dict.get("rating", 0) or 0),
            comment=row_dict.get("comment"),
            author=row_dict.get("author"),
            submitted_at=submitted_at,
            metadata=(self._json_loads(metadata_json, default={}) or {}) if metadata_json is not _MISSING else None,
        )

    def log_calibration_run(
        self,
        *,
        drummer_slug: str,
        outcome: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        note_count: Optional[int] = None,
        fills_per_minute: Optional[float] = None,
        within_tolerance_count: Optional[int] = None,
        total_compared: Optional[int] = None,
        delta_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
        comparison: Optional[Dict[str, Any]] = None,
        log_path: Optional[str] = None,
        run_id: Optional[str] = None,
    ) -> Optional[str]:
        try:
            drummer_slug = (drummer_slug or "").strip()
            outcome = (outcome or "").strip() or "unknown"
            if not drummer_slug:
                return None

            run_id = (run_id or str(uuid.uuid4())).strip()
            started_at = started_at or datetime.utcnow()
            completed_iso = completed_at.isoformat() if completed_at else None

            conn = self._get_connection()
            cursor = conn.cursor()

            def _do_write() -> str:
                cursor.execute(
                    """
                    INSERT INTO calibration_runs (
                        run_id, drummer_slug, started_at, completed_at, outcome,
                        note_count, fills_per_minute, within_tolerance_count,
                        total_compared, delta_summary, metadata_json, metrics_json,
                        comparison_json, log_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        drummer_slug = excluded.drummer_slug,
                        started_at = excluded.started_at,
                        completed_at = excluded.completed_at,
                        outcome = excluded.outcome,
                        note_count = excluded.note_count,
                        fills_per_minute = excluded.fills_per_minute,
                        within_tolerance_count = excluded.within_tolerance_count,
                        total_compared = excluded.total_compared,
                        delta_summary = excluded.delta_summary,
                        metadata_json = excluded.metadata_json,
                        metrics_json = excluded.metrics_json,
                        comparison_json = excluded.comparison_json,
                        log_path = excluded.log_path
                    """,
                    (
                        run_id,
                        drummer_slug,
                        started_at.isoformat(),
                        completed_iso,
                        outcome,
                        note_count,
                        fills_per_minute,
                        within_tolerance_count,
                        total_compared,
                        delta_summary,
                        self._json_dumps(metadata),
                        self._json_dumps(metrics),
                        self._json_dumps(comparison),
                        log_path,
                    ),
                )
                conn.commit()
                return run_id

            result = self._with_write_lock_retry(_do_write)
            self.data_changed.emit("calibration_runs", "upsert")
            return str(result)
        except sqlite3.OperationalError as e:
            logger.warning(f"calibration_runs table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error logging calibration run for {drummer_slug}: {str(e)}")
            self.database_error.emit(f"Error logging calibration run: {str(e)}")
            return None

    def get_calibration_runs(
        self,
        *,
        drummer_slug: str,
        limit: int = 25,
        include_metrics: bool = True,
    ) -> List[CalibrationRun]:
        runs: List[CalibrationRun] = []
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return runs

            conn = self._get_connection()
            cursor = conn.cursor()

            select_columns = [
                "run_id",
                "drummer_slug",
                "started_at",
                "completed_at",
                "outcome",
                "note_count",
                "fills_per_minute",
                "within_tolerance_count",
                "total_compared",
                "delta_summary",
                "log_path",
            ]
            if include_metrics:
                select_columns.extend(["metadata_json", "metrics_json", "comparison_json"])

            cursor.execute(
                f"""
                SELECT {', '.join(select_columns)}
                FROM calibration_runs
                WHERE drummer_slug = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (drummer_slug, max(1, int(limit))),
            )
            rows = cursor.fetchall() or []

            for row in rows:
                run = self._row_to_calibration_run(row)
                if run:
                    runs.append(run)

            return runs
        except sqlite3.OperationalError as e:
            logger.warning(f"calibration_runs table not available: {e}")
            return runs
        except Exception as e:
            logger.error(f"Error getting calibration runs for {drummer_slug}: {str(e)}")
            self.database_error.emit(f"Error getting calibration runs: {str(e)}")
            return runs

    def get_latest_calibration_run(self, *, drummer_slug: str) -> Optional[CalibrationRun]:
        runs = self.get_calibration_runs(drummer_slug=drummer_slug, limit=1)
        return runs[0] if runs else None

    def log_calibration_feedback(
        self,
        *,
        drummer_slug: str,
        rating: int,
        comment: Optional[str] = None,
        author: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        submitted_at: Optional[datetime] = None,
        feedback_id: Optional[str] = None,
    ) -> Optional[str]:
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return None

            try:
                rating_value = int(rating)
            except Exception:
                rating_value = 0
            rating_value = max(min(rating_value, 10), 0)

            feedback_id = (feedback_id or str(uuid.uuid4())).strip()
            submitted_at = submitted_at or datetime.utcnow()
            metadata_json = self._json_dumps(metadata) if metadata else None

            conn = self._get_connection()
            cursor = conn.cursor()

            def _do_write() -> str:
                cursor.execute(
                    """
                    INSERT INTO calibration_feedback (
                        feedback_id, drummer_slug, rating, comment, author,
                        submitted_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(feedback_id) DO UPDATE SET
                        drummer_slug = excluded.drummer_slug,
                        rating = excluded.rating,
                        comment = excluded.comment,
                        author = excluded.author,
                        submitted_at = excluded.submitted_at,
                        metadata_json = excluded.metadata_json
                    """,
                    (
                        feedback_id,
                        drummer_slug,
                        rating_value,
                        comment,
                        author,
                        submitted_at.isoformat(),
                        metadata_json,
                    ),
                )
                conn.commit()
                return feedback_id

            result = self._with_write_lock_retry(_do_write)
            self.data_changed.emit("calibration_feedback", "upsert")
            return str(result)
        except sqlite3.OperationalError as e:
            logger.warning(f"calibration_feedback table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error logging calibration feedback for {drummer_slug}: {str(e)}")
            self.database_error.emit(f"Error logging calibration feedback: {str(e)}")
            return None

    def get_calibration_feedback(
        self,
        *,
        drummer_slug: str,
        limit: int = 50,
    ) -> List[CalibrationFeedback]:
        feedback: List[CalibrationFeedback] = []
        try:
            drummer_slug = (drummer_slug or "").strip()
            if not drummer_slug:
                return feedback

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT feedback_id, drummer_slug, rating, comment, author,
                       submitted_at, metadata_json
                FROM calibration_feedback
                WHERE drummer_slug = ?
                ORDER BY submitted_at DESC
                LIMIT ?
                """,
                (drummer_slug, max(1, int(limit))),
            )
            for row in cursor.fetchall() or []:
                item = self._row_to_calibration_feedback(row)
                if item:
                    feedback.append(item)

            return feedback
        except sqlite3.OperationalError as e:
            logger.warning(f"calibration_feedback table not available: {e}")
            return feedback
        except Exception as e:
            logger.error(f"Error getting calibration feedback for {drummer_slug}: {str(e)}")
            self.database_error.emit(f"Error getting calibration feedback: {str(e)}")
            return feedback

    def get_latest_calibration_feedback(self, *, drummer_slug: str) -> Optional[CalibrationFeedback]:
        items = self.get_calibration_feedback(drummer_slug=drummer_slug, limit=1)
        return items[0] if items else None

    def add_drummer(self, name: str, description: str = "") -> Optional[str]:
        """
        Add a new drummer to the database.
        
        Args:
            name: The name of the drummer
            description: Optional description
            
        Returns:
            str or None: The ID of the new drummer or None if failed
        """
        try:
            drummer_id = str(uuid.uuid4())
            now = datetime.now().isoformat()

            conn = self._get_connection()
            cursor = conn.cursor()

            cols = self._table_columns("drummers")
            if "name" in cols:
                cursor.execute(
                    'INSERT INTO drummers (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
                    (drummer_id, name, description, now, now)
                )
            elif "display_name" in cols and "drummer_id" in cols:
                cursor.execute(
                    'INSERT INTO drummers (drummer_id, display_name) VALUES (?, ?)',
                    (drummer_id, name)
                )
            else:
                raise RuntimeError("Unsupported drummers table schema")
            conn.commit()
            
            self.data_changed.emit('drummers', 'insert')
            logger.info(f"Added new drummer: {name} (ID: {drummer_id})")
            return drummer_id
            
        except Exception as e:
            logger.error(f"Error adding drummer {name}: {str(e)}")
            self.database_error.emit(f"Error adding drummer: {str(e)}")
            return None

    def update_drummer(self, drummer_id: str, data: Dict) -> bool:
        """
        Update a drummer's information.
        
        Args:
            drummer_id: The ID of the drummer to update
            data: Dictionary with fields to update
            
        Returns:
            bool: True if successful
        """
        try:
            cols = self._table_columns("drummers")
            if "name" in cols:
                valid_fields = {'name', 'description'}
            else:
                valid_fields = {'display_name', 'real_name', 'tagline', 'bio', 'youtube_channel', 'photo_url', 'source'}
            update_data = {k: v for k, v in data.items() if k in valid_fields}
            
            if not update_data:
                logger.warning("No valid fields to update for drummer")
                return False
                
            # Add updated_at timestamp
            if "updated_at" in cols:
                update_data['updated_at'] = datetime.now().isoformat()
            
            # Build the SQL query
            field_str = ', '.join([f"{field} = ?" for field in update_data.keys()])
            values = list(update_data.values()) + [drummer_id]
            
            conn = self._get_connection()
            cursor = conn.cursor()
            if "drummer_id" in cols:
                cursor.execute(f"UPDATE drummers SET {field_str} WHERE drummer_id = ?", values)
            else:
                cursor.execute(f"UPDATE drummers SET {field_str} WHERE id = ?", values)
            conn.commit()
            
            self.data_changed.emit('drummers', 'update')
            logger.info(f"Updated drummer ID: {drummer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating drummer {drummer_id}: {str(e)}")
            self.database_error.emit(f"Error updating drummer: {str(e)}")
            return False

    def delete_drummer(self, drummer_id: str) -> bool:
        """
        Delete a drummer from the database.
        
        Args:
            drummer_id: The ID of the drummer to delete
            
        Returns:
            bool: True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cols = self._table_columns("drummers")
            if "drummer_id" in cols:
                cursor.execute('DELETE FROM drummers WHERE drummer_id = ?', (drummer_id,))
            else:
                cursor.execute('DELETE FROM drummers WHERE id = ?', (drummer_id,))
            conn.commit()
            
            self.data_changed.emit('drummers', 'delete')
            logger.info(f"Deleted drummer ID: {drummer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting drummer {drummer_id}: {str(e)}")
            self.database_error.emit(f"Error deleting drummer: {str(e)}")
            return False

    # ---- Drummer personas (admin DB integration) ---------------------

    def get_drummer_persona(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """Load a single drummer persona by ID from drummer_personas.

        Returns a dict with keys:
        - persona_id
        - display_name
        - archetypes (list[str])
        - style (dict of aggregated style metrics)
        or None if not found or table missing.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT persona_id, display_name, archetypes_json, style_json
                FROM drummer_personas
                WHERE persona_id = ?
                """,
                (persona_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            archetypes = json.loads(row["archetypes_json"]) if row["archetypes_json"] else []
            style = json.loads(row["style_json"]) if row["style_json"] else {}
            return {
                "persona_id": row["persona_id"],
                "display_name": row["display_name"],
                "archetypes": archetypes,
                "style": style,
            }
        except sqlite3.OperationalError as e:
            # Likely table does not exist in this DB; fail soft.
            logger.warning(f"drummer_personas table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting drummer persona {persona_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer persona: {str(e)}")
            return None

    def get_all_drummer_personas(self) -> List[Dict[str, Any]]:
        """Return all drummer personas as a list of dicts.

        See get_drummer_persona for the dict shape.
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT persona_id, display_name, archetypes_json, style_json
                FROM drummer_personas
                ORDER BY display_name
                """
            )
            rows = cursor.fetchall()
            personas: List[Dict[str, Any]] = []
            for row in rows:
                archetypes = json.loads(row["archetypes_json"]) if row["archetypes_json"] else []
                style = json.loads(row["style_json"]) if row["style_json"] else {}
                personas.append(
                    {
                        "persona_id": row["persona_id"],
                        "display_name": row["display_name"],
                        "archetypes": archetypes,
                        "style": style,
                    }
                )
            return personas
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_personas table not available: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting drummer personas: {str(e)}")
            self.database_error.emit(f"Error getting drummer personas: {str(e)}")
            return []

    # ---- Drummer category mappings (admin-only) ----------------------

    def get_drummer_category_mapping(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Return mapping for a public drummer category, if defined.

        Shape:
          {
            "category_id": str,
            "display_name": str,
            "primary_persona_id": str,
            "backup_persona_ids": [str],
            "default_humanize": float | None,
            "default_swing": float | None,
            "default_chorus_ride_pref": float | None,
          }
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''SELECT category_id, display_name, primary_persona_id,
                          backup_persona_ids_json, default_humanize,
                          default_swing, default_chorus_ride_pref
                   FROM drummer_category_mappings
                   WHERE category_id = ?''',
                (category_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            backups = []
            if row[3]:
                try:
                    backups = json.loads(row[3])
                except Exception:
                    backups = []
            return {
                "category_id": row[0],
                "display_name": row[1],
                "primary_persona_id": row[2],
                "backup_persona_ids": backups,
                "default_humanize": row[4],
                "default_swing": row[5],
                "default_chorus_ride_pref": row[6],
            }
        except sqlite3.OperationalError as e:
            logger.warning(f"drummer_category_mappings table not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting drummer category mapping {category_id}: {str(e)}")
            self.database_error.emit(f"Error getting drummer category mapping: {str(e)}")
            return None

    def upsert_drummer_category_mapping(
        self,
        category_id: str,
        display_name: str,
        primary_persona_id: str,
        backup_persona_ids: Optional[List[str]] = None,
        default_humanize: Optional[float] = None,
        default_swing: Optional[float] = None,
        default_chorus_ride_pref: Optional[float] = None,
    ) -> bool:
        """Insert or update a mapping from category_id -> persona + defaults."""
        try:
            now = datetime.now().isoformat()
            backups_json = json.dumps(backup_persona_ids or [])

            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO drummer_category_mappings (
                       category_id, display_name, primary_persona_id,
                       backup_persona_ids_json, default_humanize,
                       default_swing, default_chorus_ride_pref,
                       created_at, updated_at
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(category_id) DO UPDATE SET
                       display_name = excluded.display_name,
                       primary_persona_id = excluded.primary_persona_id,
                       backup_persona_ids_json = excluded.backup_persona_ids_json,
                       default_humanize = excluded.default_humanize,
                       default_swing = excluded.default_swing,
                       default_chorus_ride_pref = excluded.default_chorus_ride_pref,
                       updated_at = excluded.updated_at
                ''',
                (
                    category_id,
                    display_name,
                    primary_persona_id,
                    backups_json,
                    default_humanize,
                    default_swing,
                    default_chorus_ride_pref,
                    now,
                    now,
                ),
            )
            conn.commit()
            logger.info(f"Upserted drummer_category_mapping for {category_id} -> {primary_persona_id}")
            return True
        except Exception as e:
            logger.error(f"Error upserting drummer category mapping for {category_id}: {str(e)}")
            self.database_error.emit(f"Error upserting drummer category mapping: {str(e)}")
            return False

    # CRUD operations for songs
    def get_songs(self, drummer_id: Optional[str] = None) -> List[Dict]:
        """
        Get songs from the database, optionally filtered by drummer.
        
        Args:
            drummer_id: Optional drummer ID to filter by
            
        Returns:
            List[Dict]: List of song records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if drummer_id:
                cursor.execute('SELECT * FROM songs WHERE drummer_id = ? ORDER BY title', (drummer_id,))
            else:
                cursor.execute('SELECT * FROM songs ORDER BY title')
                
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting songs: {str(e)}")
            self.database_error.emit(f"Error getting songs: {str(e)}")
            return []

    def get_song(self, song_id: str) -> Optional[Dict]:
        """
        Get a song by ID.
        
        Args:
            song_id: The ID of the song
            
        Returns:
            Dict or None: Song record or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM songs WHERE id = ?', (song_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting song {song_id}: {str(e)}")
            self.database_error.emit(f"Error getting song: {str(e)}")
            return None

    def add_song(self, title: str, file_path: str = None, drummer_id: str = None, metadata: Dict = None) -> Optional[str]:
        """
        Add a new song to the database.
        
        Args:
            title: The title of the song
            file_path: Path to the audio file
            drummer_id: Optional ID of the associated drummer
            metadata: Optional additional metadata (artist, album, etc.)
            
        Returns:
            str or None: The ID of the new song or None if failed
        """
        try:
            song_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Extract metadata if provided
            if metadata is None:
                metadata = {}
                
            artist = metadata.get('artist', '')
            album = metadata.get('album', '')
            year = metadata.get('year', None)
            genre = metadata.get('genre', '')
            duration = metadata.get('duration', None)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO songs 
                   (id, title, artist, album, year, genre, duration, file_path, drummer_id, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (song_id, title, artist, album, year, genre, duration, file_path, drummer_id, now, now)
            )
            conn.commit()
            
            self.data_changed.emit('songs', 'insert')
            logger.info(f"Added new song: {title} (ID: {song_id})")
            return song_id
            
        except Exception as e:
            logger.error(f"Error adding song {title}: {str(e)}")
            self.database_error.emit(f"Error adding song: {str(e)}")
            return None

    # CRUD operations for drum beats
    def get_drum_beats(self, drummer_id: Optional[str] = None, song_id: Optional[str] = None) -> List[Dict]:
        """
        Get drum beats from the database, optionally filtered by drummer or song.
        
        Args:
            drummer_id: Optional drummer ID to filter by
            song_id: Optional song ID to filter by
            
        Returns:
            List[Dict]: List of drum beat records
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM drum_beats'
            params = []
            
            if drummer_id and song_id:
                query += ' WHERE drummer_id = ? AND song_id = ?'
                params = [drummer_id, song_id]
            elif drummer_id:
                query += ' WHERE drummer_id = ?'
                params = [drummer_id]
            elif song_id:
                query += ' WHERE song_id = ?'
                params = [song_id]
                
            cols = self._table_columns("drum_beats")
            query += ' ORDER BY name' if 'name' in cols else ' ORDER BY id'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            if results:
                return results

            # Fallback: if drum_beats table is empty, show beats from the local DrumBeats folder
            try:
                project_root = Path(__file__).resolve().parents[2]
                beats_dir = project_root / "DrumBeats"
                if beats_dir.exists() and beats_dir.is_dir():
                    synthetic: List[Dict[str, Any]] = []
                    for wav in sorted(beats_dir.glob("*.wav")):
                        synthetic.append({
                            "id": wav.stem,
                            "name": wav.stem.replace("_", " "),
                            "description": "(filesystem)",
                            "file_path": str(wav),
                            "song_id": None,
                            "drummer_id": None,
                            "bpm": None,
                            "time_signature": None,
                            "complexity": None,
                            "energy": None,
                        })
                    return synthetic
            except Exception:
                pass

            return []
        except Exception as e:
            logger.error(f"Error getting drum beats: {str(e)}")
            self.database_error.emit(f"Error getting drum beats: {str(e)}")
            return []

    def get_drum_beat(self, beat_id: str) -> Optional[Dict]:
        """
        Get a drum beat by ID.
        
        Args:
            beat_id: The ID of the drum beat
            
        Returns:
            Dict or None: Drum beat record or None if not found
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM drum_beats WHERE id = ?', (beat_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
            
        except Exception as e:
            logger.error(f"Error getting drum beat {beat_id}: {str(e)}")
            self.database_error.emit(f"Error getting drum beat: {str(e)}")
            return None

    def add_drum_beat(self, name: str, file_path: str = None, drummer_id: str = None, song_id: str = None, metadata: Dict = None) -> Optional[str]:
        """
        Add a new drum beat to the database.
        
        Args:
            name: The name of the drum beat
            file_path: Path to the audio file
            drummer_id: Optional ID of the associated drummer
            song_id: Optional ID of the associated song
            metadata: Optional additional metadata (bpm, complexity, etc.)
            
        Returns:
            str or None: The ID of the new drum beat or None if failed
        """
        try:
            beat_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Extract metadata if provided
            if metadata is None:
                metadata = {}
                
            description = metadata.get('description', '')
            bpm = metadata.get('bpm', None)
            time_signature = metadata.get('time_signature', '')
            complexity = metadata.get('complexity', None)
            energy = metadata.get('energy', None)
            
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO drum_beats 
                   (id, name, description, file_path, song_id, drummer_id, bpm, time_signature, complexity, energy, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (beat_id, name, description, file_path, song_id, drummer_id, bpm, time_signature, complexity, energy, now, now)
            )
            conn.commit()
            
            self.data_changed.emit('drum_beats', 'insert')
            logger.info(f"Added new drum beat: {name} (ID: {beat_id})")
            return beat_id
            
        except Exception as e:
            logger.error(f"Error adding drum beat {name}: {str(e)}")
            self.database_error.emit(f"Error adding drum beat: {str(e)}")
            return None
            
    # Function to get the singleton instance
    @staticmethod
    def get_database():
        """Get the singleton database instance"""
        return CentralDatabaseService.get_instance()

# Singleton access function
def get_database_service() -> CentralDatabaseService:
    """Get the singleton database service instance"""
    return CentralDatabaseService.get_instance()
