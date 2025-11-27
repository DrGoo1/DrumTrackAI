"""
Enhanced LLM Training Widget
============================
Comprehensive LLM training monitoring with Track A/B integration.
Real-time progress tracking, expertise evaluation, and dataset management.
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
    QTableWidgetItem, QHeaderView, QTabWidget, QComboBox, QSpinBox
)

logger = logging.getLogger(__name__)

# Import services
try:
    from ..services.expertise_tracking_service import ExpertiseTrackingService
    TRACKING_AVAILABLE = True
except ImportError:
    logger.warning("Expertise tracking not available")
    TRACKING_AVAILABLE = False


class EnhancedLLMTrainingWidget(QWidget):
    """
    Enhanced LLM training widget with comprehensive monitoring.
    
    Features:
    - Track A/B expertise monitoring
    - Real-time training progress
    - Dataset management
    - Evaluation results
    - Historical tracking
    """
    
    # Signals
    training_started = Signal(str)
    training_progress = Signal(int, str)  # percent, status
    training_completed = Signal(bool, dict)  # success, results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tracker = None
        self.training_thread = None
        self.is_training = False
        self._setup_ui()
        self._setup_tracking()
        logger.info("Enhanced LLM Training Widget initialized")
    
    def _setup_ui(self):
        """Setup user interface."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header
        header_label = QLabel("🤖 LLM Training & Expertise Tracking")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header_label.setFont(font)
        main_layout.addWidget(header_label)
        
        description = QLabel(
            "Monitor LLM training progress and track expertise development across "
            "Track A (general drumming) and Track B (drummer profiles)."
        )
        description.setWordWrap(True)
        main_layout.addWidget(description)
        
        # Create tab widget for Track A / Track B
        self.track_tabs = QTabWidget()
        
        # Track A Tab
        track_a_widget = self._create_track_a_tab()
        self.track_tabs.addTab(track_a_widget, "Track A: General Expertise")
        
        # Track B Tab
        track_b_widget = self._create_track_b_tab()
        self.track_tabs.addTab(track_b_widget, "Track B: Drummer Profiles")
        
        # Training Tab
        training_widget = self._create_training_tab()
        self.track_tabs.addTab(training_widget, "Training Control")
        
        main_layout.addWidget(self.track_tabs)
        
        # Status bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; }")
        main_layout.addWidget(self.status_label)
        
        # Auto-refresh timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.refresh_timer.start(5000)  # Refresh every 5 seconds
    
    def _create_track_a_tab(self):
        """Create Track A (general expertise) monitoring tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Current score display
        score_group = QGroupBox("Current Track A Score")
        score_layout = QVBoxLayout(score_group)
        
        self.track_a_score_label = QLabel("Overall: ---%")
        self.track_a_score_label.setFont(QFont("Arial", 24, QFont.Bold))
        self.track_a_score_label.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(self.track_a_score_label)
        
        self.track_a_level_label = QLabel("Level: Not Evaluated")
        self.track_a_level_label.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(self.track_a_level_label)
        
        layout.addWidget(score_group)
        
        # Metrics breakdown
        metrics_group = QGroupBox("Track A Metrics Breakdown")
        metrics_layout = QVBoxLayout(metrics_group)
        
        self.track_a_metrics_table = QTableWidget()
        self.track_a_metrics_table.setColumnCount(3)
        self.track_a_metrics_table.setHorizontalHeaderLabels([
            "Metric", "Score", "Weight"
        ])
        self.track_a_metrics_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.track_a_metrics_table.setRowCount(4)
        
        metrics = [
            ("Technique Coverage", "30%"),
            ("Style Versatility", "25%"),
            ("Humanization Quality", "25%"),
            ("Pattern Complexity", "20%")
        ]
        
        for i, (metric, weight) in enumerate(metrics):
            self.track_a_metrics_table.setItem(i, 0, QTableWidgetItem(metric))
            self.track_a_metrics_table.setItem(i, 1, QTableWidgetItem("--"))
            self.track_a_metrics_table.setItem(i, 2, QTableWidgetItem(weight))
        
        metrics_layout.addWidget(self.track_a_metrics_table)
        layout.addWidget(metrics_group)
        
        # Progress to next milestone
        milestone_group = QGroupBox("Progress to Next Milestone")
        milestone_layout = QVBoxLayout(milestone_group)
        
        self.track_a_milestone_label = QLabel("Next: --")
        milestone_layout.addWidget(self.track_a_milestone_label)
        
        self.track_a_milestone_progress = QProgressBar()
        milestone_layout.addWidget(self.track_a_milestone_progress)
        
        layout.addWidget(milestone_group)
        
        # Evaluate button
        eval_button = QPushButton("🔬 Evaluate Track A Now")
        eval_button.clicked.connect(self._evaluate_track_a)
        layout.addWidget(eval_button)
        
        layout.addStretch(1)
        
        return widget
    
    def _create_track_b_tab(self):
        """Create Track B (drummer profiles) monitoring tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Overview
        overview_group = QGroupBox("Drummer Profiles Overview")
        overview_layout = QVBoxLayout(overview_group)
        
        overview_stats = QHBoxLayout()
        
        self.track_b_total_label = QLabel("Total Profiles: 0")
        overview_stats.addWidget(self.track_b_total_label)
        
        self.track_b_mastered_label = QLabel("Mastered: 0")
        overview_stats.addWidget(self.track_b_mastered_label)
        
        self.track_b_learning_label = QLabel("Learning: 0")
        overview_stats.addWidget(self.track_b_learning_label)
        
        overview_layout.addLayout(overview_stats)
        
        self.track_b_avg_label = QLabel("Average Score: ---%")
        self.track_b_avg_label.setAlignment(Qt.AlignCenter)
        overview_layout.addWidget(self.track_b_avg_label)
        
        layout.addWidget(overview_group)
        
        # Profile list
        profiles_group = QGroupBox("Drummer Profile Scores")
        profiles_layout = QVBoxLayout(profiles_group)
        
        self.track_b_profiles_table = QTableWidget()
        self.track_b_profiles_table.setColumnCount(4)
        self.track_b_profiles_table.setHorizontalHeaderLabels([
            "Drummer", "Score", "Level", "Examples"
        ])
        self.track_b_profiles_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        profiles_layout.addWidget(self.track_b_profiles_table)
        layout.addWidget(profiles_group)
        
        # Evaluate all button
        eval_all_button = QPushButton("🔬 Evaluate All Profiles")
        eval_all_button.clicked.connect(self._evaluate_track_b)
        layout.addWidget(eval_all_button)
        
        layout.addStretch(1)
        
        return widget
    
    def _create_training_tab(self):
        """Create training control tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Training configuration
        config_group = QGroupBox("Training Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Dataset selection
        dataset_layout = QHBoxLayout()
        dataset_layout.addWidget(QLabel("Dataset:"))
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItem("Foundation Learning (Track A)", "track_a")
        self.dataset_combo.addItem("Drummer Profiles (Track B)", "track_b")
        self.dataset_combo.addItem("Combined (A + B)", "combined")
        dataset_layout.addWidget(self.dataset_combo)
        config_layout.addLayout(dataset_layout)
        
        # Training parameters
        params_layout = QHBoxLayout()
        
        params_layout.addWidget(QLabel("Epochs:"))
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setMinimum(1)
        self.epochs_spin.setMaximum(100)
        self.epochs_spin.setValue(10)
        params_layout.addWidget(self.epochs_spin)
        
        params_layout.addWidget(QLabel("Batch Size:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setMinimum(1)
        self.batch_spin.setMaximum(128)
        self.batch_spin.setValue(32)
        params_layout.addWidget(self.batch_spin)
        
        params_layout.addStretch(1)
        config_layout.addLayout(params_layout)
        
        layout.addWidget(config_group)
        
        # Training progress
        progress_group = QGroupBox("Training Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.training_progress_bar = QProgressBar()
        progress_layout.addWidget(self.training_progress_bar)
        
        self.training_status_label = QLabel("Not training")
        progress_layout.addWidget(self.training_status_label)
        
        layout.addWidget(progress_group)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        
        self.start_training_button = QPushButton("🚀 Start Training")
        self.start_training_button.clicked.connect(self._start_training)
        buttons_layout.addWidget(self.start_training_button)
        
        self.stop_training_button = QPushButton("⏹ Stop Training")
        self.stop_training_button.clicked.connect(self._stop_training)
        self.stop_training_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_training_button)
        
        layout.addLayout(buttons_layout)
        
        # Training log
        log_group = QGroupBox("Training Log")
        log_layout = QVBoxLayout(log_group)
        
        self.training_log = QTextEdit()
        self.training_log.setReadOnly(True)
        self.training_log.setMaximumHeight(200)
        self.training_log.setStyleSheet("QTextEdit { font-family: 'Courier New'; font-size: 9px; }")
        log_layout.addWidget(self.training_log)
        
        layout.addWidget(log_group)
        
        layout.addStretch(1)
        
        return widget
    
    def _setup_tracking(self):
        """Setup expertise tracking service."""
        if TRACKING_AVAILABLE:
            try:
                self.tracker = ExpertiseTrackingService()
                self.status_label.setText("✅ Expertise tracking active")
                logger.info("Expertise tracking service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize tracking: {e}")
                self.status_label.setText("⚠️ Expertise tracking unavailable")
        else:
            self.status_label.setText("⚠️ Expertise tracking service not found")
    
    def _evaluate_track_a(self):
        """Evaluate Track A general expertise."""
        if not self.tracker:
            self._log("❌ Expertise tracker not available")
            return
        
        self._log("🔬 Evaluating Track A: General Expertise...")
        self.status_label.setText("Evaluating Track A...")
        
        try:
            # Run evaluation
            result = self.tracker.evaluate_general_expertise()
            
            # Update UI
            score = result['overall_score']
            level = result['level']
            
            self.track_a_score_label.setText(f"Overall: {score}%")
            self.track_a_level_label.setText(f"Level: {level}")
            
            # Update metrics table
            self.track_a_metrics_table.setItem(0, 1, QTableWidgetItem(f"{result['technique_coverage']}%"))
            self.track_a_metrics_table.setItem(1, 1, QTableWidgetItem(f"{result['style_versatility']}%"))
            self.track_a_metrics_table.setItem(2, 1, QTableWidgetItem(f"{result['humanization_quality']}%"))
            self.track_a_metrics_table.setItem(3, 1, QTableWidgetItem(f"{result['pattern_complexity']}%"))
            
            # Update milestone
            self.track_a_milestone_label.setText(f"Next: {result['next_milestone']}")
            
            # Calculate progress to next milestone
            milestones = [31, 51, 71, 86, 96]
            next_milestone = next((m for m in milestones if score < m), 100)
            prev_milestone = max([m for m in [0] + milestones if m <= score])
            
            if next_milestone > score:
                progress = int(((score - prev_milestone) / (next_milestone - prev_milestone)) * 100)
                self.track_a_milestone_progress.setValue(progress)
            else:
                self.track_a_milestone_progress.setValue(100)
            
            self._log(f"✅ Track A Evaluation Complete: {score}% ({level})")
            self.status_label.setText(f"Track A: {score}% ({level})")
            
        except Exception as e:
            logger.error(f"Track A evaluation failed: {e}")
            self._log(f"❌ Evaluation failed: {e}")
            self.status_label.setText("Evaluation failed")
    
    def _evaluate_track_b(self):
        """Evaluate Track B drummer profiles."""
        if not self.tracker:
            self._log("❌ Expertise tracker not available")
            return
        
        self._log("🔬 Evaluating Track B: Drummer Profiles...")
        self.status_label.setText("Evaluating all drummer profiles...")
        
        try:
            # Run evaluation
            result = self.tracker.evaluate_all_profiles()
            
            # Update overview
            self.track_b_total_label.setText(f"Total Profiles: {result['total_drummers']}")
            self.track_b_mastered_label.setText(f"Mastered: {result['mastered_drummers']}")
            self.track_b_learning_label.setText(f"Learning: {result['learning_drummers']}")
            self.track_b_avg_label.setText(f"Average Score: {result['average_profile_score']}%")
            
            # Update profiles table
            profiles = result['profiles']
            self.track_b_profiles_table.setRowCount(len(profiles))
            
            for i, profile in enumerate(profiles):
                self.track_b_profiles_table.setItem(i, 0, QTableWidgetItem(profile['drummer_name']))
                self.track_b_profiles_table.setItem(i, 1, QTableWidgetItem(f"{profile['overall_score']}%"))
                self.track_b_profiles_table.setItem(i, 2, QTableWidgetItem(profile['level']))
                self.track_b_profiles_table.setItem(i, 3, QTableWidgetItem(str(profile['training_examples'])))
            
            self._log(f"✅ Track B Evaluation Complete: {len(profiles)} profiles")
            self._log(f"   Average: {result['average_profile_score']}%")
            self.status_label.setText(f"Track B: {len(profiles)} profiles, avg {result['average_profile_score']}%")
            
        except Exception as e:
            logger.error(f"Track B evaluation failed: {e}")
            self._log(f"❌ Evaluation failed: {e}")
            self.status_label.setText("Evaluation failed")
    
    def _start_training(self):
        """Start LLM training."""
        dataset_type = self.dataset_combo.currentData()
        epochs = self.epochs_spin.value()
        batch_size = self.batch_spin.value()
        
        self._log(f"🚀 Starting training...")
        self._log(f"   Dataset: {dataset_type}")
        self._log(f"   Epochs: {epochs}")
        self._log(f"   Batch Size: {batch_size}")
        
        self.start_training_button.setEnabled(False)
        self.stop_training_button.setEnabled(True)
        self.is_training = True
        
        # Start training simulation (replace with real training)
        self._simulate_training()
        
        self.training_started.emit(dataset_type)
    
    def _simulate_training(self):
        """Simulate training progress (replace with real training)."""
        self.training_progress_bar.setValue(0)
        
        # This would be replaced with actual training logic
        self.training_timer = QTimer(self)
        self.training_timer.timeout.connect(self._update_training_progress)
        self.training_timer.start(1000)  # Update every second
        
        self.training_epoch = 0
        self.training_max_epochs = self.epochs_spin.value()
    
    def _update_training_progress(self):
        """Update training progress (simulation)."""
        if not self.is_training:
            self.training_timer.stop()
            return
        
        self.training_epoch += 1
        progress = int((self.training_epoch / self.training_max_epochs) * 100)
        
        self.training_progress_bar.setValue(min(progress, 100))
        self.training_status_label.setText(f"Training... Epoch {self.training_epoch}/{self.training_max_epochs}")
        
        self.training_progress.emit(progress, f"Epoch {self.training_epoch}")
        
        if self.training_epoch >= self.training_max_epochs:
            self._training_complete(True)
    
    def _stop_training(self):
        """Stop training."""
        self._log("⏹ Stopping training...")
        self.is_training = False
        self.training_status_label.setText("Training stopped")
        
        self.start_training_button.setEnabled(True)
        self.stop_training_button.setEnabled(False)
    
    def _training_complete(self, success):
        """Handle training completion."""
        self.is_training = False
        self.training_timer.stop()
        
        if success:
            self._log("✅ Training complete!")
            self.training_status_label.setText("Training completed successfully")
            self.training_completed.emit(True, {'epochs': self.training_max_epochs})
        else:
            self._log("❌ Training failed")
            self.training_status_label.setText("Training failed")
            self.training_completed.emit(False, {})
        
        self.start_training_button.setEnabled(True)
        self.stop_training_button.setEnabled(False)
    
    def _auto_refresh(self):
        """Auto-refresh status periodically."""
        # Could auto-refresh Track A/B scores here
        pass
    
    def _log(self, message: str):
        """Add message to training log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.training_log.append(f"[{timestamp}] {message}")
        
        # Auto-scroll
        scrollbar = self.training_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        logger.info(message)


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    widget = EnhancedLLMTrainingWidget()
    widget.setWindowTitle("LLM Training & Expertise Tracking")
    widget.resize(1000, 700)
    widget.show()
    sys.exit(app.exec())
