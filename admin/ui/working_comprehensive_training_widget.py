"""
WORKING Comprehensive Training Widget
======================================
Actually runs real comprehensive training instead of simulating it.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QComboBox, QSpinBox, QTextEdit, QProgressBar,
    QMessageBox, QGroupBox, QGridLayout, QFormLayout
)

logger = logging.getLogger(__name__)

# Import training modules
try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from training.model_trainer import AutonomousTrainer, TrainingConfig
    from training.dataset_builder import DrumDatasetBuilder
    TRAINING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Training modules not available: {e}")
    TRAINING_AVAILABLE = False


class RealTrainingThread(QThread):
    """Actually runs real training"""
    progress_update = Signal(str, int, str)  # phase, progress, status
    phase_complete = Signal(str, dict)  # phase, results
    training_complete = Signal(bool, str)  # success, message
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.should_stop = False
        
    def run(self):
        """Run comprehensive training phases"""
        try:
            # Phase 1: Foundation Training
            if not self._run_foundation_phase():
                return
            
            # Phase 2: Pattern & Style (uses same dataset for now)
            if not self._run_pattern_phase():
                return
            
            # Phase 3: Professional (extended training)
            if not self._run_professional_phase():
                return
            
            # Complete
            self.training_complete.emit(
                True,
                "All comprehensive training phases completed successfully!"
            )
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            self.training_complete.emit(False, f"Training failed: {str(e)}")
    
    def _run_foundation_phase(self) -> bool:
        """Phase 1: Foundation training"""
        try:
            self.progress_update.emit("Foundation", 0, "Starting foundation phase...")
            
            if self.should_stop:
                return False
            
            # Build dataset
            self.progress_update.emit("Foundation", 10, "Building dataset...")
            builder = DrumDatasetBuilder()
            dataset = builder.build_humanization_dataset(min_samples=10)
            
            # Configure training
            epochs = self.config.get('epochs', 30)
            # Use absolute path for checkpoints
            module_dir = Path(__file__).parent.parent
            checkpoint_dir = module_dir / "models" / "checkpoints"
            config = TrainingConfig(
                epochs=epochs,
                batch_size=self.config.get('batch_size', 16),
                learning_rate=0.001,
                use_gpu=True,
                checkpoint_dir=checkpoint_dir,
                early_stopping_patience=10,
            )
            
            # Create trainer
            self.progress_update.emit("Foundation", 15, "Creating model...")
            trainer = AutonomousTrainer(config)
            
            input_size = dataset.X_train.shape[1]
            output_size = dataset.y_train.shape[1]
            trainer.create_model(input_size=input_size, output_size=output_size)
            
            # Train with progress
            self.progress_update.emit("Foundation", 20, "Training...")
            
            def progress_callback(epoch, total_epochs, train_loss, val_loss):
                if self.should_stop:
                    return False
                progress = 20 + int((epoch / total_epochs) * 60)
                status = f"Foundation - Epoch {epoch}/{total_epochs} | Loss: {train_loss:.4f}"
                self.progress_update.emit("Foundation", progress, status)
                return True
            
            metrics = trainer.train_model(
                dataset.X_train,
                dataset.y_train,
                dataset.X_val,
                dataset.y_val,
                progress_callback=progress_callback
            )
            
            if self.should_stop:
                return False
            
            # Save
            self.progress_update.emit("Foundation", 90, "Saving model...")
            # Convert TrainingMetrics to dict for checkpoint saving
            try:
                last_metrics = metrics[-1] if metrics else None
                if last_metrics:
                    # Check if it's a dict or dataclass
                    if isinstance(last_metrics, dict):
                        # It's already a dict
                        metrics_dict = last_metrics
                        final_loss = last_metrics.get('val_loss', 0)
                    else:
                        # It's a TrainingMetrics dataclass
                        metrics_dict = {
                            'epoch': last_metrics.epoch,
                            'train_loss': last_metrics.train_loss,
                            'val_loss': last_metrics.val_loss,
                        }
                        final_loss = last_metrics.val_loss
                else:
                    metrics_dict = {}
                    final_loss = 0
                
                checkpoint_path = trainer.save_checkpoint("foundation_model.pth", metrics_dict)
            except Exception as e:
                self.training_complete.emit(False, f"Error saving checkpoint: {e}")
                return False
            results = {
                'checkpoint': str(checkpoint_path),
                'final_loss': final_loss,
                'epochs_completed': len(metrics),
                'samples_trained': len(dataset.X_train)
            }
            
            self.progress_update.emit("Foundation", 100, "Foundation phase complete!")
            self.phase_complete.emit("Foundation", results)
            
            return True
            
        except Exception as e:
            self.training_complete.emit(False, f"Foundation phase failed: {e}")
            return False
    
    def _run_pattern_phase(self) -> bool:
        """Phase 2: Pattern & style training"""
        try:
            self.progress_update.emit("Pattern", 0, "Starting pattern phase...")
            
            if self.should_stop:
                return False
            
            # Build dataset
            self.progress_update.emit("Pattern", 10, "Building pattern dataset...")
            builder = DrumDatasetBuilder()
            dataset = builder.build_humanization_dataset(min_samples=10)
            
            # Configure for more epochs
            epochs = self.config.get('epochs', 30) + 20  # Extended training
            # Use absolute path for checkpoints
            module_dir = Path(__file__).parent.parent
            checkpoint_dir = module_dir / "models" / "checkpoints"
            config = TrainingConfig(
                epochs=epochs,
                batch_size=self.config.get('batch_size', 16),
                learning_rate=0.0008,  # Slightly lower LR
                use_gpu=True,
                checkpoint_dir=checkpoint_dir,
                early_stopping_patience=15,
            )
            
            # Create trainer
            self.progress_update.emit("Pattern", 15, "Creating model...")
            trainer = AutonomousTrainer(config)
            
            input_size = dataset.X_train.shape[1]
            output_size = dataset.y_train.shape[1]
            trainer.create_model(input_size=input_size, output_size=output_size)
            
            # Train
            self.progress_update.emit("Pattern", 20, "Training patterns...")
            
            def progress_callback(epoch, total_epochs, train_loss, val_loss):
                if self.should_stop:
                    return False
                progress = 20 + int((epoch / total_epochs) * 60)
                status = f"Pattern - Epoch {epoch}/{total_epochs} | Loss: {train_loss:.4f}"
                self.progress_update.emit("Pattern", progress, status)
                return True
            
            metrics = trainer.train_model(
                dataset.X_train,
                dataset.y_train,
                dataset.X_val,
                dataset.y_val,
                progress_callback=progress_callback
            )
            
            if self.should_stop:
                return False
            
            # Save
            self.progress_update.emit("Pattern", 90, "Saving model...")
            # Convert TrainingMetrics to dict for checkpoint saving
            try:
                last_metrics = metrics[-1] if metrics else None
                if last_metrics:
                    # Check if it's a dict or dataclass
                    if isinstance(last_metrics, dict):
                        # It's already a dict
                        metrics_dict = last_metrics
                        final_loss = last_metrics.get('val_loss', 0)
                    else:
                        # It's a TrainingMetrics dataclass
                        metrics_dict = {
                            'epoch': last_metrics.epoch,
                            'train_loss': last_metrics.train_loss,
                            'val_loss': last_metrics.val_loss,
                        }
                        final_loss = last_metrics.val_loss
                else:
                    metrics_dict = {}
                    final_loss = 0
                
                checkpoint_path = trainer.save_checkpoint("pattern_model.pth", metrics_dict)
            except Exception as e:
                self.training_complete.emit(False, f"Error saving pattern checkpoint: {e}")
                return False
            results = {
                'checkpoint': str(checkpoint_path),
                'final_loss': final_loss,
                'epochs_completed': len(metrics),
                'samples_trained': len(dataset.X_train)
            }
            
            self.progress_update.emit("Pattern", 100, "Pattern phase complete!")
            self.phase_complete.emit("Pattern", results)
            
            return True
            
        except Exception as e:
            self.training_complete.emit(False, f"Pattern phase failed: {e}")
            return False
    
    def _run_professional_phase(self) -> bool:
        """Phase 3: Professional training"""
        try:
            self.progress_update.emit("Professional", 0, "Starting professional phase...")
            
            if self.should_stop:
                return False
            
            # Build dataset
            self.progress_update.emit("Professional", 10, "Building professional dataset...")
            builder = DrumDatasetBuilder()
            dataset = builder.build_humanization_dataset(min_samples=10)
            
            # Configure for maximum training
            epochs = self.config.get('epochs', 30) + 40  # Extended training
            # Use absolute path for checkpoints
            module_dir = Path(__file__).parent.parent
            checkpoint_dir = module_dir / "models" / "checkpoints"
            config = TrainingConfig(
                epochs=epochs,
                batch_size=self.config.get('batch_size', 16),
                learning_rate=0.0005,  # Lower LR for fine-tuning
                use_gpu=True,
                checkpoint_dir=checkpoint_dir,
                early_stopping_patience=20,
            )
            
            # Create trainer
            self.progress_update.emit("Professional", 15, "Creating professional model...")
            trainer = AutonomousTrainer(config)
            
            input_size = dataset.X_train.shape[1]
            output_size = dataset.y_train.shape[1]
            trainer.create_model(input_size=input_size, output_size=output_size)
            
            # Train
            self.progress_update.emit("Professional", 20, "Training professional model...")
            
            def progress_callback(epoch, total_epochs, train_loss, val_loss):
                if self.should_stop:
                    return False
                progress = 20 + int((epoch / total_epochs) * 60)
                status = f"Professional - Epoch {epoch}/{total_epochs} | Loss: {train_loss:.4f}"
                self.progress_update.emit("Professional", progress, status)
                return True
            
            metrics = trainer.train_model(
                dataset.X_train,
                dataset.y_train,
                dataset.X_val,
                dataset.y_val,
                progress_callback=progress_callback
            )
            
            if self.should_stop:
                return False
            
            # Save as final comprehensive model
            self.progress_update.emit("Professional", 90, "Saving comprehensive model...")
            # Convert TrainingMetrics to dict for checkpoint saving
            try:
                last_metrics = metrics[-1] if metrics else None
                if last_metrics:
                    # Check if it's a dict or dataclass
                    if isinstance(last_metrics, dict):
                        # It's already a dict
                        metrics_dict = last_metrics
                        final_loss = last_metrics.get('val_loss', 0)
                    else:
                        # It's a TrainingMetrics dataclass
                        metrics_dict = {
                            'epoch': last_metrics.epoch,
                            'train_loss': last_metrics.train_loss,
                            'val_loss': last_metrics.val_loss,
                        }
                        final_loss = last_metrics.val_loss
                else:
                    metrics_dict = {}
                    final_loss = 0
                
                checkpoint_path = trainer.save_checkpoint("comprehensive_model.pth", metrics_dict)
            except Exception as e:
                self.training_complete.emit(False, f"Error saving professional checkpoint: {e}")
                return False
            results = {
                'checkpoint': str(checkpoint_path),
                'final_loss': final_loss,
                'epochs_completed': len(metrics),
                'samples_trained': len(dataset.X_train)
            }
            
            self.progress_update.emit("Professional", 100, "Professional phase complete!")
            self.phase_complete.emit("Professional", results)
            
            return True
            
        except Exception as e:
            self.training_complete.emit(False, f"Professional phase failed: {e}")
            return False
    
    def stop(self):
        """Stop training"""
        self.should_stop = True


class WorkingComprehensiveTrainingWidget(QWidget):
    """Comprehensive training widget that actually works"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.training_thread = None
        self._setup_ui()
        logger.info("Working Comprehensive Training Widget initialized")
    
    def _setup_ui(self):
        """Setup UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel("🎯 COMPREHENSIVE TRAINING - WORKING VERSION")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header.setFont(font)
        header.setStyleSheet("color: #DC3545;")
        main_layout.addWidget(header)
        
        desc = QLabel("Multi-phase training: Foundation → Pattern → Professional")
        main_layout.addWidget(desc)
        
        if not TRAINING_AVAILABLE:
            warning = QLabel("⚠️ Training modules not available")
            warning.setStyleSheet("color: orange; font-weight: bold;")
            main_layout.addWidget(warning)
        
        # Configuration
        config_group = QGroupBox("Training Configuration")
        config_layout = QFormLayout(config_group)
        
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setMinimum(10)
        self.epochs_spin.setMaximum(200)
        self.epochs_spin.setValue(30)
        config_layout.addRow("Base Epochs per Phase:", self.epochs_spin)
        
        self.batch_spin = QSpinBox()
        self.batch_spin.setMinimum(4)
        self.batch_spin.setMaximum(128)
        self.batch_spin.setValue(16)
        self.batch_spin.setSingleStep(4)
        config_layout.addRow("Batch Size:", self.batch_spin)
        
        main_layout.addWidget(config_group)
        
        # Phase progress
        phases_group = QGroupBox("Phase Progress")
        phases_layout = QGridLayout(phases_group)
        
        phases_layout.addWidget(QLabel("Foundation:"), 0, 0)
        self.foundation_progress = QProgressBar()
        phases_layout.addWidget(self.foundation_progress, 0, 1)
        self.foundation_status = QLabel("Waiting")
        phases_layout.addWidget(self.foundation_status, 0, 2)
        
        phases_layout.addWidget(QLabel("Pattern & Style:"), 1, 0)
        self.pattern_progress = QProgressBar()
        phases_layout.addWidget(self.pattern_progress, 1, 1)
        self.pattern_status = QLabel("Waiting")
        phases_layout.addWidget(self.pattern_status, 1, 2)
        
        phases_layout.addWidget(QLabel("Professional:"), 2, 0)
        self.professional_progress = QProgressBar()
        phases_layout.addWidget(self.professional_progress, 2, 1)
        self.professional_status = QLabel("Waiting")
        phases_layout.addWidget(self.professional_status, 2, 2)
        
        main_layout.addWidget(phases_group)
        
        # Training log
        log_group = QGroupBox("Training Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
        
        # Buttons
        buttons = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 LAUNCH Start Comprehensive Training")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #DC3545;
                color: white;
                padding: 12px 20px;
                font-weight: bold;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background: #c82333; }
            QPushButton:disabled { background: #cccccc; color: #666666; }
        """)
        self.start_btn.clicked.connect(self._start_training)
        self.start_btn.setEnabled(TRAINING_AVAILABLE)
        buttons.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                padding: 12px 20px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background: #5a6268; }
        """)
        self.stop_btn.clicked.connect(self._stop_training)
        self.stop_btn.setEnabled(False)
        buttons.addWidget(self.stop_btn)
        
        buttons.addStretch(1)
        main_layout.addLayout(buttons)
        
        main_layout.addStretch(1)
    
    def _log(self, message):
        """Add to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def _start_training(self):
        """Start comprehensive training"""
        if not TRAINING_AVAILABLE:
            QMessageBox.warning(self, "Not Available", "Training modules not loaded")
            return
        
        if self.training_thread and self.training_thread.isRunning():
            QMessageBox.warning(self, "Running", "Training already in progress")
            return
        
        # Confirm
        reply = QMessageBox.question(
            self,
            "Start Comprehensive Training",
            f"This will run 3 training phases:\n\n"
            f"1. Foundation (~{self.epochs_spin.value()} epochs)\n"
            f"2. Pattern & Style (~{self.epochs_spin.value() + 20} epochs)\n"
            f"3. Professional (~{self.epochs_spin.value() + 40} epochs)\n\n"
            f"Total time: ~30-90 minutes\n\n"
            f"Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Reset UI
        self.foundation_progress.setValue(0)
        self.pattern_progress.setValue(0)
        self.professional_progress.setValue(0)
        self.foundation_status.setText("Starting...")
        self.pattern_status.setText("Waiting")
        self.professional_status.setText("Waiting")
        self.log_text.clear()
        
        self._log("=" * 60)
        self._log("🚀 STARTING COMPREHENSIVE TRAINING")
        self._log(f"Base epochs: {self.epochs_spin.value()}")
        self._log(f"Batch size: {self.batch_spin.value()}")
        self._log("=" * 60)
        
        # Create and start thread
        config = {
            'epochs': self.epochs_spin.value(),
            'batch_size': self.batch_spin.value()
        }
        
        self.training_thread = RealTrainingThread(config)
        self.training_thread.progress_update.connect(self._on_progress)
        self.training_thread.phase_complete.connect(self._on_phase_complete)
        self.training_thread.training_complete.connect(self._on_complete)
        self.training_thread.start()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.epochs_spin.setEnabled(False)
        self.batch_spin.setEnabled(False)
    
    @Slot(str, int, str)
    def _on_progress(self, phase, progress, status):
        """Update progress"""
        if phase == "Foundation":
            self.foundation_progress.setValue(progress)
            self.foundation_status.setText(status)
        elif phase == "Pattern":
            self.pattern_progress.setValue(progress)
            self.pattern_status.setText(status)
        elif phase == "Professional":
            self.professional_progress.setValue(progress)
            self.professional_status.setText(status)
        
        self._log(status)
    
    @Slot(str, dict)
    def _on_phase_complete(self, phase, results):
        """Phase complete"""
        self._log(f"✅ {phase} phase COMPLETE!")
        self._log(f"   Checkpoint: {results.get('checkpoint', 'N/A')}")
        self._log(f"   Final loss: {results.get('final_loss', 0):.4f}")
        self._log(f"   Epochs: {results.get('epochs_completed', 0)}")
        self._log("")
    
    @Slot(bool, str)
    def _on_complete(self, success, message):
        """Training complete"""
        self._log("=" * 60)
        if success:
            self._log(f"✅ {message}")
            QMessageBox.information(self, "Complete", message)
        else:
            self._log(f"❌ {message}")
            QMessageBox.warning(self, "Failed", message)
        
        # Reset UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.epochs_spin.setEnabled(True)
        self.batch_spin.setEnabled(True)
    
    def _stop_training(self):
        """Stop training"""
        if self.training_thread and self.training_thread.isRunning():
            self._log("⏹ Stopping training...")
            self.training_thread.stop()
