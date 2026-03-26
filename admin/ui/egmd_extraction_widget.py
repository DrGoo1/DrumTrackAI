"""
E-GMD Feature Extraction Widget
================================
UI for extracting features from E-GMD MIDI dataset
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QSpinBox, QGroupBox, QMessageBox,
    QFileDialog, QLineEdit, QFormLayout
)

logger = logging.getLogger(__name__)

# Import extractor
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from training.egmd_midi_extractor import EGMDMIDIExtractor
    EXTRACTOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Extractor not available: {e}")
    EXTRACTOR_AVAILABLE = False


class ExtractionThread(QThread):
    """Background thread for feature extraction"""
    progress_update = Signal(int, int, dict)  # current, total, stats
    extraction_complete = Signal(bool, dict)  # success, results
    
    def __init__(self, egmd_path, max_files):
        super().__init__()
        self.egmd_path = Path(egmd_path)
        self.max_files = max_files
        self.should_stop = False
        
    def run(self):
        """Run extraction in background"""
        try:
            extractor = EGMDMIDIExtractor()
            
            def progress_callback(current, total, stats):
                if self.should_stop:
                    return False
                self.progress_update.emit(current, total, stats)
                return True
            
            results = extractor.batch_extract(
                self.egmd_path,
                max_files=self.max_files if self.max_files > 0 else None,
                progress_callback=progress_callback
            )
            
            if self.should_stop:
                self.extraction_complete.emit(False, {'message': 'Stopped by user'})
            else:
                self.extraction_complete.emit(True, results)
                
        except Exception as e:
            logger.error(f"Extraction failed: {e}", exc_info=True)
            self.extraction_complete.emit(False, {'error': str(e)})
    
    def stop(self):
        """Stop extraction"""
        self.should_stop = True


class EGMDExtractionWidget(QWidget):
    """Widget for E-GMD feature extraction"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.extraction_thread = None
        self._setup_ui()
        logger.info("E-GMD Extraction Widget initialized")
    
    def _setup_ui(self):
        """Setup UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🎹 E-GMD MIDI Feature Extraction")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header.setFont(font)
        header.setStyleSheet("color: #2E86AB;")
        main_layout.addWidget(header)
        
        desc = QLabel("Extract drum pattern features from E-GMD MIDI dataset")
        main_layout.addWidget(desc)
        
        if not EXTRACTOR_AVAILABLE:
            warning = QLabel("⚠️ Extractor not available. Install mido: pip install mido")
            warning.setStyleSheet("color: orange; font-weight: bold;")
            main_layout.addWidget(warning)
        
        # Configuration
        config_group = QGroupBox("Configuration")
        config_layout = QFormLayout(config_group)
        
        self.path_input = QLineEdit("E:\\E-GMD Dataset")
        config_layout.addRow("E-GMD Path:", self.path_input)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_path)
        config_layout.addRow("", browse_btn)
        
        self.max_files_spin = QSpinBox()
        self.max_files_spin.setMinimum(0)
        self.max_files_spin.setMaximum(1000000)
        self.max_files_spin.setValue(1000)
        self.max_files_spin.setSpecialValueText("All files")
        config_layout.addRow("Max Files (0=all):", self.max_files_spin)
        
        main_layout.addWidget(config_group)
        
        # Stats
        stats_group = QGroupBox("Current Database Stats")
        stats_layout = QVBoxLayout(stats_group)
        
        self.stats_label = QLabel("Click 'Check Stats' to load")
        stats_layout.addWidget(self.stats_label)
        
        check_stats_btn = QPushButton("Check Stats")
        check_stats_btn.clicked.connect(self._check_stats)
        stats_layout.addWidget(check_stats_btn)
        
        main_layout.addWidget(stats_group)
        
        # Progress
        progress_group = QGroupBox("Extraction Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)
        
        # Log
        log_group = QGroupBox("Extraction Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
        
        # Buttons
        buttons = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Start Extraction")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #2E86AB;
                color: white;
                padding: 10px 20px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background: #236B8E; }
            QPushButton:disabled { background: #cccccc; color: #666666; }
        """)
        self.start_btn.clicked.connect(self._start_extraction)
        self.start_btn.setEnabled(EXTRACTOR_AVAILABLE)
        buttons.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self._stop_extraction)
        self.stop_btn.setEnabled(False)
        buttons.addWidget(self.stop_btn)
        
        buttons.addStretch(1)
        main_layout.addLayout(buttons)
        
        main_layout.addStretch(1)
    
    def _log(self, message):
        """Add to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def _browse_path(self):
        """Browse for E-GMD path"""
        path = QFileDialog.getExistingDirectory(self, "Select E-GMD Dataset Directory")
        if path:
            self.path_input.setText(path)
    
    def _check_stats(self):
        """Check current database stats"""
        if not EXTRACTOR_AVAILABLE:
            QMessageBox.warning(self, "Not Available", "Extractor not available")
            return
        
        try:
            self._log("Checking database stats...")
            extractor = EGMDMIDIExtractor()
            stats = extractor.get_extraction_stats()
            
            stats_text = f"""Current Database Stats:

