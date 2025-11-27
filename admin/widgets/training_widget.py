"""
Training Widget for Admin App
User-friendly interface for autonomous LLM training
"""

import logging
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QProgressBar, QTextEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)

# Import training modules
try:
    from admin.training.data_extraction import (
        SDSampleExtractor, CommercialSongAnalyzer, SensorDataCollector
    )
    from admin.training.dataset_builder import DrumDatasetBuilder
    from admin.training.model_trainer import AutonomousTrainer, TrainingConfig
    from admin.training.validation import ModelValidator
    from admin.training.deployment import ModelDeployer
    TRAINING_MODULES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Training modules not available: {e}")
    TRAINING_MODULES_AVAILABLE = False


class TrainingThread(QThread):
    """Background thread for training"""
    progress_update = Signal(int, str)
    training_complete = Signal(object)  # metrics
    training_error = Signal(str)
    
    def __init__(self, trainer, X_train, y_train, X_val, y_val):
        super().__init__()
        self.trainer = trainer
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
    
    def run(self):
        try:
            def progress_callback(percent, message):
                self.progress_update.emit(percent, message)
            
            metrics = self.trainer.train_model(
                self.X_train, self.y_train,
                self.X_val, self.y_val,
                progress_callback
            )
            self.training_complete.emit(metrics)
        except Exception as e:
            self.training_error.emit(str(e))


