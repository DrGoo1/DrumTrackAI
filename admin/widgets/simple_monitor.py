"""
Real-Time Analysis Monitor Widget
=================================
A real-time monitor for the continuous sophistication framework in DrumTracKAI admin app.
"""

import os
import json
import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QProgressBar, QGroupBox, QComboBox, QCheckBox, QSpinBox
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from datetime import datetime

class SimpleMonitor(QWidget):
    """Real-time analysis monitor widget"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.sophistication_state_file = "production_analysis_results/production_analysis_state.json"
        # Use absolute path for production log file
        import os
        # Get the DrumTracKAI root directory (two levels up from admin/widgets/)
        drumtrackai_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.log_file = os.path.join(drumtrackai_root, "production_batch_analysis.log")
        self.setup_ui()
        
        # Reset log position to read all existing entries
        self.last_log_position = 0
        
        # Setup timer for updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_display)
        self.timer.start(2000)  # Update every 2 seconds
        
        # Force reset log position and load existing log entries immediately
        print(f"[DEBUG] Forcing log position reset to 0")
        self.last_log_position = 0
        self.load_recent_logs()
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("Real-Time Analysis Monitor")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Framework Status Group
        status_group = QGroupBox("Framework Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Status: Checking...")
        self.status_label.setFont(QFont("Arial", 12))
        status_layout.addWidget(self.status_label)
        
        self.time_label = QLabel("Last Update: --:--:--")
        status_layout.addWidget(self.time_label)
        
        layout.addWidget(status_group)
        
        # Framework Control Panel
        control_group = QGroupBox("Framework Control Panel")
        control_layout = QVBoxLayout(control_group)
        
        # Start/Stop controls
        start_stop_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Framework")
        self.start_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        self.start_btn.clicked.connect(self.start_framework)
        start_stop_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop Framework")
        self.stop_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        self.stop_btn.clicked.connect(self.stop_framework)
        start_stop_layout.addWidget(self.stop_btn)
        
        self.restart_btn = QPushButton("🔄 Restart")
        self.restart_btn.setStyleSheet("QPushButton { background-color: #FF9800; color: white; font-weight: bold; padding: 8px; }")
        self.restart_btn.clicked.connect(self.restart_framework)
        start_stop_layout.addWidget(self.restart_btn)
        
        control_layout.addLayout(start_stop_layout)
        
        # Data source selection
        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Data Source:"))
        
        self.data_source_combo = QComboBox()
        self.data_source_combo.addItems([
            "DrumBeats Database",
            "Drummer Database", 
            "Signature Songs Database",
            "Custom Path"
        ])
        self.data_source_combo.currentTextChanged.connect(self.on_data_source_changed)
        source_layout.addWidget(self.data_source_combo)
        
        control_layout.addLayout(source_layout)
        
        # Analysis configuration
        config_layout = QHBoxLayout()
        
        config_layout.addWidget(QLabel("Sophistication Target:"))
        self.sophistication_target_combo = QComboBox()
        self.sophistication_target_combo.addItems(["Basic", "Intermediate", "Advanced", "Expert", "Master"])
        self.sophistication_target_combo.setCurrentText("Expert")
        config_layout.addWidget(self.sophistication_target_combo)
        
        config_layout.addWidget(QLabel("Batch Size:"))
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setRange(1, 100)
        self.batch_size_spin.setValue(10)
        config_layout.addWidget(self.batch_size_spin)
        
        control_layout.addLayout(config_layout)
        
        # Auto-restart option
        auto_layout = QHBoxLayout()
        self.auto_restart_checkbox = QCheckBox("Auto-restart on completion")
        self.auto_restart_checkbox.setChecked(True)
        auto_layout.addWidget(self.auto_restart_checkbox)
        
        self.continuous_mode_checkbox = QCheckBox("Continuous monitoring mode")
        self.continuous_mode_checkbox.setChecked(True)
        auto_layout.addWidget(self.continuous_mode_checkbox)
        
        control_layout.addLayout(auto_layout)
        
        layout.addWidget(control_group)
        
        # Training Progress Overview
        progress_group = QGroupBox("Training Progress Overview")
        progress_layout = QVBoxLayout(progress_group)
        
        # Sophistication progress with detailed info
        self.sophistication_label = QLabel("Current Sophistication: ---%")
        self.sophistication_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        progress_layout.addWidget(self.sophistication_label)
        
        self.sophistication_progress = QProgressBar()
        self.sophistication_progress.setRange(0, 100)
        self.sophistication_progress.setValue(0)
        progress_layout.addWidget(self.sophistication_progress)
        
        # Training quality metrics
        quality_layout = QHBoxLayout()
        self.files_processed_label = QLabel("Files Processed: ---")
        self.avg_quality_label = QLabel("Avg Quality: ---")
        quality_layout.addWidget(self.files_processed_label)
        quality_layout.addWidget(self.avg_quality_label)
        progress_layout.addLayout(quality_layout)
        
        layout.addWidget(progress_group)
        
        # Current Training Job Details
        job_group = QGroupBox("Current Training Job")
        job_layout = QVBoxLayout(job_group)
        
        self.current_job_label = QLabel("Job: No active job")
        self.current_job_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        job_layout.addWidget(self.current_job_label)
        
        self.job_progress_label = QLabel("Progress: ---")
        job_layout.addWidget(self.job_progress_label)
        
        self.job_progress_bar = QProgressBar()
        self.job_progress_bar.setRange(0, 100)
        job_layout.addWidget(self.job_progress_bar)
        
        # Processing details
        details_layout = QHBoxLayout()
        self.current_file_label = QLabel("Current File: ---")
        self.processing_speed_label = QLabel("Speed: --- files/min")
        details_layout.addWidget(self.current_file_label)
        details_layout.addWidget(self.processing_speed_label)
        job_layout.addLayout(details_layout)
        
        layout.addWidget(job_group)
        
        # Training Quality Analysis
        quality_group = QGroupBox("Training Quality Analysis")
        quality_layout = QVBoxLayout(quality_group)
        
        # Quality distribution
        quality_dist_layout = QHBoxLayout()
        self.high_quality_label = QLabel("High Quality: ---")
        self.medium_quality_label = QLabel("Medium Quality: ---")
        self.low_quality_label = QLabel("Low Quality: ---")
        quality_dist_layout.addWidget(self.high_quality_label)
        quality_dist_layout.addWidget(self.medium_quality_label)
        quality_dist_layout.addWidget(self.low_quality_label)
        quality_layout.addLayout(quality_dist_layout)
        
        # Analysis methods breakdown
        self.analysis_methods_label = QLabel("Analysis Methods: ---")
        quality_layout.addWidget(self.analysis_methods_label)
        
        layout.addWidget(quality_group)
        
        # Framework Running Status
        status_group = QGroupBox("Framework Running Status")
        status_layout = QVBoxLayout(status_group)
        
        # Running indicator with visual status
        running_layout = QHBoxLayout()
        
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 20))
        self.status_indicator.setStyleSheet("color: #4CAF50;")  # Green for running
        running_layout.addWidget(self.status_indicator)
        
        self.running_status_label = QLabel("Framework Status: Running")
        self.running_status_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        running_layout.addWidget(self.running_status_label)
        
        running_layout.addStretch()
        
        # Last activity timestamp
        self.last_activity_label = QLabel("Last Activity: 10:04:17 AM")
        running_layout.addWidget(self.last_activity_label)
        
        status_layout.addLayout(running_layout)
        
        # Progress metrics in a clean layout
        metrics_layout = QHBoxLayout()
        
        self.files_processed_label = QLabel("Files Processed: 6")
        self.current_level_label = QLabel("Level: Intermediate → Master")
        self.analysis_count_label = QLabel("Analysis Jobs: 6 completed")
        
        metrics_layout.addWidget(self.files_processed_label)
        metrics_layout.addWidget(self.current_level_label)
        metrics_layout.addWidget(self.analysis_count_label)
        metrics_layout.addStretch()
        
        status_layout.addLayout(metrics_layout)
        
        layout.addWidget(status_group)
        
        # Initialize log tracking variables
        self.log_paused = False
        self.log_line_count = 0
        self.log_error_count = 0
        self.log_warning_count = 0
        self.last_log_position = 0
        
        # Essential control buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Refresh Status")
        refresh_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }")
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)
        
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
    def update_display(self):
        """Update the display with real sophistication data"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.setText(f"Last Update: {current_time}")
        
        # Load sophistication state data
        self.load_sophistication_data()
        
    def load_sophistication_data(self):
        """Load data from production batch analysis log file"""
        try:
            # Read from production batch analysis log
            production_log = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "production_batch_analysis.log")
            
            if os.path.exists(production_log):
                # Parse the log file for progress information
                progress_percentage = 0
                files_processed = 0
                total_files = 0
                current_file = "None"
                analysis_count = 0
                
                with open(production_log, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    
                # Parse log lines for progress data
                for line in reversed(lines[-50:]):  # Check last 50 lines
                    if "[PROGRESS] Progress:" in line:
                        # Extract progress: "Progress: 32.0% (8/25)"
                        import re
                        match = re.search(r'Progress: ([0-9.]+)% \((\d+)/(\d+)\)', line)
                        if match:
                            progress_percentage = float(match.group(1))
                            files_processed = int(match.group(2))
                            total_files = int(match.group(3))
                            break
                    elif "[JOB] Created analysis job:" in line:
                        analysis_count += 1
                    elif "Processing file:" in line or "analysis job:" in line:
                        # Extract current file name
                        if ".wav" in line:
                            parts = line.split(".wav")
                            if parts:
                                filename = parts[0].split()[-1] + ".wav"
                                current_file = filename
                
                # Update UI with parsed data
                if total_files > 0:
                    self.sophistication_label.setText(f"Production Analysis: {progress_percentage:.1f}% ({files_processed}/{total_files} files)")
                    self.sophistication_progress.setValue(int(progress_percentage))
                else:
                    self.sophistication_label.setText("Production Analysis: Starting...")
                    self.sophistication_progress.setValue(0)
                
                # Update status indicators with production data
                self.files_processed_label.setText(f"Files Processed: {files_processed}/{total_files}")
                self.current_level_label.setText(f"Current File: {current_file}")
                self.analysis_count_label.setText(f"Analysis Jobs: {analysis_count} created")
                
                # Update framework status based on process state
                try:
                    # Check if framework process is actually running
                    process_running = False
                    if hasattr(self, 'framework_process') and self.framework_process:
                        try:
                            # Check if process is still alive
                            process_running = self.framework_process.poll() is None
                        except:
                            process_running = False
                    
                    if process_running:
                        if progress_percentage > 0:
                            # Process is running and making progress
                            self.status_indicator.setStyleSheet("color: #4CAF50;")  # Green
                            self.running_status_label.setText("Framework Status: Production Active")
                        else:
                            # Process is running but no progress yet
                            self.status_indicator.setStyleSheet("color: #2196F3;")  # Blue
                            self.running_status_label.setText("Framework Status: Starting")
                    else:
                        if progress_percentage >= 100:
                            # Process completed successfully
                            self.status_indicator.setStyleSheet("color: #9C27B0;")  # Purple
                            self.running_status_label.setText("Framework Status: Completed")
                        else:
                            # Process not running
                            self.status_indicator.setStyleSheet("color: #FF9800;")  # Orange
                            self.running_status_label.setText("Framework Status: Idle")
                            
                    self.last_activity_label.setText(f"Last Update: {datetime.now().strftime('%I:%M:%S %p')}")
                    
                except Exception as e:
                    # Log the specific error for debugging
                    print(f"[ERROR] Framework status error: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    # Default to unknown status
                    self.status_indicator.setStyleSheet("color: #9E9E9E;")  # Gray
                    self.running_status_label.setText("Framework Status: Unknown")
                    self.last_activity_label.setText(f"Status: Error - {str(e)[:30]}")
                
                # Analyze all completed jobs for detailed insights
                total_files = 0
                quality_counts = {'high': 0, 'medium': 0, 'low': 0}
                analysis_methods = set()
                total_score = 0
                latest_job = None
                
                if completed_jobs:
                    latest_job = completed_jobs[-1]
                    
                    for job in completed_jobs:
                        if 'results' in job and 'files_analyzed' in job['results']:
                            files = job['results']['files_analyzed']
                            total_files += len(files)
                            
                            for file_data in files:
                                # Count quality distribution
                                training_value = file_data.get('training_value', 'unknown')
                                if training_value in quality_counts:
                                    quality_counts[training_value] += 1
                                
                                # Collect analysis methods
                                methods = file_data.get('analysis_methods', [])
                                analysis_methods.update(methods)
                                
                                # Sum sophistication scores
                                score = file_data.get('sophistication_score', 0)
                                total_score += score
                
                # Update training progress overview
                avg_quality = (total_score / total_files) if total_files > 0 else 0
                self.files_processed_label.setText(f"Files Processed: {total_files}")
                self.avg_quality_label.setText(f"Avg Quality: {avg_quality:.2f}")
                
                # Update current job details
                if latest_job:
                    job_type = latest_job.get('analysis_type', 'Unknown').replace('AnalysisType.', '')
                    job_status = latest_job.get('status', 'unknown')
                    
                    if job_status == 'completed':
                        self.status_label.setText("Status: Training Active (Jobs completed)")
                        self.current_job_label.setText(f"Last Job: {job_type} Analysis")
                        
                        # Show job completion details
                        if 'results' in latest_job and 'files_analyzed' in latest_job['results']:
                            job_files = len(latest_job['results']['files_analyzed'])
                            self.job_progress_label.setText(f"Completed: {job_files} files analyzed")
                            self.job_progress_bar.setValue(100)
                            
                            # Show most recent file processed
                            if latest_job['results']['files_analyzed']:
                                last_file = latest_job['results']['files_analyzed'][-1]
                                filename = last_file.get('filename', 'Unknown')
                                self.current_file_label.setText(f"Last File: {filename}")
                            
                            # Calculate processing speed from job timing
                            started = latest_job.get('started_at', '')
                            completed = latest_job.get('completed_at', '')
                            if started and completed:
                                try:
                                    from datetime import datetime
                                    start_time = datetime.strptime(started, '%Y-%m-%d %H:%M:%S.%f')
                                    end_time = datetime.strptime(completed, '%Y-%m-%d %H:%M:%S.%f')
                                    duration_minutes = (end_time - start_time).total_seconds() / 60
                                    if duration_minutes > 0:
                                        speed = job_files / duration_minutes
                                        self.processing_speed_label.setText(f"Speed: {speed:.1f} files/min")
                                    else:
                                        self.processing_speed_label.setText("Speed: Very fast")
                                except:
                                    self.processing_speed_label.setText("Speed: Calculating...")
                        else:
                            self.job_progress_label.setText("Job completed (no file details)")
                            self.job_progress_bar.setValue(100)
                    else:
                        self.status_label.setText(f"Status: {job_status}")
                        self.current_job_label.setText(f"Job: {job_type} ({job_status})")
                        self.job_progress_label.setText(f"Status: {job_status}")
                        
                # Update training quality analysis
                total_quality_files = sum(quality_counts.values())
                if total_quality_files > 0:
                    high_pct = (quality_counts['high'] / total_quality_files) * 100
                    medium_pct = (quality_counts['medium'] / total_quality_files) * 100
                    low_pct = (quality_counts['low'] / total_quality_files) * 100
                    
                    self.high_quality_label.setText(f"High Quality: {quality_counts['high']} ({high_pct:.1f}%)")
                    self.medium_quality_label.setText(f"Medium Quality: {quality_counts['medium']} ({medium_pct:.1f}%)")
                    self.low_quality_label.setText(f"Low Quality: {quality_counts['low']} ({low_pct:.1f}%)")
                else:
                    self.high_quality_label.setText("High Quality: ---")
                    self.medium_quality_label.setText("Medium Quality: ---")
                    self.low_quality_label.setText("Low Quality: ---")
                
                # Update analysis methods
                if analysis_methods:
                    methods_str = ", ".join(sorted(analysis_methods))
                    self.analysis_methods_label.setText(f"Analysis Methods: {methods_str}")
                else:
                    self.analysis_methods_label.setText("Analysis Methods: No data")
                    
                if not completed_jobs:
                    self.status_label.setText("Status: No training jobs found")
                    self.current_job_label.setText("Job: No jobs detected")
                    self.job_progress_label.setText("No training activity detected")
                    self.current_file_label.setText("Current File: None")
                    self.processing_speed_label.setText("Speed: No data")
                
            else:
                # No production log file found - set default values
                self.sophistication_label.setText("Production Analysis: No data")
                self.sophistication_progress.setValue(0)
                self.files_processed_label.setText("Files Processed: No data")
                self.current_level_label.setText("Current File: None")
                self.analysis_count_label.setText("Analysis Jobs: No data")
                
                # Set framework status to idle if no log file
                self.status_indicator.setStyleSheet("color: #FF9800;")  # Orange
                self.running_status_label.setText("Framework Status: Idle")
                self.last_activity_label.setText("No production log found")
                
        except Exception as e:
            print(f"[ERROR] Error loading sophistication data: {e}")
            import traceback
            traceback.print_exc()
            
            # Set error status with specific error information
            self.sophistication_label.setText("Production Analysis: Error")
            self.sophistication_progress.setValue(0)
            self.files_processed_label.setText("Files Processed: Error")
            self.current_level_label.setText("Current File: Error")
            self.analysis_count_label.setText("Analysis Jobs: Error")
            
            # Set framework status to error
            self.status_indicator.setStyleSheet("color: #F44336;")  # Red
            self.running_status_label.setText("Framework Status: Error")
            self.last_activity_label.setText(f"Error: {str(e)[:50]}")
            
    def load_recent_logs(self):
        """Load and stream real-time log entries from the log file"""
        if self.log_paused:
            print("[DEBUG] Log is paused, skipping load_recent_logs")
            return
            
        # Minimal debug to verify timer is running
        print(f"[DEBUG] Timer tick: {datetime.now().strftime('%H:%M:%S')}")
            
        try:
            # Load recent log entries from the framework log file
            
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    # Read all lines
                    lines = f.readlines()
                    
                    self.logger.info(f"Total lines in log file: {len(lines)}")
                    self.logger.info(f"Last log position: {self.last_log_position}")
                    
                    # Check if there are new lines since last read
                    if len(lines) > self.last_log_position:
                        new_lines = lines[self.last_log_position:]
                        self.last_log_position = len(lines)
                        
                        self.logger.info(f"Processing {len(new_lines)} new lines")
                        
                        # Process and display new lines
                        for line in new_lines:
                            line = line.strip()
                            if line:
                                self.add_formatted_log_line(line)
                    else:
                        self.logger.info("No new lines to process")
            else:
                self.logger.warning(f"Log file does not exist: {self.log_file}")
                        
            # Update statistics
            if os.path.exists(self.log_file):
                self.update_log_statistics()
                
                # Auto-scroll if enabled
                if self.auto_scroll_checkbox.isChecked():
                    scrollbar = self.log_area.verticalScrollBar()
                    scrollbar.setValue(scrollbar.maximum())
                    
                # Update last log update time
                current_time = datetime.now().strftime('%H:%M:%S')
                self.last_log_update_label.setText(f"Last Update: {current_time}")
                        
        except Exception as e:
            self.logger.error(f"Error loading log data: {e}")
            
    def add_formatted_log_line(self, line):
        """Add a formatted log line with color coding based on log level"""
        print(f"[DEBUG] add_formatted_log_line called with: {line[:50]}...")
        
        # Determine log level and apply color formatting
        line_lower = line.lower()
        
        # Color coding based on log level
        if 'error' in line_lower or 'exception' in line_lower:
            color = '#ff6b6b'  # Red for errors
            self.log_error_count += 1
        elif 'warning' in line_lower or 'warn' in line_lower:
            color = '#ffa726'  # Orange for warnings
            self.log_warning_count += 1
        elif 'info' in line_lower:
            color = '#66bb6a'  # Green for info
        elif 'debug' in line_lower:
            color = '#9e9e9e'  # Gray for debug
        elif 'completed' in line_lower or 'success' in line_lower:
            color = '#4fc3f7'  # Blue for success
        elif 'starting' in line_lower or 'processing' in line_lower:
            color = '#ffeb3b'  # Yellow for activity
        else:
            color = '#ffffff'  # White for general
        
        # Check filter
        filter_level = self.log_level_combo.currentText()
        if filter_level != "All":
            if filter_level.lower() not in line_lower:
                return  # Skip this line if it doesn't match filter
        
        # Format the line with timestamp if it doesn't have one
        if not line.startswith('2025-') and not line.startswith('['):
            timestamp = datetime.now().strftime('%H:%M:%S')
            formatted_line = f"[{timestamp}] {line}"
        else:
            formatted_line = line
        
        # Add the formatted line with color
        # Remove problematic palette call that doesn't exist in PySide6
        cursor = self.log_area.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        
        # Insert colored text
        html_content = f'<span style="color: {color};">{formatted_line}</span><br>'
        
        try:
            cursor.insertHtml(html_content)
        except Exception as e:
            # Fallback to simple append if HTML fails (without debug prefix)
            self.log_area.append(formatted_line)
        
        self.log_line_count += 1
        
        # Keep log manageable (limit to last 1000 lines)
        if self.log_line_count > 1000:
            self.clear_old_log_lines()
            
    def clear_old_log_lines(self):
        """Clear old log lines to keep the display manageable"""
        # Get current text and keep only the last 500 lines
        current_text = self.log_area.toPlainText()
        lines = current_text.split('\n')
        if len(lines) > 500:
            # Keep the last 500 lines
            kept_lines = lines[-500:]
            self.log_area.clear()
            
            # Re-add the kept lines
            for line in kept_lines:
                if line.strip():
                    self.add_formatted_log_line(line.strip())
                    
            self.log_line_count = len(kept_lines)
            
    def update_log_statistics(self):
        """Update log statistics display"""
        self.log_lines_label.setText(f"Lines: {self.log_line_count}")
        self.log_errors_label.setText(f"Errors: {self.log_error_count}")
        self.log_warnings_label.setText(f"Warnings: {self.log_warning_count}")
        
    def toggle_log_pause(self):
        """Toggle log streaming pause/resume"""
        self.log_paused = self.pause_log_btn.isChecked()
        if self.log_paused:
            self.pause_log_btn.setText("▶ Resume")
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"[DEBUG] [{current_time}] === LOG PAUSED ===")
        else:
            self.pause_log_btn.setText("⏸ Pause")
            current_time = datetime.now().strftime('%H:%M:%S')
            print(f"[DEBUG] [{current_time}] === LOG RESUMED ===")
            
    def refresh_data(self):
        """Refresh data manually"""
        print(f"[DEBUG] Manual refresh triggered at {datetime.now().strftime('%H:%M:%S')}")
        self.update_display()
        
    def clear_log(self):
        """Clear the log display"""
        print(f"[DEBUG] Log cleared at {datetime.now().strftime('%H:%M:%S')}")
        
    def reset_log_position(self):
        """Reset log position to force reprocessing of all log entries"""
        print(f"[DEBUG] Resetting log position from {self.last_log_position} to 0")
        self.last_log_position = 0
        self.log_line_count = 0
        self.log_error_count = 0
        self.log_warning_count = 0
        
        # Clear existing display (log_area not available in this widget)
        print(f"[DEBUG] Log position reset to 0")
        
        # Force immediate reload
        print(f"[DEBUG] Forcing immediate log reload")
        self.load_recent_logs()
        
        print(f"[DEBUG] Log position reset complete")
        
    def start_framework(self):
        """Start the production batch analysis framework - NO MOCK PROCESSES"""
        try:
            print(f"[DEBUG] Starting production batch analysis framework...")
            
            # Update status indicator to show starting
            self.status_indicator.setStyleSheet("color: #FF9800;")  # Orange
            self.running_status_label.setText("Framework Status: Starting...")
            
            # Get configuration
            data_source = self.data_source_combo.currentText()
            sophistication_target = self.sophistication_target_combo.currentText()
            batch_size = self.batch_size_spin.value()
            
            print(f"[DEBUG] Configuration: {data_source}, {sophistication_target}, batch_size={batch_size}")
            
            # Create production framework command using DrumTracKAI environment
            import subprocess
            import sys
            
            # Use the DrumTracKAI environment Python executable (absolute path)
            import os
            drumtrackai_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            drumtrackai_python = os.path.join(drumtrackai_root, "drumtrackai_env", "Scripts", "python.exe")
            framework_script = os.path.join(drumtrackai_root, "production_batch_analysis_system.py")
            
            # Verify paths exist
            if not os.path.exists(drumtrackai_python):
                raise FileNotFoundError(f"DrumTracKAI Python not found: {drumtrackai_python}")
            if not os.path.exists(framework_script):
                raise FileNotFoundError(f"Production framework script not found: {framework_script}")
            
            # The production framework processes verified data sources only
            cmd = [drumtrackai_python, framework_script]
            
            print(f"[DEBUG] Starting PRODUCTION framework with command: {' '.join(cmd)}")
            
            # Start the production process
            self.framework_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd="."
            )
            
            print(f"[DEBUG] Production framework started with PID {self.framework_process.pid}")
            print(f"[DEBUG] Data Source: {data_source}")
            print(f"[DEBUG] Target: {sophistication_target}, Batch Size: {batch_size}")
            print(f"[DEBUG] Using PRODUCTION SYSTEM - No mock processes")
            
            # Update status indicator to show running
            self.status_indicator.setStyleSheet("color: #4CAF50;")  # Green
            self.running_status_label.setText("Framework Status: Production Active")
            self.last_activity_label.setText(f"Started: {datetime.now().strftime('%I:%M:%S %p')}")
            
            # Update button states
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.restart_btn.setEnabled(True)
            
        except Exception as e:
            self.logger.error(f"Error starting production framework: {e}")
            print(f"[DEBUG] ERROR: Failed to start production framework - {str(e)}")
            
            # Update status indicator to show error
            self.status_indicator.setStyleSheet("color: #f44336;")  # Red
            self.running_status_label.setText("Framework Status: Error")
            self.last_activity_label.setText(f"Error: {str(e)[:50]}...")
            
    def stop_framework(self):
        """Stop the continuous sophistication framework"""
        try:
            print(f"[DEBUG] Stopping continuous sophistication framework...")
            
            # Update status indicator to show stopping
            self.status_indicator.setStyleSheet("color: #FF9800;")  # Orange
            self.running_status_label.setText("Framework Status: Stopping...")
            
            if hasattr(self, 'framework_process') and self.framework_process:
                self.framework_process.terminate()
                self.framework_process.wait(timeout=10)
                print(f"[DEBUG] Framework stopped successfully")
            else:
                # Try to find and stop any running framework processes
                import subprocess
                try:
                    # Kill any running continuous sophistication processes
                    subprocess.run(["taskkill", "/F", "/IM", "python.exe", "/FI", "WINDOWTITLE eq *sophistication*"], 
                                 capture_output=True, check=False)
                    print(f"[DEBUG] Attempted to stop any running framework processes")
                except:
                    pass
            
            # Update status indicator to show stopped
            self.status_indicator.setStyleSheet("color: #9E9E9E;")  # Gray
            self.running_status_label.setText("Framework Status: Stopped")
            self.last_activity_label.setText(f"Stopped: {datetime.now().strftime('%I:%M:%S %p')}")
            
            # Update button states
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.restart_btn.setEnabled(False)
            
        except Exception as e:
            self.logger.error(f"Error stopping framework: {e}")
            print(f"[DEBUG] ERROR: Failed to stop framework - {str(e)}")
            
            # Update status indicator to show error
            self.status_indicator.setStyleSheet("color: #f44336;")  # Red
            self.running_status_label.setText("Framework Status: Stop Error")
            self.last_activity_label.setText(f"Error: {str(e)[:50]}...")
            
    def restart_framework(self):
        """Restart the continuous sophistication framework"""
        print(f"[DEBUG] Restarting continuous sophistication framework...")
        
        # Update status indicator to show restarting
        self.status_indicator.setStyleSheet("color: #FF9800;")  # Orange
        self.running_status_label.setText("Framework Status: Restarting...")
        
        self.stop_framework()
        # Wait a moment before restarting
        import time
        time.sleep(2)
        self.start_framework()
        
    def on_data_source_changed(self, source):
        """Handle data source selection change"""
        current_time = datetime.now().strftime('%H:%M:%S')
        self.log_area.append(f"{current_time} - Data source changed to: {source}")
        
        # Update sophistication target recommendations based on data source
        if "Drummer" in source:
            self.sophistication_target_combo.setCurrentText("Advanced")
            self.batch_size_spin.setValue(5)  # Smaller batches for detailed drummer analysis
        elif "Signature Songs" in source:
            self.sophistication_target_combo.setCurrentText("Expert")
            self.batch_size_spin.setValue(3)  # Very detailed analysis for signature songs
        elif "DrumBeats" in source:
            self.sophistication_target_combo.setCurrentText("Expert")
            self.batch_size_spin.setValue(10)  # Standard batch size for drum beats
        else:
            self.sophistication_target_combo.setCurrentText("Intermediate")
            self.batch_size_spin.setValue(8)  # Conservative settings for custom paths
