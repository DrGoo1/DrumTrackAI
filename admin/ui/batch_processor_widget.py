"""
Batch Processor Implementation
=============================
Contains both the BatchProcessor service and the BatchProcessorWidget UI class.
Both are critical for the drum analysis widget to function properly.
"""
import asyncio
import json
import logging
import os
import time
import uuid
import traceback

from admin.services.mvsep_service import MVSepService
from PySide6.QtCore import QObject, Signal, QThread, QTimer, QMutex, QMutexLocker, Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QProgressBar, QListWidget, QLabel, QMessageBox,
                              QSplitter, QCheckBox, QFileDialog, QListWidgetItem)
from PySide6.QtGui import QFont
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from admin.utils.thread_safe_ui_updater import ThreadSafeUIUpdater

logger = logging.getLogger(__name__)

class BatchProcessor(QObject):
    """
    Complete batch processor with exact signal signatures required by drum analysis widget.
    NO FALLBACK OPTIONS - all failures are explicit.
    """

    # CRITICAL: These signal signatures MUST match exactly what drum_analysis_widget expects
    processing_started = Signal(str, int)  # (batch_id, files_count)
    processing_completed = Signal(str, dict)  # (batch_id, summary)
    file_processing_started = Signal(str, str, int, int)  # (batch_id, file_path, file_index, total_files)
    file_processing_completed = Signal(str, str, dict, int, int)  # (batch_id, file_path, result, file_index, total_files)
    file_processing_failed = Signal(str, str, str, int, int)  # (batch_id, file_path, error, file_index, total_files)
    progress_updated = Signal(str, float, str)  # (batch_id, progress, message)
    queue_changed = Signal()  # Signal when queue is modified (added/removed items)

    _instance = None
    _instance_lock = QMutex()

    def __init__(self):
        super().__init__()

        # Core state
        self.is_processing = False
        self.current_batch_id = None
        self._api_key = None
        self._queue = []
        self._processing_thread = None
        self._cancelled = False

        # Thread safety
        self._queue_mutex = QMutex()
        
        # Auto-detect and set API key during initialization
        self._initialize_api_key()

        logger.info("BatchProcessor initialized")

    @classmethod
    def get_instance(cls):
        """Get singleton instance of BatchProcessor"""
        if cls._instance is None:
            with QMutexLocker(cls._instance_lock):
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _initialize_api_key(self):
        """Auto-detect and initialize API key from environment or config file"""
        try:
            # Try environment variable first
            api_key = os.environ.get('MVSEP_API_KEY', '')
            
            # If environment variable not found, try config file
            if not api_key:
                try:
                    config_path = os.path.join(os.getcwd(), 'mvsep_config.txt')
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            for line in f:
                                line = line.strip()
                                if line.startswith('MVSEP_API_KEY=') and not line.startswith('#'):
                                    api_key = line.split('=', 1)[1].strip()
                                    logger.info("MVSep API key loaded from config file for batch processor")
                                    break
                except Exception as e:
                    logger.debug(f"Could not read config file for batch processor: {e}")
            
            # Set the API key if found
            if api_key and api_key.strip() and api_key != 'your_actual_api_key_here':
                self._api_key = api_key.strip()
                logger.info("SUCCESS Batch processor API key initialized successfully")
            else:
                logger.warning("ERROR Batch processor API key not found - processing will fail until key is set")
                
        except Exception as e:
            logger.error(f"Error initializing API key for batch processor: {e}")
    
    def set_api_key(self, api_key: str):
        """Set MVSep API key - REQUIRED for processing"""
        if not api_key or not api_key.strip():
            raise ValueError("CRITICAL: API key cannot be empty")

        self._api_key = api_key.strip()
        logger.info("API key set for batch processor")

    def add_to_queue(self, input_file: str, output_dir: str, metadata: Dict = None) -> bool:
        """
        Add file to processing queue.
        NO FALLBACKS - explicit validation and failure.
        """
        # CRITICAL: Validate all inputs - no fallbacks
        if not input_file:
            raise ValueError("CRITICAL: input_file cannot be empty")

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"CRITICAL: Input file does not exist: {input_file}")

        if not output_dir:
            raise ValueError("CRITICAL: output_dir cannot be empty")

        if metadata is None:
            metadata = {}

        # Validate API key is available
        if not self._api_key:
            raise RuntimeError("CRITICAL: API key not set. Call set_api_key() first.")

        with QMutexLocker(self._queue_mutex):
            job = {
                'id': str(uuid.uuid4()),
                'input_file': input_file,
                'output_dir': output_dir,
                'metadata': metadata,
                'added_time': datetime.now().isoformat(),
                'status': 'queued'
            }

            self._queue.append(job)

        # Emit signal to notify UI that queue has changed
        self.queue_changed.emit()
        
        logger.info(f"Added job to queue: {os.path.basename(input_file)}")
        return True

    def add_job(self, input_file: str, output_dir: str, metadata: Dict = None) -> bool:
        """Alias for add_to_queue for compatibility"""
        return self.add_to_queue(input_file, output_dir, metadata)

    def start_processing(self, keep_original_mix=True, keep_drum_stem=True):
        """
        Start batch processing.
        NO FALLBACKS - explicit failure if conditions not met.

        Args:
            keep_original_mix: Whether to keep a copy of the original mix in output
            keep_drum_stem: Whether to keep the isolated drum stem from stage 1
        """
        if self.is_processing:
            raise RuntimeError("CRITICAL: Processing already in progress")

        if not self._api_key:
            raise RuntimeError("CRITICAL: API key not set")

        with QMutexLocker(self._queue_mutex):
            if not self._queue:
                raise RuntimeError("CRITICAL: No jobs in queue")

            queue_copy = self._queue.copy()

        # Create new batch
        self.current_batch_id = str(uuid.uuid4())
        self.is_processing = True
        self._cancelled = False

        # Start processing thread
        self._processing_thread = BatchProcessingThread(
            self.current_batch_id,
            queue_copy,
            self._api_key,
            keep_original_mix=keep_original_mix,
            keep_drum_stem=keep_drum_stem
        )

        # Connect thread signals to our signals
        self._processing_thread.batch_started.connect(self._on_batch_started)
        self._processing_thread.batch_completed.connect(self._on_batch_completed)
        self._processing_thread.file_started.connect(self._on_file_started)
        self._processing_thread.file_completed.connect(self._on_file_completed)
        self._processing_thread.file_failed.connect(self._on_file_failed)
        self._processing_thread.progress_update.connect(self._on_progress_update)

        self._processing_thread.start()

        logger.info(f"Started batch processing: {self.current_batch_id}")

    def stop_processing(self):
        """Stop current processing"""
        if not self.is_processing:
            return

        self._cancelled = True

        if self._processing_thread and self._processing_thread.isRunning():
            self._processing_thread.cancel()
            self._processing_thread.wait(5000)  # Wait up to 5 seconds

        self.is_processing = False
        logger.info("Batch processing stopped")

    def get_queue_size(self) -> int:
        """Get current queue size"""
        with QMutexLocker(self._queue_mutex):
            return len(self._queue)

    def get_status(self) -> Dict:
        """Get current processor status"""
        return {
            'is_processing': self.is_processing,
            'current_batch_id': self.current_batch_id,
            'queue_size': self.get_queue_size(),
            'api_key_set': bool(self._api_key)
        }

    # Signal handlers that emit the exact signals expected by drum_analysis_widget
    def _on_batch_started(self, batch_id: str, files_count: int):
        """Handle batch started from processing thread"""
        logger.info(f"Batch started: {batch_id} with {files_count} files")
        self.processing_started.emit(batch_id, files_count)

    def _on_batch_completed(self, batch_id: str, summary: Dict):
        """Handle batch completion from processing thread"""
        self.is_processing = False
        self.current_batch_id = None

        # Clear processed jobs from queue
        with QMutexLocker(self._queue_mutex):
            self._queue.clear()

        logger.info(f"Batch completed: {batch_id}")
        self.processing_completed.emit(batch_id, summary)

    def _on_file_started(self, batch_id: str, file_path: str, file_index: int, total_files: int):
        """Handle file processing start"""
        logger.info(f"File started: {os.path.basename(file_path)} ({file_index}/{total_files})")
        self.file_processing_started.emit(batch_id, file_path, file_index, total_files)

    def _on_file_completed(self, batch_id: str, file_path: str, result: Dict, file_index: int, total_files: int):
        """Handle file processing completion"""
        logger.info(f"File completed: {os.path.basename(file_path)}")
        self.file_processing_completed.emit(batch_id, file_path, result, file_index, total_files)

    def _on_file_failed(self, batch_id: str, file_path: str, error: str, file_index: int, total_files: int):
        """Handle file processing failure"""
        logger.error(f"File failed: {os.path.basename(file_path)} - {error}")
        self.file_processing_failed.emit(batch_id, file_path, error, file_index, total_files)

    def _on_progress_update(self, batch_id: str, progress: float, message: str):
        """Handle progress update"""
        logger.debug(f"Progress: {progress:.1f}% - {message}")
        self.progress_updated.emit(batch_id, progress, message)


