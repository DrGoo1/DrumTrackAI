"""
Real-Time Analysis Progress Monitor for DrumTracKAI Admin App
===========================================================
Comprehensive real-time monitoring system for the continuous sophistication framework.
Provides live streaming updates, dynamic progress visualization, and real-time analysis tracking.
"""

import sys
import os
import json
import sqlite3
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QProgressBar, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QScrollArea,
    QFrame, QSplitter, QComboBox, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QFont, QPalette, QColor

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Try to import database service, but make it optional
try:
    from services.database_service import DatabaseService
except ImportError:
    DatabaseService = None

class AnalysisTrackingWidget(QWidget):
    """Widget for tracking ongoing analysis processes and sophistication metrics"""
    
    def __init__(self, database_service: DatabaseService = None):
        super().__init__()
        self.database_service = database_service
        self.logger = logging.getLogger(__name__)
        
        # Analysis tracking data
        self.analysis_jobs = []
        self.sophistication_metrics = {}
        self.framework_status = "Unknown"
        
        # Setup UI
        self.setup_ui()
        self.setup_styling()
        
        # Setup real-time refresh timers
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(1000)  # Refresh every 1 second for real-time updates
        
        # Setup live log streaming timer
        self.log_stream_timer = QTimer()
        self.log_stream_timer.timeout.connect(self.stream_live_logs)
        self.log_stream_timer.start(500)  # Stream logs every 500ms
        
        # Setup progress animation timer
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.update_animations)
        self.animation_timer.start(100)  # Smooth animations every 100ms
        
        # Real-time tracking variables
        self.last_log_position = 0
        self.animation_counter = 0
        self.live_metrics = {
            'jobs_processed': 0,
            'processing_speed': 0,
            'current_job_progress': 0,
            'eta_seconds': 0
        }
        
        # Initial data load
        self.refresh_data()
    
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Title with real-time indicator
        title_layout = QHBoxLayout()
        title_label = QLabel("🔄 Real-Time Analysis Progress Monitor")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_layout.addWidget(title_label)
        
        # Live status indicator
        self.live_indicator = QLabel("🟢 LIVE")
        self.live_indicator.setFont(QFont("Arial", 12, QFont.Bold))
        self.live_indicator.setStyleSheet("color: #00ff00; background-color: #1e1e1e; padding: 5px; border-radius: 3px;")
        title_layout.addWidget(self.live_indicator)
        
        title_layout.addStretch()
        
        # Real-time timestamp
        self.timestamp_label = QLabel("Last Update: --:--:--")
        self.timestamp_label.setFont(QFont("Arial", 10))
        self.timestamp_label.setStyleSheet("color: #888;")
        title_layout.addWidget(self.timestamp_label)
        
        title_widget = QWidget()
        title_widget.setLayout(title_layout)
        layout.addWidget(title_widget)
        
        # Create main splitter
        main_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(main_splitter)
        
        # Top section: Framework Status & Metrics
        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        
        # Framework Status Group
        self.create_framework_status_group(top_layout)
        
        # Sophistication Metrics Group
        self.create_sophistication_metrics_group(top_layout)
        
        main_splitter.addWidget(top_widget)
        
        # Middle section: Active Jobs
        self.create_active_jobs_section(main_splitter)
        
        # Bottom section: Analysis History & Logs
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        
        # Analysis History
        self.create_analysis_history_section(bottom_layout)
        
        # Live Logs
        self.create_live_logs_section(bottom_layout)
        
        main_splitter.addWidget(bottom_widget)
        
        # Control buttons
        self.create_control_buttons(layout)
        
        # Set splitter proportions
        main_splitter.setSizes([200, 300, 200])
    
    def create_framework_status_group(self, parent_layout):
        """Create framework status monitoring group"""
        status_group = QGroupBox("Framework Status")
        status_layout = QVBoxLayout(status_group)
        
        # Status indicator
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setFont(QFont("Arial", 12, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        # Framework metrics
        metrics_layout = QGridLayout()
        
        # Active jobs count
        metrics_layout.addWidget(QLabel("Active Jobs:"), 0, 0)
        self.active_jobs_label = QLabel("0")
        self.active_jobs_label.setFont(QFont("Arial", 10, QFont.Bold))
        metrics_layout.addWidget(self.active_jobs_label, 0, 1)
        
        # Completed jobs today
        metrics_layout.addWidget(QLabel("Completed Today:"), 1, 0)
        self.completed_today_label = QLabel("0")
        self.completed_today_label.setFont(QFont("Arial", 10, QFont.Bold))
        metrics_layout.addWidget(self.completed_today_label, 1, 1)
        
        # Framework uptime
        metrics_layout.addWidget(QLabel("Uptime:"), 2, 0)
        self.uptime_label = QLabel("Unknown")
        self.uptime_label.setFont(QFont("Arial", 10, QFont.Bold))
        metrics_layout.addWidget(self.uptime_label, 2, 1)
        
        # Processing rate with real-time speed
        metrics_layout.addWidget(QLabel("Processing Rate:"), 3, 0)
        self.processing_rate_label = QLabel("0 jobs/hour")
        self.processing_rate_label.setFont(QFont("Arial", 10, QFont.Bold))
        metrics_layout.addWidget(self.processing_rate_label, 3, 1)
        
        # Real-time processing speed
        metrics_layout.addWidget(QLabel("Current Speed:"), 4, 0)
        self.current_speed_label = QLabel("0 files/min")
        self.current_speed_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.current_speed_label.setStyleSheet("color: #00ff00;")
        metrics_layout.addWidget(self.current_speed_label, 4, 1)
        
        # ETA for current batch
        metrics_layout.addWidget(QLabel("Batch ETA:"), 5, 0)
        self.batch_eta_label = QLabel("--:--:--")
        self.batch_eta_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.batch_eta_label.setStyleSheet("color: #FFD700;")
        metrics_layout.addWidget(self.batch_eta_label, 5, 1)
        
        status_layout.addLayout(metrics_layout)
        parent_layout.addWidget(status_group)
    
    def create_sophistication_metrics_group(self, parent_layout):
        """Create sophistication metrics monitoring group"""
        metrics_group = QGroupBox("Sophistication Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        # Current sophistication level
        level_layout = QHBoxLayout()
        level_layout.addWidget(QLabel("Current Level:"))
        self.sophistication_level_label = QLabel("88.7%")
        self.sophistication_level_label.setFont(QFont("Arial", 14, QFont.Bold))
        self.sophistication_level_label.setStyleSheet("color: #FFD700;")
        level_layout.addWidget(self.sophistication_level_label)
        level_layout.addStretch()
        metrics_layout.addLayout(level_layout)
        
        # Progress bar
        self.sophistication_progress = QProgressBar()
        self.sophistication_progress.setRange(0, 100)
        self.sophistication_progress.setValue(88)
        self.sophistication_progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                background-color: #2b2b2b;
            }
            QProgressBar::chunk {
                background-color: #FFD700;
                border-radius: 3px;
            }
        """)
        metrics_layout.addWidget(self.sophistication_progress)
        
        # Capability breakdown
        capabilities_layout = QGridLayout()
        
        # Basic Recognition
        capabilities_layout.addWidget(QLabel("Basic Recognition:"), 0, 0)
        self.basic_recognition_label = QLabel("94%")
        capabilities_layout.addWidget(self.basic_recognition_label, 0, 1)
        
        # Pattern Analysis
        capabilities_layout.addWidget(QLabel("Pattern Analysis:"), 1, 0)
        self.pattern_analysis_label = QLabel("89%")
        capabilities_layout.addWidget(self.pattern_analysis_label, 1, 1)
        
        # Professional Skills
        capabilities_layout.addWidget(QLabel("Professional Skills:"), 2, 0)
        self.professional_skills_label = QLabel("83%")
        capabilities_layout.addWidget(self.professional_skills_label, 2, 1)
        
        # Advanced Features
        capabilities_layout.addWidget(QLabel("Advanced Features:"), 3, 0)
        self.advanced_features_label = QLabel("75%")
        capabilities_layout.addWidget(self.advanced_features_label, 3, 1)
        
        metrics_layout.addLayout(capabilities_layout)
        parent_layout.addWidget(metrics_group)
    
    def create_active_jobs_section(self, parent_splitter):
        """Create active jobs monitoring section"""
        jobs_group = QGroupBox("Active Analysis Jobs")
        jobs_layout = QVBoxLayout(jobs_group)
        
        # Real-time jobs table with progress bars
        self.jobs_table = QTableWidget()
        self.jobs_table.setColumnCount(8)
        self.jobs_table.setHorizontalHeaderLabels([
            "Job ID", "Type", "Status", "Progress", "Files", "Speed", "Started", "ETA"
        ])
        
        # Store progress bars for real-time updates
        self.job_progress_bars = {}
        
        # Configure table for real-time display
        header = self.jobs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Job ID
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QHeaderView.Stretch)           # Progress
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Files
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Speed
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Started
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # ETA
        
        jobs_layout.addWidget(self.jobs_table)
        parent_splitter.addWidget(jobs_group)
    
    def create_analysis_history_section(self, parent_layout):
        """Create analysis history section"""
        history_group = QGroupBox("Analysis History")
        history_layout = QVBoxLayout(history_group)
        
        # Real-time history table with performance metrics
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "Completed", "Type", "Duration", "Files", "Avg Speed", "Quality", "Status"
        ])
        
        # Configure table
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        
        history_layout.addWidget(self.history_table)
        parent_layout.addWidget(history_group)
    
    def create_live_logs_section(self, parent_layout):
        """Create live logs section"""
        logs_group = QGroupBox("Live Analysis Logs")
        logs_layout = QVBoxLayout(logs_group)
        
        # Real-time streaming log display
        self.logs_display = QTextEdit()
        self.logs_display.setReadOnly(True)
        self.logs_display.setMaximumBlockCount(2000)  # More log lines for real-time streaming
        self.logs_display.setFont(QFont("Consolas", 9))
        
        # Add log filtering controls
        log_controls = QHBoxLayout()
        
        # Log level filter
        log_controls.addWidget(QLabel("Filter:"))
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "INFO", "WARNING", "ERROR", "DEBUG"])
        self.log_level_combo.currentTextChanged.connect(self.filter_logs)
        log_controls.addWidget(self.log_level_combo)
        
        # Auto-scroll toggle
        self.auto_scroll_cb = QCheckBox("Auto-scroll")
        self.auto_scroll_cb.setChecked(True)
        log_controls.addWidget(self.auto_scroll_cb)
        
        # Live streaming toggle
        self.live_stream_cb = QCheckBox("Live Stream")
        self.live_stream_cb.setChecked(True)
        self.live_stream_cb.toggled.connect(self.toggle_live_stream)
        log_controls.addWidget(self.live_stream_cb)
        
        log_controls.addStretch()
        
        # Log search
        log_controls.addWidget(QLabel("Search:"))
        self.log_search = QComboBox()
        self.log_search.setEditable(True)
        self.log_search.setPlaceholderText("Search logs...")
        log_controls.addWidget(self.log_search)
        
        logs_layout.addLayout(log_controls)
        
        logs_layout.addWidget(self.logs_display)
        parent_layout.addWidget(logs_group)
    
    def create_control_buttons(self, parent_layout):
        """Create control buttons"""
        button_layout = QHBoxLayout()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)
        
        # Pause/Resume framework
        self.pause_btn = QPushButton("⏸️ Pause Framework")
        self.pause_btn.clicked.connect(self.toggle_framework)
        button_layout.addWidget(self.pause_btn)
        
        # Export report
        export_btn = QPushButton("📊 Export Report")
        export_btn.clicked.connect(self.export_report)
        button_layout.addWidget(export_btn)
        
        # Clear logs
        clear_logs_btn = QPushButton("🗑️ Clear Logs")
        clear_logs_btn.clicked.connect(self.clear_logs)
        button_layout.addWidget(clear_logs_btn)
        
        button_layout.addStretch()
        
        # Real-time controls
        self.auto_refresh_cb = QCheckBox("Real-time (1s)")
        self.auto_refresh_cb.setChecked(True)
        self.auto_refresh_cb.toggled.connect(self.toggle_auto_refresh)
        button_layout.addWidget(self.auto_refresh_cb)
        
        # Stream speed control
        button_layout.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Fast (0.5s)", "Normal (1s)", "Slow (2s)"])
        self.speed_combo.setCurrentText("Normal (1s)")
        self.speed_combo.currentTextChanged.connect(self.change_refresh_speed)
        button_layout.addWidget(self.speed_combo)
        
        parent_layout.addLayout(button_layout)
    
    def setup_styling(self):
        """Setup widget styling"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #2b2b2b;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FFD700;
            }
            QLabel {
                color: white;
                background-color: transparent;
            }
            QTableWidget {
                background-color: #1e1e1e;
                color: white;
                gridline-color: #555;
                border: 1px solid #555;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #333;
            }
            QTableWidget::item:selected {
                background-color: #FFD700;
                color: black;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 5px;
                border: 1px solid #555;
                font-weight: bold;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #00ff00;
                border: 1px solid #555;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #444;
                color: white;
                border: 1px solid #666;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """)
    
    def refresh_data(self):
        """Refresh all tracking data with real-time updates"""
        try:
            # Update timestamp
            current_time = datetime.now().strftime("%H:%M:%S")
            self.timestamp_label.setText(f"Last Update: {current_time}")
            
            # Refresh all components
            self.load_framework_status()
            self.load_sophistication_metrics()
            self.load_active_jobs()
            self.load_analysis_history()
            self.update_live_metrics()
            
            # Animate live indicator
            self.animate_live_indicator()
            
        except Exception as e:
            self.logger.error(f"Error refreshing data: {e}")
    
    def stream_live_logs(self):
        """Stream live logs in real-time"""
        if not self.live_stream_cb.isChecked():
            return
            
        try:
            self.load_live_logs_streaming()
        except Exception as e:
            self.logger.error(f"Error streaming logs: {e}")
    
    def update_animations(self):
        """Update smooth animations for progress indicators"""
        try:
            self.animation_counter += 1
            
            # Animate progress bars
            self.animate_progress_bars()
            
            # Animate sophistication progress
            self.animate_sophistication_progress()
            
        except Exception as e:
            self.logger.error(f"Error updating animations: {e}")
    
    def animate_live_indicator(self):
        """Animate the live status indicator"""
        try:
            if self.framework_status == "Running":
                # Pulse effect for live indicator
                opacity = 0.5 + 0.5 * abs(math.sin(self.animation_counter * 0.1))
                self.live_indicator.setStyleSheet(
                    f"color: #00ff00; background-color: #1e1e1e; padding: 5px; border-radius: 3px; "
                    f"opacity: {opacity};"
                )
            else:
                self.live_indicator.setStyleSheet(
                    "color: #ff0000; background-color: #1e1e1e; padding: 5px; border-radius: 3px;"
                )
                self.live_indicator.setText("🔴 OFFLINE")
        except Exception as e:
            self.logger.error(f"Error animating live indicator: {e}")
    
    def animate_progress_bars(self):
        """Animate progress bars for active jobs"""
        try:
            for job_id, progress_bar in self.job_progress_bars.items():
                if hasattr(progress_bar, 'target_value'):
                    current_value = progress_bar.value()
                    target_value = progress_bar.target_value
                    
                    # Smooth progress animation
                    if current_value < target_value:
                        new_value = min(target_value, current_value + 1)
                        progress_bar.setValue(new_value)
        except Exception as e:
            self.logger.error(f"Error animating progress bars: {e}")
    
    def animate_sophistication_progress(self):
        """Animate sophistication level progress bar"""
        try:
            if hasattr(self.sophistication_progress, 'target_value'):
                current_value = self.sophistication_progress.value()
                target_value = self.sophistication_progress.target_value
                
                if current_value != target_value:
                    # Smooth animation towards target
                    diff = target_value - current_value
                    step = max(1, abs(diff) // 10)
                    if diff > 0:
                        new_value = min(target_value, current_value + step)
                    else:
                        new_value = max(target_value, current_value - step)
                    
                    self.sophistication_progress.setValue(new_value)
        except Exception as e:
            self.logger.error(f"Error animating sophistication progress: {e}")
    
    def update_live_metrics(self):
        """Update real-time performance metrics"""
        try:
            # Calculate current processing speed
            current_speed = self.calculate_current_speed()
            self.current_speed_label.setText(f"{current_speed} files/min")
            
            # Update batch ETA
            eta = self.calculate_batch_eta()
            self.batch_eta_label.setText(eta)
            
            # Update live metrics
            self.live_metrics['processing_speed'] = current_speed
            
        except Exception as e:
            self.logger.error(f"Error updating live metrics: {e}")
    
    def calculate_current_speed(self):
        """Calculate current processing speed in files per minute"""
        try:
            # This would be calculated from recent job completions
            # Placeholder implementation
            return 15.2
        except:
            return 0.0
    
    def calculate_batch_eta(self):
        """Calculate estimated time for current batch completion"""
        try:
            # This would be calculated from current job progress and speed
            # Placeholder implementation
            return "02:15:30"
        except:
            return "--:--:--"
    
    def load_framework_status(self):
        """Load framework status information"""
        try:
            # Check if framework is running by looking for state file
            state_file = Path("sophistication_state.json")
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                self.framework_status = "Running"
                self.status_label.setText("Status: 🟢 Running")
                self.status_label.setStyleSheet("color: #00ff00;")
                
                # Update metrics from state
                active_jobs = len(state_data.get('active_jobs', []))
                self.active_jobs_label.setText(str(active_jobs))
                
                # Calculate completed today
                completed_today = self.count_completed_today()
                self.completed_today_label.setText(str(completed_today))
                
                # Calculate uptime
                start_time = state_data.get('framework_start_time')
                if start_time:
                    uptime = self.calculate_uptime(start_time)
                    self.uptime_label.setText(uptime)
                
                # Calculate processing rate
                processing_rate = self.calculate_processing_rate()
                self.processing_rate_label.setText(f"{processing_rate} jobs/hour")
                
            else:
                self.framework_status = "Stopped"
                self.status_label.setText("Status: 🔴 Stopped")
                self.status_label.setStyleSheet("color: #ff0000;")
                
        except Exception as e:
            self.logger.error(f"Error loading framework status: {e}")
            self.status_label.setText("Status: ❓ Error")
            self.status_label.setStyleSheet("color: #ffaa00;")
    
    def load_sophistication_metrics(self):
        """Load current sophistication metrics"""
        try:
            state_file = Path("sophistication_state.json")
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                metrics = state_data.get('sophistication_metrics', {})
                
                # Update main level
                current_level = metrics.get('current_level', 88.7)
                self.sophistication_level_label.setText(f"{current_level}%")
                self.sophistication_progress.setValue(int(current_level))
                
                # Update capability breakdown
                capabilities = metrics.get('capabilities', {})
                self.basic_recognition_label.setText(f"{capabilities.get('basic_recognition', 94)}%")
                self.pattern_analysis_label.setText(f"{capabilities.get('pattern_analysis', 89)}%")
                self.professional_skills_label.setText(f"{capabilities.get('professional_skills', 83)}%")
                self.advanced_features_label.setText(f"{capabilities.get('advanced_features', 75)}%")
                
        except Exception as e:
            self.logger.error(f"Error loading sophistication metrics: {e}")
    
    def load_active_jobs(self):
        """Load active analysis jobs"""
        try:
            state_file = Path("sophistication_state.json")
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state_data = json.load(f)
                
                active_jobs = state_data.get('active_jobs', [])
                
                # Update table
                self.jobs_table.setRowCount(len(active_jobs))
                
                for i, job in enumerate(active_jobs):
                    self.jobs_table.setItem(i, 0, QTableWidgetItem(job.get('job_id', '')))
                    self.jobs_table.setItem(i, 1, QTableWidgetItem(job.get('job_type', '')))
                    self.jobs_table.setItem(i, 2, QTableWidgetItem(job.get('status', '')))
                    
                    # Progress bar
                    progress = job.get('progress', 0)
                    progress_item = QTableWidgetItem(f"{progress}%")
                    self.jobs_table.setItem(i, 3, progress_item)
                    
                    self.jobs_table.setItem(i, 4, QTableWidgetItem(job.get('started', '')))
                    self.jobs_table.setItem(i, 5, QTableWidgetItem(job.get('eta', '')))
                
        except Exception as e:
            self.logger.error(f"Error loading active jobs: {e}")
    
    def load_analysis_history(self):
        """Load analysis history"""
        try:
            # Load from database or log files
            # This is a placeholder - implement based on your logging system
            history_data = self.get_recent_analysis_history()
            
            self.history_table.setRowCount(len(history_data))
            
            for i, record in enumerate(history_data):
                self.history_table.setItem(i, 0, QTableWidgetItem(record.get('completed', '')))
                self.history_table.setItem(i, 1, QTableWidgetItem(record.get('type', '')))
                self.history_table.setItem(i, 2, QTableWidgetItem(record.get('duration', '')))
                self.history_table.setItem(i, 3, QTableWidgetItem(record.get('files', '')))
                self.history_table.setItem(i, 4, QTableWidgetItem(record.get('status', '')))
                
        except Exception as e:
            self.logger.error(f"Error loading analysis history: {e}")
    
    def load_live_logs(self):
        """Load live logs from framework"""
        try:
            # Read recent log entries
            log_file = Path("continuous_sophistication.log")
            
            if log_file.exists():
                # Read last 50 lines
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                # Update display
                log_text = ''.join(recent_lines)
                self.logs_display.setPlainText(log_text)
                
                # Scroll to bottom
                cursor = self.logs_display.textCursor()
                cursor.movePosition(cursor.End)
                self.logs_display.setTextCursor(cursor)
                
        except Exception as e:
            self.logger.error(f"Error loading live logs: {e}")
    
    def count_completed_today(self):
        """Count jobs completed today"""
        # Placeholder implementation
        return 5
    
    def calculate_uptime(self, start_time):
        """Calculate framework uptime"""
        try:
            start_dt = datetime.fromisoformat(start_time)
            uptime_delta = datetime.now() - start_dt
            
            hours = int(uptime_delta.total_seconds() // 3600)
            minutes = int((uptime_delta.total_seconds() % 3600) // 60)
            
            return f"{hours}h {minutes}m"
        except:
            return "Unknown"
    
    def calculate_processing_rate(self):
        """Calculate processing rate"""
        # Placeholder implementation
        return 12
    
    def get_recent_analysis_history(self):
        """Get recent analysis history"""
        # Placeholder implementation
        return [
            {
                'completed': '08:55:30',
                'type': 'drum_samples',
                'duration': '2m 15s',
                'files': '150',
                'status': '✅ Success'
            },
            {
                'completed': '08:52:10',
                'type': 'drum_beats',
                'duration': '5m 30s',
                'files': '40',
                'status': '✅ Success'
            }
        ]
    
    def toggle_framework(self):
        """Toggle framework pause/resume"""
        if self.framework_status == "Running":
            # Send pause signal
            self.pause_btn.setText("▶️ Resume Framework")
            # Implement pause logic
        else:
            # Send resume signal
            self.pause_btn.setText("⏸️ Pause Framework")
            # Implement resume logic
    
    def export_report(self):
        """Export analysis report"""
        try:
            # Generate comprehensive report
            report_data = {
                'timestamp': datetime.now().isoformat(),
                'framework_status': self.framework_status,
                'sophistication_metrics': self.sophistication_metrics,
                'active_jobs': self.analysis_jobs
            }
            
            # Save report
            report_file = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w') as f:
                json.dump(report_data, f, indent=2)
            
            self.logger.info(f"Analysis report exported to {report_file}")
            
        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
    
    def clear_logs(self):
        """Clear the logs display"""
        self.logs_display.clear()
    
    def load_live_logs_streaming(self):
        """Load live logs with streaming updates"""
        try:
            # Read recent log entries with streaming
            log_file = Path("continuous_sophistication.log")
            
            if log_file.exists():
                with open(log_file, 'r') as f:
                    f.seek(self.last_log_position)
                    new_lines = f.readlines()
                    self.last_log_position = f.tell()
                
                # Add new lines to display
                if new_lines:
                    filtered_lines = self.filter_log_lines(new_lines)
                    for line in filtered_lines:
                        self.logs_display.append(line.rstrip())
                    
                    # Auto-scroll if enabled
                    if self.auto_scroll_cb.isChecked():
                        cursor = self.logs_display.textCursor()
                        cursor.movePosition(cursor.End)
                        self.logs_display.setTextCursor(cursor)
                        
        except Exception as e:
            self.logger.error(f"Error streaming logs: {e}")
    
    def filter_log_lines(self, lines):
        """Filter log lines based on current filter settings"""
        try:
            filter_level = self.log_level_combo.currentText()
            search_text = self.log_search.currentText().lower()
            
            filtered = []
            for line in lines:
                # Apply level filter
                if filter_level != "ALL":
                    if filter_level not in line:
                        continue
                
                # Apply search filter
                if search_text and search_text not in line.lower():
                    continue
                
                filtered.append(line)
            
            return filtered
        except:
            return lines
    
    def filter_logs(self):
        """Apply log filtering to current display"""
        try:
            # This would re-filter the entire log display
            # For now, just clear and reload
            self.logs_display.clear()
            self.last_log_position = 0
            self.load_live_logs_streaming()
        except Exception as e:
            self.logger.error(f"Error filtering logs: {e}")
    
    def toggle_live_stream(self, enabled):
        """Toggle live log streaming"""
        if enabled:
            self.log_stream_timer.start(500)
        else:
            self.log_stream_timer.stop()
    
    def change_refresh_speed(self, speed_text):
        """Change refresh speed based on selection"""
        try:
            if "Fast" in speed_text:
                interval = 500
            elif "Slow" in speed_text:
                interval = 2000
            else:  # Normal
                interval = 1000
            
            self.refresh_timer.setInterval(interval)
            self.auto_refresh_cb.setText(f"Real-time ({interval/1000}s)")
        except Exception as e:
            self.logger.error(f"Error changing refresh speed: {e}")
    
    def toggle_auto_refresh(self, enabled):
        """Toggle auto-refresh"""
        if enabled:
            current_interval = self.refresh_timer.interval()
            self.refresh_timer.start(current_interval)
            self.animation_timer.start(100)
        else:
            self.refresh_timer.stop()
            self.animation_timer.stop()
