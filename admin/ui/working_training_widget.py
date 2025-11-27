"""
Working LLM Training Widget
============================
Actually runs training instead of just simulating it
"""
import logging
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot, QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSpinBox, QTextEdit, QProgressBar, QMessageBox, QGroupBox
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


class TrainingThread(QThread):
    """Background thread for training"""
    progress_update = Signal(int, str)  # progress, status
    training_complete = Signal(bool, str)  # success, message
    
    def __init__(self, config, dataset):
        super().__init__()
        self.config = config
        self.dataset = dataset
        self.should_stop = False
        
    def run(self):
        """Run training in background"""
        try:
            self.progress_update.emit(0, "Initializing trainer...")
            
            # Create trainer
            trainer = AutonomousTrainer(self.config)
            
            # Create model
            input_size = self.dataset.X_train.shape[1]
            output_size = self.dataset.y_train.shape[1]
            
            self.progress_update.emit(5, "Creating model...")
            trainer.create_model(input_size=input_size, output_size=output_size)
            
            self.progress_update.emit(10, "Starting training...")
            
            # Train with progress callback
            def progress_callback(epoch, total_epochs, train_loss, val_loss):
                if self.should_stop:
                    return False  # Stop training
                    
                progress = int(10 + (epoch / total_epochs) * 85)
                status = f"Epoch {epoch}/{total_epochs} | Loss: {train_loss:.4f}"
                self.progress_update.emit(progress, status)
                return True
            
            # Run training
            metrics = trainer.train_model(
                self.dataset.X_train,
                self.dataset.y_train,
                self.dataset.X_val,
                self.dataset.y_val,
                progress_callback=progress_callback
            )
            
            if self.should_stop:
                self.training_complete.emit(False, "Training stopped by user")
                return
            
            # Save final model
            self.progress_update.emit(95, "Saving model...")
            checkpoint_path = trainer.save_checkpoint(
                "final_model.pth",
                metrics[-1] if metrics else {}
            )
            
            self.progress_update.emit(100, "Training complete!")
            
            # Success message
            final_loss = metrics[-1].get('val_loss', 0) if metrics else 0
            message = f"Training completed!\nFinal validation loss: {final_loss:.4f}\nModel saved to: {checkpoint_path}"
            self.training_complete.emit(True, message)
            
        except Exception as e:
            logger.error(f"Training failed: {e}", exc_info=True)
            self.training_complete.emit(False, f"Training failed: {str(e)}")
    
    def stop(self):
        """Request training to stop"""
        self.should_stop = True


