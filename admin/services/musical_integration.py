"""
Musical Arrangement Analyzer Integration for DrumAnalysisWidget
==============================================================
This module provides integration between the DrumAnalysisWidget and the
Musical Arrangement Analyzer functionality.
"""
import logging
import os
import sys
import traceback
import types
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QTextEdit, QSplitter, QGroupBox, QMessageBox
)

# Configure logging
logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import librosa
    import numpy as np
    AUDIO_LIBS_AVAILABLE = True
    logger.info("Audio processing libraries available")
except ImportError:
    AUDIO_LIBS_AVAILABLE = False
    logger.warning("Audio processing libraries not available")

try:
    import torch
    if torch.cuda.is_available():
        GPU_AVAILABLE = True
        logger.info(f"GPU available: {torch.cuda.get_device_name(0)}")
    else:
        GPU_AVAILABLE = False
        logger.warning("CUDA not available")
except ImportError:
    GPU_AVAILABLE = False
    logger.warning("PyTorch not available")

# Path to the musical arrangement analyzer
DOCS_DIR = Path(__file__).parent.parent.parent / "docs" / "Drum_Analysis_Final"
if DOCS_DIR.exists():
    sys.path.append(str(DOCS_DIR))

# Try to import musical arrangement components
MUSICAL_ANALYZER_AVAILABLE = False
if GPU_AVAILABLE and AUDIO_LIBS_AVAILABLE:
    try:
        from musical_arrangement_analyzer import (
            # Core classes
            MusicalStructureDetector,
            SectionDrumAnalyzer,
            ArrangementAwareAnalyzer,
            ArrangementTrainingDataExtractor,
            
            # Data classes
            ArrangementAnalysis,
            SectionBoundary,
            DrumSectionAnalysis,
            
            # Enums
            SectionType,
            DrumApproach,
            
            # Functions
            calculate_arrangement_training_value
        )
        MUSICAL_ANALYZER_AVAILABLE = True
        logger.info("Musical Arrangement Analyzer imported successfully")
    except ImportError as e:
        MUSICAL_ANALYZER_AVAILABLE = False
        logger.error(f"Failed to import Musical Arrangement Analyzer: {e}")
        logger.error("GPU dependencies required for musical arrangement analysis are not available.")
        logger.error("Please ensure PyTorch with CUDA support is properly installed.")
else:
    logger.error("Musical Arrangement Analyzer requires GPU and audio libraries")

# Try to import UI components
try:
    from .drum_analyzer_factory import DrumAnalyzerUIFactory
    from .drum_analyzer_functions import DrumAnalyzerFunctions
    UI_COMPONENTS_AVAILABLE = True
    logger.info("UI components imported successfully")
except ImportError as e:
    UI_COMPONENTS_AVAILABLE = False
    logger.error(f"Failed to import UI components: {e}")