class BatchProcessingThread(QThread):
    """
    Thread that performs the actual batch processing.
    NO FALLBACKS - all errors are propagated.
    """

    # Internal signals for communication with BatchProcessor
    batch_started = Signal(str, int)
    batch_completed = Signal(str, dict)
    file_started = Signal(str, str, int, int)
    file_completed = Signal(str, str, dict, int, int)
    file_failed = Signal(str, str, str, int, int)
    progress_update = Signal(str, float, str)

    def __init__(self, batch_id: str, jobs: List[Dict], api_key: str, keep_original_mix: bool = True, keep_drum_stem: bool = True):
        super().__init__()
        self.batch_id = batch_id
        self.jobs = jobs
        self.api_key = api_key
        self.keep_original_mix = keep_original_mix
        self.keep_drum_stem = keep_drum_stem
        self._cancelled = False

    def cancel(self):
        """Cancel processing"""
        self._cancelled = True

    def run(self):
        """Main processing loop - NO FALLBACKS"""
        try:
            total_jobs = len(self.jobs)
            self.batch_started.emit(self.batch_id, total_jobs)

            successful = 0
            failed = 0

            for i, job in enumerate(self.jobs):
                if self._cancelled:
                    break

                file_path = job['input_file']
                output_dir = job['output_dir']
                metadata = job['metadata']

                file_index = i + 1

                self.file_started.emit(self.batch_id, file_path, file_index, total_jobs)

                try:
                    # Process with MVSep
                    result = self._process_file_with_mvsep(file_path, output_dir, metadata)

                    if result['success']:
                        successful += 1
                        self.file_completed.emit(self.batch_id, file_path, result, file_index, total_jobs)
                    else:
                        failed += 1
                        error_msg = result.get('error', 'Unknown error')
                        self.file_failed.emit(self.batch_id, file_path, error_msg, file_index, total_jobs)

                except Exception as e:
                    failed += 1
                    error_msg = f"Processing error: {str(e)}"
                    logger.error(f"Error processing {file_path}: {error_msg}")
                    self.file_failed.emit(self.batch_id, file_path, error_msg, file_index, total_jobs)

                # Update progress - ensure consistent format (0.0 to 1.0)
                progress = file_index / total_jobs  # Send as 0.0-1.0 value for consistent processing
                message = f"Processed {file_index}/{total_jobs} files ({int(progress * 100)}%)"
                self.progress_update.emit(self.batch_id, progress, message)

            # Emit completion
            summary = {
                'total': total_jobs,
                'successful': successful,
                'failed': failed,
                'skipped': total_jobs - successful - failed
            }

            self.batch_completed.emit(self.batch_id, summary)

        except Exception as e:
            logger.error(f"Critical error in batch processing thread: {str(e)}")
            summary = {'total': len(self.jobs), 'successful': 0, 'failed': len(self.jobs), 'skipped': 0}
            self.batch_completed.emit(self.batch_id, summary)

    def _process_file_with_mvsep(self, file_path: str, output_dir: str, metadata: Dict) -> Dict:
        """
        Process file with MVSep service.
        NO FALLBACKS - explicit error handling only.
        """
        try:
            # Import MVSep service
            # Create service instance
            mvsep_service = MVSepService(self.api_key)

            # Determine if we should skip stage 1
            skip_stage_1 = metadata.get('skip_first_stage', False)
            use_gpu = metadata.get('use_gpu', True)

            # Create a progress callback function that forwards to the batch processor signals
            def batch_progress_callback(progress: float, message: str):
                # Extract file name for concise messages
                file_name = os.path.basename(file_path)

                # Format the progress message with file context
                formatted_message = f"{file_name}: {message}"

                # Forward to batch processor signals
                self.progress_update.emit(self.batch_id, progress, formatted_message)

            # Create event loop for async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Process the file with progress callback
                result_files = loop.run_until_complete(
                    mvsep_service.process_audio_file(
                        file_path,
                        output_dir,
                        progress_callback=batch_progress_callback,
                        skip_stage_1=skip_stage_1,
                        keep_original_mix=self.keep_original_mix,
                        keep_drum_stem=self.keep_drum_stem
                    )
                )

                return {
                    'success': True,
                    'result_files': result_files,
                    'output_dir': output_dir,
                    'metadata': metadata
                }

            finally:
                loop.close()

        except Exception as e:
            error_msg = f"MVSep processing failed: {str(e)}"
            logger.error(error_msg)

            # Emit error through progress update for visibility
            self.progress_update.emit(
                self.batch_id,
                0.0,
                f"ERROR: {os.path.basename(file_path)}: {error_msg}"
            )

            return {
                'success': False,
                'error': error_msg,
                'metadata': metadata
            }


