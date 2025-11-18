"""
UI Integration Handler for DrumTracKAI Complete System
Connects batch processor completion to complete analysis workflow
"""

import os
import logging
from typing import Dict, Optional, Any
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QTimer
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QProgressBar, QTextEdit, QTabWidget,
                               QWidget, QScrollArea, QFrame, QMessageBox)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from ..services.batch_complete_integration import get_batch_complete_integration
from ..services.enhanced_complete_visualization import get_enhanced_complete_visualization

logger = logging.getLogger(__name__)

class CompleteAnalysisResultDialog(QDialog):
    """Dialog to display complete analysis results"""
    
    def __init__(self, source_file: str, analysis_results: Dict, parent=None):
        super().__init__(parent)
        self.source_file = source_file
        self.analysis_results = analysis_results
        self.setWindowTitle(f"Complete Analysis Results - {Path(source_file).stem}")
        self.setModal(False)
        self.resize(1200, 800)
        
        self._setup_ui()
        self._populate_results()
    
    def _setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout(self)
        
        # Header
        header_frame = QFrame()
        header_frame.setFrameStyle(QFrame.StyledPanel)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title_label = QLabel(f"DRUM Complete Analysis Results")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Source file info
        source_label = QLabel(f"Source: {Path(self.source_file).name}")
        source_label.setStyleSheet("color: #666; font-style: italic;")
        header_layout.addWidget(source_label)
        
        layout.addWidget(header_frame)
        
        # Tab widget for different result views
        self.tab_widget = QTabWidget()
        
        # Summary tab
        self.summary_tab = self._create_summary_tab()
        self.tab_widget.addTab(self.summary_tab, "ANALYSIS Summary")
        
        # Detailed results tab
        self.details_tab = self._create_details_tab()
        self.tab_widget.addTab(self.details_tab, " Detailed Results")
        
        # Visualization tab
        self.viz_tab = self._create_visualization_tab()
        self.tab_widget.addTab(self.viz_tab, "PROGRESS Visualization")
        
        # Raw data tab
        self.raw_tab = self._create_raw_data_tab()
        self.tab_widget.addTab(self.raw_tab, "TOOL Raw Data")
        
        layout.addWidget(self.tab_widget)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton(" Save Results")
        save_btn.clicked.connect(self._save_results)
        button_layout.addWidget(save_btn)
        
        export_btn = QPushButton(" Export Visualization")
        export_btn.clicked.connect(self._export_visualization)
        button_layout.addWidget(export_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton(" Close")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_summary_tab(self) -> QWidget:
        """Create summary tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Scroll area for summary content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        
        # Summary content will be populated later
        self.summary_content = QLabel("Loading summary...")
        self.summary_content.setWordWrap(True)
        self.summary_content.setAlignment(Qt.AlignTop)
        summary_layout.addWidget(self.summary_content)
        
        summary_layout.addStretch()
        scroll.setWidget(summary_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_details_tab(self) -> QWidget:
        """Create detailed results tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Text area for detailed results
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setFont(QFont("Consolas", 10))
        layout.addWidget(self.details_text)
        
        return widget
    
    def _create_visualization_tab(self) -> QWidget:
        """Create visualization tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Placeholder for matplotlib canvas
        self.viz_canvas = None
        self.viz_placeholder = QLabel("Generating visualization...")
        self.viz_placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.viz_placeholder)
        
        return widget
    
    def _create_raw_data_tab(self) -> QWidget:
        """Create raw data tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Text area for raw JSON data
        self.raw_text = QTextEdit()
        self.raw_text.setReadOnly(True)
        self.raw_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.raw_text)
        
        return widget
    
    def _populate_results(self):
        """Populate the dialog with analysis results"""
        try:
            # Populate summary
            self._populate_summary()
            
            # Populate detailed results
            self._populate_details()
            
            # Populate raw data
            self._populate_raw_data()
            
            # Generate and display visualization
            self._generate_visualization()
            
        except Exception as e:
            logger.error(f"Error populating results: {e}")
            self.summary_content.setText(f"Error loading results: {str(e)}")
    
    def _populate_summary(self):
        """Populate summary tab"""
        try:
            # Extract key metrics from analysis results
            tempo_profile = self.analysis_results.get('tempo_profile', {})
            groove_metrics = self.analysis_results.get('groove_metrics', {})
            rhythm_hierarchy = self.analysis_results.get('rhythm_hierarchy', {})
            neural_entrainment = self.analysis_results.get('neural_entrainment', {})
            
            summary_html = f"""
            <h2>AUDIO Analysis Summary</h2>
            
            <h3>⏱ Tempo Analysis</h3>
            <ul>
                <li><b>Average Tempo:</b> {tempo_profile.get('average_tempo', 'N/A')} BPM</li>
                <li><b>Tempo Stability:</b> {tempo_profile.get('tempo_stability', 'N/A'):.3f}</li>
                <li><b>Tempo Variations:</b> {tempo_profile.get('tempo_variations', 'N/A')}</li>
            </ul>
            
            <h3>TARGET Groove Metrics</h3>
            <ul>
                <li><b>Overall Groove Score:</b> {groove_metrics.get('overall_groove_score', 'N/A'):.3f}</li>
                <li><b>Timing Tightness:</b> {groove_metrics.get('timing_tightness', 'N/A'):.3f}</li>
                <li><b>Dynamic Consistency:</b> {groove_metrics.get('dynamic_consistency', 'N/A'):.3f}</li>
                <li><b>Attack Consistency:</b> {groove_metrics.get('attack_consistency', 'N/A'):.3f}</li>
            </ul>
            
            <h3>MUSIC Rhythm Characteristics</h3>
            <ul>
                <li><b>Complexity Score:</b> {rhythm_hierarchy.get('complexity_score', 'N/A'):.3f}</li>
                <li><b>Syncopation Score:</b> {rhythm_hierarchy.get('syncopation_score', 'N/A'):.3f}</li>
                <li><b>Hierarchical Depth:</b> {rhythm_hierarchy.get('hierarchical_depth', 'N/A')}</li>
            </ul>
            
            <h3> Neural Entrainment</h3>
            <ul>
                <li><b>Flow State Compatibility:</b> {neural_entrainment.get('flow_state_compatibility', 'N/A'):.3f}</li>
                <li><b>Groove Induction Potential:</b> {neural_entrainment.get('groove_induction_potential', 'N/A'):.3f}</li>
                <li><b>Phase Coherence:</b> {neural_entrainment.get('phase_coherence', 'N/A'):.3f}</li>
            </ul>
            
            <h3>PROGRESS Analysis Statistics</h3>
            <ul>
                <li><b>Total Hits Analyzed:</b> {self.analysis_results.get('total_hits', 'N/A')}</li>
                <li><b>Analysis Duration:</b> {self.analysis_results.get('analysis_duration', 'N/A')} seconds</li>
                <li><b>Processing Method:</b> {self.analysis_results.get('processing_method', 'Complete Integrated System')}</li>
            </ul>
            """
            
            self.summary_content.setText(summary_html)
            
        except Exception as e:
            logger.error(f"Error populating summary: {e}")
            self.summary_content.setText(f"Error generating summary: {str(e)}")
    
    def _populate_details(self):
        """Populate detailed results tab"""
        try:
            details_text = "=== COMPLETE DRUMMER ANALYSIS RESULTS ===\n\n"
            
            for section, data in self.analysis_results.items():
                details_text += f"[{section.upper()}]\n"
                if isinstance(data, dict):
                    for key, value in data.items():
                        details_text += f"  {key}: {value}\n"
                else:
                    details_text += f"  {data}\n"
                details_text += "\n"
            
            self.details_text.setPlainText(details_text)
            
        except Exception as e:
            logger.error(f"Error populating details: {e}")
            self.details_text.setPlainText(f"Error loading detailed results: {str(e)}")
    
    def _populate_raw_data(self):
        """Populate raw data tab"""
        try:
            import json
            raw_json = json.dumps(self.analysis_results, indent=2, default=str)
            self.raw_text.setPlainText(raw_json)
            
        except Exception as e:
            logger.error(f"Error populating raw data: {e}")
            self.raw_text.setPlainText(f"Error loading raw data: {str(e)}")
    
    def _generate_visualization(self):
        """Generate and display visualization"""
        try:
            viz_service = get_enhanced_complete_visualization()
            figure = viz_service.create_complete_analysis_visualization(self.analysis_results)
            
            if figure:
                # Remove placeholder
                self.viz_placeholder.setParent(None)
                
                # Add matplotlib canvas
                self.viz_canvas = FigureCanvas(figure)
                self.viz_tab.layout().addWidget(self.viz_canvas)
                
                logger.info("Visualization generated and displayed")
            else:
                self.viz_placeholder.setText("Failed to generate visualization")
                
        except Exception as e:
            logger.error(f"Error generating visualization: {e}")
            self.viz_placeholder.setText(f"Visualization error: {str(e)}")
    
    def _save_results(self):
        """Save analysis results to file"""
        try:
            from PySide6.QtWidgets import QFileDialog
            import json
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Analysis Results", 
                f"{Path(self.source_file).stem}_analysis.json",
                "JSON Files (*.json)"
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    json.dump(self.analysis_results, f, indent=2, default=str)
                
                QMessageBox.information(self, "Success", f"Results saved to:\n{file_path}")
                
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            QMessageBox.critical(self, "Error", f"Failed to save results:\n{str(e)}")
    
    def _export_visualization(self):
        """Export visualization to image file"""
        try:
            if not self.viz_canvas:
                QMessageBox.warning(self, "Warning", "No visualization available to export")
                return
            
            from PySide6.QtWidgets import QFileDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Export Visualization", 
                f"{Path(self.source_file).stem}_visualization.png",
                "PNG Files (*.png);;PDF Files (*.pdf);;SVG Files (*.svg)"
            )
            
            if file_path:
                self.viz_canvas.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Success", f"Visualization exported to:\n{file_path}")
                
        except Exception as e:
            logger.error(f"Error exporting visualization: {e}")
            QMessageBox.critical(self, "Error", f"Failed to export visualization:\n{str(e)}")