class MusicalArrangementIntegrator:
    """
    Bridge between the DrumAnalysisWidget and the Musical Arrangement Analyzer.
    Provides comprehensive integration with all features of the Musical Arrangement Analyzer.
    """

    def __init__(self, parent_widget=None):
        """Initialize the integrator with a reference to the parent widget."""
        self.parent_widget = parent_widget
        self.structure_detector = None
        self.section_analyzer = None
        self.arrangement_analyzer = None
        self.training_data_extractor = None
        self.initialized = False

        if MUSICAL_ANALYZER_AVAILABLE:
            try:
                self.structure_detector = MusicalStructureDetector()
                logger.info("Musical Structure Detector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Musical Structure Detector: {e}")

    def set_drum_analyzer(self, drum_analyzer):
        """Set the drum analyzer reference for all analyzer components."""
        if not MUSICAL_ANALYZER_AVAILABLE:
            logger.error("Cannot set drum analyzer: Musical analyzer not available")
            return False

        try:
            # Initialize section analyzer
            self.section_analyzer = SectionDrumAnalyzer(drum_analyzer)
            logger.info("Section analyzer initialized with drum analyzer")

            # Initialize arrangement analyzer
            self.arrangement_analyzer = ArrangementAwareAnalyzer(drum_analyzer)
            logger.info("Arrangement analyzer initialized with drum analyzer")

            # Initialize training data extractor
            self.training_data_extractor = ArrangementTrainingDataExtractor()
            logger.info("Training data extractor initialized")

            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"Failed to initialize analyzers: {e}")
            logger.error(traceback.format_exc())
            return False

    def check_integration_status(self):
        """Check if the integration is properly set up."""
        return {
            "musical_analyzer_available": MUSICAL_ANALYZER_AVAILABLE,
            "gpu_available": GPU_AVAILABLE,
            "audio_libs_available": AUDIO_LIBS_AVAILABLE,
            "ui_components_available": UI_COMPONENTS_AVAILABLE,
            "structure_detector_initialized": self.structure_detector is not None,
            "section_analyzer_initialized": self.section_analyzer is not None,
            "arrangement_analyzer_initialized": self.arrangement_analyzer is not None,
            "training_data_extractor_initialized": self.training_data_extractor is not None,
            "fully_initialized": self.initialized
        }

    def analyze_arrangement(
        self, 
        audio_file: str, 
        drum_stem_file: str = None,
        progress_callback: Callable = None
    ) -> Optional['ArrangementAnalysis']:
        """
        Analyze the musical arrangement of an audio file with comprehensive analysis.

        Args:
            audio_file: Path to the original mix audio file
            drum_stem_file: Optional path to isolated drum stem file
            progress_callback: Optional callback for progress updates

        Returns:
            ArrangementAnalysis object or None if analysis fails
        """
        if not MUSICAL_ANALYZER_AVAILABLE:
            logger.error("Musical Arrangement Analyzer not available")
            return None

        if not self.initialized:
            logger.error("Musical Arrangement Integrator not fully initialized")
            return None

        try:
            # Use the same file for both if drum stem not provided
            if drum_stem_file is None:
                logger.info("No drum stem provided, using original audio for all analysis")
                drum_stem_file = audio_file

            # Verify audio files exist
            if progress_callback:
                progress_callback(0.1, "Verifying audio files...")

            if not os.path.exists(audio_file):
                logger.error(f"Audio file does not exist: {audio_file}")
                return None

            if not os.path.exists(drum_stem_file):
                logger.warning(f"Drum stem file does not exist: {drum_stem_file}")
                logger.warning("Falling back to using original audio file")
                drum_stem_file = audio_file

            if progress_callback:
                progress_callback(0.15, "Starting comprehensive arrangement analysis...")

            # Use the ArrangementAwareAnalyzer for full analysis
            if self.arrangement_analyzer:
                if progress_callback:
                    progress_callback(0.2, "Performing arrangement-aware drum analysis...")

                try:
                    # Perform complete arrangement analysis
                    arrangement_analysis = self.arrangement_analyzer.analyze_complete_arrangement(
                        audio_file, drum_stem_file
                    )

                    if progress_callback:
                        progress_callback(0.95, "Finalizing analysis results...")

                    # Calculate training value
                    try:
                        training_value = calculate_arrangement_training_value(arrangement_analysis)
                        arrangement_analysis.training_value = training_value
                        logger.info(f"Calculated training value: {training_value:.3f}")
                    except Exception as te:
                        logger.error(f"Error calculating training value: {te}")

                    # Extract training features if available
                    if self.training_data_extractor:
                        try:
                            training_features = self.training_data_extractor.extract_arrangement_training_features(
                                arrangement_analysis
                            )
                            arrangement_analysis.training_features = training_features
                            logger.info("Added training features to arrangement analysis")
                        except Exception as ex:
                            logger.error(f"Error extracting training features: {ex}")

                    if progress_callback:
                        progress_callback(1.0, "Arrangement analysis complete")

                    return arrangement_analysis

                except Exception as e:
                    logger.error(f"Error in arrangement analysis: {e}")
                    logger.error("Attempting fallback analysis...")

                    # Try fallback analysis
                    try:
                        if progress_callback:
                            progress_callback(0.5, "Performing fallback analysis...")

                        fallback = self._create_fallback_analysis(audio_file, drum_stem_file)

                        if progress_callback:
                            progress_callback(1.0, "Fallback analysis complete")

                        return fallback
                    except Exception as fallback_error:
                        logger.error(f"Fallback analysis also failed: {fallback_error}")

            # If arrangement analyzer not available, use basic analysis
            return self._perform_basic_analysis(audio_file, drum_stem_file, progress_callback)

        except Exception as e:
            logger.error(f"Error in arrangement analysis: {e}")
            logger.error(traceback.format_exc())
            return None

    def _perform_basic_analysis(self, audio_file, drum_stem_file, progress_callback):
        """Perform basic analysis when full analyzer is not available"""
        if progress_callback:
            progress_callback(0.3, "Falling back to basic analysis...")

        try:
            # Load audio for basic analysis
            if AUDIO_LIBS_AVAILABLE:
                y, sr = librosa.load(audio_file, sr=None)
                duration = len(y) / sr
            else:
                # Estimate duration from file size (very rough)
                file_size = os.path.getsize(audio_file)
                duration = file_size / (44100 * 2 * 2)  # Rough estimate for 16-bit stereo

            # Create basic sections
            sections = self._create_basic_sections(duration)

            if progress_callback:
                progress_callback(0.8, "Creating basic arrangement analysis...")

            # Create minimal arrangement analysis
            arrangement = self._create_minimal_arrangement(sections)

            if progress_callback:
                progress_callback(1.0, "Basic arrangement analysis complete")

            return arrangement

        except Exception as e:
            logger.error(f"Error in basic analysis: {e}")
            return None

    def _create_basic_sections(self, duration):
        """Create basic sections when detection fails."""
        if not MUSICAL_ANALYZER_AVAILABLE:
            # Return simple dict-based sections
            return [
                {
                    "start_time": 0,
                    "end_time": duration * 0.25,
                    "section_type": "intro",
                    "confidence": 0.5
                },
                {
                    "start_time": duration * 0.25,
                    "end_time": duration * 0.75,
                    "section_type": "main",
                    "confidence": 0.5
                },
                {
                    "start_time": duration * 0.75,
                    "end_time": duration,
                    "section_type": "outro",
                    "confidence": 0.5
                }
            ]

        # Create proper SectionBoundary objects
        sections = [
            SectionBoundary(
                start_time=0,
                end_time=duration * 0.25,
                section_type=SectionType.INTRO,
                confidence=0.5,
                transition_type="standard"
            ),
            SectionBoundary(
                start_time=duration * 0.25,
                end_time=duration * 0.5,
                section_type=SectionType.VERSE,
                confidence=0.5,
                transition_type="standard"
            ),
            SectionBoundary(
                start_time=duration * 0.5,
                end_time=duration * 0.75,
                section_type=SectionType.CHORUS,
                confidence=0.5,
                transition_type="standard"
            ),
            SectionBoundary(
                start_time=duration * 0.75,
                end_time=duration,
                section_type=SectionType.OUTRO,
                confidence=0.5,
                transition_type="standard"
            )
        ]
        return sections

    def _create_minimal_arrangement(self, sections):
        """Create minimal arrangement analysis."""
        if not MUSICAL_ANALYZER_AVAILABLE:
            return {
                "sections": sections,
                "narrative": "Basic arrangement analysis without detailed drum analysis.",
                "overall_consistency": 0.5,
                "arrangement_quality": 0.5
            }

        # Create proper ArrangementAnalysis object
        section_analyses = []
        for section in sections:
            analysis = DrumSectionAnalysis(
                section=section,
                drum_approach=DrumApproach.FOUNDATIONAL,
                approach_confidence=0.5,
                rhythmic_density=0.5,
                complexity_level=0.5,
                dynamic_level=0.5,
                groove_stability=0.5,
                kick_pattern="basic pattern",
                snare_pattern="basic pattern",
                hi_hat_pattern="basic pattern",
                cymbal_usage="minimal",
                tom_usage="minimal",
                musical_role="supportive",
                section_entry="standard",
                section_exit="standard",
                hit_count=0,
                fill_count=0,
                accent_frequency=0.0,
                ghost_note_frequency=0.0,
                contextual_humanness=0.5,
                section_appropriate_timing=0.5,
                stylistic_authenticity=0.5
            )
            section_analyses.append(analysis)

        return ArrangementAnalysis(
            sections=sections,
            section_analyses=section_analyses,
            overall_consistency=0.5,
            arrangement_quality=0.5,
            narrative="Basic arrangement analysis with minimal drum analysis."
        )

    def _create_fallback_analysis(self, audio_file, drum_stem_file):
        """Create fallback analysis when main analysis fails."""
        try:
            # Load audio to get duration
            if AUDIO_LIBS_AVAILABLE:
                y, sr = librosa.load(audio_file, sr=None)
                duration = len(y) / sr
            else:
                # Estimate duration
                file_size = os.path.getsize(audio_file)
                duration = file_size / (44100 * 2 * 2)

            # Create basic sections
            sections = self._create_basic_sections(duration)

            # Create minimal arrangement
            return self._create_minimal_arrangement(sections)

        except Exception as e:
            logger.error(f"Error in fallback analysis: {e}")
            return None

    def analyze_sections_only(self, audio_file, progress_callback=None):
        """Perform section detection only (no drum analysis)."""
        if not MUSICAL_ANALYZER_AVAILABLE or not self.structure_detector:
            logger.error("Musical structure detector not available")
            return []

        try:
            if progress_callback:
                progress_callback(0.1, "Loading audio file...")

            # Load audio
            y, sr = librosa.load(audio_file, sr=None)

            if progress_callback:
                progress_callback(0.4, "Detecting musical structure...")

            # Detect sections
            sections = self.structure_detector.detect_sections(y, sr)

            if progress_callback:
                progress_callback(1.0, "Section detection complete")

            return sections
        except Exception as e:
            logger.error(f"Error in section detection: {e}")
            logger.error(traceback.format_exc())
            return []


