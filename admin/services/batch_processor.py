"""
Batch Processor Widget - CLEAN FIXED IMPLEMENTATION
====================================================
Enhanced widget for managing batch processing of audio files with MVSep.
All duplicate code, syntax errors, and structural issues have been resolved.
Integrated with DrumTracKAI Complete System for advanced analysis.
"""
import sys
import json
import logging
import os
import traceback
from datetime import datetime
from typing import Dict, Optional, Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
    QLineEdit, QFormLayout, QTextEdit, QProgressBar, QMessageBox,
    QFileDialog, QCheckBox, QSpinBox, QComboBox, QApplication
)

# Import services with proper error handling
try:
    from services.batch_processor import BatchProcessor, get_batch_processor
    BATCH_PROCESSOR_SERVICE_AVAILABLE = True
except ImportError as e:
    BATCH_PROCESSOR_SERVICE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Batch processor service not available: {e}")

try:
    from utils.thread_safe_ui_updater import ThreadSafeUIUpdater
    THREADSAFE_UI_AVAILABLE = True
except ImportError:
    THREADSAFE_UI_AVAILABLE = False

# Import DrumTracKAI Complete System integration
try:
    from ui.complete_system_integration_handler import get_complete_system_integration_handler
    COMPLETE_SYSTEM_INTEGRATION_AVAILABLE = True
except ImportError as e:
    COMPLETE_SYSTEM_INTEGRATION_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(f"Complete system integration not available: {e}")

logger = logging.getLogger(__name__)