class CompleteSystemIntegrationHandler(QObject):
    """Handles integration between batch processor and complete system"""
    
    # Signals
    analysis_dialog_requested = Signal(str, dict)  # source_file, results
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.integration_service = None
        self.active_dialogs = {}
        
    def initialize(self) -> bool:
        """Initialize the integration handler"""
        try:
            # Get integration service
            self.integration_service = get_batch_complete_integration()
            
            # Connect signals
            self.integration_service.analysis_completed.connect(self._on_analysis_completed)
            self.integration_service.analysis_failed.connect(self._on_analysis_failed)
            self.integration_service.visualization_ready.connect(self._on_visualization_ready)
            
            # Initialize the service
            if not self.integration_service.initialize():
                logger.error("Failed to initialize integration service")
                return False
            
            logger.info("Complete system integration handler initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize integration handler: {e}")
            return False
    
    def handle_mvsep_completion(self, mvsep_result: Dict):
        """Handle MVSep completion by triggering complete analysis"""
        try:
            if not self.integration_service:
                logger.error("Integration service not available")
                return False
            
            # Process through complete system
            success = self.integration_service.process_mvsep_output(mvsep_result)
            
            if success:
                logger.info(f"Triggered complete analysis for: {mvsep_result.get('source_file')}")
            else:
                logger.error("Failed to trigger complete analysis")
            
            return success
            
        except Exception as e:
            logger.error(f"Error handling MVSep completion: {e}")
            return False
    
    def _on_analysis_completed(self, source_file: str, analysis_results: Dict):
        """Handle analysis completion"""
        try:
            logger.info(f"Complete analysis finished for: {source_file}")
            
            # Show results dialog
            self._show_results_dialog(source_file, analysis_results)
            
            # Emit signal for other components
            self.analysis_dialog_requested.emit(source_file, analysis_results)
            
        except Exception as e:
            logger.error(f"Error handling analysis completion: {e}")
    
    def _on_analysis_failed(self, source_file: str, error_message: str):
        """Handle analysis failure"""
        try:
            logger.error(f"Complete analysis failed for {source_file}: {error_message}")
            
            # Show error dialog
            QMessageBox.critical(
                None, "Analysis Failed",
                f"Complete analysis failed for:\n{Path(source_file).name}\n\nError: {error_message}"
            )
            
        except Exception as e:
            logger.error(f"Error handling analysis failure: {e}")
    
    def _on_visualization_ready(self, source_file: str, figure):
        """Handle visualization ready"""
        try:
            logger.info(f"Visualization ready for: {source_file}")
            
            # Update existing dialog if open
            if source_file in self.active_dialogs:
                dialog = self.active_dialogs[source_file]
                if dialog and not dialog.viz_canvas:
                    # Add visualization to existing dialog
                    dialog.viz_canvas = FigureCanvas(figure)
                    dialog.viz_tab.layout().addWidget(dialog.viz_canvas)
                    dialog.viz_placeholder.setParent(None)
            
        except Exception as e:
            logger.error(f"Error handling visualization ready: {e}")
    
    def _show_results_dialog(self, source_file: str, analysis_results: Dict):
        """Show complete analysis results dialog"""
        try:
            # Close existing dialog if open
            if source_file in self.active_dialogs:
                old_dialog = self.active_dialogs[source_file]
                if old_dialog:
                    old_dialog.close()
            
            # Create new dialog
            dialog = CompleteAnalysisResultDialog(source_file, analysis_results)
            self.active_dialogs[source_file] = dialog
            
            # Show dialog
            dialog.show()
            dialog.raise_()
            dialog.activateWindow()
            
            logger.info(f"Displayed results dialog for: {source_file}")
            
        except Exception as e:
            logger.error(f"Error showing results dialog: {e}")
    
    def get_analysis_results(self, source_file: str) -> Optional[Dict]:
        """Get analysis results for a source file"""
        try:
            if self.integration_service:
                return self.integration_service.get_analysis_results(source_file)
            return None
            
        except Exception as e:
            logger.error(f"Error getting analysis results: {e}")
            return None
    
    def shutdown(self):
        """Shutdown the integration handler"""
        try:
            # Close all active dialogs
            for dialog in self.active_dialogs.values():
                if dialog:
                    dialog.close()
            self.active_dialogs.clear()
            
            # Shutdown integration service
            if self.integration_service:
                self.integration_service.shutdown()
            
            logger.info("Complete system integration handler shutdown")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global handler instance
_integration_handler = None

def get_complete_system_integration_handler() -> CompleteSystemIntegrationHandler:
    """Get the global complete system integration handler"""
    global _integration_handler
    if _integration_handler is None:
        _integration_handler = CompleteSystemIntegrationHandler()
    return _integration_handler

def initialize_complete_system_integration() -> bool:
    """Initialize the global complete system integration"""
    handler = get_complete_system_integration_handler()
    return handler.initialize()