def enhance_drum_analysis_widget(widget):
    """
    Enhance the DrumAnalysisWidget with comprehensive musical arrangement analysis capabilities.
    """
    logger.info("Enhancing DrumAnalysisWidget with comprehensive musical arrangement analysis")

    if not widget:
        logger.error("Cannot enhance widget: Widget is None")
        return False

    # Check if full support is available
    if not MUSICAL_ANALYZER_AVAILABLE:
        # Show a visible error in the widget
        error_label = QLabel("WARNING GPU required: Missing CUDA dependencies for musical arrangement analysis")
        error_label.setStyleSheet("background-color: #F8D7DA; color: #721C24; padding: 10px; border-radius: 3px; font-weight: bold;")
        error_label.setAlignment(Qt.AlignCenter)

        # Add to main layout if it exists
        if hasattr(widget, 'main_layout'):
            widget.main_layout.insertWidget(0, error_label)
            widget._error_notification = error_label

        # Display a one-time error message
        QMessageBox.critical(
            widget, "GPU Required",
            "Musical arrangement analysis requires GPU with CUDA support.\n\n"
            "The advanced drum analysis features will not be available.\n"
            "Please install PyTorch with CUDA support to enable these features."
        )

        logger.error("Musical Analyzer not available - GPU required")
        return False

    try:
        # Initialize the arrangement integrator
        widget._arrangement_integrator = MusicalArrangementIntegrator(widget)

        # Initialize the UI factory if available
        if UI_COMPONENTS_AVAILABLE:
            widget._ui_factory = DrumAnalyzerUIFactory(widget)
            logger.info("UI factory initialized")

        # Initialize the functions helper if available
        if UI_COMPONENTS_AVAILABLE:
            widget._analyzer_functions = DrumAnalyzerFunctions(
                arrangement_integrator=widget._arrangement_integrator
            )
            logger.info("Analyzer functions initialized")

        # Add arrangement analysis tab if we have result_tabs
        if hasattr(widget, 'result_tabs'):
            # Create arrangement analysis tab
            arrangement_tab = create_arrangement_tab(widget)
            tab_idx = widget.result_tabs.addTab(arrangement_tab, "Musical Arrangement")
            widget._arrangement_tab = arrangement_tab

            # Store widgets for later access
            widget._sections_table = arrangement_tab.findChild(QTableWidget, "sectionTable")
            widget._narrative_text = arrangement_tab.findChild(QTextEdit, "arrangementNarrative")

            logger.info(f"Added musical arrangement tab at index {tab_idx}")

        # Store the original analyze_file method
        original_analyze_file = widget.analyze_file

        # Define the new analyze_file method with arrangement analysis
        def analyze_file_with_arrangement(self, audio_file, use_mvsep=False, *args, **kwargs):
            """Analyze file with comprehensive arrangement analysis."""
            logger.info("Analyzing file with comprehensive arrangement analysis")

            # Call the original analyze_file method
            result = original_analyze_file(audio_file, use_mvsep, *args, **kwargs)

            # Now perform arrangement analysis if available
            try:
                if hasattr(self, "_drum_analyzer") and hasattr(self, "_arrangement_integrator"):
                    # Set drum analyzer reference
                    self._arrangement_integrator.set_drum_analyzer(self._drum_analyzer)

                    # Check if we have a separated drum stem from MVSep
                    drum_stem_file = None
                    if hasattr(self, "_separated_stems") and self._separated_stems:
                        if "drums" in self._separated_stems:
                            drum_stem_file = self._separated_stems["drums"]
                            logger.info(f"Using separated drum stem: {drum_stem_file}")

                    # Function to update progress in the status bar
                    def progress_callback(progress, message):
                        status_text = f"Arrangement analysis: {message} ({int(progress*100)}%)"
                        if hasattr(self, "update_status"):
                            self.update_status(status_text)
                        else:
                            logger.info(status_text)

                    # Update status
                    if hasattr(self, "update_status"):
                        self.update_status("Starting comprehensive musical arrangement analysis...")

                    # Perform arrangement analysis
                    arrangement = self._arrangement_integrator.analyze_arrangement(
                        audio_file,
                        drum_stem_file=drum_stem_file,
                        progress_callback=progress_callback
                    )

                    if arrangement:
                        logger.info("Comprehensive arrangement analysis complete, updating UI")
                        self._arrangement_analysis = arrangement

                        # Display the analysis in the UI
                        if hasattr(self, "_ui_factory") and UI_COMPONENTS_AVAILABLE:
                            # Use the comprehensive UI
                            self._ui_factory.display_arrangement_analysis(arrangement)
                        elif hasattr(self, "_sections_table") and hasattr(self, "_narrative_text"):
                            # Use simple display method
                            self.display_basic_arrangement_analysis(arrangement)

                        if hasattr(self, "update_status"):
                            self.update_status("Arrangement analysis complete")
                    else:
                        logger.warning("Arrangement analysis failed or not available")
                        if hasattr(self, "update_status"):
                            self.update_status("Arrangement analysis failed or not available")
                else:
                    logger.warning("Drum analyzer or arrangement integrator not available")
            except Exception as e:
                logger.error(f"Error in arrangement analysis: {e}")
                logger.error(traceback.format_exc())
                if hasattr(widget, "update_status"):
                    widget.update_status(f"Error in arrangement analysis: {str(e)[:50]}...")

            return result

        # Add method to widget for displaying basic arrangement analysis
        def display_basic_arrangement_analysis(self, analysis):
            """Display the arrangement analysis in the UI using basic components."""
            if not analysis:
                return

            logger.info("Displaying basic arrangement analysis in UI")

            try:
                # Update sections table
                if hasattr(self, "_sections_table"):
                    # Clear previous results
                    self._sections_table.setRowCount(0)

                    # Handle both dict and object formats
                    sections = analysis.get("sections", []) if isinstance(analysis, dict) else getattr(analysis, "sections", [])
                    section_analyses = analysis.get("section_analyses", []) if isinstance(analysis, dict) else getattr(analysis, "section_analyses", [])

                    # Display sections in table
                    for i, section in enumerate(sections):
                        row_position = self._sections_table.rowCount()
                        self._sections_table.insertRow(row_position)

                        # Get section data
                        if isinstance(section, dict):
                            start_time = section.get("start_time", 0)
                            end_time = section.get("end_time", 0)
                            section_type = section.get("section_type", "unknown")
                        else:
                            start_time = getattr(section, "start_time", 0)
                            end_time = getattr(section, "end_time", 0)
                            section_type = getattr(section, "section_type", "unknown")

                        # Format time as MM:SS
                        start_time_str = f"{int(start_time // 60):02d}:{int(start_time % 60):02d}"
                        end_time_str = f"{int(end_time // 60):02d}:{int(end_time % 60):02d}"

                        # Add data to table
                        self._sections_table.setItem(row_position, 0, QTableWidgetItem(start_time_str))
                        self._sections_table.setItem(row_position, 1, QTableWidgetItem(end_time_str))

                        # Get section type as string
                        if hasattr(section_type, 'value'):
                            section_type_str = section_type.value
                        else:
                            section_type_str = str(section_type)
                        self._sections_table.setItem(row_position, 2, QTableWidgetItem(section_type_str))

                        # Add analysis data if available
                        if i < len(section_analyses):
                            section_analysis = section_analyses[i]
                            if isinstance(section_analysis, dict):
                                drum_approach = section_analysis.get("drum_approach", "unknown")
                                density = section_analysis.get("rhythmic_density", 0.5)
                                complexity = section_analysis.get("complexity_level", 0.5)
                            else:
                                drum_approach = getattr(section_analysis, "drum_approach", "unknown")
                                density = getattr(section_analysis, "rhythmic_density", 0.5)
                                complexity = getattr(section_analysis, "complexity_level", 0.5)

                            # Format drum approach
                            if hasattr(drum_approach, 'value'):
                                drum_approach_str = drum_approach.value
                            else:
                                drum_approach_str = str(drum_approach)
                            
                            self._sections_table.setItem(row_position, 3, QTableWidgetItem(drum_approach_str))
                            
                            # Add metrics
                            metrics = f"D: {density:.2f}, C: {complexity:.2f}"
                            self._sections_table.setItem(row_position, 4, QTableWidgetItem(metrics))
                        else:
                            self._sections_table.setItem(row_position, 3, QTableWidgetItem("N/A"))
                            self._sections_table.setItem(row_position, 4, QTableWidgetItem("N/A"))

                # Update narrative text
                if hasattr(self, "_narrative_text"):
                    narrative = analysis.get("narrative", "No narrative available") if isinstance(analysis, dict) else getattr(analysis, "narrative", "No narrative available")
                    self._narrative_text.setText(narrative)

                # Show the arrangement tab
                if hasattr(self, "result_tabs"):
                    for i in range(self.result_tabs.count()):
                        if self.result_tabs.tabText(i) == "Musical Arrangement":
                            self.result_tabs.setCurrentIndex(i)
                            break
            except Exception as e:
                logger.error(f"Error displaying arrangement analysis: {e}")
                logger.error(traceback.format_exc())

        # Replace the original analyze_file method
        widget.analyze_file = types.MethodType(analyze_file_with_arrangement, widget)

        # Add display method
        widget.display_basic_arrangement_analysis = types.MethodType(display_basic_arrangement_analysis, widget)

        # Add attributes for arrangement analysis data
        widget._arrangement_analysis = None

        logger.info("DrumAnalysisWidget successfully enhanced with comprehensive arrangement analysis")

        return True

    except Exception as e:
        logger.error(f"Error enhancing DrumAnalysisWidget: {e}")
        logger.error(traceback.format_exc())
        return False


