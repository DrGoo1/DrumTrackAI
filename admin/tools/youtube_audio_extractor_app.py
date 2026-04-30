import os
import re
import sys
import threading
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QHeaderView,
    QDialog,
    QDialogButtonBox,
    QVBoxLayout,
    QWidget,
)

try:
    from admin.services.youtube_service import YouTubeService
except Exception:
    from services.youtube_service import YouTubeService


def _sanitize_folder_name(name: str) -> str:
    n = str(name or "").strip()
    n = re.sub(r"[<>:\\/*?\"|]", "_", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n or "Unknown"


def _sanitize_filename(name: str) -> str:
    n = str(name or "").strip()
    n = re.sub(r"[<>:\\/*?\"|]", "_", n)
    n = re.sub(r"\s+", " ", n).strip()
    n = n.replace(" ", "_")
    return n or "audio"


DRUMMERS = [
    "John Bonham",
    "Neil Peart",
    "Keith Moon",
    "Buddy Rich",
    "Gene Krupa",
    "Billy Cobham",
    "Tony Williams",
    "Elvin Jones",
    "Dave Lombardo",
    "Bill Bruford",
    "Steve Gadd",
    "Vinnie Colaiuta",
    "Stewart Copeland",
    "Phil Collins",
    "Charlie Watts",
    "Ringo Starr",
    "Ginger Baker",
    "Art Blakey",
    "Max Roach",
    "Mike Portnoy",
    "Danny Carey",
    "Carter Beauford",
    "Questlove",
    "Travis Barker",
    "Chad Smith",
    "Taylor Hawkins",
    "Lars Ulrich",
    "Dave Grohl",
    "Terry Bozzio",
    "Simon Phillips",
]


class BulkPasteDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Paste URLs")
        self.setMinimumSize(700, 400)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Paste URLs / IDs (one per line):"))
        self.edit = QPlainTextEdit()
        layout.addWidget(self.edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_lines(self) -> List[str]:
        return [ln.strip() for ln in (self.edit.toPlainText() or "").splitlines() if ln.strip()]


class YouTubeAudioExtractorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Audio Extractor")
        self.setMinimumSize(980, 650)

        self._service = YouTubeService()
        self._active_thread: Optional[threading.Thread] = None
        self._active_dl_thread = None
        self._queue: List[Tuple[int, str, str]] = []
        self._running = False
        self._total_jobs = 0

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        form = QGridLayout()
        form.addWidget(QLabel("Output root:"), 0, 0)
        self.output_root_edit = QLineEdit(r"C:\Users\dagol\Downloads\files")
        self.output_root_btn = QPushButton("Browse")
        self.output_root_btn.clicked.connect(self._browse_output_root)
        form.addWidget(self.output_root_edit, 0, 1)
        form.addWidget(self.output_root_btn, 0, 2)
        layout.addLayout(form)

        row_actions = QHBoxLayout()
        self.add_row_btn = QPushButton("Add Row")
        self.bulk_paste_btn = QPushButton("Bulk Paste")
        self.clear_btn = QPushButton("Clear")
        self.add_row_btn.clicked.connect(self._add_row)
        self.bulk_paste_btn.clicked.connect(self._bulk_paste)
        self.clear_btn.clicked.connect(self._clear_rows)
        row_actions.addWidget(self.add_row_btn)
        row_actions.addWidget(self.bulk_paste_btn)
        row_actions.addWidget(self.clear_btn)
        row_actions.addStretch()
        layout.addLayout(row_actions)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Drummer", "YouTube URL / ID", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        actions = QHBoxLayout()
        self.start_btn = QPushButton("Start Batch Download")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._on_start)
        self.cancel_btn.clicked.connect(self._on_cancel)
        actions.addWidget(self.start_btn)
        actions.addWidget(self.cancel_btn)
        actions.addStretch()
        layout.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.progress)

        layout.addWidget(QLabel("Log:"))
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)

        self._add_row()
        self._log("Ready.")

    def _log(self, msg: str) -> None:
        line = str(msg or "").rstrip()
        if not line:
            return

        def _append():
            try:
                self.log.appendPlainText(line)
            except Exception:
                pass

        QTimer.singleShot(0, _append)

    def _browse_output_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Root")
        folder = str(folder or "").strip()
        if folder:
            self.output_root_edit.setText(folder)

    def _add_row(self) -> None:
        r = self.table.rowCount()
        self.table.insertRow(r)

        drummer = QComboBox()
        drummer.addItems(DRUMMERS)
        self.table.setCellWidget(r, 0, drummer)

        url_item = QTableWidgetItem("")
        self.table.setItem(r, 1, url_item)

        status_item = QTableWidgetItem("queued")
        status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(r, 2, status_item)

    def _bulk_paste(self) -> None:
        dlg = BulkPasteDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return
        lines = dlg.get_lines()
        if not lines:
            return
        for ln in lines:
            self._add_row()
            r = self.table.rowCount() - 1
            it = self.table.item(r, 1)
            if it is not None:
                it.setText(ln)

    def _clear_rows(self) -> None:
        if self._running:
            return
        self.table.setRowCount(0)
        self._add_row()

    def _set_row_status(self, row: int, status: str) -> None:
        try:
            it = self.table.item(row, 2)
            if it is None:
                it = QTableWidgetItem("")
                it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 2, it)
            it.setText(str(status or ""))
        except Exception:
            pass

    def _on_start(self) -> None:
        if self._running:
            return

        output_root = str(self.output_root_edit.text() or "").strip()
        if not output_root:
            QMessageBox.warning(self, "Missing Output Root", "Please select an output root folder.")
            return

        jobs: List[Tuple[int, str, str]] = []
        for r in range(self.table.rowCount()):
            dcb = self.table.cellWidget(r, 0)
            url_it = self.table.item(r, 1)
            if not isinstance(dcb, QComboBox) or url_it is None:
                continue
            drummer = str(dcb.currentText() or "").strip()
            url = str(url_it.text() or "").strip()
            if not url:
                continue
            jobs.append((r, drummer, url))
            self._set_row_status(r, "queued")

        if not jobs:
            QMessageBox.warning(self, "No URLs", "Add at least one URL/ID.")
            return

        for _r, drummer, _u in jobs:
            drummer_folder = Path(output_root) / _sanitize_folder_name(drummer)
            try:
                drummer_folder.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                QMessageBox.critical(self, "Folder Error", f"Failed to create folder:\n{drummer_folder}\n\n{e}")
                return

        self._queue = jobs
        self._total_jobs = len(jobs)
        self._running = True
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.add_row_btn.setEnabled(False)
        self.bulk_paste_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.output_root_btn.setEnabled(False)
        self.output_root_edit.setEnabled(False)
        self.table.setEnabled(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self._log(f"Starting batch: {self._total_jobs} item(s)")
        self._start_next()

    def _on_cancel(self) -> None:
        if not self._running:
            return

        self._log("Cancel requested.")
        self._running = False
        try:
            if self._active_dl_thread is not None:
                self._active_dl_thread.cancel()
        except Exception:
            pass

        self._finish_ui()

    def _finish_ui(self) -> None:
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.add_row_btn.setEnabled(True)
        self.bulk_paste_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.output_root_btn.setEnabled(True)
        self.output_root_edit.setEnabled(True)
        self.table.setEnabled(True)

    def _start_next(self) -> None:
        if not self._running:
            return

        if not self._queue:
            self._running = False
            self.progress.setValue(100)
            self._log("All downloads complete.")
            self._finish_ui()
            QMessageBox.information(self, "Done", "All downloads complete.")
            return

        row, drummer, url = self._queue.pop(0)
        output_root = str(self.output_root_edit.text() or "").strip()
        drummer_folder = Path(output_root) / _sanitize_folder_name(drummer)

        safe_base = _sanitize_filename(url)[:100]
        output_path = str(drummer_folder / f"{safe_base}.mp3")

        self._set_row_status(row, "downloading")
        self._log(f"[{self._total_jobs - len(self._queue)}/{self._total_jobs}] {drummer} <- {url}")

        def on_progress(p: int):
            try:
                if p is None:
                    return
                pv = int(p)
            except Exception:
                return

            def _set():
                try:
                    if pv < 0:
                        self.progress.setRange(0, 0)
                    else:
                        if self.progress.minimum() == 0 and self.progress.maximum() == 0:
                            self.progress.setRange(0, 100)
                        self.progress.setValue(max(0, min(100, pv)))
                except Exception:
                    pass

            QTimer.singleShot(0, _set)

        def on_done(path: str):
            self._set_row_status(row, "done")
            self._log(f"Saved: {path}")
            try:
                self.progress.setRange(0, 100)
                self.progress.setValue(100)
            except Exception:
                pass
            QTimer.singleShot(0, self._start_next)

        def on_err(err: str):
            self._set_row_status(row, "error")
            self._log(f"ERROR: {err.splitlines()[0] if err else 'Unknown error'}")
            QTimer.singleShot(0, self._start_next)

        self._active_dl_thread, self._active_thread = self._service.download_audio(
            url,
            output_path,
            progress_callback=on_progress,
            completion_callback=on_done,
            error_callback=on_err,
            search_query=url,
        )


def main() -> int:
    app = QApplication(sys.argv)
    w = YouTubeAudioExtractorWindow()
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
