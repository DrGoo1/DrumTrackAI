"""
YouTube Learning Widget for DrumTracKAI Admin
============================================
UI for YouTube-to-LLM learning pipeline.
Provides user-friendly interface for sourcing and learning from YouTube.
"""

import logging
import threading
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QTextEdit, QProgressBar, QGroupBox,
    QListWidget, QSplitter, QCheckBox, QDoubleSpinBox
)

logger = logging.getLogger(__name__)

# Import the learning pipeline
try:
    from ..services.youtube_llm_learning_service import (
        YouTubeLLMLearningPipeline, 
        FAMOUS_DRUMMER_SEARCHES
    )
    PIPELINE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"YouTube LLM Learning Pipeline not available: {e}")
    PIPELINE_AVAILABLE = False


class YouTubeLearningWidget(QWidget):
    """Widget for YouTube-to-LLM learning pipeline."""
    
    # Signals
    pipeline_started = Signal(str)  # drummer_name
    pipeline_progress = Signal(str)  # status message
    pipeline_completed = Signal(bool, dict)  # success, results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pipeline = None
        self.current_thread = None
        self._setup_ui()
        
        try:
            self.pipeline_started.connect(self._on_pipeline_started)
            self.pipeline_progress.connect(self._on_pipeline_progress)
            self.pipeline_completed.connect(self._on_pipeline_completed)
        except Exception:
            pass
        logger.info("YouTube Learning Widget initialized")
    
    def _setup_ui(self):
        """Setup user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header
        header_label = QLabel("🎥 YouTube LLM Learning Pipeline")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header_label.setFont(font)
        main_layout.addWidget(header_label)
        
        description = QLabel(
            "Automatically source, analyze, and learn from YouTube drum performances. "
            "The pipeline will download videos, extract features, and build training datasets."
        )
        description.setWordWrap(True)
        main_layout.addWidget(description)
        
        # Create splitter for left/right panels
        splitter = QSplitter(Qt.Horizontal)
        
        # ============================================================
        # LEFT PANEL: Configuration
        # ============================================================
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        
        # Drummer Selection
        drummer_group = QGroupBox("Drummer Selection")
        drummer_layout = QVBoxLayout(drummer_group)
        
        # Pre-defined drummers
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Preset:")
        self.drummer_combo = QComboBox()
        self.drummer_combo.addItem("Select Drummer...", "")
        
        if PIPELINE_AVAILABLE and FAMOUS_DRUMMER_SEARCHES:
            for drummer in sorted(FAMOUS_DRUMMER_SEARCHES.keys()):
                self.drummer_combo.addItem(drummer, drummer)
        else:
            self.drummer_combo.addItem("Jeff Porcaro", "Jeff Porcaro")
            self.drummer_combo.addItem("John Bonham", "John Bonham")
            self.drummer_combo.addItem("Neil Peart", "Neil Peart")
        
        self.drummer_combo.currentIndexChanged.connect(self._on_drummer_selected)
        
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.drummer_combo, 1)
        drummer_layout.addLayout(preset_layout)
        
        config_layout.addWidget(drummer_group)
        
        # Pipeline Parameters
        params_group = QGroupBox("Pipeline Parameters")
        params_layout = QVBoxLayout(params_group)

        url_group = QGroupBox("Signature Song URLs (optional)")
        url_layout = QVBoxLayout(url_group)
        self.urls_input = QTextEdit()
        self.urls_input.setPlaceholderText("Paste YouTube URLs here, one per line. If provided, these exact URLs will be downloaded instead of search-based sourcing.")
        self.urls_input.setMaximumHeight(100)
        url_layout.addWidget(self.urls_input)
        params_layout.addWidget(url_group)
        
        # Style selection
        style_layout = QHBoxLayout()
        style_label = QLabel("Style:")
        self.style_combo = QComboBox()
        self.style_combo.addItem("Rock", "rock")
        self.style_combo.addItem("Jazz", "jazz")
        self.style_combo.addItem("Funk", "funk")
        self.style_combo.addItem("Metal", "metal")
        self.style_combo.addItem("Electronic", "electronic")
        
        style_layout.addWidget(style_label)
        style_layout.addWidget(self.style_combo, 1)
        params_layout.addLayout(style_layout)
        
        # Max videos
        videos_layout = QHBoxLayout()
        videos_label = QLabel("Max Videos:")
        self.max_videos_spin = QSpinBox()
        self.max_videos_spin.setMinimum(1)
        self.max_videos_spin.setMaximum(20)
        self.max_videos_spin.setValue(5)
        
        videos_layout.addWidget(videos_label)
        videos_layout.addWidget(self.max_videos_spin)
        videos_layout.addStretch(1)
        params_layout.addLayout(videos_layout)
        
        # Quality threshold
        quality_layout = QHBoxLayout()
        quality_label = QLabel("Quality Threshold:")
        self.quality_spin = QDoubleSpinBox()
        self.quality_spin.setMinimum(0.0)
        self.quality_spin.setMaximum(1.0)
        self.quality_spin.setSingleStep(0.1)
        self.quality_spin.setValue(0.7)
        self.quality_spin.setToolTip("Minimum quality score (0-1). Higher = stricter filtering.")
        
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_spin)
        quality_layout.addStretch(1)
        params_layout.addLayout(quality_layout)
        
        # Auto-train checkbox
        self.auto_train_check = QCheckBox("Start LLM Training After Pipeline")
        self.auto_train_check.setChecked(False)
        params_layout.addWidget(self.auto_train_check)

        self.ingest_drummerbrain_check = QCheckBox("Ingest downloaded audio into DrummerBrain")
        self.ingest_drummerbrain_check.setChecked(True)
        params_layout.addWidget(self.ingest_drummerbrain_check)

        ingest_limit_layout = QHBoxLayout()
        ingest_limit_layout.addWidget(QLabel("DrummerBrain ingest limit:"))
        self.ingest_limit_spin = QSpinBox()
        self.ingest_limit_spin.setMinimum(0)
        self.ingest_limit_spin.setMaximum(9999)
        self.ingest_limit_spin.setValue(0)
        self.ingest_limit_spin.setToolTip("0 = no limit")
        ingest_limit_layout.addWidget(self.ingest_limit_spin)
        ingest_limit_layout.addStretch(1)
        params_layout.addLayout(ingest_limit_layout)
        
        config_layout.addWidget(params_group)
        
        # Action Buttons
        buttons_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 Start Pipeline")
        self.start_button.clicked.connect(self._on_start_pipeline)
        self.start_button.setStyleSheet("QPushButton { padding: 10px; font-weight: bold; }")
        
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.clicked.connect(self._on_stop_pipeline)
        self.stop_button.setEnabled(False)
        
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        
        config_layout.addLayout(buttons_layout)
        
        # Batch Operations
        batch_group = QGroupBox("Batch Operations")
        batch_layout = QVBoxLayout(batch_group)
        
        batch_desc = QLabel("Run pipeline for multiple drummers automatically.")
        batch_desc.setWordWrap(True)
        batch_layout.addWidget(batch_desc)
        
        self.batch_button = QPushButton("🎯 Learn from All Famous Drummers")
        self.batch_button.clicked.connect(self._on_batch_pipeline)
        batch_layout.addWidget(self.batch_button)
        
        config_layout.addWidget(batch_group)
        config_layout.addStretch(1)
        
        splitter.addWidget(config_widget)
        
        # ============================================================
        # RIGHT PANEL: Progress & Results
        # ============================================================
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        # Status Label
        self.status_label = QLabel("Ready to start pipeline")
        self.status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; }")
        progress_layout.addWidget(self.status_label)
        
        # Log Output
        log_label = QLabel("Pipeline Log:")
        progress_layout.addWidget(log_label)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("QTextEdit { font-family: 'Courier New'; font-size: 10px; }")
        progress_layout.addWidget(self.log_output)
        
        # Results Summary
        results_label = QLabel("Results Summary:")
        progress_layout.addWidget(results_label)
        
        self.results_list = QListWidget()
        progress_layout.addWidget(self.results_list)
        
        splitter.addWidget(progress_widget)
        
        # Set splitter sizes (40% config, 60% progress)
        splitter.setSizes([400, 600])
        
        main_layout.addWidget(splitter)
        
        # Check if pipeline is available
        if not PIPELINE_AVAILABLE:
            self.start_button.setEnabled(False)
            self.batch_button.setEnabled(False)
            self._log("❌ YouTube LLM Learning Pipeline not available")
            self._log("   Check that youtube_llm_learning_service.py is installed")
    
    def _on_drummer_selected(self, index):
        """Handle drummer selection."""
        drummer = self.drummer_combo.currentData()
        if drummer:
            self._log(f"Selected drummer: {drummer}")
    
    def _on_start_pipeline(self):
        """Start the learning pipeline."""
        drummer = self.drummer_combo.currentData()
        
        if not drummer:
            self._log("❌ Please select a drummer first")
            return
        
        style = self.style_combo.currentData()
        max_videos = self.max_videos_spin.value()
        quality_threshold = self.quality_spin.value()
        auto_train = self.auto_train_check.isChecked()
        ingest_to_drummerbrain = self.ingest_drummerbrain_check.isChecked()
        ingest_limit = self.ingest_limit_spin.value()

        urls = []
        if hasattr(self, "urls_input") and self.urls_input is not None:
            urls = [u.strip() for u in (self.urls_input.toPlainText() or "").splitlines() if u.strip()]
        
        # Clear previous results
        self.log_output.clear()
        self.results_list.clear()
        self.progress_bar.setValue(0)
        
        self._log(f"🚀 Starting pipeline for {drummer}")
        self._log(f"   Style: {style}")
        self._log(f"   Max Videos: {max_videos}")
        self._log(f"   Quality Threshold: {quality_threshold}")
        self._log(f"   Auto-train: {auto_train}")
        self._log(f"   URL list: {len(urls)}")
        self._log(f"   Ingest to DrummerBrain: {ingest_to_drummerbrain}")
        self._log("")
        
        # Disable start button
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # Start pipeline in background thread
        self.current_thread = threading.Thread(
            target=self._run_pipeline_thread,
            args=(drummer, style, max_videos, quality_threshold, auto_train, ingest_to_drummerbrain, ingest_limit, urls),
            daemon=True
        )
        self.current_thread.start()
        
        # Start progress updater
        self._start_progress_updater()
        
        self.pipeline_started.emit(drummer)
    
    def _run_pipeline_thread(self, drummer, style, max_videos, quality_threshold, auto_train, ingest_to_drummerbrain, ingest_limit, urls):
        """Run pipeline in background thread."""
        try:
            # Initialize pipeline
            self.pipeline = YouTubeLLMLearningPipeline()
            
            # Run complete pipeline
            self.pipeline_progress.emit("📥 Step 1/4: Sourcing from YouTube...")

            session = self.pipeline.run_complete_pipeline(
                drummer_name=drummer,
                style=style,
                max_videos=int(max_videos),
                quality_threshold=float(quality_threshold),
                start_training=bool(auto_train),
                ingest_to_drummerbrain=bool(ingest_to_drummerbrain),
                drummerbrain_limit=int(ingest_limit or 0),
                urls=list(urls) if urls else None,
            )
            
            logger.info("Worker: pipeline finished; preparing results")
            
            # Success results
            results = {
                'success': True,
                'drummer': drummer,
                'style': style,
                'files_sourced': session.get('files_sourced', 0),
                'dataset_file': session.get('dataset_file', ''),
                'training_started': bool(session.get('training_started')),
                'drummerbrain_ingest': session.get('drummerbrain_ingest')
            }
            logger.info("Worker: pipeline complete; emitting results to UI thread")
            self.pipeline_completed.emit(True, results)
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.pipeline_completed.emit(False, {'error': str(e), 'drummer': drummer})
        
        finally:
            pass
    
    def _on_stop_pipeline(self):
        """Stop the pipeline."""
        self._log("\n⏹ Stopping pipeline...")
        self.status_label.setText("Stopping...")
        
        # In a real implementation, would terminate the thread gracefully
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def _on_batch_pipeline(self):
        """Run batch pipeline for multiple drummers."""
        self._log("🎯 Starting batch pipeline for famous drummers...")
        self._log("   This will take several minutes...")
        
        # Disable buttons
        self.start_button.setEnabled(False)
        self.batch_button.setEnabled(False)
        
        # Run in thread
        self.current_thread = threading.Thread(
            target=self._run_batch_pipeline_thread,
            daemon=True
        )
        self.current_thread.start()
    
    def _run_batch_pipeline_thread(self):
        """Run batch pipeline in background thread."""
        try:
            self.pipeline = YouTubeLLMLearningPipeline()
            
            famous_drummers = [
                ("Jeff Porcaro", "rock"),
                ("John Bonham", "rock"),
                ("Neil Peart", "rock"),
                ("Dave Grohl", "rock"),
                ("Steve Gadd", "jazz"),
            ]
            
            results = self.pipeline.run_batch_pipeline(famous_drummers, max_videos_each=3)
            
            # Summary
            successful = len([r for r in results if r['success']])
            self._log(f"\n✅ Batch complete: {successful}/{len(results)} successful")
            
            for result in results:
                if result['success']:
                    self.results_list.addItem(f"✅ {result['drummer']} - {result['files_sourced']} files")
                else:
                    self.results_list.addItem(f"❌ {result['drummer']} - FAILED")
            
        except Exception as e:
            self._log(f"\n❌ Batch pipeline failed: {e}")
        
        finally:
            self.start_button.setEnabled(True)
            self.batch_button.setEnabled(True)
    
    def _start_progress_updater(self):
        """Start progress bar animation."""
        # Could implement more sophisticated progress tracking
        pass
    
    def _log(self, message: str):
        """Add message to log output."""
        self.log_output.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        logger.info(message)

    def _on_pipeline_started(self, drummer_name: str):
        self.status_label.setText(f"Starting pipeline for {drummer_name}...")
        self.progress_bar.setValue(0)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def _on_pipeline_progress(self, message: str):
        self._log(message)
        self.status_label.setText(message)

    def _on_pipeline_completed(self, success: bool, results: dict):
        try:
            if success:
                self.progress_bar.setValue(100)
                drummer = results.get('drummer', '')
                files = results.get('files_sourced', 0)
                dataset = results.get('dataset_file') or ''
                dataset_name = Path(str(dataset)).name if dataset else ''
                self._log("\n" + "="*50)
                self._log("✅ PIPELINE COMPLETE!")
                self._log(f"   Drummer: {drummer}")
                self._log(f"   Files: {files}")
                self._log(f"   Dataset: {dataset_name}")
                self._log("="*50)
                self.results_list.addItem(f"✅ {drummer} - {files} files")
                if dataset_name:
                    self.results_list.addItem(f"   Dataset: {dataset_name}")
                ingest = results.get('drummerbrain_ingest') or None
                if isinstance(ingest, dict):
                    ok = ingest.get('ok')
                    dsid = ingest.get('dataset_id')
                    self.results_list.addItem(f"   DrummerBrain ingest: {'OK' if ok else 'FAILED'} ({dsid})")
                self.status_label.setText("Pipeline completed successfully!")
            else:
                drummer = (results or {}).get('drummer', '')
                err = (results or {}).get('error', 'Unknown error')
                self._log(f"\n❌ Pipeline failed: {err}")
                self.status_label.setText("Pipeline failed!")
                if drummer:
                    self.results_list.addItem(f"❌ {drummer} - FAILED: {err}")
        finally:
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    widget = YouTubeLearningWidget()
    widget.setWindowTitle("YouTube LLM Learning Pipeline")
    widget.resize(1000, 700)
    widget.show()
    sys.exit(app.exec())