✅ Total Extracted: {stats['total_extracted']} files
📊 Avg Hits per File: {stats['avg_hits_per_file']:.1f}
⏱️  Avg Duration: {stats['avg_duration']:.1f} seconds
🎵 Avg Tempo: {stats['avg_tempo']:.1f} BPM

Style Distribution:
"""
            for style, count in stats['style_distribution'].items():
                stats_text += f"  - {style}: {count}\n"
            
            self.stats_label.setText(stats_text)
            self._log(f"✅ Stats loaded: {stats['total_extracted']} files extracted")
            
        except Exception as e:
            self._log(f"❌ Error loading stats: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load stats: {e}")
    
    def _start_extraction(self):
        """Start feature extraction"""
        if not EXTRACTOR_AVAILABLE:
            QMessageBox.warning(self, "Not Available", "Extractor not available")
            return
        
        if self.extraction_thread and self.extraction_thread.isRunning():
            QMessageBox.warning(self, "Running", "Extraction already in progress")
            return
        
        egmd_path = Path(self.path_input.text())
        if not egmd_path.exists():
            QMessageBox.critical(self, "Error", f"Path does not exist: {egmd_path}")
            return
        
        max_files = self.max_files_spin.value()
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Start Extraction",
            f"Extract features from E-GMD MIDI files?\n\n"
            f"Path: {egmd_path}\n"
            f"Max files: {max_files if max_files > 0 else 'All'}\n\n"
            f"This may take several hours for full dataset.\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Reset UI
        self.progress_bar.setValue(0)
        self.log_text.clear()
        
        self._log("=" * 60)
        self._log("🚀 STARTING E-GMD FEATURE EXTRACTION")
        self._log(f"Path: {egmd_path}")
        self._log(f"Max files: {max_files if max_files > 0 else 'All'}")
        self._log("=" * 60)
        
        # Create and start thread
        self.extraction_thread = ExtractionThread(egmd_path, max_files)
        self.extraction_thread.progress_update.connect(self._on_progress)
        self.extraction_thread.extraction_complete.connect(self._on_complete)
        self.extraction_thread.start()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.max_files_spin.setEnabled(False)
        self.path_input.setEnabled(False)
    
    @Slot(int, int, dict)
    def _on_progress(self, current, total, stats):
        """Update progress"""
        progress = int((current / total) * 100) if total > 0 else 0
        self.progress_bar.setValue(progress)
        
        status = (f"Processing: {current}/{total} files | "
                 f"Success: {stats['successful']} | "
                 f"Failed: {stats['failed']} | "
                 f"Skipped: {stats['skipped']}")
        self.status_label.setText(status)
        
        if current % 100 == 0:
            self._log(f"Progress: {current}/{total} files processed")
    
    @Slot(bool, dict)
    def _on_complete(self, success, results):
        """Extraction complete"""
        self._log("=" * 60)
        
        if success:
            elapsed = results.get('elapsed_time', 0)
            files_per_sec = results.get('files_per_second', 0)
            
            self._log(f"✅ EXTRACTION COMPLETE!")
            self._log(f"   Processed: {results['processed']} files")
            self._log(f"   Successful: {results['successful']} files")
            self._log(f"   Failed: {results['failed']} files")
            self._log(f"   Skipped: {results['skipped']} files")
            self._log(f"   Time: {elapsed:.1f} seconds")
            self._log(f"   Speed: {files_per_sec:.1f} files/sec")
            
            QMessageBox.information(
                self, "Complete",
                f"Feature extraction complete!\n\n"
                f"Processed: {results['processed']} files\n"
                f"Successful: {results['successful']} files\n"
                f"Time: {elapsed:.1f} seconds"
            )
            
            # Refresh stats
            self._check_stats()
        else:
            error = results.get('error', results.get('message', 'Unknown error'))
            self._log(f"❌ Extraction failed: {error}")
            QMessageBox.warning(self, "Failed", f"Extraction failed:\n{error}")
        
        # Reset UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.max_files_spin.setEnabled(True)
        self.path_input.setEnabled(True)
    
    def _stop_extraction(self):
        """Stop extraction"""
        if self.extraction_thread and self.extraction_thread.isRunning():
            self._log("⏹ Stopping extraction...")
            self.extraction_thread.stop()
