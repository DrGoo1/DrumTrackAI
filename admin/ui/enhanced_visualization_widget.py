"""
Enhanced Visualization Widget for DrumTracKAI Desktop Application
Combines matplotlib, plotly, and web technologies for sophisticated analysis visualization
"""

import sys
import os
import tempfile
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QTimer, QUrl, QThread, pyqtSignal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, QPushButton, 
    QComboBox, QSplitter, QGroupBox, QGridLayout, QCheckBox, QSpinBox,
    QSlider, QProgressBar, QTextEdit, QFileDialog, QMessageBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QFont, QPalette, QColor

# Matplotlib imports with Qt backend
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# Import our advanced visualization service
from admin.services.advanced_visualization_service import AdvancedVisualizationService, VisualizationData
from admin.ui.base_widget import BaseWidget

logger = logging.getLogger(__name__)

class EnhancedVisualizationWidget(BaseWidget):
    """Enhanced visualization widget with web-style graphics for desktop"""
    
    # Signals
    analysis_requested = Signal(str)  # drum_type
    export_requested = Signal(str, str)  # format, path
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.visualization_service = AdvancedVisualizationService()
        self.current_data = None
        self.temp_files = []  # Track temp files for cleanup
        
        self._setup_ui()
        self._connect_signals()
        self._apply_dark_theme()
        
    def _setup_ui(self):
        """Setup the enhanced visualization UI"""
        super()._setup_ui()
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Header with controls
        header_widget = self._create_header_controls()
        main_layout.addWidget(header_widget)
        
        # Main content area with tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Create visualization tabs
        self._create_visualization_tabs()
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.status_label = QLabel("Ready for analysis...")
        self.status_label.setStyleSheet("color: #10b981; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
    def _create_header_controls(self) -> QWidget:
        """Create header with analysis controls"""
        header = QGroupBox("Analysis Controls")
        header.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #374151;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #1f2937;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #f9fafb;
            }
        """)
        
        layout = QHBoxLayout(header)
        
        # Drum type selector
        layout.addWidget(QLabel("Drum Type:"))
        self.drum_selector = QComboBox()
        self.drum_selector.addItems(['kick', 'snare', 'hihat', 'crash', 'ride', 'toms'])
        self.drum_selector.setCurrentText('kick')
        layout.addWidget(self.drum_selector)
        
        # Analysis mode
        layout.addWidget(QLabel("Analysis Mode:"))
        self.analysis_mode = QComboBox()
        self.analysis_mode.addItems(['Real-time', 'Detailed', 'Neural Focus', 'Timing Focus'])
        layout.addWidget(self.analysis_mode)
        
        # Refresh button
        self.refresh_btn = QPushButton(" Refresh Analysis")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #6366f1;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4f46e5;
            }
            QPushButton:pressed {
                background-color: #3730a3;
            }
        """)
        layout.addWidget(self.refresh_btn)
        
        layout.addStretch()
        
        # Export controls
        self.export_btn = QPushButton("ANALYSIS Export Analysis")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        layout.addWidget(self.export_btn)
        
        return header
        
    def _create_visualization_tabs(self):
        """Create tabs for different visualization types"""
        
        # 1. Overview Dashboard Tab
        self.overview_tab = self._create_overview_tab()
        self.tab_widget.addTab(self.overview_tab, "TARGET Overview")
        
        # 2. Neural Entrainment Tab
        self.neural_tab = self._create_neural_tab()
        self.tab_widget.addTab(self.neural_tab, " Neural Analysis")
        
        # 3. Micro-Timing Tab
        self.timing_tab = self._create_timing_tab()
        self.tab_widget.addTab(self.timing_tab, "⏱ Micro-Timing")
        
        # 4. Interactive Dashboard Tab
        self.interactive_tab = self._create_interactive_tab()
        self.tab_widget.addTab(self.interactive_tab, "LAUNCH Interactive")
        
        # 5. Advanced Analysis Tab
        self.advanced_tab = self._create_advanced_tab()
        self.tab_widget.addTab(self.advanced_tab, " Advanced")
        
    def _create_overview_tab(self) -> QWidget:
        """Create overview tab with key metrics"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Splitter for multiple charts
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Groove radar and humanness
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # Groove radar chart
        self.groove_radar_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        self.groove_radar_canvas.figure.patch.set_facecolor('#1f2937')
        left_layout.addWidget(self.groove_radar_canvas)
        
        # Humanness gauge
        self.humanness_canvas = FigureCanvas(Figure(figsize=(8, 6)))
        self.humanness_canvas.figure.patch.set_facecolor('#1f2937')
        left_layout.addWidget(self.humanness_canvas)
        
        splitter.addWidget(left_widget)
        
        # Right side - Key metrics and summary
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # Key metrics display
        metrics_group = QGroupBox("Key Metrics")
        metrics_layout = QGridLayout(metrics_group)
        
        # Create metric labels
        self.tempo_label = QLabel("-- BPM")
        self.humanness_label = QLabel("--%")
        self.groove_label = QLabel("--%")
        self.sync_label = QLabel("--%")
        
        # Style metric labels
        for label in [self.tempo_label, self.humanness_label, self.groove_label, self.sync_label]:
            label.setFont(QFont("Arial", 16, QFont.Bold))
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #00ff88; background-color: #374151; padding: 10px; border-radius: 8px;")
        
        metrics_layout.addWidget(QLabel("Tempo:"), 0, 0)
        metrics_layout.addWidget(self.tempo_label, 0, 1)
        metrics_layout.addWidget(QLabel("Humanness:"), 1, 0)
        metrics_layout.addWidget(self.humanness_label, 1, 1)
        metrics_layout.addWidget(QLabel("Groove:"), 2, 0)
        metrics_layout.addWidget(self.groove_label, 2, 1)
        metrics_layout.addWidget(QLabel("Bass Sync:"), 3, 0)
        metrics_layout.addWidget(self.sync_label, 3, 1)
        
        right_layout.addWidget(metrics_group)
        
        # Analysis summary
        summary_group = QGroupBox("Analysis Summary")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMaximumHeight(200)
        self.summary_text.setStyleSheet("""
            QTextEdit {
                background-color: #374151;
                color: #f9fafb;
                border: 1px solid #4b5563;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        summary_layout.addWidget(self.summary_text)
        
        right_layout.addWidget(summary_group)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        
        layout.addWidget(splitter)
        return tab
        
    def _create_neural_tab(self) -> QWidget:
        """Create neural entrainment analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Neural entrainment chart
        self.neural_canvas = FigureCanvas(Figure(figsize=(12, 8)))
        self.neural_canvas.figure.patch.set_facecolor('#1f2937')
        layout.addWidget(self.neural_canvas)
        
        # Neural analysis controls
        controls_group = QGroupBox("Neural Analysis Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Brainwave focus
        controls_layout.addWidget(QLabel("Focus Band:"))
        self.brainwave_selector = QComboBox()
        self.brainwave_selector.addItems(['All Bands', 'Delta (0.5-4 Hz)', 'Theta (4-8 Hz)', 
                                         'Alpha (8-13 Hz)', 'Beta (13-30 Hz)', 'Gamma (30-100 Hz)'])
        controls_layout.addWidget(self.brainwave_selector)
        
        # Flow state analysis
        self.flow_analysis_btn = QPushButton(" Analyze Flow State")
        self.flow_analysis_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7c3aed; }
        """)
        controls_layout.addWidget(self.flow_analysis_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        return tab
        
    def _create_timing_tab(self) -> QWidget:
        """Create micro-timing analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Timing analysis chart
        self.timing_canvas = FigureCanvas(Figure(figsize=(14, 10)))
        self.timing_canvas.figure.patch.set_facecolor('#1f2937')
        layout.addWidget(self.timing_canvas)
        
        # Timing controls
        controls_group = QGroupBox("Timing Analysis Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Precision level
        controls_layout.addWidget(QLabel("Precision:"))
        self.precision_slider = QSlider(Qt.Horizontal)
        self.precision_slider.setRange(1, 10)
        self.precision_slider.setValue(5)
        self.precision_slider.setTickPosition(QSlider.TicksBelow)
        controls_layout.addWidget(self.precision_slider)
        
        self.precision_label = QLabel("0.1ms")
        controls_layout.addWidget(self.precision_label)
        
        # Window size
        controls_layout.addWidget(QLabel("Window:"))
        self.window_spin = QSpinBox()
        self.window_spin.setRange(5, 50)
        self.window_spin.setValue(10)
        self.window_spin.setSuffix(" beats")
        controls_layout.addWidget(self.window_spin)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        return tab
        
    def _create_interactive_tab(self) -> QWidget:
        """Create interactive web-based dashboard tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Web view for interactive content
        self.web_view = QWebEngineView()
        self.web_view.setMinimumHeight(600)
        layout.addWidget(self.web_view)
        
        # Interactive controls
        controls_group = QGroupBox("Interactive Controls")
        controls_layout = QHBoxLayout(controls_group)
        
        # Real-time updates
        self.realtime_checkbox = QCheckBox("Real-time Updates")
        controls_layout.addWidget(self.realtime_checkbox)
        
        # Animation speed
        controls_layout.addWidget(QLabel("Animation Speed:"))
        self.animation_slider = QSlider(Qt.Horizontal)
        self.animation_slider.setRange(1, 10)
        self.animation_slider.setValue(5)
        controls_layout.addWidget(self.animation_slider)
        
        # Fullscreen button
        self.fullscreen_btn = QPushButton("INSPECTING Fullscreen")
        self.fullscreen_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #4b5563; }
        """)
        controls_layout.addWidget(self.fullscreen_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        return tab
        
    def _create_advanced_tab(self) -> QWidget:
        """Create advanced analysis tab with TFR and neural features"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Advanced analysis placeholder
        advanced_label = QLabel(" Advanced Analysis Features")
        advanced_label.setFont(QFont("Arial", 16, QFont.Bold))
        advanced_label.setAlignment(Qt.AlignCenter)
        advanced_label.setStyleSheet("color: #6366f1; padding: 20px;")
        layout.addWidget(advanced_label)
        
        # Feature toggles
        features_group = QGroupBox("Analysis Features")
        features_layout = QGridLayout(features_group)
        
        # TFR Analysis
        self.tfr_checkbox = QCheckBox("Time-Frequency Reassignment")
        self.tfr_checkbox.setChecked(True)
        features_layout.addWidget(self.tfr_checkbox, 0, 0)
        
        # Neural Style Encoding
        self.neural_style_checkbox = QCheckBox("Neural Style Encoding")
        self.neural_style_checkbox.setChecked(True)
        features_layout.addWidget(self.neural_style_checkbox, 0, 1)
        
        # GPU Acceleration
        self.gpu_checkbox = QCheckBox("GPU Acceleration")
        features_layout.addWidget(self.gpu_checkbox, 1, 0)
        
        # Synchrosqueezing
        self.synchro_checkbox = QCheckBox("Synchrosqueezing Transform")
        features_layout.addWidget(self.synchro_checkbox, 1, 1)
        
        layout.addWidget(features_group)
        
        # Advanced metrics display
        self.advanced_canvas = FigureCanvas(Figure(figsize=(12, 8)))
        self.advanced_canvas.figure.patch.set_facecolor('#1f2937')
        layout.addWidget(self.advanced_canvas)
        
        return tab
        
    def _connect_signals(self):
        """Connect UI signals"""
        self.refresh_btn.clicked.connect(self._refresh_analysis)
        self.export_btn.clicked.connect(self._export_analysis)
        self.drum_selector.currentTextChanged.connect(self._on_drum_changed)
        self.analysis_mode.currentTextChanged.connect(self._on_mode_changed)
        
        # Visualization service signals
        self.visualization_service.visualization_updated.connect(self._on_visualization_updated)
        self.visualization_service.error_occurred.connect(self._on_error)
        
        # Tab change
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
    def _apply_dark_theme(self):
        """Apply dark theme styling"""
        self.setStyleSheet("""
            QWidget {
                background-color: #1f2937;
                color: #f9fafb;
            }
            QTabWidget::pane {
                border: 2px solid #374151;
                border-radius: 8px;
                background-color: #1f2937;
            }
            QTabBar::tab {
                background-color: #374151;
                color: #d1d5db;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #6366f1;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #4b5563;
            }
            QComboBox {
                background-color: #374151;
                color: #f9fafb;
                border: 1px solid #4b5563;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #f9fafb;
            }
            QLabel {
                color: #f9fafb;
            }
        """)
        
    def update_analysis_data(self, data: VisualizationData):
        """Update visualization with new analysis data"""
        self.current_data = data
        self.status_label.setText(f"Analysis updated for {data.drum_type}")
        self.status_label.setStyleSheet("color: #10b981; font-weight: bold;")
        
        # Update visualizations
        self._update_overview_visualizations()
        self._update_neural_visualization()
        self._update_timing_visualization()
        self._update_interactive_dashboard()
        
        # Update metrics
        self._update_key_metrics()
        
    def _update_overview_visualizations(self):
        """Update overview tab visualizations"""
        if not self.current_data:
            return
            
        # Update groove radar
        groove_fig = self.visualization_service.create_groove_radar_chart(self.current_data)
        self.groove_radar_canvas.figure.clear()
        self.groove_radar_canvas.figure = groove_fig
        self.groove_radar_canvas.draw()
        
        # Update humanness gauge
        humanness_fig = self.visualization_service.create_humanness_gauge(self.current_data)
        self.humanness_canvas.figure.clear()
        self.humanness_canvas.figure = humanness_fig
        self.humanness_canvas.draw()
        
    def _update_neural_visualization(self):
        """Update neural entrainment visualization"""
        if not self.current_data:
            return
            
        neural_fig = self.visualization_service.create_neural_entrainment_chart(self.current_data)
        self.neural_canvas.figure.clear()
        self.neural_canvas.figure = neural_fig
        self.neural_canvas.draw()
        
    def _update_timing_visualization(self):
        """Update micro-timing visualization"""
        if not self.current_data:
            return
            
        timing_fig = self.visualization_service.create_micro_timing_visualization(self.current_data)
        self.timing_canvas.figure.clear()
        self.timing_canvas.figure = timing_fig
        self.timing_canvas.draw()
        
    def _update_interactive_dashboard(self):
        """Update interactive web dashboard"""
        if not self.current_data:
            return
            
        try:
            html_content = self.visualization_service.create_interactive_plotly_dashboard(self.current_data)
            
            # Save to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_path = f.name
                self.temp_files.append(temp_path)
            
            # Load in web view
            self.web_view.load(QUrl.fromLocalFile(temp_path))
            
        except Exception as e:
            logger.error(f"Failed to update interactive dashboard: {str(e)}")
            
    def _update_key_metrics(self):
        """Update key metrics display"""
        if not self.current_data:
            return
            
        # Update metric labels
        tempo = self.current_data.tempo_profile.get('average_tempo', 0)
        self.tempo_label.setText(f"{tempo:.0f} BPM")
        
        humanness = self.current_data.humanness_score
        self.humanness_label.setText(f"{humanness:.0%}")
        
        groove = self.current_data.groove_pattern.get('groove_coherence', 0)
        self.groove_label.setText(f"{groove:.0%}")
        
        sync = self.current_data.groove_pattern.get('bass_sync_average', 0)
        self.sync_label.setText(f"{sync:.0%}")
        
        # Update summary text
        summary = f"""
        <h3 style="color: #6366f1;">Analysis Summary - {self.current_data.drum_type.title()}</h3>
        <p><b>Tempo:</b> {tempo:.1f} BPM (Stability: {self.current_data.tempo_profile.get('tempo_stability', 0):.1%})</p>
        <p><b>Humanness Score:</b> {humanness:.1%} - {'Highly Human' if humanness > 0.8 else 'Moderately Human' if humanness > 0.6 else 'Mechanical'}</p>
        <p><b>Groove Characteristics:</b></p>
        <ul>
        <li>Timing Variance: {self.current_data.groove_pattern.get('timing_variance', 0)*1000:.1f}ms</li>
        <li>Syncopation: {self.current_data.groove_pattern.get('syncopation_score', 0):.1%}</li>
        <li>Rhythmic Complexity: {self.current_data.groove_pattern.get('rhythmic_complexity', 0):.1%}</li>
        </ul>
        <p><b>Neural Entrainment:</b> Dominant frequency at {self.current_data.neural_entrainment.get('dominant_frequency', 0):.1f} Hz</p>
        """
        self.summary_text.setHtml(summary)
        
    def _refresh_analysis(self):
        """Refresh analysis for current drum type"""
        drum_type = self.drum_selector.currentText()
        self.status_label.setText("Refreshing analysis...")
        self.status_label.setStyleSheet("color: #f59e0b; font-weight: bold;")
        self.analysis_requested.emit(drum_type)
        
    def _export_analysis(self):
        """Export current analysis"""
        if not self.current_data:
            QMessageBox.warning(self, "No Data", "No analysis data available to export.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Analysis", 
            f"drumtrackai_analysis_{self.current_data.drum_type}.html",
            "HTML Files (*.html);;JSON Files (*.json)"
        )
        
        if file_path:
            format_type = "html" if file_path.endswith('.html') else "json"
            self.visualization_service.export_analysis(self.current_data, file_path, format_type)
            QMessageBox.information(self, "Export Complete", f"Analysis exported to {file_path}")
            
    def _on_drum_changed(self, drum_type: str):
        """Handle drum type change"""
        if self.current_data:
            self.current_data.drum_type = drum_type
            self._refresh_analysis()
            
    def _on_mode_changed(self, mode: str):
        """Handle analysis mode change"""
        self.status_label.setText(f"Analysis mode: {mode}")
        
    def _on_tab_changed(self, index: int):
        """Handle tab change"""
        tab_names = ["Overview", "Neural", "Timing", "Interactive", "Advanced"]
        if 0 <= index < len(tab_names):
            self.status_label.setText(f"Viewing {tab_names[index]} analysis")
            
    def _on_visualization_updated(self, viz_type: str, data):
        """Handle visualization service updates"""
        self.status_label.setText(f"Visualization updated: {viz_type}")
        
    def _on_error(self, error_message: str):
        """Handle visualization errors"""
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        logger.error(f"Visualization error: {error_message}")
        
    def cleanup(self):
        """Cleanup temporary files"""
        for temp_file in self.temp_files:
            try:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {str(e)}")
        self.temp_files.clear()
        
    def closeEvent(self, event):
        """Handle widget close event"""
        self.cleanup()
        super().closeEvent(event)
