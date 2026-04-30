"""
MVSep Widget
===========
Main widget for MVSep audio processing that implements the two-step stemming workflow
with thread-safe UI updates to prevent Qt recursive repaint issues.
"""

import os
import logging
import time
from typing import Dict, Optional, List
from pathlib import Path

from PySide6.QtCore import Qt, Slot, QMutex, QMutexLocker
from PySide6.QtWidgets import QMessageBox, QFileDialog, QVBoxLayout

from admin.ui.mvsep_widget_base import MVSepWidgetBase
from admin.ui.mvsep_worker import MVSepThreadWorker
from admin.utils.thread_safe_ui_updater import ThreadSafeUIUpdater

logger = logging.getLogger(__name__)

class MVSepWidget(MVSepWidgetBase):
    """
    Main MVSep processing widget that handles the two-step stemming process:
    1. HDemucs to generate multiple stereo stems
    2. DrumSep Melband Roformer for drum component separation

    Features:
    - Thread-safe UI updates to prevent Qt crashes
    - Progress monitoring with watchdog
    - Error recovery
    - Cancellation support
    - Results display
    """

    def __init__(self, parent=None):
        """Initialize the MVSep widget."""
        # Critical flag for main window initialization detection
        self._initialization_complete = False

        super().__init__(parent)

        # Setup components that weren't initialized in the base class
        self._init_thread_safety()

        # Set the window title
        self.setWindowTitle("MVSep Audio Processing")

        # Processing state
        self.processing_thread = None
        self.processing_start_time = 0
        self.result_files = {}

        # Mark initialization as complete - critical for main window tab detection
        self._initialization_complete = True
        logger.info("MVSepWidget initialization complete")

    def _init_thread_safety(self):
        """Initialize thread-safe UI update mechanisms."""
        self.ui_updater = ThreadSafeUIUpdater()
        
        # ThreadSafeUIUpdater doesn't use register_handler - it uses direct method calls
        # Store references to update methods for thread-safe access
        self._thread_safe_updates = {
            'progress': self._update_progress_unsafe,
            'status': self._update_status_unsafe,
            'detailed_status': self._update_detailed_status_unsafe,
            'results': self._update_results_unsafe,
            'log': self._add_log_unsafe,
            'reset': self._reset_ui_unsafe
        }

    def _on_start_clicked(self):
        """Handle start button click with thread-safe implementation."""
        input_file = self.file_path_input.text().strip()
        output_dir = self.output_dir_input.text().strip()
        api_key = self.api_key_input.text().strip()

        if not os.path.exists(input_file):
            QMessageBox.warning(self, "Error", "Input file not found.")
            return

        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create output directory: {str(e)}")
                return

        # Get processing options
        keep_original_mix = self.keep_original_mix.isChecked()
        keep_drum_stem = self.keep_drum_stem.isChecked()

        # Update UI state
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.safe_update_ui('status', "Starting processing...")
        self.safe_update_ui('progress', (0.0, "Initializing..."))
        self.safe_update_ui('reset', None)  # Clear previous results

        # Log initiation
        self.safe_update_ui('log', f"Starting processing of {os.path.basename(input_file)}")

        # Record start time
        self.processing_start_time = time.time()

        # Start processing in a background thread
        self.processing_thread = MVSepThreadWorker(
            api_key,
            input_file,
            output_dir,
            keep_original_mix=keep_original_mix,
            keep_drum_stem=keep_drum_stem
        )

        # Connect signals
        worker = self.processing_thread.worker
        if worker:
            worker.progress_updated.connect(self._on_progress_updated)
            worker.status_updated.connect(self._on_status_updated)
            worker.log_message.connect(self._on_log_message)
            worker.processing_completed.connect(self._on_processing_completed)
            worker.processing_failed.connect(self._on_processing_failed)

        # Start the thread
        self.processing_thread.start()

    def _on_cancel_clicked(self):
        """Handle cancel button click."""
        if not self.processing_thread:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Cancellation",
            "Are you sure you want to cancel the current processing job?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.safe_update_ui('status', "Cancelling...")
            self.safe_update_ui('log', "Cancelling processing job...")

            if self.processing_thread and self.processing_thread.isRunning():
                self.processing_thread.cancel()

                # Wait briefly for cancellation to take effect
                if not self.processing_thread.wait(5000):  # 5 second timeout
                    self.safe_update_ui('log', "Warning: Thread did not terminate normally, forcing termination")
                    self.processing_thread.terminate()
                    self.processing_thread.wait()

            self._finalize_processing(cancelled=True)

    def _finalize_processing(self, cancelled: bool = False, error: bool = False):
        """
        Clean up after processing completes or is cancelled.

        Args:
            cancelled: Whether the processing was cancelled
            error: Whether the processing failed with an error
        """
        # Enable/disable buttons
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # Calculate processing time
        if self.processing_start_time > 0:
            elapsed = time.time() - self.processing_start_time
            if cancelled:
                self.safe_update_ui('log', f"Processing cancelled after {elapsed:.1f} seconds")
            elif error:
                self.safe_update_ui('log', f"Processing failed after {elapsed:.1f} seconds")
            else:
                self.safe_update_ui('log', f"Processing completed in {elapsed:.1f} seconds")

            self.processing_start_time = 0

        # Clean up thread
        if self.processing_thread:
            if self.processing_thread.isRunning():
                self.processing_thread.quit()
                self.processing_thread.wait()
            self.processing_thread = None

    @Slot(float, str)
    def _on_progress_updated(self, progress: float, message: str):
        """Handle progress updates from the worker thread."""
        self.safe_update_ui('progress', (progress, message))

    @Slot(str)
    def _on_status_updated(self, message: str):
        """Handle status updates from the worker thread."""
        self.safe_update_ui('status', message)

    @Slot(str)
    def _on_log_message(self, message: str):
        """Handle log messages from the worker thread."""
        self.safe_update_ui('log', message)

    @Slot(dict)
    def _on_processing_completed(self, result_files: Dict[str, str]):
        """Handle processing completion from the worker thread."""
        self.result_files = result_files
        self.safe_update_ui('progress', (1.0, "Processing complete"))
        self.safe_update_ui('status', "Processing complete")
        self.safe_update_ui('results', result_files)
        self.safe_update_ui('log', f"Processing completed successfully with {len(result_files)} output files")
        self._finalize_processing()

    @Slot(str)
    def _on_processing_failed(self, error_message: str):
        """Handle processing failure from the worker thread."""
        self.safe_update_ui('log', f"ERROR: {error_message}")
        self.safe_update_ui('status', "Processing failed")
        self.safe_update_ui('progress', (0.0, "Failed"))

        # Create a detailed error message
        detailed_error = error_message
        if "Cannot connect to MVSep API server" in error_message:
            detailed_error = (
                f"Cannot connect to MVSep API server at {os.environ.get('MVSEP_BASE_URL', 'default URL')}\n\n"
                f"Error details: {error_message}\n\n"
                f"Possible solutions:\n"
                f"- Check your internet connection\n"
                f"- Verify the API server is running and accessible\n"
                f"- Check if the API endpoint URL is correct in the .env file"
            )

        # Display error message with more details
        error_box = QMessageBox(self)
        error_box.setIcon(QMessageBox.Critical)
        error_box.setWindowTitle("Processing Error")
        error_box.setText("MVSep Processing Failed")
        error_box.setInformativeText(error_message)
        error_box.setDetailedText(detailed_error)
        error_box.setStandardButtons(QMessageBox.Ok)
        error_box.exec_()

        # Cleanup processing thread with error flag
        self._finalize_processing(cancelled=False, error=True)

    def safe_update_ui(self, component_id: str, value):
        """
        Update UI components safely from any thread.

        Args:
            component_id: Identifier for the UI component to update
            value: Value to update the component with
        """
        self.ui_updater.safe_update(component_id, value)

    def _update_progress_unsafe(self, value):
        """
        Update progress bar and message (unsafe, must be called in UI thread).

        Args:
            value: Tuple of (progress, message)
        """
        progress, message = value
        progress_percent = int(progress * 100)
        self.progress_bar.setValue(progress_percent)
        self.detailed_status.setText(message)

    def _update_status_unsafe(self, message: str):
        """
        Update status label (unsafe, must be called in UI thread).

        Args:
            message: Status message
        """
        self.status_label.setText(message)

    def _update_detailed_status_unsafe(self, message: str):
        """
        Update detailed status label (unsafe, must be called in UI thread).

        Args:
            message: Detailed status message
        """
        self.detailed_status.setText(message)

    def _update_results_unsafe(self, result_files: Dict[str, str]):
        """
        Update results section (unsafe, must be called in UI thread).

        Args:
            result_files: Dictionary mapping stem names to file paths
        """
        if not result_files:
            self.results_label.setText("No results available")
            return

        # Build results text
        result_text = "<b>Processing Results:</b><br>"
        result_text += f"<p>Successfully processed {len(result_files)} stems:</p>"
        result_text += "<ul>"

        # Group results by type
        drum_components = {}
        other_stems = {}

        for stem_name, file_path in result_files.items():
            # Check if this is a drum component
            if stem_name in ['kick', 'snare', 'tom', 'hihat', 'crash', 'ride']:
                drum_components[stem_name] = file_path
            else:
                other_stems[stem_name] = file_path

        # Add drum components
        if drum_components:
            result_text += "<li><b>Drum Components:</b><ul>"
            for stem_name, file_path in sorted(drum_components.items()):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                result_text += f"<li>{stem_name.title()}: {file_name} ({file_size:.2f} MB)</li>"
            result_text += "</ul></li>"

        # Add other stems
        if other_stems:
            result_text += "<li><b>Other Stems:</b><ul>"
            for stem_name, file_path in sorted(other_stems.items()):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # MB
                result_text += f"<li>{stem_name.title()}: {file_name} ({file_size:.2f} MB)</li>"
            result_text += "</ul></li>"

        result_text += "</ul>"

        # Add output directory
        if result_files:
            first_file = next(iter(result_files.values()))
            output_dir = os.path.dirname(first_file)
            result_text += f"<p>Files saved to: {output_dir}</p>"

        self.results_label.setText(result_text)

    def _add_log_unsafe(self, message: str):
        """
        Add message to log (unsafe, must be called in UI thread).

        Args:
            message: Log message
        """
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")

        # Scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _reset_ui_unsafe(self, _):
        """Reset UI components to initial state (unsafe, must be called in UI thread)."""
        self.progress_bar.setValue(0)
        self.detailed_status.setText("")
        self.result_files = {}
        self.results_label.setText("No results available")

    def closeEvent(self, event):
        """Handle widget close event to clean up resources."""
        # Cancel any ongoing processing
        if self.processing_thread and self.processing_thread.isRunning():
            self.processing_thread.cancel()
            self.processing_thread.quit()
            self.processing_thread.wait()

        # Clean up UI updater
        self.ui_updater.clear_pending_updates()

        # Accept the event
        event.accept()
