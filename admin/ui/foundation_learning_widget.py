"""
Foundation Learning Widget
=========================
UI for monitoring YouTube foundation learning progress.
Shows real-time progress for Track A learning.
"""

import logging
import threading
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QGroupBox, QTextEdit, QListWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QCheckBox, QSpinBox
)

logger = logging.getLogger(__name__)

# Import foundation learning service
try:
    from ..services.youtube_foundation_learning import (
        YouTubeFoundationLearning,
        full_foundation_curriculum,
        show_available_techniques
    )
    SERVICE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Foundation learning service not available: {e}")
    SERVICE_AVAILABLE = False


class FoundationLearningWidget(QWidget):
    """Widget for YouTube foundation learning with real-time progress monitoring."""
    
    # Signals
    learning_started = Signal()
    progress_update = Signal(str, int)  # category, progress
    learning_completed = Signal(bool, dict)  # success, results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.learner = None
        self.learning_thread = None
        self.is_running = False
        self._setup_ui()
        logger.info("Foundation Learning Widget initialized")
    
    def _setup_ui(self):
        """Setup user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header
        header_label = QLabel("🎓 Foundation Learning (Track A)")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header_label.setFont(font)
        main_layout.addWidget(header_label)
        
        description = QLabel(
            "Autonomous YouTube learning for fundamental drumming techniques. "
            "The system will search for and learn 50+ techniques automatically."
        )
        description.setWordWrap(True)
        main_layout.addWidget(description)
        
        # Status section
        status_group = QGroupBox("Current Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Ready to start foundation learning")
        self.status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; }")
        status_layout.addWidget(self.status_label)
        
        # Overall progress
        overall_layout = QHBoxLayout()
        overall_layout.addWidget(QLabel("Overall Progress:"))
        self.overall_progress = QProgressBar()
        self.overall_progress.setMinimum(0)
        self.overall_progress.setMaximum(100)
        self.overall_progress.setValue(0)
        overall_layout.addWidget(self.overall_progress)
        self.overall_percent_label = QLabel("0%")
        overall_layout.addWidget(self.overall_percent_label)
        status_layout.addLayout(overall_layout)
        
        main_layout.addWidget(status_group)
        
        # Configuration section
        config_group = QGroupBox("Learning Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Level selection
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Start Level:"))
        self.level_buttons = {}
        for level in ['beginner', 'intermediate', 'advanced']:
            btn = QCheckBox(level.capitalize())
            btn.setChecked(True)  # All enabled by default
            self.level_buttons[level] = btn
            level_layout.addWidget(btn)
        level_layout.addStretch(1)
        config_layout.addLayout(level_layout)
        
        # Videos per technique
        videos_layout = QHBoxLayout()
        videos_layout.addWidget(QLabel("Videos per Technique:"))
        self.videos_spin = QSpinBox()
        self.videos_spin.setMinimum(1)
        self.videos_spin.setMaximum(5)
        self.videos_spin.setValue(2)
        videos_layout.addWidget(self.videos_spin)
        videos_layout.addStretch(1)
        config_layout.addLayout(videos_layout)
        
        main_layout.addWidget(config_group)
        
        # Progress by category
        category_group = QGroupBox("Progress by Category")
        category_layout = QVBoxLayout(category_group)
        
        # Create progress table
        self.category_table = QTableWidget()
        self.category_table.setColumnCount(4)
        self.category_table.setHorizontalHeaderLabels([
            "Category", "Level", "Progress", "Status"
        ])
        self.category_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.category_table.setRowCount(8)  # 8 categories
        
        # Initialize categories
        categories = [
            ("Basic Beats", "beginner"),
            ("Rudiments", "intermediate"),
            ("Ghost Notes", "intermediate"),
            ("Fills", "intermediate"),
            ("Advanced Timing", "advanced"),
            ("Dynamics", "intermediate"),
            ("Independence", "advanced"),
            ("Styles", "intermediate")
        ]
        
        for i, (category, level) in enumerate(categories):
            self.category_table.setItem(i, 0, QTableWidgetItem(category))
            self.category_table.setItem(i, 1, QTableWidgetItem(level.capitalize()))
            self.category_table.setItem(i, 2, QTableWidgetItem("0%"))
            self.category_table.setItem(i, 3, QTableWidgetItem("Pending"))
        
        category_layout.addWidget(self.category_table)
        main_layout.addWidget(category_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 Start Foundation Learning")
        self.start_button.clicked.connect(self._on_start_learning)
        self.start_button.setStyleSheet("QPushButton { padding: 10px; font-weight: bold; }")
        
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.clicked.connect(self._on_stop_learning)
        self.stop_button.setEnabled(False)
        
        self.refresh_button = QPushButton("🔄 Refresh Status")
        self.refresh_button.clicked.connect(self._refresh_status)
        
        buttons_layout.addWidget(self.start_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.refresh_button)
        
        main_layout.addLayout(buttons_layout)
        
        # Log output
        log_group = QGroupBox("Learning Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumHeight(150)
        self.log_output.setStyleSheet("QTextEdit { font-family: 'Courier New'; font-size: 9px; }")
        log_layout.addWidget(self.log_output)
        
        main_layout.addWidget(log_group)
        
        # Results summary
        results_group = QGroupBox("Learning Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_list = QListWidget()
        self.results_list.setMaximumHeight(100)
        results_layout.addWidget(self.results_list)
        
        main_layout.addWidget(results_group)
        
        # Check if service is available
        if not SERVICE_AVAILABLE:
            self.start_button.setEnabled(False)
            self._log("❌ Foundation learning service not available")
            self._log("   Check that youtube_foundation_learning.py is installed")
        
        # Start status refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(2000)  # Refresh every 2 seconds
    
    def _on_start_learning(self):
        """Start foundation learning."""
        if not SERVICE_AVAILABLE:
            self._log("❌ Service not available")
            return
        
        # Get configuration
        enabled_levels = [level for level, btn in self.level_buttons.items() if btn.isChecked()]
        
        if not enabled_levels:
            self._log("❌ Please select at least one difficulty level")
            return
        
        videos_per_technique = self.videos_spin.value()
        
        # Clear previous results
        self.log_output.clear()
        self.results_list.clear()
        self.overall_progress.setValue(0)
        
        self._log(f"🚀 Starting foundation learning...")
        self._log(f"   Levels: {', '.join(enabled_levels)}")
        self._log(f"   Videos per technique: {videos_per_technique}")
        self._log("")
        
        # Update UI state
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.is_running = True
        
        # Start learning in background thread
        self.learning_thread = threading.Thread(
            target=self._run_learning_thread,
            args=(enabled_levels, videos_per_technique),
            daemon=True
        )
        self.learning_thread.start()
        
        self.learning_started.emit()
    
    def _run_learning_thread(self, levels, videos_per_technique):
        """Run learning in background thread."""
        try:
            self.learner = YouTubeFoundationLearning()
            
            # Determine start level
            level_order = ['beginner', 'intermediate', 'advanced']
            start_level = next((level for level in level_order if level in levels), 'beginner')
            
            self._log(f"📚 Initializing learning pipeline...")
            self.status_label.setText("Learning in progress...")
            
            # Run progressive learning
            result = self.learner.learn_foundation_progressive(
                max_videos_per_technique=videos_per_technique,
                start_level=start_level
            )
            
            # Success
            self._log("\n" + "="*60)
            self._log("✅ FOUNDATION LEARNING COMPLETE!")
            self._log(f"   Total Videos: {result['total_videos']}")
            self._log(f"   Total Techniques: {result['total_techniques']}")
            self._log(f"   Levels Completed: {len(result['levels_completed'])}")
            self._log("="*60)
            
            # Update results
            for level_result in result['levels_completed']:
                self.results_list.addItem(
                    f"✅ {level_result['level'].upper()}: "
                    f"{level_result['videos_downloaded']} videos, "
                    f"{level_result['techniques_learned']} techniques"
                )
            
            self.overall_progress.setValue(100)
            self.overall_percent_label.setText("100%")
            self.status_label.setText("Learning completed successfully!")
            
            self.learning_completed.emit(True, result)
            
        except Exception as e:
            logger.error(f"Learning failed: {e}", exc_info=True)
            self._log(f"\n❌ Learning failed: {e}")
            self.status_label.setText("Learning failed!")
            self.learning_completed.emit(False, {'error': str(e)})
        
        finally:
            self.is_running = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
    
    def _on_stop_learning(self):
        """Stop learning."""
        self._log("\n⏹ Stopping foundation learning...")
        self.is_running = False
        self.status_label.setText("Stopping...")
        
        # Thread will terminate on next check
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
    
    def _refresh_status(self):
        """Refresh current status."""
        if not SERVICE_AVAILABLE:
            return
        
        self._log("🔄 Refreshing status...")
        
        # Check if learning is in progress
        if self.learner:
            # Try to get current status
            try:
                # Check download history
                history = self.learner.youtube_downloader.get_download_history()
                downloaded_count = len(history)
                
                self._log(f"   Downloads so far: {downloaded_count}")
                
                # Update progress estimate
                # Assume ~110 total videos for full curriculum
                estimated_total = 110
                progress = min(int((downloaded_count / estimated_total) * 100), 99)
                self.overall_progress.setValue(progress)
                self.overall_percent_label.setText(f"{progress}%")
                
            except Exception as e:
                logger.debug(f"Status refresh error: {e}")
    
    def _auto_refresh(self):
        """Auto-refresh during learning."""
        if self.is_running and self.learner:
            try:
                history = self.learner.youtube_downloader.get_download_history()
                downloaded_count = len(history)
                
                # Update progress
                estimated_total = 110
                progress = min(int((downloaded_count / estimated_total) * 100), 99)
                self.overall_progress.setValue(progress)
                self.overall_percent_label.setText(f"{progress}%")
                
                # Update status label
                self.status_label.setText(f"Learning... ({downloaded_count} videos downloaded)")
                
            except Exception as e:
                logger.debug(f"Auto-refresh error: {e}")
    
    def _log(self, message: str):
        """Add message to log output."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.append(f"[{timestamp}] {message}")
        
        # Auto-scroll to bottom
        scrollbar = self.log_output.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        logger.info(message)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    widget = FoundationLearningWidget()
    widget.setWindowTitle("Foundation Learning Monitor")
    widget.resize(900, 800)
    widget.show()
    sys.exit(app.exec())