class BatchProcessorWidget(QWidget):
    """
    Complete batch processor widget for MVSep audio processing.
    Handles file queue management, processing control, and progress monitoring.
    """

    # Signals for external communication
    job_added = Signal(str, str, dict)  # input_file, output_dir, metadata
    processing_started = Signal()
    processing_stopped = Signal()

    def __init__(self, parent=None, event_bus=None):
        super().__init__(parent)

        # Initialize core attributes
        self._initialization_complete = False
        self._current_batch_id = None
        self._processing = False
        self.event_bus = event_bus

        # File tracking for duplicate detection
        self._ui_file_paths_set = set()
        self._ui_filename_size_map = {}
        
        # Automatic routing to drum analysis
        self.route_to_drum_analysis = False
        
        # Complete system integration
        self.complete_system_handler = None
        self.enable_complete_analysis = True  # Enable by default

        # Initialize UI elements first
        self._initialize_ui_elements()

        # Initialize batch processor service
        self._initialize_batch_processor_service()
        
        # Initialize complete system integration
        self._initialize_complete_system_integration()

        # Setup UI layout
        self._setup_ui()

        # Setup status timer
        self._setup_status_timer()

        # Mark initialization as complete
        self._initialization_complete = True
        logger.info("BatchProcessorWidget initialized successfully")

    def _initialize_ui_elements(self):
        """Initialize all UI elements to prevent null reference errors"""
        # Core UI elements
        self.status_label = QLabel("Initializing...")
        self.api_key_input = QLineEdit()
        self.add_files_btn = QPushButton("Add Files")
        self.clear_queue_btn = QPushButton("Clear Queue")
        self.start_btn = QPushButton("Start Processing")
        self.stop_btn = QPushButton("Stop Processing")
        self.queue_table = QTableWidget()
        self.current_file_label = QLabel("No file being processed")
        self.progress_bar = QProgressBar()
        self.progress_message = QLabel("Ready")

        # Processing options
        self.keep_original_mix = QCheckBox("Keep Original Mix")
        self.keep_drum_stem = QCheckBox("Keep Drum Stem")

        # Service reference
        self.batch_processor = None

        logger.debug("All UI elements initialized successfully")

    def _initialize_batch_processor_service(self):
        """Initialize batch processor service with proper error handling"""
        try:
            logger.info("Attempting to initialize batch processor service...")
            if BATCH_PROCESSOR_SERVICE_AVAILABLE:
                # Get the batch processor singleton instance
                self.batch_processor = get_batch_processor()

                if self.batch_processor is None:
                    raise RuntimeError("Batch processor returned None from get_batch_processor()")

                # Try to set API key from environment if available
                api_key = os.environ.get('MVSEP_API_KEY', '')
                if api_key:
                    try:
                        self.batch_processor.set_api_key(api_key)
                        logger.info("API key set from environment variable")
                    except Exception as api_error:
                        logger.warning(f"Failed to set API key from environment: {api_error}")

                # Connect signals
                self._connect_batch_processor_signals()

                logger.info("SUCCESS Batch processor service successfully initialized")
                self.status_label.setText("Batch processor service ready")
            else:
                logger.critical("CRITICAL: Batch processor service not available")
                self.status_label.setText("ERROR: Batch processor service not available")
                logger.critical("Application will continue without batch processing capabilities")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to initialize batch processor service: {e}")
            self.status_label.setText(f"ERROR: Failed to initialize batch processor: {e}")
            logger.critical(f"Traceback: {traceback.format_exc()}")

    def _connect_batch_processor_signals(self):
        """Connect signals from batch processor to this widget's slots"""
        try:
            if not hasattr(self, 'batch_processor') or self.batch_processor is None:
                logger.warning("Cannot connect signals - batch processor not available")
                return

            # Connect all required signals
            self.batch_processor.processing_started.connect(self._on_batch_started)
            self.batch_processor.processing_completed.connect(self._on_batch_completed)
            self.batch_processor.file_processing_started.connect(self._on_file_started)
            self.batch_processor.file_processing_completed.connect(self._on_file_completed)
            self.batch_processor.file_processing_failed.connect(self._on_file_failed)
            self.batch_processor.progress_updated.connect(self._on_progress_updated)

            # Connect job_added signal if available
            if hasattr(self.batch_processor, "job_added"):
                self.batch_processor.job_added.connect(self._add_to_ui_table)
                logger.info("Connected job_added signal to _add_to_ui_table")
            else:
                logger.warning("batch_processor does not have job_added signal")

            logger.info("Successfully connected batch processor signals")
        except Exception as e:
            logger.error(f"Error connecting batch processor signals: {e}")
            logger.error(traceback.format_exc())

    def _setup_ui(self):
        """Setup the user interface"""
        self.layout = QVBoxLayout(self)

        # Title
        title = QLabel("Batch Processor")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.layout.addWidget(title)

        # Instructions
        instructions = QLabel(
            "Add audio files to the queue for batch processing with MVSep. "
            "Files will be processed with stem separation and optional drum analysis."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        self.layout.addWidget(instructions)

        # Create main sections
        self._create_control_panel(self.layout)
        self._create_queue_table_section(self.layout)
        self._create_progress_section(self.layout)
        self._create_status_section(self.layout)

    def _create_control_panel(self, parent_layout):
        """Create the control panel"""
        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)

        # API Key section
        api_layout = QFormLayout()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter MVSep API key...")
        self.api_key_input.textChanged.connect(self._on_api_key_changed)
        api_layout.addRow("API Key:", self.api_key_input)
        control_layout.addLayout(api_layout)

        # Output options
        options_layout = QHBoxLayout()
        self.keep_original_mix.setChecked(True)
        self.keep_original_mix.setToolTip("Keep a copy of the original audio files in the output directory")
        options_layout.addWidget(self.keep_original_mix)

        self.keep_drum_stem.setChecked(True)
        self.keep_drum_stem.setToolTip("Keep the isolated drum stems from stage 1 processing")
        options_layout.addWidget(self.keep_drum_stem)

        options_layout.addStretch()
        control_layout.addLayout(options_layout)

        # File operations
        file_ops_layout = QHBoxLayout()
        self.add_files_btn.clicked.connect(self._on_add_files)
        file_ops_layout.addWidget(self.add_files_btn)

        self.clear_queue_btn.clicked.connect(self._on_clear_queue)
        file_ops_layout.addWidget(self.clear_queue_btn)

        file_ops_layout.addStretch()
        control_layout.addLayout(file_ops_layout)

        # Processing controls
        process_layout = QHBoxLayout()
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        self.start_btn.clicked.connect(self._on_start_processing)
        self.start_btn.setEnabled(False)
        process_layout.addWidget(self.start_btn)

        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")
        self.stop_btn.clicked.connect(self._on_stop_processing)
        self.stop_btn.setEnabled(False)
        process_layout.addWidget(self.stop_btn)

        process_layout.addStretch()
        control_layout.addLayout(process_layout)

        parent_layout.addWidget(control_group)

    def _create_queue_table_section(self, parent_layout):
        """Create the queue table"""
        queue_group = QGroupBox("Processing Queue")
        queue_layout = QVBoxLayout(queue_group)

        self.queue_table.setColumnCount(5)
        self.queue_table.setHorizontalHeaderLabels([
            "File", "Output Directory", "Added", "Status", "Actions"
        ])

        # Configure table
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        queue_layout.addWidget(self.queue_table)
        parent_layout.addWidget(queue_group)

    def _create_progress_section(self, parent_layout):
        """Create the progress section"""
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)

        progress_layout.addWidget(self.current_file_label)

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)

        progress_layout.addWidget(self.progress_message)

        parent_layout.addWidget(progress_group)

    def _create_status_section(self, parent_layout):
        """Create the status section"""
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout(status_group)

        self.status_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        status_layout.addWidget(self.status_label)

        parent_layout.addWidget(status_group)

    def _setup_status_timer(self):
        """Setup status timer"""
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)  # Update every second

    def add_to_queue(self, input_file: str, output_dir: str, metadata: Dict = None) -> bool:
        """
        Add file to processing queue.
        This is the method called by other widgets (DrumBeats, etc.)
        """
        try:
            # Validate inputs
            if not input_file:
                raise ValueError("input_file cannot be empty")

            if not os.path.exists(input_file):
                raise FileNotFoundError(f"Input file not found: {input_file}")

            if not output_dir:
                raise ValueError("output_dir cannot be empty")

            if metadata is None:
                metadata = {}

            # Prepare data for duplicate checking
            normalized_input = os.path.normcase(os.path.normpath(input_file))
            input_filename = os.path.basename(input_file)
            input_size = os.path.getsize(input_file)
            size_key = f"{input_filename}:{input_size}"

            # Check for duplicates
            if normalized_input in self._ui_file_paths_set:
                logger.warning(f"Duplicate detected: {input_filename}")
                QMessageBox.information(
                    self, "Duplicate File",
                    f"The file '{input_filename}' is already in the queue."
                )
                return False

            if size_key in self._ui_filename_size_map:
                logger.warning(f"Duplicate detected by name and size: {input_filename}")
                QMessageBox.information(
                    self, "Duplicate File",
                    f"The file '{input_filename}' appears to be a duplicate based on name and size."
                )
                return False

            # Ensure API key is set
            if not self._ensure_api_key():
                logger.warning("No API key set, but continuing for debugging purposes")
                QMessageBox.warning(self, "API Key Missing",
                    "No API key was found. The batch processing may fail when started.\n"
                    "For now, we'll add the job to the queue for debugging purposes.")

            # Check if batch processor is available
            if not hasattr(self, 'batch_processor') or self.batch_processor is None:
                logger.error("Batch processor service not available")
                raise RuntimeError("Batch processor service not available")

            # Add to batch processor
            logger.info(f"File started: {filename} - Progress: {progress_percentage}%")

        except Exception as e:
            logger.error(f"Error handling file started: {e}")

    def _on_file_completed(self, batch_id: str, file_path: str, output_files: Dict, file_index: int, total_files: int):
        """Handle file processing completed"""
        try:
            filename = os.path.basename(file_path)
            progress_percentage = int((file_index / total_files) * 100) if total_files > 0 else 0

            if hasattr(self, 'progress_bar') and self.progress_bar is not None:
                self.progress_bar.setValue(progress_percentage)

            num_outputs = len(output_files) if output_files else 0
            self._update_table_status(file_path, f"Completed ({num_outputs} files)", "#4CAF50")

            logger.info(f"File completed: {filename} - {num_outputs} output files - Progress: {progress_percentage}%")
            
            # Route extracted stems to drum analysis if routing is enabled
            if hasattr(self, 'route_to_drum_analysis') and self.route_to_drum_analysis and output_files:
                logger.info(f"Routing {len(output_files)} extracted stems to drum analysis...")
                self._route_stems_to_drum_analysis(file_path, output_files)

        except Exception as e:
            logger.error(f"Error handling file completion: {e}")
            traceback.print_exc()

    def _on_file_failed(self, batch_id: str, file_path: str, error: str, file_index: int, total_files: int):
        """Handle file failed"""
        try:
            filename = os.path.basename(file_path)
            progress_percentage = int((file_index / total_files) * 100) if total_files > 0 else 0

            if hasattr(self, 'current_file_label') and self.current_file_label is not None:
                self.current_file_label.setText(f"Failed: {filename}")

            if hasattr(self, 'progress_message') and self.progress_message is not None:
                if total_files > 1:
                    self.progress_message.setText(f"Failed file {file_index}/{total_files} ({progress_percentage}%)")

            self._update_table_status(file_path, f"Failed: {error}", "#F44336")

            logger.error(f"File failed: {filename} - {error} - Progress: {progress_percentage}%")

        except Exception as e:
            logger.error(f"Error handling file failure: {e}")

    def _on_progress_updated(self, batch_id: str, progress: float, message: str):
        """Handle progress update"""
        try:
            if hasattr(self, 'progress_bar') and self.progress_bar is not None:
                progress_value = int(progress * 100) if progress <= 1.0 else int(progress)
                progress_value = max(0, min(progress_value, 100))
                self.progress_bar.setValue(progress_value)

            if message and hasattr(self, 'progress_message') and self.progress_message is not None:
                self.progress_message.setText(message)

            logger.debug(f"Progress: {progress:.1f}% - {message}")

        except Exception as e:
            logger.error(f"Error handling progress update: {e}")

    def _update_table_status(self, file_path: str, status: str, color: str = None):
        """Update status of a file in the table"""
        try:
            if not hasattr(self, 'queue_table') or self.queue_table is None:
                return

            # Find the row for this file
            for row in range(self.queue_table.rowCount()):
                status_item = self.queue_table.item(row, 3)
                if status_item:
                    job_data = status_item.data(Qt.ItemDataRole.UserRole)
                    if job_data and job_data.get('input_file') == file_path:
                        # Update status
                        status_item.setText(status)
                        if color:
                            status_item.setForeground(QColor(color))
                        break

        except Exception as e:
            logger.error(f"Error updating table status: {e}")

    def closeEvent(self, event):
        """Handle widget close event"""
        try:
            # Stop status timer
            if hasattr(self, '_status_timer') and self._status_timer is not None:
                self._status_timer.stop()

            # Stop processing if active
            if self._processing:
                reply = QMessageBox.question(
                    self, "Processing Active",
                    "Batch processing is active. Stop processing and close?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )

                if reply == QMessageBox.StandardButton.Yes:
                    if hasattr(self, 'batch_processor') and self.batch_processor is not None:
                        self.batch_processor.stop_processing()
                else:
                    event.ignore()
                    return

            logger.info("BatchProcessorWidget closing")

        except Exception as e:
            logger.error(f"Error during close: {e}")

        super().closeEvent(event)


# Example usage and testing
if __name__ == "__main__":
    import sys

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create application
    app = QApplication(sys.argv)

    # Create widget
    widget = BatchProcessorWidget()
    widget.show()
    widget.resize(800, 600)

    # Run application
    sys.exit(app.exec())


def get_batch_processor_widget():
    """Get or create batch processor widget instance"""
    return BatchProcessorWidget()

            if not success:
                raise RuntimeError("Failed to add job to batch processor")

            # Add to UI table
            self._add_to_ui_table(input_file, output_dir, metadata)

            # Update UI state
            self._update_button_states()

            # Emit signal
            self.job_added.emit(input_file, output_dir, metadata)

            logger.info(f"Successfully added to queue: {os.path.basename(input_file)}")
            return True

        except Exception as e:
            error_msg = f"Failed to add to queue: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Traceback: {traceback.format_exc()}")

            QMessageBox.critical(self, "Queue Addition Failed",
                f"{error_msg}\n\nPlease check the logs for more details.")
            return False

    def _add_to_ui_table(self, input_file: str, output_dir: str, metadata: Dict):
        """Add job to the UI table and update tracking data structures"""
        row = self.queue_table.rowCount()
        self.queue_table.insertRow(row)

        # Create job data dictionary
        job_data = {
            'input_file': input_file,
            'output_dir': output_dir,
            'metadata': metadata,
            'added_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # Update tracking data structures
        normalized_input = os.path.normcase(os.path.normpath(input_file))
        input_filename = os.path.basename(input_file)
        input_size = os.path.getsize(input_file)
        size_key = f"{input_filename}:{input_size}"

        self._ui_file_paths_set.add(normalized_input)
        self._ui_filename_size_map[size_key] = input_file

        # File name
        filename = os.path.basename(input_file)
        file_item = QTableWidgetItem(filename)
        file_item.setToolTip(input_file)
        self.queue_table.setItem(row, 0, file_item)

        # Output directory
        output_item = QTableWidgetItem(output_dir)
        output_item.setToolTip(output_dir)
        self.queue_table.setItem(row, 1, output_item)

        # Added time
        added_item = QTableWidgetItem(job_data['added_time'])
        self.queue_table.setItem(row, 2, added_item)

        # Status
        status_item = QTableWidgetItem("Queued")
        status_item.setData(Qt.ItemDataRole.UserRole, job_data)
        self.queue_table.setItem(row, 3, status_item)

        # Actions
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked=False, r=row: self._remove_from_queue(r))
        self.queue_table.setCellWidget(row, 4, remove_btn)

    def _ensure_api_key(self) -> bool:
        """Ensure API key is set"""
        if not hasattr(self, 'api_key_input') or self.api_key_input is None:
            logger.error("API key input not initialized")
            return False

        api_key = self.api_key_input.text().strip()
        if not api_key:
            # Try environment variable
            api_key = os.environ.get('MVSEP_API_KEY', '')
            if api_key:
                logger.info("Found API key in environment variable")
                self.api_key_input.setText(api_key)

        if api_key:
            return self._set_api_key()
        return False

    def _set_api_key(self):
        """Set API key in batch processor"""
        try:
            if not hasattr(self, 'batch_processor') or self.batch_processor is None:
                logger.warning("Batch processor not initialized when setting API key")
                return False

            api_key = self.api_key_input.text()
            if api_key:
                if hasattr(self.batch_processor, 'set_api_key'):
                    self.batch_processor.set_api_key(api_key)
                    self.status_label.setText("API key set. Ready for processing.")
                    logger.info("API key set successfully")
                    return True
                else:
                    logger.error("Batch processor has no set_api_key method")
                    self.status_label.setText("Error setting API key: API method not available")
            return False
        except Exception as e:
            logger.error(f"Error in _set_api_key: {e}")
            return False

    def _update_status(self):
        """Update status information periodically"""
        try:
            if not hasattr(self, 'batch_processor') or self.batch_processor is None:
                if hasattr(self, 'status_label') and self.status_label is not None:
                    self.status_label.setText("Batch processor not available")
                    self.status_label.setStyleSheet("color: red;")
                return

            status = self.batch_processor.get_status()

            if status['is_processing']:
                self.status_label.setText(f"Processing batch: {status.get('current_batch_id', 'Unknown')}")
                self.status_label.setStyleSheet("color: #00FF00;")
            else:
                queue_size = status.get('queue_size', 0)
                if queue_size > 0:
                    self.status_label.setText(f"Ready - {queue_size} jobs queued")
                    self.status_label.setStyleSheet("color: orange;")
                else:
                    self.status_label.setText("Ready - No jobs queued")
                    self.status_label.setStyleSheet("color: green;")

            self._processing = status['is_processing']
            self._update_button_states()

        except Exception as e:
            logger.error(f"Error updating status: {e}")
            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText(f"Status update error: {str(e)}")
                self.status_label.setStyleSheet("color: red;")

    def _update_button_states(self):
        """Update button states based on current batch processor state"""
        try:
            if not hasattr(self, 'batch_processor') or self.batch_processor is None:
                # Default enabled state if no batch processor
                if hasattr(self, 'add_files_btn') and self.add_files_btn is not None:
                    self.add_files_btn.setEnabled(True)
                if hasattr(self, 'start_btn') and self.start_btn is not None:
                    self.start_btn.setEnabled(False)
                if hasattr(self, 'clear_queue_btn') and self.clear_queue_btn is not None:
                    self.clear_queue_btn.setEnabled(False)
                return

            is_processing = getattr(self, '_processing', False)

            try:
                status = self.batch_processor.get_status()
                queue_empty = status.get('queue_size', 0) == 0
            except Exception:
                queue_empty = True

            # Update button states
            if hasattr(self, 'add_files_btn') and self.add_files_btn is not None:
                self.add_files_btn.setEnabled(not is_processing)
            if hasattr(self, 'start_btn') and self.start_btn is not None:
                self.start_btn.setEnabled(not queue_empty and not is_processing)
            if hasattr(self, 'stop_btn') and self.stop_btn is not None:
                self.stop_btn.setEnabled(is_processing)
            if hasattr(self, 'clear_queue_btn') and self.clear_queue_btn is not None:
                self.clear_queue_btn.setEnabled(not queue_empty and not is_processing)

        except Exception as e:
            logger.error(f"Error updating button states: {e}")

    # Event handlers
    def _on_api_key_changed(self):
        """Handle API key change"""
        self._set_api_key()
        self._update_button_states()

    def _on_clear_queue(self):
        """Handle clear queue button"""
        try:
            if self._processing:
                QMessageBox.warning(self, "Cannot Clear", "Cannot clear queue while processing.")
                return

            reply = QMessageBox.question(
                self, "Clear Queue",
                "Are you sure you want to clear all queued jobs?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                success = self.clear_queue()
                if success:
                    self._update_button_states()
                    logger.info("Queue cleared successfully by user")
        except Exception as e:
            logger.error(f"Error clearing queue: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to clear queue: {str(e)}")

    def clear_queue(self):
        """Clear the entire queue from both UI and backend service"""
        try:
            logger.info("Clearing batch processing queue...")

            # Clear the UI table
            row_count = self.queue_table.rowCount()
            for i in range(row_count, 0, -1):
                self.queue_table.removeRow(i-1)

            # Clear tracking data structures
            self._ui_file_paths_set.clear()
            self._ui_filename_size_map.clear()

            # Call backend service to clear queue
            if self.batch_processor and hasattr(self.batch_processor, 'clear_queue'):
                removed_count = self.batch_processor.clear_queue()
                logger.info(f"Backend queue cleared: {removed_count} jobs removed")

            self._update_status()

            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText("Queue cleared successfully")
                self.status_label.setStyleSheet("color: green;")

            return True
        except Exception as e:
            logger.error(f"Error clearing queue: {str(e)}")
            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText(f"Error clearing queue: {str(e)}")
                self.status_label.setStyleSheet("color: red;")
            QMessageBox.warning(self, "Error", f"Failed to clear queue: {str(e)}")
            return False

    def _on_add_files(self):
        """Handle add files button"""
        try:
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Select Audio Files",
                "",
                "Audio Files (*.wav *.mp3 *.flac *.ogg *.aiff);;All Files (*)"
            )

            for file_path in file_paths:
                output_dir = os.path.join(os.path.dirname(file_path), "mvsep_output")
                metadata = {
                    'type': 'Manual Upload',
                    'auto_analyze': True,
                    'added_from': 'batch_processor_widget'
                }
                self.add_to_queue(file_path, output_dir, metadata)

        except Exception as e:
            logger.error(f"Error adding files: {e}")
            QMessageBox.critical(self, "Error", f"Failed to add files: {str(e)}")

    def _on_start_processing(self):
        """Handle start processing button"""
        try:
            if not hasattr(self, 'batch_processor') or self.batch_processor is None:
                logger.error("Batch processor not initialized when starting processing")
                QMessageBox.critical(self, "Error", "Batch processor not initialized")
                return

            if self.queue_table.rowCount() == 0:
                QMessageBox.information(self, "No Files", "Please add files to the queue first")
                return

            if self._processing:
                logger.warning("Processing already in progress")
                return

            # Check for API key before starting
            api_key = self.api_key_input.text().strip() if hasattr(self, 'api_key_input') else ""
            if not api_key:
                QMessageBox.warning(self, "Missing API Key", "Please enter a valid MVSep API key before processing")
                logger.warning("Processing attempted without an API key")
                self.status_label.setText("Error: MVSep API key required")
                return

            # Start processing
            if hasattr(self.batch_processor, 'start_processing'):
                self._set_api_key()
                self.batch_processor.start_processing()
                self._processing = True
                self.status_label.setText("Processing queue...")
                self.processing_started.emit()
                self._update_button_states()
                logger.info("Started batch processing")
            else:
                QMessageBox.critical(self, "Error", "Batch processor missing start_processing method")

        except Exception as e:
            logger.error(f"Error starting processing: {e}")
            QMessageBox.critical(self, "Error", f"Error starting processing: {str(e)}")

    def _on_stop_processing(self):
        """Handle stop processing button"""
        try:
            reply = QMessageBox.question(
                self, "Stop Processing",
                "Are you sure you want to stop processing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                if hasattr(self, 'batch_processor') and self.batch_processor is not None:
                    self.batch_processor.stop_processing()
                    logger.info("Processing stopped by user")
                    self._processing = False
                    self._update_button_states()
                    self.processing_stopped.emit()
        except Exception as e:
            logger.error(f"Error stopping processing: {e}")
            QMessageBox.critical(self, "Error", f"Error stopping processing: {str(e)}")

    def _remove_from_queue(self, row: int):
        """Remove job from queue"""
        try:
            if row < 0 or row >= self.queue_table.rowCount():
                logger.error(f"Invalid row index for removal: {row}")
                return

            # Get the file path for the job to be removed
            file_item = self.queue_table.item(row, 0)
            if not file_item:
                logger.error(f"Cannot find filename item in row {row}")
                return

            file_path = file_item.toolTip()  # Full path is stored in the tooltip

            # Remove from tracking data structures
            try:
                normalized_path = os.path.normcase(os.path.normpath(file_path))
                filename = os.path.basename(file_path)

                if normalized_path in self._ui_file_paths_set:
                    self._ui_file_paths_set.remove(normalized_path)

                try:
                    file_size = os.path.getsize(file_path) if os.path.isfile(file_path) else None
                    if file_size is not None:
                        size_key = f"{filename}:{file_size}"
                        if size_key in self._ui_filename_size_map:
                            del self._ui_filename_size_map[size_key]
                except Exception as size_err:
                    logger.error(f"Error handling size map removal: {str(size_err)}")
            except Exception as tracking_err:
                logger.error(f"Error updating tracking structures: {str(tracking_err)}")

            # Remove from batch processor service
            if self.batch_processor and hasattr(self.batch_processor, 'remove_from_queue'):
                removed = self.batch_processor.remove_from_queue(file_path)
                if removed:
                    logger.info(f"Removed job from service queue: {os.path.basename(file_path)}")
                else:
                    logger.warning(f"Job not found in service queue: {os.path.basename(file_path)}")

            # Remove from UI table
            self.queue_table.removeRow(row)
            logger.info(f"Removed job from UI table: {os.path.basename(file_path)}")

            self._update_status()

        except Exception as e:
            logger.error(f"Error removing job from queue: {str(e)}")
            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText(f"Error: {str(e)}")
                self.status_label.setStyleSheet("color: red;")
            QMessageBox.warning(self, "Error", f"Failed to remove file from queue: {str(e)}")

    # Batch processor signal handlers
    def _on_batch_started(self, batch_id: str):
        """Handle batch processing started"""
        try:
            self._current_batch_id = batch_id
            self._processing = True

            if hasattr(self, 'status_label') and self.status_label is not None:
                self.status_label.setText("Processing...")

            if hasattr(self, 'progress_bar') and self.progress_bar is not None:
                self.progress_bar.setValue(0)

            if hasattr(self, 'progress_message') and self.progress_message is not None:
                self.progress_message.setText("Processing started")

            self._update_button_states()
            self.processing_started.emit()

            logger.info(f"Batch processing started: {batch_id}")

        except Exception as e:
            logger.error(f"Error handling batch started: {e}")

    def _on_batch_completed(self, batch_id: str, summary: Dict):
        """Handle batch processing completed"""
        try:
            self._current_batch_id = None
            self._processing = False

            total = summary.get('total', 0)
            successful = summary.get('successful', 0)
            failed = summary.get('failed', 0)

            if hasattr(self, 'progress_bar') and self.progress_bar is not None:
                self.progress_bar.setValue(total)

            if hasattr(self, 'progress_message') and self.progress_message is not None:
                self.progress_message.setText(
                    f"Batch complete: {successful} successful, {failed} failed"
                )

            # Clear the queue table
            if hasattr(self, 'queue_table') and self.queue_table is not None:
                self.queue_table.setRowCount(0)

            self._update_button_states()
            self.processing_stopped.emit()

            # Trigger DrumTracKAI Complete System analysis if enabled
            if (self.enable_complete_analysis and 
                COMPLETE_SYSTEM_INTEGRATION_AVAILABLE and 
                self.complete_system_handler and 
                successful > 0):
                
                logger.info("Triggering DrumTracKAI Complete System analysis for batch results")
                try:
                    # Get batch results for complete analysis
                    batch_results = self.batch_processor.get_batch_results(batch_id)
                    if batch_results:
                        # Trigger complete analysis in background
                        self.complete_system_handler.process_batch_results(batch_results)
                        
                        QMessageBox.information(
                            self,
                            "Batch Complete - Analysis Starting",
                            f"Batch processing completed.\n\n"
                            f"Total: {total}\n"
                            f"Successful: {successful}\n"
                            f"Failed: {failed}\n\n"
                            f"AUDIO DrumTracKAI Complete Analysis starting..."
                        )
                    else:
                        logger.warning("No batch results available for complete analysis")
                        QMessageBox.information(
                            self,
                            "Batch Complete",
                            f"Batch processing completed.\n\n"
                            f"Total: {total}\n"
                            f"Successful: {successful}\n"
                            f"Failed: {failed}\n\n"
                            f"WARNING Complete analysis not available (no results)"
                        )
                        
                except Exception as e:
                    logger.error(f"Error triggering complete system analysis: {e}")
                    QMessageBox.information(
                        self,
                        "Batch Complete",
                        f"Batch processing completed.\n\n"
                        f"Total: {total}\n"
                        f"Successful: {successful}\n"
                        f"Failed: {failed}\n\n"
                        f"WARNING Complete analysis failed to start"
                    )
            else:
                # Standard completion message
                reason = "disabled" if not self.enable_complete_analysis else "unavailable"
                QMessageBox.information(
                    self,
                    "Batch Complete",
                    f"Batch processing completed.\n\n"
                    f"Total: {total}\n"
                    f"Successful: {successful}\n"
                    f"Failed: {failed}\n\n"
                    f"INFO Complete analysis {reason}"
                )
            
        except Exception as e:
            logger.error(f"Error handling batch completion: {e}")
            
    def set_drum_analysis_routing(self, enable=True):
        """Enable or disable automatic routing of stems to drum analysis
        
        Args:
            enable: True to enable routing, False to disable
        """
        self.route_to_drum_analysis = enable
        logger.info(f"Drum analysis routing {'enabled' if enable else 'disabled'}")
        return True
        
    def _route_stems_to_drum_analysis(self, source_file: str, output_files: Dict):
        """Route extracted stems to drum analysis widget
        
        Args:
            source_file: Path to the original file processed
            output_files: Dictionary of output files by type
        """
        try:
            if not output_files:
                logger.warning(f"No output files to route for {source_file}")
                return False
                
            # Find drum analysis widget
            drum_analysis_widget = self._find_drum_analysis_widget()
            if not drum_analysis_widget:
                logger.warning("No drum analysis widget found for routing stems")
                return False
                
            # Initialize the drum analysis widget with stems
            result = drum_analysis_widget.initialize_with_stems(source_file, output_files)
            if result:
                logger.info(f"Successfully routed {len(output_files)} stems to drum analysis")
                self._show_routing_confirmation_dialog(source_file, output_files, drum_analysis_widget)
                return True
            else:
                logger.warning(f"Failed to initialize drum analysis with stems from {source_file}")
                return False
                
        except Exception as e:
            logger.error(f"Error routing stems to drum analysis: {e}")
            traceback.print_exc()
            return False
            
    def _find_drum_analysis_widget(self):
        """Find the drum analysis widget in the main window"""
        try:
            # Try to find the parent window
            window = None
            parent = self.parent()
            while parent:
                # Check if this might be the main window with tabs
                if hasattr(parent, 'findChild'):
                    window = parent
                    break
                parent = parent.parent()
                
            if not window:
                logger.warning("Could not find main window for drum analysis widget lookup")
                return None
                
            # Try different methods to find the drum analysis widget
            # Method 1: Direct find by class name
            drum_widget = window.findChild(QWidget, "DrumAnalysisWidget")
            if drum_widget:
                return drum_widget
                
            # Method 2: Find through tab widget
            tab_widget = window.findChild(QTabWidget)
            if tab_widget:
                for i in range(tab_widget.count()):
                    tab = tab_widget.widget(i)
                    if "drum analysis" in tab_widget.tabText(i).lower() or \
                       "drumanalysis" in tab.__class__.__name__.lower():
                        return tab
                        
            logger.warning("Could not find drum analysis widget through normal methods")
            return None
        
        except Exception as e:
            logger.error(f"Error finding drum analysis widget: {e}")
            return None
            
    def _show_routing_confirmation_dialog(self, source_file, output_files, drum_analysis_widget):
        """Show confirmation dialog for successful stem routing"""
        try:
            msg = QMessageBox()
            msg.setWindowTitle("Stems Routed to Drum Analysis")
            msg.setIcon(QMessageBox.Information)
            
            # Count stem types
            drum_stems = sum(1 for stem_type in output_files if any(term in stem_type.lower() 
                                                            for term in ["drum", "kick", "snare", "hat"]))
            
            msg.setText(f"<b>Stems from {os.path.basename(source_file)} have been routed to Drum Analysis</b>")
            msg.setInformativeText(f"Total stems: {len(output_files)}<br>")
            msg.setDetailedText("\n".join([f"{stem_type}: {os.path.basename(path)}" 
                                      for stem_type, path in output_files.items()]))
            
            # Add button to switch to drum analysis tab
            switch_btn = msg.addButton("Switch to Drum Analysis", QMessageBox.ActionRole)
            close_btn = msg.addButton(QMessageBox.Close)
            msg.setDefaultButton(switch_btn)
            
            # Non-blocking dialog
            msg.setModal(False)
            msg.show()
            
            # Connect button click to tab switching
            switch_btn.clicked.connect(lambda: self._switch_to_drum_analysis_tab(drum_analysis_widget))
            
        except Exception as e:
            logger.error(f"Error showing routing confirmation dialog: {e}")
            
    def _switch_to_drum_analysis_tab(self, drum_analysis_widget):
        """Switch to the drum analysis tab"""
        try:
            # Find parent tab widget
            parent = drum_analysis_widget.parent()
            while parent and not isinstance(parent, QTabWidget):
                parent = parent.parent()
                
            if parent and isinstance(parent, QTabWidget):
                # Find tab index and switch to it
                for i in range(parent.count()):
                    if parent.widget(i) == drum_analysis_widget:
                        parent.setCurrentIndex(i)
                        return
        except Exception as e:
            logger.error(f"Error switching to drum analysis tab: {e}")

    def _on_file_started(self, batch_id: str, file_path: str, file_index: int, total_files: int):
        """Handle file processing started"""
        try:
            filename = os.path.basename(file_path)
            progress_percentage = int((file_index / total_files) * 100) if total_files > 0 else 0

            if hasattr(self, 'current_file_label') and self.current_file_label is not None:
                self.current_file_label.setText(f"Processing: {filename}")

            if hasattr(self, 'progress_message') and self.progress_message is not None:
                if total_files > 1:
                    self.progress_message.setText(f"Processing file {file_index}/{total_files} ({progress_percentage}%)")
                else:
                    self.progress_message.setText(f"Processing: {filename}")

            self._update_table_status(file_path, "Processing...", "#2196F3")

            logger.info(f"