# Export this function for external modules to access the singleton
def get_batch_processor() -> BatchProcessor:
    """
    Get the singleton instance of the BatchProcessor.
    This is the function imported by other modules to access the processor.

    Returns:
        BatchProcessor: The singleton BatchProcessor instance
    """
    return BatchProcessor.get_instance()


class BatchProcessorWidget(QWidget):
    """Batch Processing Widget for MVSep audio processing queue management"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("BatchProcessorWidget")
        self._initialization_complete = False
        self.batch_processor = get_batch_processor()
        self.thread_safe_updater = None
        self._init_thread_safety()
        self._setup_ui()
        self._connect_signals()
        self._update_ui_state()
        self._initialization_complete = True
        logger.info("BatchProcessorWidget initialized")
        
    def get_batch_processor(self):
        """Return the batch processor instance for use by other widgets"""
        return self.batch_processor
    
    def _init_thread_safety(self):
        """Initialize thread-safe UI update handler"""
        try:
            self.thread_safe_updater = ThreadSafeUIUpdater()
            logger.debug("Thread-safe UI updater initialized")
        except Exception as e:
            logger.error(f"Failed to initialize thread safety: {e}")
            traceback.print_exc()
    
    def _setup_ui(self):
        """Setup the UI components"""
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # Queue status section
            status_layout = QHBoxLayout()
            self.status_label = QLabel("Queue Status: Idle")
            self.status_label.setFont(QFont("Arial", 10, QFont.Bold))
            status_layout.addWidget(self.status_label)
            
            self.queue_size_label = QLabel("Queue Size: 0")
            status_layout.addWidget(self.queue_size_label)
            status_layout.addStretch()
            main_layout.addLayout(status_layout)
            
            # Main content splitter
            splitter = QSplitter(Qt.Horizontal)
            
            # Queue list
            queue_widget = QWidget()
            queue_layout = QVBoxLayout(queue_widget)
            queue_layout.setContentsMargins(0, 0, 0, 0)
            
            queue_label = QLabel("Processing Queue")
            queue_label.setFont(QFont("Arial", 10, QFont.Bold))
            queue_layout.addWidget(queue_label)
            
            self.queue_list = QListWidget()
            queue_layout.addWidget(self.queue_list)
            
            splitter.addWidget(queue_widget)
            
            # Progress panel
            progress_widget = QWidget()
            progress_layout = QVBoxLayout(progress_widget)
            progress_layout.setContentsMargins(0, 0, 0, 0)
            
            progress_label = QLabel("Processing Status")
            progress_label.setFont(QFont("Arial", 10, QFont.Bold))
            progress_layout.addWidget(progress_label)
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            progress_layout.addWidget(self.progress_bar)
            
            self.progress_label = QLabel("Ready")
            progress_layout.addWidget(self.progress_label)
            
            # Options
            options_layout = QHBoxLayout()
            
            self.keep_original_mix_checkbox = QCheckBox("Keep Original Mix")
            self.keep_original_mix_checkbox.setChecked(True)
            options_layout.addWidget(self.keep_original_mix_checkbox)
            
            self.keep_drum_stem_checkbox = QCheckBox("Keep Drum Stem")
            self.keep_drum_stem_checkbox.setChecked(True)
            options_layout.addWidget(self.keep_drum_stem_checkbox)
            
            progress_layout.addLayout(options_layout)
            progress_layout.addStretch()
            
            splitter.addWidget(progress_widget)
            splitter.setSizes([200, 400])
            
            main_layout.addWidget(splitter, 1)  # 1 = stretch factor
            
            # Buttons
            buttons_layout = QHBoxLayout()
            buttons_layout.setSpacing(10)
            
            self.start_button = QPushButton("Start Processing")
            self.start_button.setEnabled(False)
            buttons_layout.addWidget(self.start_button)
            
            self.stop_button = QPushButton("Stop Processing")
            self.stop_button.setEnabled(False)
            buttons_layout.addWidget(self.stop_button)
            
            self.clear_button = QPushButton("Clear Queue")
            self.clear_button.setEnabled(False)
            buttons_layout.addWidget(self.clear_button)
            
            buttons_layout.addStretch()
            
            self.add_file_button = QPushButton("Add File")
            buttons_layout.addWidget(self.add_file_button)
            
            main_layout.addLayout(buttons_layout)
            
        except Exception as e:
            logger.error(f"Error setting up UI: {e}")
            traceback.print_exc()
    
    def _connect_signals(self):
        """Connect UI signals"""
        try:
            # UI Buttons
            self.start_button.clicked.connect(self._on_start_processing)
            self.stop_button.clicked.connect(self._on_stop_processing)
            self.clear_button.clicked.connect(self._on_clear_queue)
            self.add_file_button.clicked.connect(self._on_add_file)
            
            # Batch processor signals
            self.batch_processor.processing_started.connect(self._on_processing_started)
            self.batch_processor.processing_completed.connect(self._on_processing_completed)
            self.batch_processor.file_processing_started.connect(self._on_file_processing_started)
            self.batch_processor.file_processing_completed.connect(self._on_file_processing_completed)
            self.batch_processor.file_processing_failed.connect(self._on_file_processing_failed)
            self.batch_processor.progress_updated.connect(self._on_progress_updated)
            self.batch_processor.queue_changed.connect(self._on_queue_changed)
            
            logger.debug("Signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            traceback.print_exc()
    
    def _on_start_processing(self):
        """Start processing the queue"""
        try:
            keep_original_mix = self.keep_original_mix_checkbox.isChecked()
            keep_drum_stem = self.keep_drum_stem_checkbox.isChecked()
            
            self.batch_processor.start_processing(
                keep_original_mix=keep_original_mix,
                keep_drum_stem=keep_drum_stem
            )
            
            self._update_ui_state()
            
        except Exception as e:
            logger.error(f"Error starting processing: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Processing Error", f"Error starting processing: {str(e)}")
    
    def _on_stop_processing(self):
        """Stop current processing"""
        try:
            self.batch_processor.stop_processing()
            self._update_ui_state()
            
        except Exception as e:
            logger.error(f"Error stopping processing: {e}")
            traceback.print_exc()
    
    def _on_clear_queue(self):
        """Clear the queue (not implemented in service yet)"""
        # TODO: Implement queue clearing in batch processor
        QMessageBox.information(self, "Not Implemented", "Queue clearing not implemented yet")
    
    def _on_add_file(self):
        """Add file to processing queue"""
        try:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Audio File", "", "Audio Files (*.wav *.mp3 *.flac *.ogg *.aiff);;All Files (*.*)"
            )
            
            if not file_path:
                return
            
            output_dir = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", ""
            )
            
            if not output_dir:
                return
                
            # Add to queue
            try:
                # Try to get API key from environment
                from os import environ
                api_key = environ.get("MVSEP_API_KEY")
                
                if api_key:
                    self.batch_processor.set_api_key(api_key)
                else:
                    QMessageBox.warning(
                        self, "API Key Missing",
                        "MVSEP_API_KEY not found in environment variables. Processing may fail."
                    )
                    
            except Exception as e:
                logger.warning(f"Error retrieving API key: {e}")
                
            self.batch_processor.add_to_queue(file_path, output_dir)
            self._update_queue_list()
            self._update_ui_state()
            
        except Exception as e:
            logger.error(f"Error adding file: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Add File Error", f"Error adding file: {str(e)}")
    
    def _on_processing_started(self, batch_id, files_count):
        """Handle batch processing started"""
        self.thread_safe_updater.run_in_main_thread(self._ui_update_processing_started, batch_id, files_count)
    
    def _ui_update_processing_started(self, batch_id, files_count):
        """Update UI for processing started (runs in main thread)"""
        self.status_label.setText(f"Queue Status: Processing")
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Starting batch {batch_id} with {files_count} files")
        self._update_ui_state()
    
    def _on_processing_completed(self, batch_id, summary):
        """Handle batch processing completed"""
        self.thread_safe_updater.run_in_main_thread(self._ui_update_processing_completed, batch_id, summary)
    
    def _ui_update_processing_completed(self, batch_id, summary):
        """Update UI for processing completed (runs in main thread)"""
        self.status_label.setText(f"Queue Status: Idle")
        self.progress_bar.setValue(100)
        
        successful = summary.get("successful", 0)
        failed = summary.get("failed", 0)
        total = summary.get("total", 0)
        
        self.progress_label.setText(
            f"Completed batch {batch_id}: {successful} successful, {failed} failed out of {total}"
        )
        self._update_ui_state()
        self._update_queue_list()
    
    def _on_file_processing_started(self, batch_id, file_path, file_index, total_files):
        """Handle file processing started"""
        self.thread_safe_updater.run_in_main_thread(
            self._ui_update_file_processing_started,
            batch_id, file_path, file_index, total_files
        )
    
    def _ui_update_file_processing_started(self, batch_id, file_path, file_index, total_files):
        """Update UI for file processing started (runs in main thread)"""
        file_name = os.path.basename(file_path)
        self.progress_label.setText(f"Processing {file_name} ({file_index}/{total_files})")
        progress = (file_index - 1) / total_files * 100
        self.progress_bar.setValue(int(progress))
    
    def _on_file_processing_completed(self, batch_id, file_path, result, file_index, total_files):
        """Handle file processing completed"""
        self.thread_safe_updater.run_in_main_thread(
            self._ui_update_file_processing_completed,
            batch_id, file_path, result, file_index, total_files
        )
    
    def _ui_update_file_processing_completed(self, batch_id, file_path, result, file_index, total_files):
        """Update UI for file processing completed (runs in main thread)"""
        file_name = os.path.basename(file_path)
        status = "Success" if result.get("success") else "Failed"
        self.progress_label.setText(f"Completed {file_name}: {status} ({file_index}/{total_files})")
        progress = file_index / total_files * 100
        self.progress_bar.setValue(int(progress))
    
    def _on_file_processing_failed(self, batch_id, file_path, error, file_index, total_files):
        """Handle file processing failed"""
        self.thread_safe_updater.run_in_main_thread(
            self._ui_update_file_processing_failed,
            batch_id, file_path, error, file_index, total_files
        )
    
    def _ui_update_file_processing_failed(self, batch_id, file_path, error, file_index, total_files):
        """Update UI for file processing failed (runs in main thread)"""
        file_name = os.path.basename(file_path)
        self.progress_label.setText(f"Failed {file_name}: {error} ({file_index}/{total_files})")
        progress = file_index / total_files * 100
        self.progress_bar.setValue(int(progress))
    
    def _on_progress_updated(self, batch_id, progress, message):
        """Handle progress updated"""
        self.thread_safe_updater.run_in_main_thread(self._ui_update_progress_updated, batch_id, progress, message)
    
    def _on_queue_changed(self):
        """Handle queue changed - update UI to reflect current queue state"""
        self.thread_safe_updater.run_in_main_thread(self._ui_update_queue_changed)
    
    def _ui_update_progress_updated(self, batch_id, progress, message):
        """Update UI for progress updated (runs in main thread)"""
        # This is for file-level progress, so we need to scale it to the current file
        # Just update the message for now
        self.progress_label.setText(message)
    
    def _ui_update_queue_changed(self):
        """Update UI when queue changes (runs in main thread)"""
        try:
            # Update the queue list display
            self._update_queue_list()
            # Update UI button states
            self._update_ui_state()
            logger.debug("Queue UI updated after queue change")
        except Exception as e:
            logger.error(f"Error updating UI after queue change: {e}")
            traceback.print_exc()
    
    def _update_queue_list(self):
        """Update the queue list display"""
        try:
            self.queue_list.clear()
            
            # Reflect current queue state from service
            queue_size = self.batch_processor.get_queue_size()
            self.queue_size_label.setText(f"Queue Size: {queue_size}")
            
            # Always display queue items, regardless of processing status
            if hasattr(self.batch_processor, '_queue') and self.batch_processor._queue:
                for i, job in enumerate(self.batch_processor._queue):
                    status = job.get('status', 'queued')
                    file_name = os.path.basename(job['input_file'])
                    
                    # Show different status indicators
                    if status == 'processing':
                        display_text = f" Processing: {file_name}"
                    elif status == 'completed':
                        display_text = f"SUCCESS Completed: {file_name}"
                    elif status == 'failed':
                        display_text = f"ERROR Failed: {file_name}"
                    else:
                        display_text = f"⏳ Queued: {file_name}"
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.UserRole, job)
                    self.queue_list.addItem(item)
            
            # If processing but no queue items, show current processing status
            elif self.batch_processor.is_processing and queue_size == 0:
                self.queue_list.addItem(QListWidgetItem(" Processing current job..."))
            
            # If no items at all
            elif queue_size == 0:
                self.queue_list.addItem(QListWidgetItem(" Queue is empty"))
            
        except Exception as e:
            logger.error(f"Error updating queue list: {e}")
            traceback.print_exc()
    
    def _update_ui_state(self):
        """Update UI component states based on current status"""
        try:
            is_processing = self.batch_processor.is_processing
            queue_size = self.batch_processor.get_queue_size()
            
            # Update buttons
            self.start_button.setEnabled(queue_size > 0 and not is_processing)
            self.stop_button.setEnabled(is_processing)
            self.clear_button.setEnabled(queue_size > 0 and not is_processing)
            
            # Update status
            status_text = "Processing" if is_processing else "Idle"
            self.status_label.setText(f"Queue Status: {status_text}")
            self.queue_size_label.setText(f"Queue Size: {queue_size}")
            
        except Exception as e:
            logger.error(f"Error updating UI state: {e}")
            traceback.print_exc()