class TrainingWidget(QWidget):
    """
    Comprehensive training interface for the admin app
    Allows users to:
    - Extract training data
    - Build datasets
    - Train models
    - Validate results
    - Deploy to production
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if not TRAINING_MODULES_AVAILABLE:
            self._show_error_ui()
            return
        
        # Initialize training components
        self.sd_extractor = SDSampleExtractor()
        self.song_analyzer = CommercialSongAnalyzer()
        self.sensor_collector = SensorDataCollector()
        self.dataset_builder = DrumDatasetBuilder()
        self.trainer = None
        self.validator = ModelValidator()
        self.deployer = ModelDeployer()
        
        # Training state
        self.training_thread = None
        self.current_dataset = None
        
        self._init_ui()
        self._update_stats()
    
    def _show_error_ui(self):
        """Show error UI if modules not available"""
        layout = QVBoxLayout(self)
        error_label = QLabel(
            "⚠️ Training modules not available\n\n"
            "Please install required dependencies:\n"
            "pip install torch numpy sklearn librosa soundfile"
        )
        error_label.setStyleSheet("color: #ff6b6b; font-size: 14px; padding: 20px;")
        error_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(error_label)
    
    def _init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab widget for different stages
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_data_tab(), "📥 1. Data Extraction")
        self.tabs.addTab(self._create_dataset_tab(), "📊 2. Dataset Building")
        self.tabs.addTab(self._create_training_tab(), "🚀 3. Model Training")
        self.tabs.addTab(self._create_validation_tab(), "✅ 4. Validation")
        self.tabs.addTab(self._create_deployment_tab(), "🎯 5. Deployment")
        
        layout.addWidget(self.tabs)
        
        # Status bar at bottom
        status_bar = self._create_status_bar()
        layout.addWidget(status_bar)
    
    def _create_header(self) -> QWidget:
        """Create header with title and controls"""
        header = QGroupBox("Autonomous LLM Training System")
        header.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; }")
        layout = QVBoxLayout(header)
        
        # Title and description
        desc = QLabel(
            "Train AI to understand what makes drums sound human.\n"
            "Analyzes commercial songs, SD samples, and live sensor data."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(desc)
        
        return header
    
    def _create_data_tab(self) -> QWidget:
        """Create data extraction tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Statistics group
        stats_group = QGroupBox("📊 Current Data")
        stats_layout = QVBoxLayout(stats_group)
        self.data_stats_label = QLabel("Loading statistics...")
        stats_layout.addWidget(self.data_stats_label)
        layout.addWidget(stats_group)
        
        # SD Sample Extraction
        sd_group = QGroupBox("Superior Drummer Samples")
        sd_layout = QVBoxLayout(sd_group)
        
        sd_btn = QPushButton("📦 Extract SD3 Samples")
        sd_btn.clicked.connect(self._extract_sd_samples)
        sd_layout.addWidget(sd_btn)
        
        layout.addWidget(sd_group)
        
        # Commercial Songs
        songs_group = QGroupBox("Commercial Songs")
        songs_layout = QVBoxLayout(songs_group)
        
        song_btn = QPushButton("🎵 Analyze Commercial Songs")
        song_btn.clicked.connect(self._analyze_songs)
        songs_layout.addWidget(song_btn)
        
        layout.addWidget(songs_group)
        
        # Live Sensor Data
        sensor_group = QGroupBox("Live Drum Sensors")
        sensor_layout = QVBoxLayout(sensor_group)
        
        self.sensor_status = QLabel("Status: Not recording")
        sensor_layout.addWidget(self.sensor_status)
        
        sensor_buttons = QHBoxLayout()
        self.start_sensor_btn = QPushButton("🔴 Start Recording")
        self.start_sensor_btn.clicked.connect(self._start_sensor_recording)
        self.stop_sensor_btn = QPushButton("⏹️ Stop Recording")
        self.stop_sensor_btn.clicked.connect(self._stop_sensor_recording)
        self.stop_sensor_btn.setEnabled(False)
        
        sensor_buttons.addWidget(self.start_sensor_btn)
        sensor_buttons.addWidget(self.stop_sensor_btn)
        sensor_layout.addLayout(sensor_buttons)
        
        layout.addWidget(sensor_group)
        
        layout.addStretch()
        return tab
    
    def _create_dataset_tab(self) -> QWidget:
        """Create dataset building tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Dataset info
        info_group = QGroupBox("📦 Dataset Information")
        info_layout = QVBoxLayout(info_group)
        self.dataset_info_label = QLabel("No dataset built yet")
        info_layout.addWidget(self.dataset_info_label)
        layout.addWidget(info_group)
        
        # Build dataset button
        build_btn = QPushButton("🔨 Build Training Dataset")
        build_btn.clicked.connect(self._build_dataset)
        build_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        layout.addWidget(build_btn)
        
        # Export dataset
        export_btn = QPushButton("💾 Export Dataset")
        export_btn.clicked.connect(self._export_dataset)
        layout.addWidget(export_btn)
        
        layout.addStretch()
        return tab
    
    def _create_training_tab(self) -> QWidget:
        """Create model training tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Training configuration
        config_group = QGroupBox("⚙️ Training Configuration")
        config_layout = QVBoxLayout(config_group)
        
        # Epochs
        epochs_layout = QHBoxLayout()
        epochs_layout.addWidget(QLabel("Epochs:"))
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(10, 1000)
        self.epochs_spin.setValue(100)
        epochs_layout.addWidget(self.epochs_spin)
        epochs_layout.addStretch()
        config_layout.addLayout(epochs_layout)
        
        # Batch size
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(QLabel("Batch Size:"))
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(8, 128)
        self.batch_spin.setValue(32)
        batch_layout.addWidget(self.batch_spin)
        batch_layout.addStretch()
        config_layout.addLayout(batch_layout)
        
        # Learning rate
        lr_layout = QHBoxLayout()
        lr_layout.addWidget(QLabel("Learning Rate:"))
        self.lr_spin = QDoubleSpinBox()
        self.lr_spin.setDecimals(4)
        self.lr_spin.setRange(0.0001, 0.1)
        self.lr_spin.setValue(0.001)
        self.lr_spin.setSingleStep(0.0001)
        lr_layout.addWidget(self.lr_spin)
        lr_layout.addStretch()
        config_layout.addLayout(lr_layout)
        
        # Use GPU
        self.use_gpu_check = QCheckBox("Use GPU if available")
        self.use_gpu_check.setChecked(True)
        config_layout.addWidget(self.use_gpu_check)
        
        layout.addWidget(config_group)
        
        # Training progress
        progress_group = QGroupBox("📈 Training Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.training_progress = QProgressBar()
        progress_layout.addWidget(self.training_progress)
        
        self.training_status = QLabel("Ready to train")
        progress_layout.addWidget(self.training_status)
        
        layout.addWidget(progress_group)
        
        # Training controls
        controls_layout = QHBoxLayout()
        
        self.train_btn = QPushButton("🚀 Start Training")
        self.train_btn.clicked.connect(self._start_training)
        self.train_btn.setStyleSheet("font-size: 14px; padding: 10px; background: #4CAF50; color: white;")
        
        self.stop_train_btn = QPushButton("⏹️ Stop Training")
        self.stop_train_btn.clicked.connect(self._stop_training)
        self.stop_train_btn.setEnabled(False)
        
        controls_layout.addWidget(self.train_btn)
        controls_layout.addWidget(self.stop_train_btn)
        
        layout.addLayout(controls_layout)
        
        # Training log
        log_group = QGroupBox("📝 Training Log")
        log_layout = QVBoxLayout(log_group)
        self.training_log = QTextEdit()
        self.training_log.setReadOnly(True)
        self.training_log.setMaximumHeight(200)
        log_layout.addWidget(self.training_log)
        layout.addWidget(log_group)
        
        layout.addStretch()
        return tab
    
    def _create_validation_tab(self) -> QWidget:
        """Create validation tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Validation results
        results_group = QGroupBox("📊 Validation Results")
        results_layout = QVBoxLayout(results_group)
        self.validation_results = QTextEdit()
        self.validation_results.setReadOnly(True)
        self.validation_results.setPlainText("No validation results yet")
        results_layout.addWidget(self.validation_results)
        layout.addWidget(results_group)
        
        # Validate button
        validate_btn = QPushButton("✅ Validate Model")
        validate_btn.clicked.connect(self._validate_model)
        layout.addWidget(validate_btn)
        
        return tab
    
    def _create_deployment_tab(self) -> QWidget:
        """Create deployment tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Deployed models
        models_group = QGroupBox("📦 Deployed Models")
        models_layout = QVBoxLayout(models_group)
        
        self.models_table = QTableWidget()
        self.models_table.setColumnCount(4)
        self.models_table.setHorizontalHeaderLabels(["Name", "Version", "Active", "Deployed At"])
        models_layout.addWidget(self.models_table)
        
        layout.addWidget(models_group)
        
        # Deploy button
        deploy_btn = QPushButton("🎯 Deploy Current Model")
        deploy_btn.clicked.connect(self._deploy_model)
        deploy_btn.setStyleSheet("font-size: 14px; padding: 10px; background: #2196F3; color: white;")
        layout.addWidget(deploy_btn)
        
        return tab
    
    def _create_status_bar(self) -> QWidget:
        """Create status bar"""
        status_bar = QGroupBox()
        layout = QHBoxLayout(status_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._update_stats)
        layout.addWidget(refresh_btn)
        
        return status_bar
    
    @Slot()
    def _update_stats(self):
        """Update statistics display"""
        try:
            stats = self.dataset_builder.get_dataset_stats()
            
            stats_text = (
                f"📊 Total Samples: {stats['total_samples']}\n"
                f"👨‍🎤 Drummers: {len(stats['drummers'])}\n"
                f"🎵 Styles: {', '.join(stats['styles'].keys())}\n"
                f"💾 Sources: {stats['sources']}"
            )
            
            self.data_stats_label.setText(stats_text)
            self.status_label.setText(f"Ready - {stats['total_samples']} training samples available")
            
        except Exception as e:
            logger.error(f"Error updating stats: {e}")
            self.data_stats_label.setText(f"Error: {e}")
    
    @Slot()
    def _extract_sd_samples(self):
        """Extract Superior Drummer samples"""
        self.status_label.setText("Extracting SD samples...")
        try:
            count = self.sd_extractor.batch_extract(limit=100)
            self.status_label.setText(f"✅ Extracted {count} SD samples")
            self._update_stats()
            QMessageBox.information(self, "Success", f"Extracted {count} Superior Drummer samples!")
        except Exception as e:
            logger.error(f"SD extraction failed: {e}")
            QMessageBox.warning(self, "Error", f"SD extraction failed: {e}")
            self.status_label.setText("❌ SD extraction failed")
    
    @Slot()
    def _analyze_songs(self):
        """Analyze commercial songs"""
        # Open file dialog
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Audio Files",
            "",
            "Audio Files (*.wav *.mp3 *.flac);;All Files (*.*)"
        )
        
        if not files:
            return
        
        self.status_label.setText(f"Analyzing {len(files)} songs...")
        
        try:
            from pathlib import Path
            count = 0
            for file_path in files:
                features = self.song_analyzer.analyze_song(Path(file_path))
                if features:
                    count += 1
            
            self.status_label.setText(f"✅ Analyzed {count} songs")
            self._update_stats()
            QMessageBox.information(self, "Success", f"Analyzed {count} songs!")
        except Exception as e:
            logger.error(f"Song analysis failed: {e}")
            QMessageBox.warning(self, "Error", f"Song analysis failed: {e}")
            self.status_label.setText("❌ Song analysis failed")
    
    @Slot()
    def _start_sensor_recording(self):
        """Start recording from drum sensors"""
        self.sensor_collector.start_recording()
        self.sensor_status.setText("Status: 🔴 Recording...")
        self.start_sensor_btn.setEnabled(False)
        self.stop_sensor_btn.setEnabled(True)
        self.status_label.setText("Recording from drum sensors...")
    
    @Slot()
    def _stop_sensor_recording(self):
        """Stop recording from drum sensors"""
        events = self.sensor_collector.stop_recording()
        self.sensor_status.setText(f"Status: ✅ Recorded {len(events)} events")
        self.start_sensor_btn.setEnabled(True)
        self.stop_sensor_btn.setEnabled(False)
        
        # Extract features
        if events:
            features = self.sensor_collector.extract_features_from_recording(events, "live_drummer")
            self.status_label.setText(f"✅ Recorded and extracted features from {len(events)} events")
            self._update_stats()
    
    @Slot()
    def _build_dataset(self):
        """Build training dataset"""
        self.status_label.setText("Building dataset...")
        try:
            self.current_dataset = self.dataset_builder.build_humanization_dataset(min_samples=10)
            
            info_text = (
                f"✅ Dataset Built Successfully\n\n"
                f"Training samples: {len(self.current_dataset.X_train)}\n"
                f"Validation samples: {len(self.current_dataset.X_val)}\n"
                f"Test samples: {len(self.current_dataset.X_test)}\n"
                f"Features: {len(self.current_dataset.feature_names)}"
            )
            
            self.dataset_info_label.setText(info_text)
            self.status_label.setText("✅ Dataset built successfully")
            
            QMessageBox.information(self, "Success", "Dataset built successfully!")
            
        except Exception as e:
            logger.error(f"Dataset building failed: {e}")
            QMessageBox.warning(self, "Error", f"Dataset building failed: {e}")
            self.status_label.setText("❌ Dataset building failed")
    
    @Slot()
    def _export_dataset(self):
        """Export dataset to files"""
        if not self.current_dataset:
            QMessageBox.warning(self, "Error", "No dataset to export. Build a dataset first.")
            return
        
        folder = QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if folder:
            try:
                self.dataset_builder.export_dataset(self.current_dataset, Path(folder))
                QMessageBox.information(self, "Success", f"Dataset exported to {folder}")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Export failed: {e}")
    
    @Slot()
    def _start_training(self):
        """Start model training"""
        if not self.current_dataset:
            QMessageBox.warning(self, "Error", "No dataset available. Build a dataset first.")
            return
        
        # Create trainer with config
        config = TrainingConfig(
            epochs=self.epochs_spin.value(),
            batch_size=self.batch_spin.value(),
            learning_rate=self.lr_spin.value(),
            use_gpu=self.use_gpu_check.isChecked()
        )
        
        self.trainer = AutonomousTrainer(config)
        self.trainer.create_model(input_size=3, output_size=9)
        
        # Start training thread
        self.training_thread = TrainingThread(
            self.trainer,
            self.current_dataset.X_train,
            self.current_dataset.y_train,
            self.current_dataset.X_val,
            self.current_dataset.y_val
        )
        
        self.training_thread.progress_update.connect(self._on_training_progress)
        self.training_thread.training_complete.connect(self._on_training_complete)
        self.training_thread.training_error.connect(self._on_training_error)
        
        self.training_thread.start()
        
        # Update UI
        self.train_btn.setEnabled(False)
        self.stop_train_btn.setEnabled(True)
        self.training_status.setText("Training in progress...")
        self.status_label.setText("🚀 Training model...")
        self.training_log.clear()
        self.training_log.append("Training started...\n")
    
    @Slot(int, str)
    def _on_training_progress(self, percent, message):
        """Handle training progress updates"""
        self.training_progress.setValue(percent)
        self.training_status.setText(message)
        self.training_log.append(f"{message}")
    
    @Slot(object)
    def _on_training_complete(self, metrics):
        """Handle training completion"""
        self.train_btn.setEnabled(True)
        self.stop_train_btn.setEnabled(False)
        self.training_status.setText("✅ Training complete!")
        self.status_label.setText("✅ Training complete!")
        
        # Show final metrics
        final_metrics = metrics[-1]
        summary = (
            f"\n✅ Training Complete!\n"
            f"Epochs: {final_metrics.epoch}\n"
            f"Final train loss: {final_metrics.train_loss:.4f}\n"
            f"Final val loss: {final_metrics.val_loss:.4f}\n"
        )
        self.training_log.append(summary)
        
        QMessageBox.information(self, "Success", "Training complete!")
    
    @Slot(str)
    def _on_training_error(self, error_msg):
        """Handle training error"""
        self.train_btn.setEnabled(True)
        self.stop_train_btn.setEnabled(False)
        self.training_status.setText("❌ Training failed")
        self.status_label.setText("❌ Training failed")
        self.training_log.append(f"\n❌ Error: {error_msg}")
        
        QMessageBox.critical(self, "Training Error", error_msg)
    
    @Slot()
    def _stop_training(self):
        """Stop training"""
        if self.trainer:
            self.trainer.stop_training()
        self.training_status.setText("Stopping training...")
    
    @Slot()
    def _validate_model(self):
        """Validate trained model"""
        if not self.trainer or not self.current_dataset:
            QMessageBox.warning(self, "Error", "No trained model to validate.")
            return
        
        self.status_label.setText("Validating model...")
        
        try:
            metrics = self.validator.validate_model(
                self.trainer,
                self.current_dataset.X_test,
                self.current_dataset.y_test
            )
            
            results_text = (
                f"📊 Validation Results\n\n"
                f"Mean Absolute Error: {metrics.mae:.4f}\n"
                f"Mean Squared Error: {metrics.mse:.4f}\n"
                f"R² Score: {metrics.r2_score:.3f}\n"
                f"Humanization Score: {metrics.humanization_score:.1f}/100\n\n"
                f"Per-Parameter MAE:\n"
            )
            
            for param, mae in metrics.per_param_mae.items():
                results_text += f"  {param}: {mae:.4f}\n"
            
            self.validation_results.setPlainText(results_text)
            self.status_label.setText("✅ Validation complete")
            
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            QMessageBox.warning(self, "Error", f"Validation failed: {e}")
    
    @Slot()
    def _deploy_model(self):
        """Deploy model to production"""
        if not self.trainer:
            QMessageBox.warning(self, "Error", "No trained model to deploy.")
            return
        
        # Get model name and version
        from PySide6.QtWidgets import QInputDialog
        model_name, ok1 = QInputDialog.getText(self, "Deploy Model", "Model Name:", text="drum_humanizer")
        if not ok1:
            return
        
        version, ok2 = QInputDialog.getText(self, "Deploy Model", "Version:", text="1.0.0")
        if not ok2:
            return
        
        try:
            # Export model
            model_path = self.trainer.config.checkpoint_dir / "best_model.pth"
            
            # Deploy
            success = self.deployer.deploy_model(
                model_path,
                model_name,
                version,
                metadata={'note': 'Deployed from admin app'}
            )
            
            if success:
                self.status_label.setText(f"✅ Model deployed: {model_name} v{version}")
                QMessageBox.information(self, "Success", f"Model deployed successfully!")
                self._refresh_models_table()
            else:
                QMessageBox.warning(self, "Error", "Deployment failed")
                
        except Exception as e:
            logger.error(f"Deployment failed: {e}")
            QMessageBox.warning(self, "Error", f"Deployment failed: {e}")
    
    def _refresh_models_table(self):
        """Refresh deployed models table"""
        models = self.deployer.list_models()
        
        self.models_table.setRowCount(len(models))
        
        for i, model in enumerate(models):
            self.models_table.setItem(i, 0, QTableWidgetItem(model['name']))
            self.models_table.setItem(i, 1, QTableWidgetItem(model['version']))
            active_text = "✅" if model.get('active') else "  "
            self.models_table.setItem(i, 2, QTableWidgetItem(active_text))
            self.models_table.setItem(i, 3, QTableWidgetItem(model.get('deployed_at', 'N/A')))