class WorkingTrainingWidget(QWidget):
    """Training widget that actually works"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.training_thread = None
        self._setup_ui()
        logger.info("Working Training Widget initialized")
    
    def _setup_ui(self):
        """Set up the user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header
        header = QLabel("🤖 LLM Training - WORKING VERSION")
        font = QFont()
        font.setBold(True)
        font.setPointSize(14)
        header.setFont(font)
        main_layout.addWidget(header)
        
        # Status check
        if not TRAINING_AVAILABLE:
            warning = QLabel("⚠️ Training modules not available. Check Python environment.")
            warning.setStyleSheet("color: orange; font-weight: bold;")
            main_layout.addWidget(warning)
        
        # Dataset info group
        dataset_group = QGroupBox("Training Data")
        dataset_layout = QVBoxLayout(dataset_group)
        
        self.dataset_info = QLabel("Click 'Check Data' to see available samples")
        dataset_layout.addWidget(self.dataset_info)
        
        check_data_btn = QPushButton("Check Data")
        check_data_btn.clicked.connect(self._check_data)
        dataset_layout.addWidget(check_data_btn)
        
        main_layout.addWidget(dataset_group)
        
        # Training parameters
        params_group = QGroupBox("Training Parameters")
        params_layout = QVBoxLayout(params_group)
        
        # Dataset selection
        dataset_selector_layout = QHBoxLayout()
        dataset_selector_layout.addWidget(QLabel("Dataset:"))
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItem("Track A: Foundation Learning", "track_a")
        self.dataset_combo.addItem("Track B: Drummer Profiles", "track_b")
        self.dataset_combo.addItem("Combined Training", "combined")
        dataset_selector_layout.addWidget(self.dataset_combo, 1)
        params_layout.addLayout(dataset_selector_layout)
        
        # Epochs and batch size
        training_params = QHBoxLayout()
        
        training_params.addWidget(QLabel("Epochs:"))
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setMinimum(5)
        self.epochs_spin.setMaximum(500)
        self.epochs_spin.setValue(50)
        training_params.addWidget(self.epochs_spin)
        
        training_params.addWidget(QLabel("Batch Size:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setMinimum(4)
        self.batch_spin.setMaximum(128)
        self.batch_spin.setValue(16)
        self.batch_spin.setSingleStep(4)
        training_params.addWidget(self.batch_spin)
        
        training_params.addStretch(1)
        params_layout.addLayout(training_params)
        
        main_layout.addWidget(params_group)
        
        # Progress group
        progress_group = QGroupBox("Training Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to train")
        progress_layout.addWidget(self.status_label)
        
        main_layout.addWidget(progress_group)
        
        # Training log
        log_group = QGroupBox("Training Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
        
        # Buttons
        buttons = QHBoxLayout()
        
        self.start_btn = QPushButton("▶ Start Training")
        self.start_btn.clicked.connect(self._start_training)
        self.start_btn.setEnabled(TRAINING_AVAILABLE)
        buttons.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.clicked.connect(self._stop_training)
        self.stop_btn.setEnabled(False)
        buttons.addWidget(self.stop_btn)
        
        buttons.addStretch(1)
        main_layout.addLayout(buttons)
        
        main_layout.addStretch(1)
    
    def _log(self, message):
        """Add message to log"""
        self.log_text.append(message)
    
    def _check_data(self):
        """Check available training data"""
        if not TRAINING_AVAILABLE:
            QMessageBox.warning(self, "Not Available", "Training modules not loaded")
            return
        
        try:
            self._log("📊 Checking training data...")
            builder = DrumDatasetBuilder()
            stats = builder.get_dataset_stats()
            
            info = f"""Training Data Summary:
            
Total Samples: {stats['total_samples']}
Drummers: {len(stats['drummers'])}
Styles: {len(stats['styles'])}

Drummer List: {', '.join(stats['drummers']) if stats['drummers'] else 'None'}
Style List: {', '.join(stats['styles']) if stats['styles'] else 'None'}

Status: {'✅ Ready to train' if stats['total_samples'] >= 10 else '⚠️ Need at least 10 samples'}"""
            
            self.dataset_info.setText(info)
            self._log(f"✅ Found {stats['total_samples']} training samples")
            
        except Exception as e:
            self._log(f"❌ Error checking data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to check data: {e}")
    
    def _start_training(self):
        """Start actual training"""
        if not TRAINING_AVAILABLE:
            QMessageBox.warning(self, "Not Available", "Training modules not loaded")
            return
        
        if self.training_thread and self.training_thread.isRunning():
            QMessageBox.warning(self, "Already Running", "Training is already in progress")
            return
        
        try:
            self._log("=" * 60)
            self._log("🚀 Starting training...")
            
            # Build dataset
            self._log("📊 Building dataset...")
            builder = DrumDatasetBuilder()
            dataset = builder.build_humanization_dataset(min_samples=10)
            
            self._log(f"   Train: {len(dataset.X_train)} samples")
            self._log(f"   Val: {len(dataset.X_val)} samples")
            self._log(f"   Test: {len(dataset.X_test)} samples")
            
            # Create config
            # Use absolute path for checkpoints
            module_dir = Path(__file__).parent.parent
            checkpoint_dir = module_dir / "models" / "checkpoints"
            config = TrainingConfig(
                epochs=self.epochs_spin.value(),
                batch_size=self.batch_spin.value(),
                learning_rate=0.001,
                use_gpu=True,
                checkpoint_dir=checkpoint_dir,
                early_stopping_patience=15,
            )
            
            self._log(f"⚙️  Config: {config.epochs} epochs, batch size {config.batch_size}")
            
            # Create and start training thread
            self.training_thread = TrainingThread(config, dataset)
            self.training_thread.progress_update.connect(self._on_progress)
            self.training_thread.training_complete.connect(self._on_complete)
            self.training_thread.start()
            
            # Update UI
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.epochs_spin.setEnabled(False)
            self.batch_spin.setEnabled(False)
            self.dataset_combo.setEnabled(False)
            
        except Exception as e:
            self._log(f"❌ Failed to start training: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start training:\n{e}")
    
    @Slot(int, str)
    def _on_progress(self, progress, status):
        """Update progress"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(status)
        self._log(status)
    
    @Slot(bool, str)
    def _on_complete(self, success, message):
        """Handle training completion"""
        self._log("=" * 60)
        if success:
            self._log(f"✅ {message}")
            QMessageBox.information(self, "Success", message)
        else:
            self._log(f"❌ {message}")
            QMessageBox.warning(self, "Training Stopped", message)
        
        # Reset UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.epochs_spin.setEnabled(True)
        self.batch_spin.setEnabled(True)
        self.dataset_combo.setEnabled(True)
    
    def _stop_training(self):
        """Stop training"""
        if self.training_thread and self.training_thread.isRunning():
            self._log("⏹️ Stopping training...")
            self.training_thread.stop()
            self.status_label.setText("Stopping...")
