import base64
import librosa
import librosa.display
import matplotlib
import matplotlib.pyplot as plt
import scipy
import scipy.signal
import scipy.signal.windows
import json
import logging
import numpy as np
import os
import struct
import sys
import traceback

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
except ImportError:
    try:
        # Try PySide6 compatible backend
        import matplotlib
        matplotlib.use('Qt5Agg')  # Set backend before importing
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
    except ImportError:
        # Fallback: create dummy classes to prevent import errors
        class FigureCanvas:
            def __init__(self, *args, **kwargs):
                pass
        class NavigationToolbar2QT:
            def __init__(self, *args, **kwargs):
                pass
from matplotlib.figure import Figure
from scipy.signal import savgol_filter, hilbert
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QSize, QUrl, QRect, QPoint
from PySide6.QtGui import (
    QPixmap, QIcon, QPainter, QColor, QBrush, QPen, QFont,
    QPalette, QLinearGradient, QRadialGradient, QPolygon, QImage,
    QTransform, QConicalGradient, QPaintDevice, QPainterPath
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QRadioButton,
    QSpinBox, QDoubleSpinBox, QTabWidget, QGroupBox, QLineEdit,
    QFileDialog, QListWidget, QProgressBar, QSlider, QScrollArea,
    QSplitter, QGraphicsView, QGraphicsScene, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QTextEdit,
    QListWidgetItem, QTreeWidget, QTreeWidgetItem, QDialog,
    QDialogButtonBox, QMessageBox, QColorDialog, QFrame,
    QSizePolicy, QApplication
)
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Union
from admin.ui.base_widget import BaseWidget

# audio_visualization_widget.py
# Properly structured audio visualization widget

# Configure logging
logger = logging.getLogger(__name__)

# Import visualization libraries (with fallbacks)
try:
    LIBROSA_AVAILABLE = True
except ImportError:
    logger.warning("librosa not available - some features will be disabled")
    LIBROSA_AVAILABLE = False

try:
    SCIPY_AVAILABLE = True
except ImportError:
    logger.warning("scipy not available - some features will be disabled")
    SCIPY_AVAILABLE = False

try:
    matplotlib.use('Qt5Agg')
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    logger.warning("matplotlib not available - visualization will be limited")
    MATPLOTLIB_AVAILABLE = False


