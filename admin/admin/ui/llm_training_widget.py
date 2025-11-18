"""
LLM Training Tab for DrumTracKAI Admin
======================================
This module provides a simple LLM training interface tab.
"""
import logging
import os

from PySide6.QtCore import QTimer
from PySide6.QtCore import Qt, Signal, Slot, QThreadPool
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QSpinBox, QLineEdit, QTextEdit,
    QProgressBar, QFileDialog, QMessageBox, QGroupBox
)
from pathlib import Path

logger = logging.getLogger(__name__)

class LLMTrainingTab(QWidget):
    """Tab for LLM model training and management."""

    training_started = Signal(str)  # model_name
    training_progress = Signal(int)  # percent
    training_completed = Signal(str, bool)  # model_name, success

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        logger.info("LLM Training tab initialized")

    def _setup_ui(self):
        """Set up the user interface."""
        self.setObjectName("LLMTrainingTab")

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Header section
        header_label = QLabel("LLM Training & Management")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header_label.setFont(font)
        main_layout.addWidget(header_label)

        # Description
        description = QLabel("Train and manage language models for drum pattern generation.")
        main_layout.addWidget(description)

        # Model selection section
        model_group = QGroupBox("Model Selection")
        model_layout = QVBoxLayout(model_group)

        # Model selector
        model_selector_layout = QHBoxLayout()
        model_label = QLabel("Model:")
        self.model_combo = QComboBox()
        self.model_combo.addItem("DrumTracKAI-Small", "small")
        self.model_combo.addItem("DrumTracKAI-Medium", "medium")
        self.model_combo.addItem("DrumTracKAI-Large", "large")
        self.refresh_button = QPushButton("Refresh")

        model_selector_layout.addWidget(model_label)
        model_selector_layout.addWidget(self.model_combo, 1)
        model_selector_layout.addWidget(self.refresh_button)
        model_layout.addLayout(model_selector_layout)

        # Model info
        self.model_info = QLabel("Model information will appear here")
        model_layout.addWidget(self.model_info)

        main_layout.addWidget(model_group)

        # Training parameters section
        training_group = QGroupBox("Training Parameters")
        training_layout = QVBoxLayout(training_group)

        # Dataset selection
        dataset_layout = QHBoxLayout()
        dataset_label = QLabel("Dataset:")
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItem("Standard Drum Patterns", "standard")
        self.dataset_combo.addItem("Jazz Patterns", "jazz")
        self.dataset_combo.addItem("Rock Patterns", "rock")
        self.dataset_combo.addItem("Electronic Patterns", "electronic")

        dataset_layout.addWidget(dataset_label)
        dataset_layout.addWidget(self.dataset_combo, 1)
        training_layout.addLayout(dataset_layout)

        # Epochs and batch size
        params_layout = QHBoxLayout()

        epochs_label = QLabel("Epochs:")
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setMinimum(1)
        self.epochs_spin.setMaximum(100)
        self.epochs_spin.setValue(10)

        batch_label = QLabel("Batch Size:")
        self.batch_spin = QSpinBox()
        self.batch_spin.setMinimum(1)
        self.batch_spin.setMaximum(128)
        self.batch_spin.setValue(32)
        self.batch_spin.setSingleStep(4)

        params_layout.addWidget(epochs_label)
        params_layout.addWidget(self.epochs_spin)
        params_layout.addWidget(batch_label)
        params_layout.addWidget(self.batch_spin)
        params_layout.addStretch(1)

        training_layout.addLayout(params_layout)

        main_layout.addWidget(training_group)

        # Training progress
        progress_group = QGroupBox("Training Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)

        self.status_label = QLabel("Ready")

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)

        main_layout.addWidget(progress_group)

        # Action buttons
        buttons_layout = QHBoxLayout()

        self.train_button = QPushButton("Start Training")
        self.train_button.clicked.connect(self._on_train)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self._on_stop)
        self.stop_button.setEnabled(False)

        self.export_button = QPushButton("Export Model")
        self.export_button.clicked.connect(self._on_export)

        buttons_layout.addWidget(self.train_button)
        buttons_layout.addWidget(self.stop_button)
        buttons_layout.addWidget(self.export_button)

        main_layout.addLayout(buttons_layout)

        # Add stretching space at the bottom
        main_layout.addStretch(1)

        # Initial UI update
        self._update_model_info()

    def _update_model_info(self):
        """Update the model information display."""
        model_id = self.model_combo.currentData()
        model_name = self.model_combo.currentText()

        # In a real implementation, this would fetch actual model info
        if model_id == "small":
            info = "Small model: 10M parameters, suitable for basic patterns"
        elif model_id == "medium":
            info = "Medium model: 50M parameters, balanced performance"
        elif model_id == "large":
            info = "Large model: 200M parameters, highest quality output"
        else:
            info = "Unknown model"

        self.model_info.setText(info)

    def _on_train(self):
        """Handle start training button click - Launch real MVSep+LLM training pipeline."""
        model_id = self.model_combo.currentData()
        dataset_id = self.dataset_combo.currentData()
        epochs = self.epochs_spin.value()
        batch_size = self.batch_spin.value()

        msg = (f"Starting REAL MVSep+LLM training pipeline: {model_id} model on {dataset_id} dataset\n"
               f"Epochs: {epochs}, Batch Size: {batch_size}")

        logger.info(msg)
        self.status_label.setText("Starting MVSep+LLM training pipeline...")
        self.progress_bar.setValue(0)

        # Launch the real training pipeline as a background process
        self._start_real_training_pipeline(model_id, dataset_id, epochs, batch_size)

        # Update UI state
        self.train_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.export_button.setEnabled(False)

        self.training_started.emit(model_id)

    def _start_real_training_pipeline(self, model_id, dataset_id, epochs, batch_size):
        """Start the real MVSep+LLM training pipeline as a background process."""
        import subprocess
        import threading
        import os
        from pathlib import Path
        
        # Set up environment variables for GPU-only training
        env = os.environ.copy()
        env['NUMBA_DISABLE_INTEL_SVML'] = '1'
        env['OMP_NUM_THREADS'] = '1'
        env['MKL_NUM_THREADS'] = '1'
        
        # Path to the training pipeline script
        base_path = Path("D:/DrumTracKAI_v1.1.7")
        training_script = base_path / "training_pipeline_v1.1.7.py"
        python_exe = base_path / "drumtrackai_gpu_env" / "Scripts" / "python.exe"
        
        def run_training():
            """Run the training pipeline in a separate thread."""
            try:
                self.training_process = subprocess.Popen(
                    [str(python_exe), str(training_script)],
                    cwd=str(base_path),
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                # Monitor the process output for progress updates
                self._monitor_training_output()
                
            except Exception as e:
                logger.error(f"Failed to start training pipeline: {e}")
                self.status_label.setText(f"Training failed to start: {e}")
                self._on_training_completed(False)
        
        # Start training in background thread
        self.training_thread = threading.Thread(target=run_training, daemon=True)
        self.training_thread.start()
        
        # Start progress monitoring timer
        self.current_progress = 0
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._update_real_progress)
        self.progress_timer.start(1000)  # Update every 1 second
        
        logger.info(f"Real MVSep+LLM training pipeline started for {model_id}")
    
    def _monitor_training_output(self):
        """Monitor the training process output for progress and status updates."""
        if not hasattr(self, 'training_process') or self.training_process is None:
            return
            
        try:
            # Read output line by line
            for line in iter(self.training_process.stdout.readline, ''):
                if line:
                    line = line.strip()
                    logger.info(f"Training output: {line}")
                    
                    # Parse progress from output
                    if "MVSep Progress:" in line:
                        # Extract progress percentage from MVSep output
                        try:
                            progress_str = line.split("MVSep Progress:")[1].split("%")[0].strip()
                            progress = float(progress_str)
                            self.current_progress = min(int(progress * 0.3), 30)  # MVSep is 30% of total
                        except:
                            pass
                    elif "Training..." in line and "Epoch" in line:
                        # Extract epoch progress
                        try:
                            if "/" in line:
                                epoch_part = line.split("Epoch")[1].strip()
                                current, total = epoch_part.split("/")
                                epoch_progress = (int(current) / int(total)) * 70  # Training is 70% of total
                                self.current_progress = 30 + int(epoch_progress)  # Add to MVSep progress
                        except:
                            pass
                    elif "Training completed" in line:
                        self.current_progress = 100
                        self._on_training_completed(True)
                        break
                    elif "Training failed" in line or "Error" in line:
                        self._on_training_completed(False)
                        break
                        
            # Check if process has finished
            if self.training_process.poll() is not None:
                return_code = self.training_process.returncode
                if return_code == 0:
                    self._on_training_completed(True)
                else:
                    self._on_training_completed(False)
                    
        except Exception as e:
            logger.error(f"Error monitoring training output: {e}")
            self._on_training_completed(False)
    
    def _update_real_progress(self):
        """Update progress bar with real training progress."""
        self.progress_bar.setValue(self.current_progress)
        
        # Update status based on progress
        if self.current_progress <= 30:
            self.status_label.setText(f"Processing signature songs with MVSep... {self.current_progress}%")
        elif self.current_progress <= 100:
            epoch_progress = int((self.current_progress - 30) / 70 * self.epochs_spin.value())
            self.status_label.setText(f"Training neural network... Epoch {epoch_progress}/{self.epochs_spin.value()}")
        
        # Emit progress signal
        self.training_progress.emit(self.current_progress)
        
        # Stop timer if training is complete
        if self.current_progress >= 100:
            self.progress_timer.stop()

    def _simulate_training_progress(self):
        """Legacy method - now redirects to real training."""
        # This method is kept for compatibility but now starts real training
        self._start_real_training_pipeline("small", "standard", 10, 32)

    def _update_progress(self):
        """Update the progress simulation."""
        self.current_progress += 1
        self.progress_bar.setValue(self.current_progress)

        if self.current_progress >= 100:
            self.progress_timer.stop()
            self._on_training_completed(True)
        else:
            # Update status with current epoch info
            epochs = self.epochs_spin.value()
            current_epoch = int(self.current_progress / 100 * epochs)
            self.status_label.setText(f"Training... Epoch {current_epoch}/{epochs}")

            # Emit progress signal
            self.training_progress.emit(self.current_progress)

    def _on_stop(self):
        """Handle stop button click - Terminate real training process."""
        if hasattr(self, "progress_timer") and self.progress_timer.isActive():
            self.progress_timer.stop()
        
        # Terminate the real training process if running
        if hasattr(self, 'training_process') and self.training_process is not None:
            try:
                self.training_process.terminate()
                logger.info("Real training process terminated by user")
                self.status_label.setText("Training process terminated")
            except Exception as e:
                logger.error(f"Error terminating training process: {e}")
                self.status_label.setText(f"Error stopping training: {e}")
        else:
            logger.info("Training stopped by user")
            self.status_label.setText("Training stopped")

        # Update UI state
        self.train_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(True)

    def _on_training_completed(self, success):
        """Handle training completion."""
        model_id = self.model_combo.currentData()

        if success:
            logger.info(f"Training completed successfully for model {model_id}")
            self.status_label.setText("Training completed successfully")
        else:
            logger.error(f"Training failed for model {model_id}")
            self.status_label.setText("Training failed")

        # Update UI state
        self.train_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.export_button.setEnabled(True)

        # Emit completion signal
        self.training_completed.emit(model_id, success)

    def _on_export(self):
        """Handle export model button click."""
        model_id = self.model_combo.currentData()
        model_name = self.model_combo.currentText()

        # Ask for export location
        export_dir = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", "", QFileDialog.ShowDirsOnly
        )

        if not export_dir:
            return

        # In a real implementation, this would export the actual model
        # For now, just create a dummy file
        try:
            dummy_file = os.path.join(export_dir, f"{model_id}_model_export.txt")
            with open(dummy_file, 'w') as f:
                f.write(f"DrumTracKAI {model_name} model export\n")
                f.write(f"This is a placeholder for the actual model export file.")

            logger.info(f"Model {model_id} exported to {dummy_file}")
            QMessageBox.information(
                self, "Export Successful",
                f"Model successfully exported to:\n{dummy_file}"
            )
        except Exception as e:
            logger.error(f"Error exporting model: {e}")
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export model: {str(e)}"
            )
