#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Musical Arrangement Analyzer Widget for DrumTracKAI Admin
"""

import sys
import logging
import os
import traceback

from PySide6.QtCore import QThread, QObject, Signal, Slot
from importlib import reload, import_module
from services.mvsep_service import MVSepService
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer
from PySide6.QtGui import QFont, QPainter, QColor, QPen, QBrush, QLinearGradient
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QSplitter, QTabWidget, QTextEdit, QComboBox,
    QProgressBar, QScrollArea, QFrame, QGridLayout, QCheckBox
)
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

# Create a logger for this module
logger = logging.getLogger(__name__)

# Add the Drum Analysis Final directory to the path to import the musical_arrangement_analyzer module
drum_analysis_path = Path(r"H:\DrumTracKAI_v1.1.7\docs\Drum_Analysis_Final")
if drum_analysis_path.exists() and str(drum_analysis_path) not in sys.path:
    sys.path.append(str(drum_analysis_path))

try:
    from musical_arrangement_analyzer import (
        MusicalStructureDetector, SectionDrumAnalyzer, SectionType,
        DrumApproach, MVSepProgressWidget, MVSepIntegration,
        DrumAnalysisWindow, DrumAnalysisResults
    )
    ANALYZER_AVAILABLE = True
    logger.info("Successfully imported musical_arrangement_analyzer module")
except ImportError as e:
    logger.error(f"Failed to import musical_arrangement_analyzer: {e}")
    traceback.print_exc()
    ANALYZER_AVAILABLE = False


class MusicalArrangementAnalyzerWidget(QWidget):
    """
    Widget for integrating the Musical Arrangement Analyzer into DrumTracKAI Admin
    """

    # Define signals
    analysis_started = Signal()
    analysis_completed = Signal(dict)
    analysis_error = Signal(str)

    def __init__(self, parent=None, event_bus=None, strict_mode=False):
        super().__init__(parent)
        self.setObjectName("MusicalArrangementAnalyzerWidget")
        self._initialization_complete = False

        # Store event bus and strict mode parameters
        self.event_bus = event_bus
        self.strict_mode = strict_mode

        # Initialize attributes
        self.analysis_data = None
        self.current_file = None
        self.is_analyzing = False

        # Get path to Drum Analysis Final directory
        self.drum_analysis_path = drum_analysis_path

        # Set up UI
        self._setup_ui()

        # Connect signals and slots
        self._connect_signals()

        # Mark initialization as complete
        self._initialization_complete = True
        logger.info("Musical Arrangement Analyzer Widget initialization complete")

    def _setup_ui(self):
        """Set up the user interface"""
        # Main layout
        main_layout = QVBoxLayout(self)

        if not ANALYZER_AVAILABLE:
            # Display error message if analyzer module is not available
            error_label = QLabel("Error: Musical Arrangement Analyzer module not available")
            error_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")

            details_label = QLabel(
                "Please make sure the musical_arrangement_analyzer.py module is available "
                "and all dependencies are installed."
            )
            details_label.setWordWrap(True)

            retry_button = QPushButton("Retry Loading Module")
            retry_button.clicked.connect(self._retry_load_module)

            main_layout.addWidget(error_label)
            main_layout.addWidget(details_label)
            main_layout.addWidget(retry_button)
            return

        # File selection area
        file_layout = QHBoxLayout()

        self.file_label = QLabel("Audio File:")
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setStyleSheet("font-style: italic; color: gray;")
        self.browse_button = QPushButton("Browse...")

        file_layout.addWidget(self.file_label)
        file_layout.addWidget(self.file_path_label, 1)
        file_layout.addWidget(self.browse_button)

        main_layout.addLayout(file_layout)

        # Analysis controls
        self.controls_layout = QHBoxLayout()

        self.analyze_button = QPushButton("Analyze Musical Arrangement")
        self.analyze_button.setEnabled(False)
        self.analyze_button.setMinimumWidth(220)

        self.use_mvsep_checkbox = QCheckBox("Use MVSep for Drum Extraction")
        self.use_mvsep_checkbox.setChecked(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready")
        self.progress_bar.setVisible(False)

        self.controls_layout.addWidget(self.use_mvsep_checkbox)
        self.controls_layout.addWidget(self.analyze_button)
        self.controls_layout.addStretch()

        main_layout.addLayout(self.controls_layout)

        # Status label and progress bar
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-weight: bold;")
        main_layout.addWidget(self.status_label)
        main_layout.addWidget(self.progress_bar)

        # Create MVSep integration if possible
        try:
            if ANALYZER_AVAILABLE:
                self.mvsep_progress_widget = MVSepProgressWidget(parent=self)
                self.mvsep_integration = MVSepService()
                main_layout.addWidget(self.mvsep_progress_widget)
                self.mvsep_progress_widget.setVisible(False)

                # Connect signals from mvsep widget - with fallback options
                try:
                    # First try the signal-based approach
                    if hasattr(self.mvsep_progress_widget, 'on_status_update'):
                        self.mvsep_progress_widget.on_status_update.connect(self._on_mvsep_status)
                        logger.info("Connected to MVSep status update signal")
                    # Alternatively, try the register_handler approach
                    elif hasattr(self.mvsep_progress_widget, 'ui_updater') and hasattr(self.mvsep_progress_widget.ui_updater, 'register_handler'):
                        self.mvsep_progress_widget.ui_updater.register_handler('progress', self._on_mvsep_status)
                        logger.info("Registered handler for MVSep progress updates")
                    else:
                        # If neither mechanism is available, use a polling approach
                        logger.info("Using polling approach for MVSep status updates")
                        self._mvsep_polling_timer = QTimer()
                        self._mvsep_polling_timer.setInterval(500)  # 500ms polling
                        self._mvsep_polling_timer.timeout.connect(self._poll_mvsep_status)
                        self._mvsep_polling_timer.start()
                except Exception as e:
                    logger.warning(f"Could not connect MVSep signals: {e}")

                logger.info("MVSep integration initialized")
        except Exception as e:
            logger.error(f"Could not initialize MVSep integration: {e}")
            traceback.print_exc()
            self.mvsep_integration = None
            self.mvsep_progress_widget = None

        # Splitter for results
        self.main_splitter = QSplitter(Qt.Vertical)

        # Results tabbed widget
        self.results_tabs = QTabWidget()

        # Summary tab
        self.summary_tab = QWidget()
        summary_layout = QVBoxLayout(self.summary_tab)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)

        summary_layout.addWidget(self.summary_text)

        # Sections tab
        self.sections_tab = QWidget()
        sections_layout = QVBoxLayout(self.sections_tab)

        self.sections_text = QTextEdit()
        self.sections_text.setReadOnly(True)

        sections_layout.addWidget(self.sections_text)

        # Drum Analysis tab
        self.drum_analysis_tab = QWidget()
        drum_layout = QVBoxLayout(self.drum_analysis_tab)

        self.drum_text = QTextEdit()
        self.drum_text.setReadOnly(True)

        drum_layout.addWidget(self.drum_text)

        # Add tabs to tab widget
        self.results_tabs.addTab(self.summary_tab, "Summary")
        self.results_tabs.addTab(self.sections_tab, "Sections")
        self.results_tabs.addTab(self.drum_analysis_tab, "Drum Analysis")

        self.main_splitter.addWidget(self.results_tabs)
        main_layout.addWidget(self.main_splitter, 1)

    def _connect_signals(self):
        """Connect signals and slots"""
        if not ANALYZER_AVAILABLE:
            return

        self.browse_button.clicked.connect(self._browse_file)
        self.analyze_button.clicked.connect(self._analyze_file)

        # Connect MVSep progress widget signals if available
        if hasattr(self, 'mvsep_progress_widget') and self.mvsep_progress_widget:
            if hasattr(self.mvsep_progress_widget, 'progress_updated'):
                self.mvsep_progress_widget.progress_updated.connect(self._on_mvsep_progress)

    def _retry_load_module(self):
        """Attempt to reload the analyzer module"""
        global ANALYZER_AVAILABLE

        try:
            # Remove old layout
            layout = self.layout()
            if layout:
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()

            # Try importing again
            if "musical_arrangement_analyzer" in sys.modules:
                reload(sys.modules["musical_arrangement_analyzer"])
            else:
                import_module("musical_arrangement_analyzer")

            from musical_arrangement_analyzer import (
                MusicalStructureDetector, SectionDrumAnalyzer, SectionType,
                DrumApproach, MVSepProgressWidget, MVSepIntegration,
                DrumAnalysisWindow, DrumAnalysisResults
            )

            ANALYZER_AVAILABLE = True
            logger.info("Successfully reloaded musical_arrangement_analyzer module")

            # Re-setup UI
            self._setup_ui()
            self._connect_signals()

        except ImportError as e:
            logger.error(f"Failed to import musical_arrangement_analyzer: {e}")
            traceback.print_exc()
            ANALYZER_AVAILABLE = False

            # Display error message
            error_label = QLabel(f"Error reloading module: {str(e)}")
            error_label.setStyleSheet("color: red; font-weight: bold; padding: 20px;")
            self.layout().addWidget(error_label)

    def _browse_file(self):
        """Open file dialog to select audio file"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Select Audio File",
            "",
            "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a);;All Files (*.*)"
        )

        if file_path:
            self.current_file = file_path
            self.file_path_label.setText(file_path)
            self.file_path_label.setStyleSheet("font-weight: normal; color: black;")
            self.analyze_button.setEnabled(True)
            self.status_label.setText("File selected. Ready to analyze.")

    def _analyze_file(self):
        """Start analysis of the selected file"""
        if not self.current_file or not os.path.exists(self.current_file):
            self.status_label.setText("Error: File not found")
            return

        self.is_analyzing = True
        self.analysis_started.emit()
        self._on_analysis_started()

        # Configure analysis options
        use_mvsep = self.use_mvsep_checkbox.isChecked()

        try:
            # Create worker thread for analysis
            class AnalysisWorker(QObject):
                finished = Signal(dict)
                progress = Signal(float, str)
                error = Signal(str)

                def __init__(self, file_path, use_mvsep, mvsep_integration=None, mvsep_progress_widget=None):
                    super().__init__()
                    self.file_path = file_path
                    self.use_mvsep = use_mvsep
                    self.mvsep_integration = mvsep_integration
                    self.mvsep_progress_widget = mvsep_progress_widget

                def run(self):
                    try:
                        # Create analyzer window (without showing UI)
                        analysis_window = DrumAnalysisWindow(show_ui=False)

                        # Connect progress signals
                        if self.mvsep_progress_widget:
                            analysis_window.set_mvsep_progress_widget(self.mvsep_progress_widget)

                        # Run analysis
                        results = analysis_window.run_analysis(
                            self.file_path,
                            use_mvsep=self.use_mvsep,
                            mvsep_integration=self.mvsep_integration,
                            progress_callback=lambda p, msg: self.progress.emit(p, msg)
                        )

                        # Emit finished signal with results
                        self.finished.emit(results)
                    except Exception as e:
                        logger.error(f"Analysis error: {str(e)}")
                        traceback.print_exc()
                        self.error.emit(f"Analysis failed: {str(e)}")

            # Create thread and worker
            self.analysis_thread = QThread()
            self.analysis_worker = AnalysisWorker(
                self.current_file,
                use_mvsep,
                getattr(self, 'mvsep_integration', None),
                getattr(self, 'mvsep_progress_widget', None)
            )
            self.analysis_worker.moveToThread(self.analysis_thread)

            # Connect signals
            self.analysis_thread.started.connect(self.analysis_worker.run)
            self.analysis_worker.finished.connect(self._on_analysis_completed)
            self.analysis_worker.progress.connect(self._on_analysis_progress)
            self.analysis_worker.error.connect(self._on_analysis_error)
            self.analysis_worker.finished.connect(self.analysis_thread.quit)
            self.analysis_worker.finished.connect(self.analysis_worker.deleteLater)
            self.analysis_thread.finished.connect(self.analysis_thread.deleteLater)

            # Show MVSep progress widget if using MVSep
            if use_mvsep and hasattr(self, 'mvsep_progress_widget') and self.mvsep_progress_widget:
                self.mvsep_progress_widget.clear_log()
                self.mvsep_progress_widget.setVisible(True)

            # Start analysis thread
            self.analysis_thread.start()

        except Exception as e:
            logger.error(f"Error starting analysis: {str(e)}")
            traceback.print_exc()
            self._on_analysis_error(f"Failed to start analysis: {str(e)}")

    def _on_analysis_progress(self, progress, message):
        """Handle progress updates from the analysis worker"""
        self.progress_bar.setValue(int(progress * 100))
        self.status_label.setText(message)

    def _on_mvsep_progress(self, progress, message):
        """Handle MVSep progress updates"""
        # MVSep progress is already displayed in the MVSep progress widget
        pass

    def _on_mvsep_status(self, status):
        """Handle MVSep status updates"""
        # Handle status updates from MVSep
        pass

    def _poll_mvsep_status(self):
        """Poll MVSep status (fallback method)"""
        # Polling method for MVSep status if signals are not available
        pass

    def _on_analysis_completed(self, results):
        """Handle analysis completed signal"""
        self.is_analyzing = False
        self.analysis_data = results

        # Update UI
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("Complete")
        self.status_label.setText("Analysis complete")
        self.analyze_button.setEnabled(True)

        # Hide MVSep progress widget
        if hasattr(self, 'mvsep_progress_widget') and self.mvsep_progress_widget:
            self.mvsep_progress_widget.setVisible(False)

        # Display results
        self._display_results(results)

        # Notify parent
        self.analysis_completed.emit(results)

        # Emit event to event bus if available
        if self.event_bus and hasattr(self.event_bus, "emit"):
            try:
                self.event_bus.emit("drum_analysis_completed", results)
            except Exception as e:
                logger.error(f"Failed to emit event to event bus: {e}")

    def _on_analysis_error(self, error_message):
        """Handle analysis error signal"""
        self.is_analyzing = False

        # Update UI
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Failed")
        self.status_label.setText(f"Error: {error_message}")
        self.analyze_button.setEnabled(True)

        # Hide MVSep progress widget
        if hasattr(self, 'mvsep_progress_widget') and self.mvsep_progress_widget:
            self.mvsep_progress_widget.setVisible(False)

        # Notify parent
        self.analysis_error.emit(error_message)

    def _on_analysis_started(self):
        """Handle analysis started signal"""
        # Update UI
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.status_label.setText("Analyzing...")
        self.analyze_button.setEnabled(False)

        # Clear previous results
        self.summary_text.clear()
        self.sections_text.clear()
        self.drum_text.clear()

    def _display_results(self, results):
        """Display analysis results in the UI"""
        # Update summary tab
        self._update_summary(results)

        # Update sections tab
        self._update_sections(results)

        # Update drum analysis tab
        self._update_drum_analysis(results)

        # Show results tabs
        self.results_tabs.setCurrentIndex(0)  # Show summary tab

    def _update_summary(self, results):
        """Update summary text with analysis results"""
        if not results:
            self.summary_text.setText("No results available")
            return

        html = "<h2>Musical Arrangement Analysis Summary</h2>"

        # File info
        file_path = self.current_file
        html += f"<p><b>File:</b> {os.path.basename(file_path)}</p>"

        # Overall statistics
        if "duration" in results:
            minutes = int(results["duration"] // 60)
            seconds = int(results["duration"] % 60)
            html += f"<p><b>Duration:</b> {minutes}:{seconds:02d}</p>"

        if "sections" in results:
            html += f"<p><b>Number of Sections:</b> {len(results['sections'])}</p>"

        if "overall_complexity" in results:
            complexity = results["overall_complexity"]
            html += f"<p><b>Overall Complexity:</b> {complexity:.2f}/10</p>"

        if "energy_profile" in results:
            energy = results["energy_profile"]
            html += f"<p><b>Energy Profile:</b> {energy:.2f}/10</p>"

        # Dominant drum approaches
        if "dominant_approaches" in results:
            html += "<h3>Dominant Drum Approaches</h3>"
            html += "<ul>"
            for approach, confidence in results["dominant_approaches"].items():
                html += f"<li><b>{approach}:</b> {confidence:.2f}</li>"
            html += "</ul>"

        self.summary_text.setHtml(html)

    def _update_sections(self, results):
        """Update sections text with analysis results"""
        if not results or "sections" not in results:
            self.sections_text.setText("No section data available")
            return

        sections = results["sections"]

        html = "<h2>Arrangement Structure</h2>"
        html += "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse: collapse;'>"
        html += "<tr><th>#</th><th>Type</th><th>Start</th><th>End</th><th>Duration</th><th>Energy</th><th>Complexity</th><th>Drum Approach</th></tr>"

        for i, section in enumerate(sections):
            section_type = section.get("type", "Unknown")
            start_time = section.get("start_time", 0)
            end_time = section.get("end_time", 0)
            duration = end_time - start_time
            energy = section.get("energy", 0)
            complexity = section.get("complexity", 0)
            approach = section.get("drum_approach", "Unknown")

            # Format times
            start_str = f"{int(start_time // 60)}:{int(start_time % 60):02d}"
            end_str = f"{int(end_time // 60)}:{int(end_time % 60):02d}"
            duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}"

            # Color code by section type
            color = "#FFFFFF"  # Default white
            if section_type == "INTRO":
                color = "#E6F2FF"  # Light blue
            elif section_type == "VERSE":
                color = "#E6FFEC"  # Light green
            elif section_type == "CHORUS":
                color = "#FFE6E6"  # Light red
            elif section_type == "BRIDGE":
                color = "#FFF3E6"  # Light orange
            elif section_type == "OUTRO":
                color = "#F2E6FF"  # Light purple

            html += f"<tr style='background-color: {color};'>"
            html += f"<td>{i+1}</td>"
            html += f"<td>{section_type}</td>"
            html += f"<td>{start_str}</td>"
            html += f"<td>{end_str}</td>"
            html += f"<td>{duration_str}</td>"
            html += f"<td>{energy:.2f}</td>"
            html += f"<td>{complexity:.2f}</td>"
            html += f"<td>{approach}</td>"
            html += "</tr>"

        html += "</table>"

        self.sections_text.setHtml(html)

    def _update_drum_analysis(self, results):
        """Update drum analysis text with analysis results"""
        if not results:
            self.drum_text.setText("No drum analysis data available")
            return

        html = "<h2>Drum Analysis Details</h2>"

        # Drum characteristics
        if "sections" in results:
            html += "<h3>Section-by-Section Drum Analysis</h3>"
            html += "<table border='1' cellspacing='0' cellpadding='5' style='border-collapse: collapse;'>"
            html += "<tr><th>Section</th><th>Approach</th><th>Fill Density</th><th>Onset Density</th><th>Rhythmic Complexity</th><th>Key Features</th></tr>"

            for i, section in enumerate(results["sections"]):
                section_type = section.get("type", "Unknown")
                approach = section.get("drum_approach", "Unknown")
                fill_density = section.get("fill_density", 0)
                onset_density = section.get("onset_density", 0)
                rhythmic_complexity = section.get("rhythmic_complexity", 0)

                # Generate key features text based on characteristics
                features = []
                if fill_density > 0.7:
                    features.append("Heavy drum fills")
                elif fill_density < 0.3:
                    features.append("Minimal fills")

                if onset_density > 0.7:
                    features.append("Dense percussion")
                elif onset_density < 0.3:
                    features.append("Sparse percussion")

                if rhythmic_complexity > 0.7:
                    features.append("Complex patterns")
                elif rhythmic_complexity < 0.3:
                    features.append("Simple patterns")

                if approach == "FOUR_ON_THE_FLOOR":
                    features.append("Steady kick drum")
                elif approach == "HALF_TIME":
                    features.append("Half-time feel")
                elif approach == "DOUBLE_TIME":
                    features.append("Fast, double-time feel")

                features_text = ", ".join(features) if features else "Standard drums"

                html += "<tr>"
                html += f"<td>{section_type} {i+1}</td>"
                html += f"<td>{approach}</td>"
                html += f"<td>{fill_density:.2f}</td>"
                html += f"<td>{onset_density:.2f}</td>"
                html += f"<td>{rhythmic_complexity:.2f}</td>"
                html += f"<td>{features_text}</td>"
                html += "</tr>"

            html += "</table>"

        # Overall drum characteristics
        html += "<h3>Overall Drum Characteristics</h3>"

        if "overall_complexity" in results:
            complexity = results["overall_complexity"]
            html += f"<p><b>Overall Complexity:</b> {complexity:.2f}/10</p>"

        if "energy_profile" in results:
            energy = results["energy_profile"]
            html += f"<p><b>Energy Profile:</b> {energy:.2f}/10</p>"

        if "onset_density_avg" in results:
            onset_density = results["onset_density_avg"]
            html += f"<p><b>Average Onset Density:</b> {onset_density:.2f}</p>"

        if "fill_density_avg" in results:
            fill_density = results["fill_density_avg"]
            html += f"<p><b>Average Fill Density:</b> {fill_density:.2f}</p>"

        self.drum_text.setHtml(html)


# For testing the widget directly
if __name__ == "__main__":
    app = QApplication(sys.argv)

    widget = MusicalArrangementAnalyzerWidget()
    widget.setWindowTitle("Musical Arrangement Analyzer Test")
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())
