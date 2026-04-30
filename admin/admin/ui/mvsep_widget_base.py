"""
MVSep Widget Base
===============
Base class for the MVSep Widget that implements the UI layout
"""

import os
import logging
from typing import Dict, Optional, List
from pathlib import Path

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QProgressBar, QFileDialog, QGroupBox,
    QTextEdit, QCheckBox, QSplitter, QScrollArea
)

logger = logging.getLogger(__name__)

class MVSepWidgetBase(QWidget):
    """
    Base class for MVSep widget that handles UI setup
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup UI
        self._setup_ui()
        
    def _setup_ui(self):
        """Set up the user interface"""
        main_layout = QVBoxLayout(self)
        
        # Input section
        input_group = QGroupBox("Input")
        input_layout = QVBoxLayout(input_group)
        
        file_layout = QHBoxLayout()
        file_label = QLabel("Audio File:")
        self.file_path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_path_input, 1)
        file_layout.addWidget(browse_button)
        
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Dir:")
        self.output_dir_input = QLineEdit()
        output_browse_button = QPushButton("Browse")
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir_input, 1)
        output_layout.addWidget(output_browse_button)
        
        api_layout = QHBoxLayout()
        api_label = QLabel("API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter MVSep API key")
        api_layout.addWidget(api_label)
        api_layout.addWidget(self.api_key_input, 1)
        
        input_layout.addLayout(file_layout)
        input_layout.addLayout(output_layout)
        input_layout.addLayout(api_layout)
        
        # Options section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        
        self.keep_original_mix = QCheckBox("Keep Original Mix")
        self.keep_original_mix.setChecked(True)
        
        self.keep_drum_stem = QCheckBox("Keep Drum Stem")
        self.keep_drum_stem.setChecked(True)
        
        options_layout.addWidget(self.keep_original_mix)
        options_layout.addWidget(self.keep_drum_stem)
        
        # Button section
        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Processing")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        
        # Progress section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.detailed_status = QLabel("")
        
        progress_layout.addWidget(self.status_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.detailed_status)
        
        # Results section
        results_group = QGroupBox("Results")
        results_layout = QVBoxLayout(results_group)
        
        self.results_label = QLabel("No results available")
        self.results_label.setWordWrap(True)
        self.results_label.setTextFormat(Qt.RichText)
        
        results_scroll = QScrollArea()
        results_scroll.setWidget(self.results_label)
        results_scroll.setWidgetResizable(True)
        
        results_layout.addWidget(results_scroll)
        
        # Log section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(self.log_text)
        
        # Add all sections to main layout
        main_layout.addWidget(input_group)
        main_layout.addWidget(options_group)
        main_layout.addLayout(button_layout)
        main_layout.addWidget(progress_group)
        main_layout.addWidget(results_group)
        main_layout.addWidget(log_group)
        
        # Connect signals
        browse_button.clicked.connect(self._on_browse_file)
        output_browse_button.clicked.connect(self._on_browse_output)
        self.start_button.clicked.connect(self._on_start_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        
    def _on_browse_file(self):
        """Handle browse button click for input file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Audio File", "", "Audio Files (*.mp3 *.wav *.flac *.ogg *.m4a);;All Files (*.*)"
        )
        
        if file_path:
            self.file_path_input.setText(file_path)
            
            # Suggest output directory based on input file
            input_dir = os.path.dirname(file_path)
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            output_dir = os.path.join(input_dir, f"{file_name}_stems")
            
            self.output_dir_input.setText(output_dir)
            
    def _on_browse_output(self):
        """Handle browse button click for output directory"""
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", ""
        )
        
        if output_dir:
            self.output_dir_input.setText(output_dir)
    
    # These methods should be implemented by subclasses
    def _on_start_clicked(self):
        """Handle start button click (to be implemented by subclass)"""
        pass
        
    def _on_cancel_clicked(self):
        """Handle cancel button click (to be implemented by subclass)"""
        pass