class AudioVisualizationWidget(BaseWidget):
    """Audio visualization widget with waveforms, spectrograms, and real-time analysis"""

    def __init__(self, parent=None):
        # Initialize the _initialization_complete flag to False
        self._initialization_complete = False
        
        # Services will be injected by ServiceContainer
        self.audio_service = None
        self.visualization_service = None
        self.container = None  # Add container attribute for service injection

        # Audio data
        self.current_audio_file = None
        self.audio_data = None
        self.sample_rate = None
        self.visualization_timer = QTimer()

        super().__init__(parent)
        
        # Initialize the UI
        self._setup_ui()
        self._connect_events()
        self._load_initial_data()
        
        # Mark initialization as complete
        self._initialization_complete = True
        self.logger.info("AudioVisualizationWidget initialization complete")

    def _setup_ui(self):
        """Setup audio visualization UI"""
        # BaseWidget doesn't have _setup_ui method, so we skip the super() call

        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # File selection area
        file_layout = QHBoxLayout()
        self.audio_file_edit = QLineEdit()
        self.audio_file_edit.setPlaceholderText("Select audio file for visualization...")
        self.audio_file_edit.setReadOnly(True)

        self.browse_btn = QPushButton("Browse")
        self.browse_btn.clicked.connect(self._load_audio_file)

        file_layout.addWidget(self.audio_file_edit)
        file_layout.addWidget(self.browse_btn)

        self.main_layout.addLayout(file_layout)

        # Create visualization tabs
        self.viz_tabs = QTabWidget()

        # Create individual visualization tabs
        self._create_waveform_tab()
        self._create_spectrogram_tab()
        self._create_realtime_tab()
        self._create_3d_tab()

        self.main_layout.addWidget(self.viz_tabs)

        # Setup visualization controls
        self._setup_visualization_controls()

        # Set busy indicator
        self.busy_indicator = QProgressBar()
        self.busy_indicator.setRange(0, 0)  # Indeterminate
        self.busy_indicator.setVisible(False)
        self.main_layout.addWidget(self.busy_indicator)

    def _setup_visualization_controls(self):
        """Setup visualization control panel with time range, frequency range and colormap selection"""
        control_panel = QGroupBox("Visualization Controls")
        control_panel.setStyleSheet("""
            QGroupBox { 
                background-color: #2D2D2D; 
                color: #E0E0E0; 
                border: 1px solid #8A2BE2; 
            }
            QLabel { 
                color: #E0E0E0; 
            }
            QSpinBox, QDoubleSpinBox, QComboBox { 
                background-color: #3D3D3D; 
                color: #E0E0E0; 
                border: 1px solid #8A2BE2; 
            }
            QPushButton { 
                background-color: #8A2BE2; 
                color: #FFD700; 
                font-weight: bold; 
            }
            QPushButton:hover { 
                background-color: #9A3BFF; 
            }
            QPushButton:pressed { 
                background-color: #7A1BD2; 
            }
        """)
        control_layout = QFormLayout(control_panel)

        # Time range controls
        time_range_layout = QHBoxLayout()
        self.time_start_spinner = QDoubleSpinBox()
        self.time_start_spinner.setRange(0, 3600)
        self.time_start_spinner.setValue(0)
        self.time_start_spinner.setSuffix(" sec")
        self.time_end_spinner = QDoubleSpinBox()
        self.time_end_spinner.setRange(0, 3600)
        self.time_end_spinner.setValue(60)
        self.time_end_spinner.setSuffix(" sec")
        time_range_layout.addWidget(QLabel("From:"))
        time_range_layout.addWidget(self.time_start_spinner)
        time_range_layout.addWidget(QLabel("To:"))
        time_range_layout.addWidget(self.time_end_spinner)

        control_layout.addRow("Time Range:", time_range_layout)

        # Frequency range controls
        freq_range_layout = QHBoxLayout()
        self.freq_min_spinner = QSpinBox()
        self.freq_min_spinner.setRange(0, 20000)
        self.freq_min_spinner.setValue(20)
        self.freq_min_spinner.setSuffix(" Hz")
        self.freq_max_spinner = QSpinBox()
        self.freq_max_spinner.setRange(0, 20000)
        self.freq_max_spinner.setValue(20000)
        self.freq_max_spinner.setSuffix(" Hz")
        freq_range_layout.addWidget(QLabel("Min:"))
        freq_range_layout.addWidget(self.freq_min_spinner)
        freq_range_layout.addWidget(QLabel("Max:"))
        freq_range_layout.addWidget(self.freq_max_spinner)

        control_layout.addRow("Frequency Range:", freq_range_layout)

        # Colormap controls
        colormap_layout = QHBoxLayout()
        self.colormap_combo = QComboBox()
        self.colormap_combo.addItems([
            "viridis", "plasma", "inferno", "magma", "cividis",
            "twilight", "coolwarm", "rainbow", "jet", "turbo"
        ])
        self.colormap_combo.setCurrentText("viridis")
        colormap_layout.addWidget(self.colormap_combo)

        # Colormap inversion checkbox
        self.invert_colormap_check = QCheckBox("Invert")
        self.invert_colormap_check.setStyleSheet("color: #E0E0E0;")
        colormap_layout.addWidget(self.invert_colormap_check)

        control_layout.addRow("Colormap:", colormap_layout)

        # Resolution controls
        resolution_layout = QHBoxLayout()
        self.fft_size_combo = QComboBox()
        self.fft_size_combo.addItems(["512", "1024", "2048", "4096", "8192"])
        self.fft_size_combo.setCurrentText("2048")
        resolution_layout.addWidget(QLabel("FFT Size:"))
        resolution_layout.addWidget(self.fft_size_combo)

        self.hop_length_combo = QComboBox()
        self.hop_length_combo.addItems(["256", "512", "1024", "2048"])
        self.hop_length_combo.setCurrentText("512")
        resolution_layout.addWidget(QLabel("Hop Length:"))
        resolution_layout.addWidget(self.hop_length_combo)

        control_layout.addRow("Resolution:", resolution_layout)

        # Update button
        self.update_viz_button = QPushButton("Update Visualization")
        self.update_viz_button.clicked.connect(self._update_visualization)
        control_layout.addRow("", self.update_viz_button)

        # Add to main layout
        self.main_layout.addWidget(control_panel)

        # Connect spinners and controls to update events
        self.time_start_spinner.valueChanged.connect(self._update_visualization)
        self.time_end_spinner.valueChanged.connect(self._update_visualization)
        self.freq_min_spinner.valueChanged.connect(self._update_visualization)
        self.freq_max_spinner.valueChanged.connect(self._update_visualization)
        self.colormap_combo.currentTextChanged.connect(self._update_visualization)
        self.invert_colormap_check.stateChanged.connect(self._update_visualization)
        self.fft_size_combo.currentTextChanged.connect(self._update_visualization)
        self.hop_length_combo.currentTextChanged.connect(self._update_visualization)

    def _create_waveform_tab(self):
        """Create waveform visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Waveform display
        self.waveform_view = QGraphicsView()
        self.waveform_scene = QGraphicsScene()
        self.waveform_view.setScene(self.waveform_scene)
        if MATPLOTLIB_AVAILABLE:
            self.waveform_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout.addWidget(self.waveform_view)

        # Controls
        controls_layout = QHBoxLayout()

        # Envelope checkbox
        self.show_envelope_check = QCheckBox("Show Envelope")
        self.show_envelope_check.toggled.connect(self._update_waveform)
        controls_layout.addWidget(self.show_envelope_check)

        # Normalize checkbox
        self.normalize_check = QCheckBox("Normalize")
        self.normalize_check.setChecked(True)
        self.normalize_check.toggled.connect(self._update_waveform)
        controls_layout.addWidget(self.normalize_check)

        # Onsets checkbox
        self.show_onsets_check = QCheckBox("Show Onsets")
        self.show_onsets_check.toggled.connect(self._update_waveform)
        controls_layout.addWidget(self.show_onsets_check)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Add tab to widget
        self.viz_tabs.addTab(tab, "Waveform")

    def _create_spectrogram_tab(self):
        """Create spectrogram visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Spectrogram display
        self.spectrogram_view = QGraphicsView()
        self.spectrogram_scene = QGraphicsScene()
        self.spectrogram_view.setScene(self.spectrogram_scene)
        layout.addWidget(self.spectrogram_view)

        # Controls
        controls_layout = QHBoxLayout()

        # Window type
        controls_layout.addWidget(QLabel("Window:"))
        self.window_combo = QComboBox()
        self.window_combo.addItems(["Hann", "Hamming", "Blackman", "Rectangular"])
        self.window_combo.currentIndexChanged.connect(self._update_spectrogram)
        controls_layout.addWidget(self.window_combo)

        # FFT size
        controls_layout.addWidget(QLabel("FFT Size:"))
        self.spec_fft_size_combo = QComboBox()
        self.spec_fft_size_combo.addItems(["256", "512", "1024", "2048", "4096"])
        self.spec_fft_size_combo.setCurrentIndex(2)
        self.spec_fft_size_combo.currentIndexChanged.connect(self._update_spectrogram)
        controls_layout.addWidget(self.spec_fft_size_combo)

        # Log scale checkbox
        self.log_scale_check = QCheckBox("Log Scale")
        self.log_scale_check.setChecked(True)
        self.log_scale_check.toggled.connect(self._update_spectrogram)
        controls_layout.addWidget(self.log_scale_check)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Add tab to widget
        self.viz_tabs.addTab(tab, "Spectrogram")

    def _create_realtime_tab(self):
        """Create real-time analysis visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Create splitter for multiple visualizations
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Onset strength view
        onset_group = QGroupBox("Onset Strength")
        onset_layout = QVBoxLayout(onset_group)
        self.onset_view = QGraphicsView()
        self.onset_scene = QGraphicsScene()
        self.onset_view.setScene(self.onset_scene)
        onset_layout.addWidget(self.onset_view)
        splitter.addWidget(onset_group)

        # Tempo tracking view
        tempo_group = QGroupBox("Tempo Tracking")
        tempo_layout = QVBoxLayout(tempo_group)
        self.tempo_view = QGraphicsView()
        self.tempo_scene = QGraphicsScene()
        self.tempo_view.setScene(self.tempo_scene)
        tempo_layout.addWidget(self.tempo_view)
        splitter.addWidget(tempo_group)

        # Spectral features view
        spectral_group = QGroupBox("Spectral Features")
        spectral_layout = QVBoxLayout(spectral_group)
        self.spectral_view = QGraphicsView()
        self.spectral_scene = QGraphicsScene()
        self.spectral_view.setScene(self.spectral_scene)
        spectral_layout.addWidget(self.spectral_view)
        splitter.addWidget(spectral_group)

        layout.addWidget(splitter, 3)

        # Controls
        controls_group = QGroupBox("Real-time Analysis Controls")
        controls_layout = QHBoxLayout(controls_group)

        # Feature selection
        controls_layout.addWidget(QLabel("Feature:"))
        self.feature_combo = QComboBox()
        self.feature_combo.addItems(["Spectral Centroid", "Spectral Rolloff", "Zero Crossing Rate", "Spectral Contrast"])
        self.feature_combo.currentIndexChanged.connect(self._update_realtime_analysis)
        controls_layout.addWidget(self.feature_combo)

        # Buffer size
        controls_layout.addWidget(QLabel("Buffer:"))
        self.buffer_spin = QSpinBox()
        self.buffer_spin.setRange(1024, 16384)
        self.buffer_spin.setSingleStep(1024)
        self.buffer_spin.setValue(4096)
        self.buffer_spin.valueChanged.connect(self._update_realtime_analysis)
        controls_layout.addWidget(self.buffer_spin)

        # Activate checkbox
        self.realtime_active_check = QCheckBox("Activate")
        self.realtime_active_check.toggled.connect(self._toggle_realtime_analysis)
        controls_layout.addWidget(self.realtime_active_check)

        controls_layout.addStretch()
        layout.addWidget(controls_group, 1)

        # Add tab to widget
        self.viz_tabs.addTab(tab, "Real-time Analysis")

    def _create_3d_tab(self):
        """Create 3D visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 3D view container
        self.view_3d = QWidget()
        self.view_3d.setMinimumHeight(400)
        self.view_3d.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #444; border-radius: 4px;"
        )

        # Create layout for 3D visualization
        self.visualization_3d_layout = QVBoxLayout(self.view_3d)

        layout.addWidget(self.view_3d)

        # Controls
        controls_layout = QHBoxLayout()

        # Render button
        self.render_3d_button = QPushButton("Render 3D Spectrogram")
        self.render_3d_button.clicked.connect(self._render_3d_visualization)
        controls_layout.addWidget(self.render_3d_button)

        # Export button
        self.export_3d_button = QPushButton("Export 3D Model")
        self.export_3d_button.clicked.connect(self._export_3d_model)
        controls_layout.addWidget(self.export_3d_button)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # Add tab to widget
        self.viz_tabs.addTab(tab, "3D View")

    def _connect_events(self):
        """Connect event handlers"""
        self.visualization_timer.timeout.connect(self._update_visualizations)

    def _load_initial_data(self):
        """Load initial data"""
        try:
            if self.container:
                self.audio_service = self.container.get("audio_service")
                self.visualization_service = self.container.get("visualization_service")

            self.emit_status("Audio visualization initialized")
        except Exception as e:
            self.emit_error(f"Failed to initialize visualization: {e}")

    def _load_audio_file(self):
        """Load audio file for visualization"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*.*)"
        )

        if file_path:
            try:
                self.current_audio_file = file_path
                self.audio_file_edit.setText(os.path.basename(file_path))

                # Load audio data using service or librosa
                if self.audio_service:
                    self.audio_data, self.sample_rate = self.audio_service.load_audio(file_path)
                elif LIBROSA_AVAILABLE:
                    self.audio_data, self.sample_rate = librosa.load(file_path, sr=None)
                else:
                    self.emit_error("No audio loading capability available")
                    return

                # Update time range
                if self.audio_data is not None:
                    duration = len(self.audio_data) / self.sample_rate
                    self.time_end_spinner.setMaximum(duration)
                    self.time_end_spinner.setValue(min(30, duration))

                    self._update_visualizations()

                    self.emit_status(f"Loaded audio file: {os.path.basename(file_path)}")
                else:
                    self.emit_error("Failed to load audio data")

            except Exception as e:
                logger.error(f"Error loading audio file: {e}")
                self.emit_error(f"Error loading audio file: {str(e)}")

    def _update_visualization(self):
        """Update visualization based on current settings"""
        # If no audio data is loaded, don't do anything
        if self.audio_data is None or self.sample_rate is None:
            logger.warning("Cannot update visualization: No audio data loaded")
            return

        try:
            # Get current settings from controls
            time_start = self.time_start_spinner.value()
            time_end = self.time_end_spinner.value()
            freq_min = self.freq_min_spinner.value()
            freq_max = self.freq_max_spinner.value()
            colormap = self.colormap_combo.currentText()
            invert_colormap = self.invert_colormap_check.isChecked()
            fft_size = int(self.fft_size_combo.currentText())
            hop_length = int(self.hop_length_combo.currentText())

            # Validate settings
            if time_end <= time_start:
                logger.warning("Invalid time range: end time must be greater than start time")
                return

            if freq_max <= freq_min:
                logger.warning("Invalid frequency range: max frequency must be greater than min frequency")
                return

            # Update busy indicator
            self.busy_indicator.setRange(0, 0)  # Set to indeterminate mode
            self.busy_indicator.show()
            QApplication.processEvents()  # Process UI events to show busy indicator

            # Update all visualizations with new settings
            self._update_visualizations()

            # Reset busy indicator
            self.busy_indicator.setRange(0, 100)
            self.busy_indicator.setValue(100)
            self.busy_indicator.hide()

            logger.debug(f"Visualization updated with: time={time_start}-{time_end}s, freq={freq_min}-{freq_max}Hz, "
                        f"colormap={colormap}, fft_size={fft_size}, hop_length={hop_length}")

        except Exception as e:
            logger.error(f"Error updating visualization: {e}")
            traceback.print_exc()
            self.busy_indicator.setRange(0, 100)
            self.busy_indicator.setValue(0)
            self.busy_indicator.hide()

    def _update_visualizations(self):
        """Update all visualizations with current audio data"""
        if self.audio_data is not None and self.sample_rate is not None:
            # Update waveform
            self._update_waveform()

            # Update spectrogram
            self._update_spectrogram()

            # Update real-time analysis if active
            current_tab = self.viz_tabs.tabText(self.viz_tabs.currentIndex())
            if current_tab == "Real-time Analysis" and hasattr(self, "realtime_active_check") and self.realtime_active_check.isChecked():
                self._update_realtime_analysis()

    def _update_waveform(self):
        """Update waveform visualization"""
        if not MATPLOTLIB_AVAILABLE or self.audio_data is None:
            return

        try:
            # Show busy indicator during processing
            self.busy_indicator.setVisible(True)

            # Get time range
            time_start = self.time_start_spinner.value()
            time_end = self.time_end_spinner.value()

            # Convert to samples
            start_sample = int(time_start * self.sample_rate)
            end_sample = int(time_end * self.sample_rate)

            # Ensure valid sample range
            if start_sample >= len(self.audio_data) or end_sample > len(self.audio_data):
                logger.warning(f"Invalid sample range: {start_sample}-{end_sample} for data length {len(self.audio_data)}")
                self.busy_indicator.setVisible(False)
                return

            # Extract segment
            audio_segment = self.audio_data[start_sample:end_sample]

            if len(audio_segment) == 0:
                logger.warning("Empty audio segment for visualization")
                self.busy_indicator.setVisible(False)
                return

            # Create figure
            width = max(self.waveform_view.width() - 20, 400) / 100
            height = max(self.waveform_view.height() - 20, 300) / 100
            fig = Figure(figsize=(width, height), dpi=100)
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            # Normalize audio if checkbox is checked
            if self.normalize_check.isChecked():
                max_val = np.max(np.abs(audio_segment))
                if max_val > 0:
                    audio_segment = audio_segment / max_val

            # Time array for plotting
            time_array = np.linspace(time_start, time_end, len(audio_segment))

            # Plot the waveform
            ax.plot(time_array, audio_segment, linewidth=0.8, color='#3498db')

            # Show envelope if checkbox is checked
            if SCIPY_AVAILABLE and self.show_envelope_check.isChecked():
                try:
                    analytic_signal = hilbert(audio_segment)
                    envelope = np.abs(analytic_signal)
                    # Smooth the envelope
                    window_len = min(int(self.sample_rate * 0.01), len(envelope)//10)
                    if window_len > 1 and window_len % 2 == 0:
                        window_len += 1
                    if window_len > 3:
                        envelope = savgol_filter(envelope, window_len, 2)
                    ax.plot(time_array, envelope, linewidth=1.0, color='#e74c3c', alpha=0.7)
                except Exception as e:
                    logger.debug(f"Failed to compute envelope: {e}")

            # Show onsets if checkbox is checked
            if LIBROSA_AVAILABLE and self.show_onsets_check.isChecked():
                try:
                    onset_env = librosa.onset.onset_strength(y=audio_segment, sr=self.sample_rate)
                    onsets_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=self.sample_rate)
                    onset_times = librosa.frames_to_time(onsets_frames, sr=self.sample_rate) + time_start

                    for onset_time in onset_times:
                        if onset_time >= time_start and onset_time <= time_end:
                            ax.axvline(onset_time, color='#2ecc71', linewidth=1.0, alpha=0.7)
                except Exception as e:
                    logger.debug(f"Failed to compute onsets: {e}")

            # Format the plot
            ax.set_xlim([time_start, time_end])
            ax.set_ylim([-1.1, 1.1])
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Amplitude')
            ax.grid(True, alpha=0.3)
            fig.tight_layout()

            # Render to QPixmap
            canvas.draw()
            width, height = canvas.get_width_height()
            image = QImage(canvas.buffer_rgba(), width, height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(image)

            # Clear and update scene
            self.waveform_scene.clear()
            self.waveform_scene.addPixmap(pixmap)
            self.waveform_view.fitInView(
                self.waveform_scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )

            # Hide busy indicator
            self.busy_indicator.setVisible(False)

        except Exception as e:
            logger.error(f"Failed to update waveform: {str(e)}")
            self.busy_indicator.setVisible(False)
            self.emit_error(f"Waveform visualization error: {str(e)}")

    def _update_spectrogram(self):
        """Update spectrogram visualization"""
        if not MATPLOTLIB_AVAILABLE or not LIBROSA_AVAILABLE or self.audio_data is None:
            return

        try:
            # Show busy indicator during processing
            self.busy_indicator.setVisible(True)

            # Get time range
            time_start = self.time_start_spinner.value()
            time_end = self.time_end_spinner.value()

            # Get frequency range
            freq_min = self.freq_min_spinner.value()
            freq_max = self.freq_max_spinner.value()

            # Convert to samples
            start_sample = int(time_start * self.sample_rate)
            end_sample = int(time_end * self.sample_rate)

            # Ensure valid sample range
            if start_sample >= len(self.audio_data) or end_sample > len(self.audio_data):
                logger.warning(f"Invalid sample range: {start_sample}-{end_sample} for data length {len(self.audio_data)}")
                self.busy_indicator.setVisible(False)
                return

            # Extract segment
            audio_segment = self.audio_data[start_sample:end_sample]

            if len(audio_segment) == 0:
                logger.warning("Empty audio segment for visualization")
                self.busy_indicator.setVisible(False)
                return

            # Get parameters from UI
            window_type = self.window_combo.currentText().lower()
            fft_size = int(self.spec_fft_size_combo.currentText())
            use_log_scale = self.log_scale_check.isChecked()

            # Create figure
            width = max(self.spectrogram_view.width() - 20, 400) / 100
            height = max(self.spectrogram_view.height() - 20, 300) / 100
            fig = Figure(figsize=(width, height), dpi=100)
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            # Compute STFT
            hop_length = fft_size // 4

            # Compute spectrogram using librosa
            stft = librosa.stft(
                audio_segment,
                n_fft=fft_size,
                hop_length=hop_length,
                window=window_type
            )

            magnitude = np.abs(stft)

            # Convert to dB scale if log scale is checked
            if use_log_scale:
                spectrogram = librosa.amplitude_to_db(magnitude, ref=np.max)
            else:
                spectrogram = magnitude

            # Get colormap
            colormap = self.colormap_combo.currentText()

            # Plot spectrogram
            img = librosa.display.specshow(
                spectrogram,
                y_axis='log' if use_log_scale else 'linear',
                x_axis='time',
                sr=self.sample_rate,
                hop_length=hop_length,
                ax=ax,
                cmap=colormap
            )

            # Set frequency limits if specified
            if freq_min > 0 and freq_max > freq_min:
                ax.set_ylim(freq_min, min(freq_max, self.sample_rate / 2))

            # Add colorbar
            fig.colorbar(img, ax=ax, format='%+2.0f dB' if use_log_scale else '%+2.0f')

            # Set labels
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Frequency (Hz)')
            ax.set_title(f"Spectrogram ({window_type}, {fft_size} FFT size)")

            fig.tight_layout()

            # Render to QPixmap
            canvas.draw()
            width, height = canvas.get_width_height()
            image = QImage(canvas.buffer_rgba(), width, height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(image)

            # Clear and update scene
            self.spectrogram_scene.clear()
            self.spectrogram_scene.addPixmap(pixmap)
            self.spectrogram_view.fitInView(
                self.spectrogram_scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )

            # Hide busy indicator
            self.busy_indicator.setVisible(False)

        except Exception as e:
            logger.error(f"Failed to update spectrogram: {str(e)}")
            self.busy_indicator.setVisible(False)
            self.emit_error(f"Spectrogram visualization error: {str(e)}")

    def _update_realtime_analysis(self):
        """Update real-time analysis visualization"""
        if not MATPLOTLIB_AVAILABLE or not LIBROSA_AVAILABLE or self.audio_data is None:
            return

        try:
            # Show busy indicator during processing
            self.busy_indicator.setVisible(True)

            # Get time range
            time_start = self.time_start_spinner.value()
            time_end = self.time_end_spinner.value()

            # Convert to samples
            start_sample = int(time_start * self.sample_rate)
            end_sample = int(time_end * self.sample_rate)

            # Ensure valid sample range
            if start_sample >= len(self.audio_data) or end_sample > len(self.audio_data):
                logger.warning(f"Invalid sample range: {start_sample}-{end_sample} for data length {len(self.audio_data)}")
                self.busy_indicator.setVisible(False)
                return

            # Extract segment
            audio_segment = self.audio_data[start_sample:end_sample]

            if len(audio_segment) == 0:
                logger.warning("Empty audio segment for visualization")
                self.busy_indicator.setVisible(False)
                return

            # Update onset strength visualization
            self._update_onset_visualization(audio_segment)

            # Update tempo tracking visualization
            self._update_tempo_visualization(audio_segment)

            # Update spectral features visualization
            self._update_spectral_features_visualization(audio_segment)

            # Hide busy indicator when done
            self.busy_indicator.setVisible(False)

        except Exception as e:
            logger.error(f"Failed to update real-time analysis: {str(e)}")
            self.busy_indicator.setVisible(False)
            self.emit_error(f"Real-time analysis error: {str(e)}")

    def _update_onset_visualization(self, audio_segment):
        """Update onset strength visualization"""
        if not hasattr(self, "onset_scene") or not hasattr(self, "onset_view"):
            return

        try:
            # Create figure
            width = max(self.onset_view.width() - 20, 400) / 100
            height = max(self.onset_view.height() - 20, 200) / 100
            fig = Figure(figsize=(width, height), dpi=100)
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            # Calculate onset envelope
            hop_length = 512
            onset_envelope = librosa.onset.onset_strength(
                audio_segment,
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Generate onset frames
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_envelope,
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Generate time values
            times = librosa.frames_to_time(
                np.arange(len(onset_envelope)),
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Generate onset times
            onset_times = librosa.frames_to_time(onset_frames, sr=self.sample_rate, hop_length=hop_length)

            # Plot onset envelope
            ax.plot(times, onset_envelope, alpha=0.8, label='Onset strength')

            # Plot detected onsets
            ax.vlines(onset_times, 0, onset_envelope.max(), color='r', alpha=0.7,
                     linestyle='--', label='Detected onsets')

            # Apply smoothing if we have enough data points
            if SCIPY_AVAILABLE and len(onset_envelope) > 5:
                window_length = min(15, len(onset_envelope) - 3)
                if window_length % 2 == 0:
                    window_length -= 1

                if window_length >= 5:
                    try:
                        smoothed = savgol_filter(onset_envelope, window_length=window_length, polyorder=2)
                        ax.plot(times, smoothed, color='g', linewidth=2, alpha=0.8, label='Smoothed envelope')
                    except Exception as e:
                        logger.debug(f"Skipping smoothing filter: {e}")

            # Add legend and labels
            ax.legend(loc='upper right')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Onset Strength')
            ax.set_title(f'Onset Detection: {len(onset_frames)} onsets')
            fig.tight_layout()

            # Convert to QImage and display
            canvas.draw()
            width, height = canvas.get_width_height()
            image = QImage(canvas.buffer_rgba(), width, height, QImage.Format.Format_RGBA8888)

            # Update scene
            self.onset_scene.clear()
            pixmap = QPixmap.fromImage(image)
            self.onset_scene.addPixmap(pixmap)
            self.onset_view.fitInView(
                self.onset_scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )

        except Exception as e:
            logger.error(f"Failed to update onset visualization: {e}")

    def _update_tempo_visualization(self, audio_segment):
        """Update tempo tracking visualization"""
        if not hasattr(self, "tempo_scene") or not hasattr(self, "tempo_view"):
            return

        try:
            # Create figure
            width = max(self.tempo_view.width() - 20, 400) / 100
            height = max(self.tempo_view.height() - 20, 200) / 100
            fig = Figure(figsize=(width, height), dpi=100)
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111)

            # Calculate onset envelope
            hop_length = 512
            onset_envelope = librosa.onset.onset_strength(
                audio_segment,
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Calculate tempo and beats
            tempo, beats = librosa.beat.beat_track(
                onset_envelope=onset_envelope,
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Generate time axis for onset envelope
            times = librosa.frames_to_time(
                np.arange(len(onset_envelope)),
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Generate beat times
            beat_times = librosa.frames_to_time(beats, sr=self.sample_rate, hop_length=hop_length)

            # Compute tempogram
            tempogram = librosa.feature.tempogram(
                onset_envelope=onset_envelope,
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Plot tempogram
            ax.imshow(
                tempogram,
                aspect='auto',
                origin='lower',
                cmap='hot',
                extent=[0, times[-1], 0, tempogram.shape[0]]
            )

            # Plot estimated tempo line
            ax.axhline(y=tempo, color='w', linestyle='--', alpha=0.8,
                      label=f'Estimated tempo: {tempo:.1f} BPM')

            # Plot beat markers
            ax.vlines(beat_times, 0, tempogram.shape[0], color='w', alpha=0.5)

            # Add legend and labels
            ax.legend(loc='upper right')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Tempo (BPM)')
            ax.set_title(f'Tempo Estimation: {tempo:.1f} BPM, {len(beats)} beats')
            fig.tight_layout()

            # Convert to QImage and display
            canvas.draw()
            width, height = canvas.get_width_height()
            image = QImage(canvas.buffer_rgba(), width, height, QImage.Format.Format_RGBA8888)

            # Update scene
            self.tempo_scene.clear()
            pixmap = QPixmap.fromImage(image)
            self.tempo_scene.addPixmap(pixmap)
            self.tempo_view.fitInView(
                self.tempo_scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )

        except Exception as e:
            logger.error(f"Failed to update tempo visualization: {e}")

    def _update_spectral_features_visualization(self, audio_segment):
        """Update spectral features visualization"""
        if not hasattr(self, "spectral_scene") or not hasattr(self, "spectral_view"):
            return

        try:
            # Create figure
            width = max(self.spectral_view.width() - 20, 400) / 100
            height = max(self.spectral_view.height() - 20, 200) / 100
            fig = Figure(figsize=(width, height), dpi=100)
            canvas = FigureCanvas(fig)

            # Get feature type
            feature_type = 'spectral_centroid'  # default
            if hasattr(self, 'feature_combo'):
                feature_type = self.feature_combo.currentText().lower().replace(' ', '_')

            # Compute hop length
            hop_length = 512

            # Compute frame times
            frames = range(0, len(audio_segment) - hop_length, hop_length)
            times = librosa.frames_to_time(frames, sr=self.sample_rate, hop_length=hop_length)

            ax = fig.add_subplot(111)

            # Create different spectral features based on selection
            if feature_type == 'spectral_centroid':
                feature_data = librosa.feature.spectral_centroid(
                    y=audio_segment,
                    sr=self.sample_rate,
                    hop_length=hop_length
                )[0]

                # Apply smoothing
                if SCIPY_AVAILABLE and len(feature_data) > 7:
                    window_length = min(7, len(feature_data)-3)
                    if window_length % 2 == 0:
                        window_length -= 1

                    if window_length >= 5:
                        try:
                            smoothed_feature = savgol_filter(feature_data, window_length=window_length, polyorder=2)
                        except Exception:
                            smoothed_feature = feature_data
                else:
                    smoothed_feature = feature_data

                # Plot
                ax.semilogy(times, feature_data, label='Spectral Centroid',
                           color='#3498db', alpha=0.6)
                ax.semilogy(times, smoothed_feature, label='Smoothed',
                           color='#3498db', linewidth=2.5)
                ax.set_ylabel('Hz')
                ax.set_title('Spectral Centroid (Brightness)')

            elif feature_type == 'spectral_rolloff':
                feature_data = librosa.feature.spectral_rolloff(
                    y=audio_segment,
                    sr=self.sample_rate,
                    hop_length=hop_length
                )[0]

                # Apply smoothing
                if SCIPY_AVAILABLE and len(feature_data) > 7:
                    window_length = min(7, len(feature_data)-3)
                    if window_length % 2 == 0:
                        window_length -= 1

                    if window_length >= 5:
                        try:
                            smoothed_feature = savgol_filter(feature_data, window_length=window_length, polyorder=2)
                        except Exception:
                            smoothed_feature = feature_data
                else:
                    smoothed_feature = feature_data

                # Plot
                ax.semilogy(times, feature_data, label='Spectral Rolloff',
                           color='#e67e22', alpha=0.6)
                ax.semilogy(times, smoothed_feature, label='Smoothed',
                           color='#e67e22', linewidth=2.5)
                ax.set_ylabel('Hz')
                ax.set_title('Spectral Rolloff (85%)')

            elif feature_type == 'zero_crossing_rate':
                feature_data = librosa.feature.zero_crossing_rate(
                    y=audio_segment,
                    hop_length=hop_length
                )[0]

                # Apply smoothing
                if SCIPY_AVAILABLE and len(feature_data) > 7:
                    window_length = min(7, len(feature_data)-3)
                    if window_length % 2 == 0:
                        window_length -= 1

                    if window_length >= 5:
                        try:
                            smoothed_feature = savgol_filter(feature_data, window_length=window_length, polyorder=2)
                        except Exception:
                            smoothed_feature = feature_data
                else:
                    smoothed_feature = feature_data

                # Plot
                ax.plot(times, feature_data, label='Zero Crossing Rate',
                       color='#2ecc71', alpha=0.6)
                ax.plot(times, smoothed_feature, label='Smoothed',
                       color='#2ecc71', linewidth=2.5)
                ax.set_ylabel('Rate')
                ax.set_title('Zero Crossing Rate (Noisiness)')

            else:  # Default to spectral contrast
                contrast = librosa.feature.spectral_contrast(
                    y=audio_segment,
                    sr=self.sample_rate,
                    hop_length=hop_length
                )

                # Plot multiple bands
                for i, band in enumerate(contrast):
                    ax.plot(times, band, label=f'Band {i}', alpha=0.7)

                ax.set_ylabel('Contrast (dB)')
                ax.set_title('Spectral Contrast (Harmonics vs. Noise)')

            # Common styling
            ax.set_xlabel('Time (s)')
            ax.grid(True, alpha=0.3)
            ax.legend()

            fig.tight_layout()

            # Convert to QImage and display
            canvas.draw()
            width, height = canvas.get_width_height()
            image = QImage(canvas.buffer_rgba(), width, height, QImage.Format.Format_RGBA8888)

            # Update scene
            self.spectral_scene.clear()
            pixmap = QPixmap.fromImage(image)
            self.spectral_scene.addPixmap(pixmap)
            self.spectral_view.fitInView(
                self.spectral_scene.sceneRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )

        except Exception as e:
            logger.error(f"Failed to update spectral features visualization: {e}")

    def _toggle_realtime_analysis(self, active):
        """Toggle real-time analysis"""
        if active:
            self.visualization_timer.start(100)  # Update every 100ms
        else:
            self.visualization_timer.stop()

    def _render_3d_visualization(self):
        """Render interactive 3D visualization of spectrogram"""
        if not MATPLOTLIB_AVAILABLE or not LIBROSA_AVAILABLE or self.audio_data is None:
            self.emit_error("3D visualization requires matplotlib and librosa")
            return

        try:
            # Show busy indicator during processing
            self.busy_indicator.setVisible(True)

            # Get time range
            time_start = self.time_start_spinner.value()
            time_end = self.time_end_spinner.value()

            # Convert to samples
            start_sample = int(time_start * self.sample_rate)
            end_sample = int(time_end * self.sample_rate)

            # Ensure valid sample range
            if start_sample >= len(self.audio_data) or end_sample > len(self.audio_data):
                logger.warning(f"Invalid sample range: {start_sample}-{end_sample} for data length {len(self.audio_data)}")
                self.busy_indicator.setVisible(False)
                return

            # Extract segment
            audio_segment = self.audio_data[start_sample:end_sample]

            if len(audio_segment) == 0:
                logger.warning("Empty audio segment for visualization")
                self.busy_indicator.setVisible(False)
                return

            # Compute STFT
            n_fft = 2048  # Default FFT size
            if hasattr(self, "fft_size_combo"):
                n_fft = int(self.fft_size_combo.currentText())

            hop_length = n_fft // 4  # 75% overlap

            # Get window function
            window_function = 'hann'  # default
            if hasattr(self, "window_combo"):
                window_function = self.window_combo.currentText().lower()

            # Compute STFT
            D = librosa.stft(audio_segment, n_fft=n_fft, hop_length=hop_length, window=window_function)

            # Convert to magnitude spectrogram
            spectrogram = np.abs(D)

            # Get log scale option
            log_scale = True  # default
            if hasattr(self, "log_scale_check"):
                log_scale = self.log_scale_check.isChecked()

            if log_scale:
                # Convert to dB with reference normalization
                spectrogram = librosa.amplitude_to_db(spectrogram, ref=np.max)

            # Get frequency and time values
            freqs = librosa.fft_frequencies(sr=self.sample_rate, n_fft=n_fft)
            times = librosa.frames_to_time(
                np.arange(0, spectrogram.shape[1]),
                sr=self.sample_rate,
                hop_length=hop_length
            )

            # Create a new 3D figure
            fig = plt.figure(figsize=(10, 6), facecolor='black')
            ax = fig.add_subplot(111, projection='3d')

            # Prepare grid for 3D plot
            time_grid, freq_grid = np.meshgrid(times, freqs)

            # Create colormap
            colormap_name = 'viridis'  # default
            if hasattr(self, "colormap_combo"):
                colormap_name = self.colormap_combo.currentText().lower()

            # Get frequency range if available
            min_freq = 0
            max_freq = self.sample_rate // 2
            if hasattr(self, "freq_min_spinner") and hasattr(self, "freq_max_spinner"):
                min_freq = self.freq_min_spinner.value()
                max_freq = self.freq_max_spinner.value()

            # Filter frequencies
            mask = (freqs >= min_freq) & (freqs <= max_freq)
            freq_grid_filtered = freq_grid[mask]
            time_grid_filtered = time_grid[mask]
            spectrogram_filtered = spectrogram[mask]

            # Create the 3D surface plot with the selected colormap
            surf = ax.plot_surface(
                time_grid_filtered,
                freq_grid_filtered / 1000,  # Convert to kHz for readability
                spectrogram_filtered,
                cmap=colormap_name,
                linewidth=0,
                antialiased=True,
                alpha=0.8,
                shade=True
            )

            # Add color bar
            fig.colorbar(surf, ax=ax, shrink=0.5, aspect=5)

            # Configure 3D view
            ax.view_init(elev=30, azim=45)  # Default viewing angle
            ax.dist = 12  # Distance from the plot

            # Configure axis labels and styling
            ax.set_xlabel('Time (s)', fontsize=10, color='white')
            ax.set_ylabel('Frequency (kHz)', fontsize=10, color='white')
            if log_scale:
                ax.set_zlabel('Magnitude (dB)', fontsize=10, color='white')
            else:
                ax.set_zlabel('Magnitude', fontsize=10, color='white')

            ax.set_title('3D Audio Spectrogram', fontsize=14, color='white')

            # Set grid colors
            ax.xaxis.pane.fill = False
            ax.yaxis.pane.fill = False
            ax.zaxis.pane.fill = False
            ax.xaxis.pane.set_edgecolor('gray')
            ax.yaxis.pane.set_edgecolor('gray')
            ax.zaxis.pane.set_edgecolor('gray')
            ax.grid(True, linestyle='-', color='gray', alpha=0.3)

            # Set tick colors
            ax.tick_params(axis='x', colors='white')
            ax.tick_params(axis='y', colors='white')
            ax.tick_params(axis='z', colors='white')

            # Apply tight layout and styling
            fig.tight_layout()

            # Store the figure for later use in export
            self.current_3d_fig = fig
            self.current_spectrogram = spectrogram_filtered
            self.current_freqs = freq_grid_filtered
            self.current_times = time_grid_filtered

            # Convert the 3D plot to a Qt widget that can be displayed
            canvas = FigureCanvas(fig)
            toolbar = NavigationToolbar2QT(canvas, self.viz_tabs)
            toolbar.setStyleSheet("background-color: #333333; color: white;")

            # Configure canvas and toolbar
            toolbar.setMinimumHeight(30)
            toolbar.setMaximumHeight(40)

            # Update the 3D visualization container
            if hasattr(self, "visualization_3d_layout"):
                # Clear existing widgets from layout
                while self.visualization_3d_layout.count():
                    item = self.visualization_3d_layout.takeAt(0)
                    widget = item.widget()
                    if widget is not None:
                        widget.hide()
                        widget.deleteLater()

                # Add the new canvas and toolbar
                self.visualization_3d_layout.addWidget(toolbar)
                self.visualization_3d_layout.addWidget(canvas)

                # Connect the canvas resize event
                canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            # Hide busy indicator when done
            self.busy_indicator.setVisible(False)

        except Exception as e:
            logger.error(f"Failed to render 3D visualization: {str(e)}")
            traceback.print_exc()
            self.busy_indicator.setVisible(False)
            self.emit_error(f"3D visualization error: {str(e)}")

    def _export_3d_model(self):
        """Export 3D model to file"""
        if not hasattr(self, "current_spectrogram") or self.current_spectrogram is None:
            self.emit_error("No 3D data available for export. Please generate a 3D visualization first.")
            return

        # Get file extension filter based on supported formats
        file_filter = "Wavefront OBJ (*.obj);;STL Files (*.stl);;glTF Files (*.gltf);;All Files (*.*)"
        default_name = f"spectrogram_3d_{datetime.now().strftime('%Y%m%d_%H%M%S')}.obj"

        # Show file dialog
        export_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export 3D Model",
            default_name,
            file_filter
        )

        if export_path:
            try:
                # Show busy indicator
                self.busy_indicator.setVisible(True)

                # Process events to show busy indicator
                QApplication.processEvents()

                # Get file extension
                file_ext = os.path.splitext(export_path)[1].lower()

                success = False
                if file_ext == '.obj':
                    success = self._export_obj(export_path)
                elif file_ext == '.stl':
                    success = self._export_stl(export_path)
                elif file_ext == '.gltf':
                    success = self._export_gltf(export_path)
                else:
                    # Default to OBJ format if extension not recognized
                    if not any(export_path.endswith(ext) for ext in [".obj", ".stl", ".gltf"]):
                        export_path += ".obj"
                    success = self._export_obj(export_path)

                # Hide busy indicator
                self.busy_indicator.setVisible(False)

                if success:
                    self.emit_status(f"Successfully exported 3D model to {export_path}")
                else:
                    self.emit_error(f"Failed to export 3D model to {export_path}")

            except Exception as e:
                logger.error(f"Failed to export 3D model: {str(e)}")
                traceback.print_exc()
                self.busy_indicator.setVisible(False)
                self.emit_error(f"Failed to export 3D model: {str(e)}")

    def _export_obj(self, file_path: str) -> bool:
        """Export spectrogram as Wavefront OBJ file"""
        try:
            if not hasattr(self, "current_spectrogram") or self.current_spectrogram is None:
                return False

            spectrogram = self.current_spectrogram
            freqs = self.current_freqs
            times = self.current_times

            # Downsample for manageable file size
            downsample_factor = 4
            spectrogram = spectrogram[::downsample_factor, ::downsample_factor]
            freqs = freqs[::downsample_factor, ::downsample_factor]
            times = times[::downsample_factor, ::downsample_factor]

            # Normalize coordinates to 0-10 range
            times_norm = times / np.max(times) * 10 if np.max(times) > 0 else times
            freqs_norm = freqs / np.max(freqs) * 10 if np.max(freqs) > 0 else freqs

            # Normalize height values (spectrogram magnitudes)
            spec_min = np.min(spectrogram)
            spec_max = np.max(spectrogram)
            if spec_max > spec_min:
                z_scale = 3.0  # Height scale factor
                spectrogram_norm = (spectrogram - spec_min) / (spec_max - spec_min) * z_scale
            else:
                spectrogram_norm = np.zeros_like(spectrogram)

            # Create OBJ file
            with open(file_path, 'w') as f:
                # Write header
                f.write(f"# 3D Spectrogram OBJ file - DrumTracKAI AudioVisualization\n")
                f.write(f"# Created on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # Write vertices (v x y z)
                for i in range(spectrogram_norm.shape[0]):
                    for j in range(spectrogram_norm.shape[1]):
                        f.write(f"v {times_norm[i, j]} {freqs_norm[i, j]} {spectrogram_norm[i, j]}\n")

                # Write texture coordinates (optional)
                f.write("\n")

                # Generate faces (indices start at 1 in OBJ format)
                rows, cols = spectrogram_norm.shape
                for i in range(rows - 1):
                    for j in range(cols - 1):
                        # Calculate vertex indices
                        v1 = i * cols + j + 1
                        v2 = i * cols + (j + 1) + 1
                        v3 = (i + 1) * cols + (j + 1) + 1
                        v4 = (i + 1) * cols + j + 1

                        # Write faces as triangles
                        f.write(f"f {v1} {v2} {v3}\n")
                        f.write(f"f {v1} {v3} {v4}\n")

            return True

        except Exception as e:
            logger.error(f"Failed to export OBJ file: {str(e)}")
            traceback.print_exc()
            return False

    def _export_stl(self, file_path: str) -> bool:
        """Export spectrogram as binary STL file"""
        try:
            if not hasattr(self, "current_spectrogram") or self.current_spectrogram is None:
                return False

            spectrogram = self.current_spectrogram
            freqs = self.current_freqs
            times = self.current_times

            # Downsample for manageable file size
            downsample_factor = 4
            spectrogram = spectrogram[::downsample_factor, ::downsample_factor]
            freqs = freqs[::downsample_factor, ::downsample_factor]
            times = times[::downsample_factor, ::downsample_factor]

            # Normalize coordinates
            times_norm = times / np.max(times) * 10 if np.max(times) > 0 else times
            freqs_norm = freqs / np.max(freqs) * 10 if np.max(freqs) > 0 else freqs

            # Normalize height values
            spec_min = np.min(spectrogram)
            spec_max = np.max(spectrogram)
            if spec_max > spec_min:
                z_scale = 3.0  # Height scale factor
                spectrogram_norm = (spectrogram - spec_min) / (spec_max - spec_min) * z_scale
            else:
                spectrogram_norm = np.zeros_like(spectrogram)

            # Get shape dimensions
            rows, cols = spectrogram_norm.shape
            num_triangles = (rows - 1) * (cols - 1) * 2  # Two triangles per grid square

            # Create binary STL file
            with open(file_path, 'wb') as f:
                # Write STL header (80 bytes + 4-byte triangle count)
                header = f"DrumTracKAI 3D Spectrogram - {datetime.now().strftime('%Y%m%d')}\0".encode('ascii')
                header = header + b'\0' * (80 - len(header))  # Pad to 80 bytes
                f.write(header)
                f.write(struct.pack('<I', num_triangles))  # Number of triangles as unsigned int (4 bytes)

                # Write triangle data
                for i in range(rows - 1):
                    for j in range(cols - 1):
                        # Define the vertices of the grid square
                        v1 = np.array([times_norm[i, j], freqs_norm[i, j], spectrogram_norm[i, j]])
                        v2 = np.array([times_norm[i, j+1], freqs_norm[i, j+1], spectrogram_norm[i, j+1]])
                        v3 = np.array([times_norm[i+1, j+1], freqs_norm[i+1, j+1], spectrogram_norm[i+1, j+1]])
                        v4 = np.array([times_norm[i+1, j], freqs_norm[i+1, j], spectrogram_norm[i+1, j]])

                        # Triangle 1: v1-v2-v3
                        # Calculate normal
                        normal = np.cross(v2 - v1, v3 - v1)
                        if np.linalg.norm(normal) > 0:
                            normal = normal / np.linalg.norm(normal)

                        # Write normal and vertices
                        f.write(struct.pack('<3f', *normal))  # Normal vector
                        f.write(struct.pack('<3f', *v1))  # Vertex 1
                        f.write(struct.pack('<3f', *v2))  # Vertex 2
                        f.write(struct.pack('<3f', *v3))  # Vertex 3
                        f.write(struct.pack('<H', 0))  # Attribute byte count (0)

                        # Triangle 2: v1-v3-v4
                        # Calculate normal
                        normal = np.cross(v3 - v1, v4 - v1)
                        if np.linalg.norm(normal) > 0:
                            normal = normal / np.linalg.norm(normal)

                        # Write normal and vertices
                        f.write(struct.pack('<3f', *normal))  # Normal vector
                        f.write(struct.pack('<3f', *v1))  # Vertex 1
                        f.write(struct.pack('<3f', *v3))  # Vertex 3
                        f.write(struct.pack('<3f', *v4))  # Vertex 4
                        f.write(struct.pack('<H', 0))  # Attribute byte count (0)

            return True

        except Exception as e:
            logger.error(f"Failed to export STL file: {str(e)}")
            traceback.print_exc()
            return False

    def _export_gltf(self, file_path: str) -> bool:
        """Export spectrogram as glTF 2.0 format"""
        try:
            if not hasattr(self, "current_spectrogram") or self.current_spectrogram is None:
                return False

            # Use json module for glTF creation
            spectrogram = self.current_spectrogram
            freqs = self.current_freqs
            times = self.current_times

            # Downsample for manageable file size
            downsample_factor = 6  # Higher downsample for glTF (smaller file)
            spectrogram = spectrogram[::downsample_factor, ::downsample_factor]
            freqs = freqs[::downsample_factor, ::downsample_factor]
            times = times[::downsample_factor, ::downsample_factor]

            # Normalize coordinates to 0-10 range
            times_norm = times / np.max(times) * 10 if np.max(times) > 0 else times
            freqs_norm = freqs / np.max(freqs) * 10 if np.max(freqs) > 0 else freqs

            # Normalize height values (spectrogram magnitudes)
            spec_min = np.min(spectrogram)
            spec_max = np.max(spectrogram)
            if spec_max > spec_min:
                z_scale = 3.0  # Height scale factor
                spectrogram_norm = (spectrogram - spec_min) / (spec_max - spec_min) * z_scale
            else:
                spectrogram_norm = np.zeros_like(spectrogram)

            # Get dimensions
            rows, cols = spectrogram_norm.shape

            # Prepare vertices and indices
            vertices = []
            normals = []
            indices = []

            # Create vertices array (x, y, z coordinates)
            for i in range(rows):
                for j in range(cols):
                    vertices.extend([float(times_norm[i, j]), float(freqs_norm[i, j]), float(spectrogram_norm[i, j])])

            # Create indices for triangles
            for i in range(rows - 1):
                for j in range(cols - 1):
                    # Calculate vertex indices
                    v1 = i * cols + j
                    v2 = i * cols + (j + 1)
                    v3 = (i + 1) * cols + (j + 1)
                    v4 = (i + 1) * cols + j

                    # Two triangles per grid square
                    indices.extend([v1, v2, v3])  # First triangle
                    indices.extend([v1, v3, v4])  # Second triangle

                    # Calculate normals for first triangle
                    p1 = np.array([vertices[v1*3], vertices[v1*3+1], vertices[v1*3+2]])
                    p2 = np.array([vertices[v2*3], vertices[v2*3+1], vertices[v2*3+2]])
                    p3 = np.array([vertices[v3*3], vertices[v3*3+1], vertices[v3*3+2]])

                    # Calculate normal vector for this face
                    normal = np.cross(p2 - p1, p3 - p1)
                    if np.linalg.norm(normal) > 0:
                        normal = normal / np.linalg.norm(normal)

                    # Store normal for each vertex of this face
                    for _ in range(3):  # Three vertices in first triangle
                        normals.extend([float(normal[0]), float(normal[1]), float(normal[2])])

                    # Calculate normals for second triangle
                    p4 = np.array([vertices[v4*3], vertices[v4*3+1], vertices[v4*3+2]])
                    normal = np.cross(p3 - p1, p4 - p1)
                    if np.linalg.norm(normal) > 0:
                        normal = normal / np.linalg.norm(normal)

                    # Store normal for each vertex of this face
                    for _ in range(3):  # Three vertices in second triangle
                        normals.extend([float(normal[0]), float(normal[1]), float(normal[2])])

            # Convert arrays to bytes for binary glTF
            vertices_bytes = bytearray(struct.pack('<%df' % len(vertices), *vertices))
            indices_bytes = bytearray(struct.pack('<%dI' % len(indices), *indices))
            normals_bytes = bytearray(struct.pack('<%df' % len(normals), *normals))

            # Create buffer and buffer views
            buffer_data = vertices_bytes + indices_bytes + normals_bytes
            buffer_length = len(buffer_data)

            # Base64 encode the buffer data
            buffer_uri = "data:application/octet-stream;base64," + base64.b64encode(buffer_data).decode('ascii')

            # Define buffer views
            buffer_views = [
                {
                    "buffer": 0,
                    "byteOffset": 0,
                    "byteLength": len(vertices_bytes),
                    "target": 34962  # ARRAY_BUFFER
                },
                {
                    "buffer": 0,
                    "byteOffset": len(vertices_bytes),
                    "byteLength": len(indices_bytes),
                    "target": 34963  # ELEMENT_ARRAY_BUFFER
                },
                {
                    "buffer": 0,
                    "byteOffset": len(vertices_bytes) + len(indices_bytes),
                    "byteLength": len(normals_bytes),
                    "target": 34962  # ARRAY_BUFFER
                }
            ]

            # Define accessors
            accessors = [
                {
                    "bufferView": 0,
                    "byteOffset": 0,
                    "componentType": 5126,  # FLOAT
                    "count": len(vertices) // 3,
                    "type": "VEC3",
                    "max": [10.0, 10.0, 3.0],  # Maximum values for x, y, z
                    "min": [0.0, 0.0, 0.0]  # Minimum values for x, y, z
                },
                {
                    "bufferView": 1,
                    "byteOffset": 0,
                    "componentType": 5125,  # UNSIGNED_INT
                    "count": len(indices),
                    "type": "SCALAR"
                },
                {
                    "bufferView": 2,
                    "byteOffset": 0,
                    "componentType": 5126,  # FLOAT
                    "count": len(normals) // 3,
                    "type": "VEC3"
                }
            ]

            # Define materials
            materials = [
                {
                    "pbrMetallicRoughness": {
                        "baseColorFactor": [0.8, 0.3, 0.3, 1.0],  # RGBA
                        "metallicFactor": 0.5,
                        "roughnessFactor": 0.6
                    },
                    "name": "Spectrogram_Material"
                }
            ]

            # Define mesh
            meshes = [
                {
                    "name": "Spectrogram_Surface",
                    "primitives": [
                        {
                            "attributes": {
                                "POSITION": 0,
                                "NORMAL": 2
                            },
                            "indices": 1,
                            "material": 0,
                            "mode": 4  # TRIANGLES
                        }
                    ]
                }
            ]

            # Define node
            nodes = [
                {
                    "name": "Spectrogram_Node",
                    "mesh": 0
                }
            ]

            # Define scene
            scenes = [
                {
                    "nodes": [0]
                }
            ]

            # Assemble glTF structure
            gltf = {
                "asset": {
                    "version": "2.0",
                    "generator": "DrumTracKAI Audio Visualization"
                },
                "scene": 0,
                "scenes": scenes,
                "nodes": nodes,
                "meshes": meshes,
                "materials": materials,
                "accessors": accessors,
                "bufferViews": buffer_views,
                "buffers": [
                    {
                        "byteLength": buffer_length,
                        "uri": buffer_uri
                    }
                ]
            }

            # Write glTF file
            with open(file_path, 'w') as f:
                json.dump(gltf, f, indent=2)

            return True

        except Exception as e:
            logger.error(f"Failed to export glTF file: {str(e)}")
            traceback.print_exc()
            return False

    def emit_status(self, message: str):
        """Emit status message"""
        # If we have a parent with status_updated signal, use it
        if hasattr(self.parent(), 'status_updated'):
            self.parent().status_updated.emit(message)
        else:
            logger.info(f"Status: {message}")

    def emit_error(self, message: str):
        """Emit error message"""
        # If we have a parent with error signal, use it
        if hasattr(self.parent(), 'error_occurred'):
            self.parent().error_occurred.emit(message)
        else:
            logger.error(f"Error: {message}")
            # Show error dialog as fallback
            try:
                QMessageBox.critical(self, "Error", message)
            except Exception:
                pass