def create_arrangement_tab(parent):
    """Create the musical arrangement analysis tab."""
    try:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Add header
        header_label = QLabel("Musical Arrangement Analysis")
        header_font = header_label.font()
        header_font.setBold(True)
        header_font.setPointSize(12)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # Create splitter for sections table and narrative
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter, 1)

        # Create sections table
        sections_group = QGroupBox("Song Sections")
        sections_layout = QVBoxLayout(sections_group)

        section_table = QTableWidget()
        section_table.setObjectName("sectionTable")
        section_table.setColumnCount(5)
        section_table.setHorizontalHeaderLabels([
            "Start", "End", "Section", "Drum Approach", "Metrics"
        ])
        section_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        sections_layout.addWidget(section_table)

        # Add sections group to splitter
        splitter.addWidget(sections_group)

        # Create narrative section
        narrative_group = QGroupBox("Arrangement Analysis")
        narrative_layout = QVBoxLayout(narrative_group)

        arrangement_narrative = QTextEdit()
        arrangement_narrative.setObjectName("arrangementNarrative")
        arrangement_narrative.setReadOnly(True)
        narrative_layout.addWidget(arrangement_narrative)

        # Add narrative group to splitter
        splitter.addWidget(narrative_group)

        # Set initial splitter sizes
        splitter.setSizes([300, 200])

        return tab

    except Exception as e:
        logger.error(f"Error creating arrangement tab: {e}")
        logger.error(traceback.format_exc())
        return QWidget()  # Return empty widget if creation failed


def initialize():
    """Initialize the module and ensure the musical arrangement analyzer is available."""
    if MUSICAL_ANALYZER_AVAILABLE:
        logger.info("Musical Arrangement Integration module initialized successfully")
        return True
    else:
        logger.warning("Musical Arrangement Analyzer is not available. Some features will be disabled.")
        return False


# Run initialization when module is imported
initialize()
