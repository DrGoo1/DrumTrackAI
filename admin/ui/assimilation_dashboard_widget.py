from __future__ import annotations

import os
import logging
from typing import Dict, List, Any, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QInputDialog,
)

from admin.services.central_database_service import CentralDatabaseService

logger = logging.getLogger(__name__)


class AssimilationDashboardWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.container = None

        self.db = CentralDatabaseService.get_instance()

        self._setup_ui()
        self.refresh_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Drummer Brain Assimilation")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        header.addWidget(title)
        header.addStretch()

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(self.refresh_btn)

        self.ingest_btn = QPushButton("Ingest Processed Stems Folder...")
        self.ingest_btn.clicked.connect(self._on_ingest_processed_stems_folder)
        header.addWidget(self.ingest_btn)

        self.phase2_btn = QPushButton("Run Phase 2 (Hit Events)")
        self.phase2_btn.clicked.connect(self._on_run_phase2)
        header.addWidget(self.phase2_btn)

        self.phase3_btn = QPushButton("Run Phase 3 (Fills + Techniques)")
        self.phase3_btn.clicked.connect(self._on_run_phase3)
        header.addWidget(self.phase3_btn)

        self.phase4_btn = QPushButton("Run Phase 4 (Microtiming + Dynamics)")
        self.phase4_btn.clicked.connect(self._on_run_phase4)
        header.addWidget(self.phase4_btn)

        self.phase5_btn = QPushButton("Run Phase 5 (Drummer Rollup)")
        self.phase5_btn.clicked.connect(self._on_run_phase5)
        header.addWidget(self.phase5_btn)

        self.phase6_btn = QPushButton("Run Phase 6 (Persona + Preset + Export)")
        self.phase6_btn.clicked.connect(self._on_run_phase6)
        header.addWidget(self.phase6_btn)

        layout.addLayout(header)

        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            [
                "Drummer",
                "Songs",
                "Artifacts",
                "Stems",
                "Hit Events",
                "Fills",
                "Techniques",
                "Timing Std (ms)",
                "Pocket",
                "Humanness",
                "Assimilation %",
            ]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.table.setStyleSheet(
            "QTableWidget {"
            " background-color: #f8f9fb;"
            " alternate-background-color: #eef2f9;"
            " color: #1c1f26;"
            " font-size: 13px;"
            " gridline-color: #d8dde7;"
            " }"
            "QTableWidget::item { padding: 6px 8px; }"
            "QTableWidget::item:selected { background-color: #2a68ff; color: #ffffff; }"
            "QHeaderView::section {"
            " background-color: #f0f2f7;"
            " color: #1c1f26;"
            " font-weight: 600;"
            " padding: 4px 6px;"
            " border: 0px;"
            " border-right: 1px solid #d0d6e2;"
            " }"
        )
        layout.addWidget(self.table, 1)

    def _resolve_db_path(self) -> Optional[str]:
        try:
            return getattr(self.db, "_db_path", None)
        except Exception:
            return None

    def _compute_assimilation_score(self, *, songs: int, artifacts: int, stems: int, hit_events: int) -> int:
        try:
            target_songs = 20
            song_score = min(50.0, (float(songs) / float(target_songs)) * 50.0) if target_songs > 0 else 0.0

            richness = 0.0
            if artifacts > 0:
                richness += 10.0
            if stems >= 6:
                richness += 15.0
            elif stems > 0:
                richness += 7.0
            if hit_events > 0:
                richness += 25.0

            total = song_score + richness
            if total < 0:
                total = 0.0
            if total > 100:
                total = 100.0
            return int(total)
        except Exception:
            return 0

    def _compute_assimilation_score_v3(
        self,
        *,
        songs: int,
        artifacts: int,
        stems: int,
        hit_events: int,
        fills: int,
        techniques: int,
        pocket_tightness: Optional[float],
        humanness: Optional[float],
    ) -> int:
        try:
            # Start with v2
            base = self._compute_assimilation_score_v2(
                songs=songs,
                artifacts=artifacts,
                stems=stems,
                hit_events=hit_events,
                fills=fills,
                techniques=techniques,
            )

            bonus = 0.0
            if pocket_tightness is not None:
                bonus += 5.0
                try:
                    bonus += max(0.0, min(1.0, float(pocket_tightness))) * 5.0
                except Exception:
                    pass
            if humanness is not None:
                bonus += 5.0
                try:
                    bonus += max(0.0, min(1.0, float(humanness))) * 5.0
                except Exception:
                    pass

            total = float(base) + bonus
            total = max(0.0, min(100.0, total))
            return int(round(total))
        except Exception:
            return 0

    def _compute_assimilation_score_v2(
        self, *, songs: int, artifacts: int, stems: int, hit_events: int, fills: int, techniques: int
    ) -> int:
        try:
            target_songs = 20
            song_score = min(50.0, (float(songs) / float(target_songs)) * 50.0) if target_songs > 0 else 0.0

            richness = 0.0
            if artifacts > 0:
                richness += 10.0
            if stems >= 6:
                richness += 15.0
            elif stems > 0:
                richness += 7.0
            if hit_events > 0:
                richness += 25.0
            if fills > 0:
                richness += 10.0
            if techniques > 0:
                richness += 10.0

            # Cap richness at 50 to keep total within 0–100
            richness = min(50.0, richness)

            total = song_score + richness
            total = max(0.0, min(100.0, total))
            return int(round(total))
        
        except Exception:
            return 0

    def _progress_style(self, pct: int) -> str:
        pct = int(pct or 0)
        if pct >= 85:
            color = "#2ecc71"
            text_color = "#ffffff"
        elif pct >= 60:
            color = "#f1c40f"
            text_color = "#111111"
        elif pct >= 35:
            color = "#e67e22"
            text_color = "#111111"
        else:
            color = "#e74c3c"
            text_color = "#ffffff"

        return (
            f"QProgressBar {{border: 1px solid #444; border-radius: 4px; text-align: center; height: 18px; color: {text_color};}}"
            f"QProgressBar::chunk {{background-color: {color}; border-radius: 4px;}}"
        )

    def refresh_data(self) -> None:
        try:
            if not getattr(self.db, "_initialized", False):
                self.db.initialize()

            conn = self.db._get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                SELECT
                    COALESCE(d.drummer_id, CAST(spa.drummer_id AS TEXT)) AS drummer_slug,
                    spa.drummer_id AS drummer_fk,
                    COUNT(DISTINCT spa.analysis_id) AS songs_ingested,
                    COALESCE((SELECT COUNT(1) FROM analysis_artifacts aa WHERE aa.drummer_id = spa.drummer_id), 0) AS artifacts,
                    COALESCE((SELECT COUNT(1) FROM stem_artifacts sa WHERE sa.drummer_id = spa.drummer_id), 0) AS stems,
                    COALESCE((SELECT COUNT(1) FROM drum_hit_events he WHERE he.drummer_id = spa.drummer_id), 0) AS hit_events,
                    COALESCE((SELECT COUNT(1) FROM fill_events fe WHERE fe.drummer_id = spa.drummer_id), 0) AS fills,
                    COALESCE((SELECT COUNT(1) FROM technique_events te WHERE te.drummer_id = spa.drummer_id), 0) AS techniques,
                    AVG(spa.groove_micro_timing_variance) AS avg_timing_std_ms,
                    AVG(spa.groove_pocket_tightness) AS avg_pocket,
                    AVG(spa.humanness_score) AS avg_humanness
                FROM song_performance_analysis spa
                LEFT JOIN drummers d ON d.id = spa.drummer_id
                GROUP BY spa.drummer_id
                ORDER BY songs_ingested DESC, spa.drummer_id
                """
            )
            rows = cur.fetchall() or []

            self.table.setRowCount(len(rows))
            for r, row in enumerate(rows):
                drummer_slug = row[0] if row[0] else "unknown"
                songs = int(row[2] or 0)
                artifacts = int(row[3] or 0)
                stems = int(row[4] or 0)
                hit_events = int(row[5] or 0)
                fills = int(row[6] or 0)
                techniques = int(row[7] or 0)

                avg_timing_std_ms = None
                avg_pocket = None
                avg_humanness = None
                try:
                    avg_timing_std_ms = float(row[8]) if row[8] is not None else None
                except Exception:
                    avg_timing_std_ms = None
                try:
                    avg_pocket = float(row[9]) if row[9] is not None else None
                except Exception:
                    avg_pocket = None
                try:
                    avg_humanness = float(row[10]) if row[10] is not None else None
                except Exception:
                    avg_humanness = None

                self.table.setItem(r, 0, QTableWidgetItem(str(drummer_slug)))
                self.table.setItem(r, 1, QTableWidgetItem(str(songs)))
                self.table.setItem(r, 2, QTableWidgetItem(str(artifacts)))
                self.table.setItem(r, 3, QTableWidgetItem(str(stems)))
                self.table.setItem(r, 4, QTableWidgetItem(str(hit_events)))
                self.table.setItem(r, 5, QTableWidgetItem(str(fills)))
                self.table.setItem(r, 6, QTableWidgetItem(str(techniques)))

                self.table.setItem(
                    r,
                    7,
                    QTableWidgetItem("" if avg_timing_std_ms is None else f"{avg_timing_std_ms:.2f}"),
                )
                self.table.setItem(
                    r,
                    8,
                    QTableWidgetItem("" if avg_pocket is None else f"{avg_pocket:.3f}"),
                )
                self.table.setItem(
                    r,
                    9,
                    QTableWidgetItem("" if avg_humanness is None else f"{avg_humanness:.3f}"),
                )

                pct = self._compute_assimilation_score_v3(
                    songs=songs,
                    artifacts=artifacts,
                    stems=stems,
                    hit_events=hit_events,
                    fills=fills,
                    techniques=techniques,
                    pocket_tightness=avg_pocket,
                    humanness=avg_humanness,
                )
                pb = QProgressBar()
                pb.setRange(0, 100)
                pb.setValue(pct)
                pb.setFormat(f"{pct}%")
                pb.setStyleSheet(self._progress_style(pct))
                self.table.setCellWidget(r, 10, pb)

            db_path = self._resolve_db_path() or "(unknown)"
            self.summary_label.setText(f"DB: {db_path}    Drummers tracked: {len(rows)}")

            self.table.resizeColumnsToContents()
            try:
                self.table.horizontalHeader().setStretchLastSection(True)
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Error refreshing assimilation dashboard: {e}")
            QMessageBox.warning(self, "Assimilation", f"Failed to refresh: {e}")

    def _selected_drummer_slug(self) -> str:
        try:
            row = self.table.currentRow()
            if row is not None and int(row) >= 0:
                item = self.table.item(int(row), 0)
                if item is not None:
                    return str(item.text() or "").strip()
        except Exception:
            pass
        return ""

    def _on_run_phase2(self) -> None:
        try:
            slug = self._selected_drummer_slug()
            if not slug:
                slug, ok = QInputDialog.getText(self, "Phase 2", "Drummer slug (folder name):")
                slug = str(slug or "").strip()
                if not ok or not slug:
                    return

            if not getattr(self.db, "_initialized", False):
                self.db.initialize()

            self.phase2_btn.setEnabled(False)
            try:
                result = self.db.run_phase2_hit_event_extraction_for_drummer(drummer_slug=slug)
            finally:
                self.phase2_btn.setEnabled(True)

            analyses = int((result or {}).get("analyses") or 0)
            events = int((result or {}).get("events") or 0)

            # Enrichment report (so reruns show visible differences)
            enrich_lines: List[str] = []
            try:
                conn = self.db._get_connection()
                cur = conn.cursor()
                cur.execute(
                    """
                    SELECT id FROM drummers WHERE drummer_id = ?
                    LIMIT 1
                    """,
                    (slug,),
                )
                row = cur.fetchone()
                drummer_fk = row[0] if row else None
                if drummer_fk is not None:
                    cur.execute(
                        """
                        SELECT
                            COUNT(1) AS total,
                            SUM(CASE WHEN velocity_est IS NOT NULL THEN 1 ELSE 0 END) AS with_velocity,
                            SUM(CASE WHEN onset_strength IS NOT NULL THEN 1 ELSE 0 END) AS with_strength,
                            SUM(CASE WHEN timing_offset_ms IS NOT NULL THEN 1 ELSE 0 END) AS with_offset
                        FROM drum_hit_events
                        WHERE drummer_id = ?
                        """,
                        (drummer_fk,),
                    )
                    stats = cur.fetchone()
                    if stats:
                        total = int(stats[0] or 0)
                        with_velocity = int(stats[1] or 0)
                        with_strength = int(stats[2] or 0)
                        with_offset = int(stats[3] or 0)
                        enrich_lines.append(f"Total events in DB: {total}")
                        if total > 0:
                            enrich_lines.append(f"velocity_est populated: {with_velocity} ({int((with_velocity/total)*100)}%)")
                            enrich_lines.append(f"onset_strength populated: {with_strength} ({int((with_strength/total)*100)}%)")
                            enrich_lines.append(f"timing_offset_ms populated: {with_offset} ({int((with_offset/total)*100)}%)")

                    cur.execute(
                        """
                        SELECT instrument, COUNT(1) AS n
                        FROM drum_hit_events
                        WHERE drummer_id = ?
                        GROUP BY instrument
                        ORDER BY n DESC
                        LIMIT 10
                        """,
                        (drummer_fk,),
                    )
                    top = cur.fetchall() or []
                    if top:
                        enrich_lines.append("Top instruments:")
                        for inst, n in top:
                            enrich_lines.append(f"  {inst}: {int(n or 0)}")
            except Exception:
                enrich_lines = []

            msg = f"Processed {analyses} analysis(es). Inserted {events} hit event(s)."
            if enrich_lines:
                msg = msg + "\n\n" + "\n".join(enrich_lines)
            QMessageBox.information(self, "Phase 2", msg)
            self.refresh_data()

        except Exception as e:
            logger.error(f"Error running phase 2: {e}")
            QMessageBox.warning(self, "Phase 2", f"Failed: {e}")

    def _on_ingest_processed_stems_folder(self) -> None:
        try:
            base_dir = QFileDialog.getExistingDirectory(self, "Select processed_stems/<drummer_id> folder")
            if not base_dir:
                return

            drummer_id = os.path.basename(base_dir).strip()
            if not drummer_id:
                QMessageBox.warning(self, "Assimilation", "Could not infer drummer_id from folder name")
                return

            if not getattr(self.db, "_initialized", False):
                self.db.initialize()

            ingested = 0
            skipped = 0
            skipped_details: List[str] = []
            for name in sorted(os.listdir(base_dir)):
                song_folder = os.path.join(base_dir, name)
                if not os.path.isdir(song_folder):
                    continue
                if not os.path.exists(os.path.join(song_folder, "drum_analysis.json")):
                    skipped += 1
                    skipped_details.append(f"{name}: missing drum_analysis.json")
                    continue
                aid = self.db.ingest_processed_stems_song_folder(drummer_id=drummer_id, song_folder=song_folder)
                if aid:
                    ingested += 1
                else:
                    skipped += 1
                    err = ""
                    try:
                        err = self.db.get_last_ingest_error()
                    except Exception:
                        err = ""
                    err = (err or "").strip()
                    if err:
                        skipped_details.append(f"{name}: {err}")
                    else:
                        skipped_details.append(f"{name}: unknown ingest failure")

            msg = f"Ingested {ingested} song folder(s). Skipped {skipped}."
            if skipped_details:
                msg = msg + "\n\nSkipped details:\n" + "\n".join(skipped_details[:50])
                if len(skipped_details) > 50:
                    msg = msg + f"\n... and {len(skipped_details) - 50} more"
            QMessageBox.information(self, "Assimilation", msg)
            self.refresh_data()

        except Exception as e:
            logger.error(f"Error ingesting processed stems folder: {e}")
            QMessageBox.warning(self, "Assimilation", f"Failed to ingest: {e}")

    def _on_run_phase3(self) -> None:
        try:
            slug = self._selected_drummer_slug()
            if not slug:
                slug, ok = QInputDialog.getText(self, "Phase 3", "Drummer slug (folder name):")
                slug = str(slug or "").strip()
                if not ok or not slug:
                    return

            if not getattr(self.db, "_initialized", False):
                self.db.initialize()

            self.phase3_btn.setEnabled(False)
            try:
                result = self.db.run_phase3_fills_and_techniques_for_drummer(drummer_slug=slug)
            finally:
                self.phase3_btn.setEnabled(True)

            analyses = int((result or {}).get("analyses") or 0)
            fills = int((result or {}).get("fills") or 0)
            techniques = int((result or {}).get("techniques") or 0)
            avg_fpm = float((result or {}).get("avg_fills_per_min") or 0.0)
            breakdown = (result or {}).get("technique_breakdown") or {}

            lines: List[str] = []
            if avg_fpm > 0:
                lines.append(f"Avg fills/min: {avg_fpm:.2f}")
            if isinstance(breakdown, dict) and breakdown:
                parts: List[str] = []
                for k in sorted(breakdown.keys()):
                    try:
                        parts.append(f"{k}={int(breakdown.get(k) or 0)}")
                    except Exception:
                        continue
                if parts:
                    lines.append("Techniques: " + ", ".join(parts))

            msg = f"Processed {analyses} analysis(es). Inserted {fills} fill(s) and {techniques} technique event(s)."
            if lines:
                msg = msg + "\n\n" + "\n".join(lines)
            QMessageBox.information(
                self,
                "Phase 3",
                msg,
            )
            self.refresh_data()

        except Exception as e:
            logger.error(f"Error running phase 3: {e}")
            QMessageBox.warning(self, "Phase 3", f"Failed: {e}")

    def _on_run_phase4(self) -> None:
        try:
            slug = self._selected_drummer_slug()
            if not slug:
                slug, ok = QInputDialog.getText(self, "Phase 4", "Drummer slug (folder name):")
                slug = str(slug or "").strip()
                if not ok or not slug:
                    return

            if not getattr(self.db, "_initialized", False):
                self.db.initialize()

            self.phase4_btn.setEnabled(False)
            try:
                result = self.db.run_phase4_microtiming_and_dynamics_for_drummer(drummer_slug=slug)
            finally:
                self.phase4_btn.setEnabled(True)

            analyses = int((result or {}).get("analyses") or 0)
            updated = int((result or {}).get("updated") or 0)
            avg_std = (result or {}).get("avg_timing_std_ms")
            avg_pocket = (result or {}).get("avg_pocket_tightness")
            avg_human = (result or {}).get("avg_humanness_score")

            lines: List[str] = []
            try:
                if avg_std is not None:
                    lines.append(f"Avg timing std (ms): {float(avg_std):.2f}")
            except Exception:
                pass
            try:
                if avg_pocket is not None:
                    lines.append(f"Avg pocket tightness: {float(avg_pocket):.3f}")
            except Exception:
                pass
            try:
                if avg_human is not None:
                    lines.append(f"Avg humanness: {float(avg_human):.3f}")
            except Exception:
                pass

            msg = f"Processed {analyses} analysis(es). Updated {updated} analysis row(s)."
            if lines:
                msg = msg + "\n\n" + "\n".join(lines)
            QMessageBox.information(self, "Phase 4", msg)
            self.refresh_data()

        except Exception as e:
            logger.error(f"Error running phase 4: {e}")
            QMessageBox.warning(self, "Phase 4", f"Failed: {e}")

    def _on_run_phase5(self) -> None:
        try:
            slug = self._selected_drummer_slug()
            if not slug:
                slug, ok = QInputDialog.getText(self, "Phase 5", "Drummer slug (folder name):")
                slug = str(slug or "").strip()
                if not ok or not slug:
                    return

            if not getattr(self.db, "_initialized", False):
                self.db.initialize()

            self.phase5_btn.setEnabled(False)
            try:
                result = self.db.run_phase5_profile_rollup_for_drummer(drummer_slug=slug)
            finally:
                self.phase5_btn.setEnabled(True)

            saved = bool((result or {}).get("saved"))
            rollup = (result or {}).get("rollup") or {}

            songs = int(rollup.get("songs") or 0)
            hits = int(rollup.get("hits") or 0)
            fills = int(rollup.get("fills") or 0)
            fpm = rollup.get("fills_per_min")
            tech = int(rollup.get("techniques") or 0)
            timing_std = rollup.get("timing_std_ms")
            pocket = rollup.get("pocket_tightness")
            human = rollup.get("humanness")

            lines: List[str] = []
            lines.append(f"Saved: {saved}")
            lines.append(f"Songs: {songs}    Hits: {hits}")
            if fpm is not None:
                try:
                    lines.append(f"Fills: {fills} ({float(fpm):.2f}/min)    Techniques: {tech}")
                except Exception:
                    lines.append(f"Fills: {fills}    Techniques: {tech}")
            else:
                lines.append(f"Fills: {fills}    Techniques: {tech}")

            try:
                if timing_std is not None:
                    lines.append(f"Timing std (ms): {float(timing_std):.2f}")
            except Exception:
                pass
            try:
                if pocket is not None:
                    lines.append(f"Pocket: {float(pocket):.3f}")
            except Exception:
                pass
            try:
                if human is not None:
                    lines.append(f"Humanness: {float(human):.3f}")
            except Exception:
                pass

            QMessageBox.information(self, "Phase 5", "\n".join(lines))
            self.refresh_data()

        except Exception as e:
            logger.error(f"Error running phase 5: {e}")
            QMessageBox.warning(self, "Phase 5", f"Failed: {e}")

    def _on_run_phase6(self) -> None:
        try:
            slug = self._selected_drummer_slug()
            if not slug:
                slug, ok = QInputDialog.getText(self, "Phase 6", "Drummer slug (folder name):")
                slug = str(slug or "").strip()
                if not ok or not slug:
                    return

            if not getattr(self.db, "_initialized", False):
                self.db.initialize()

            self.phase6_btn.setEnabled(False)
            try:
                result = self.db.run_phase6_persona_preset_export_for_drummer(drummer_slug=slug)
            finally:
                self.phase6_btn.setEnabled(True)

            persona = (result or {}).get("persona") or {}
            label = str(persona.get("label") or "")
            conf = persona.get("confidence")
            preset_saved = bool((result or {}).get("preset_saved"))
            preset_id = (result or {}).get("preset_id")
            saved_rollup = bool((result or {}).get("saved_rollup"))
            export_path = str((result or {}).get("export_path") or "")

            lines: List[str] = []
            lines.append(f"Saved rollup: {saved_rollup}")
            if label:
                if conf is not None:
                    try:
                        lines.append(f"Persona: {label} (conf {float(conf):.2f})")
                    except Exception:
                        lines.append(f"Persona: {label}")
                else:
                    lines.append(f"Persona: {label}")
            else:
                lines.append("Persona: (none)")

            lines.append(f"Preset saved: {preset_saved}")
            if preset_id:
                lines.append(f"Preset ID: {preset_id}")
            if export_path:
                lines.append(f"Export: {export_path}")

            QMessageBox.information(self, "Phase 6", "\n".join(lines))
            self.refresh_data()

        except Exception as e:
            logger.error(f"Error running phase 6: {e}")
            QMessageBox.warning(self, "Phase 6", f"Failed: {e}")
