"""
Professional Drum Creation Widget
=================================
Advanced drum creation interface integrating Professional WebDAW tools
with the DrumTracKAI admin system for comprehensive drum pattern generation,
editing, and management.
"""
import logging
import os
import json
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal, Slot, QSize, QTimer, QThread, pyqtSignal
from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QProgressBar, QComboBox, QLineEdit, QGroupBox,
    QSplitter, QListWidget, QListWidgetItem, QSlider, QSpinBox,
    QCheckBox, QTabWidget, QTextEdit, QFrame, QGridLayout,
    QScrollArea, QButtonGroup, QRadioButton, QDial, QSizePolicy
)

from admin.services.central_database_service import get_database_service
from admin.utils.thread_safe_ui_updater import ThreadSafeUIUpdater

logger = logging.getLogger(__name__)

class DrumCreationWidget(QWidget):
    """Main drum creation widget integrating Professional WebDAW tools"""
    
    # Signals
    pattern_created = Signal(dict)
    pattern_exported = Signal(str, dict)
    initialization_completed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DrumCreationWidget")
        
        # Initialize state
        self.current_pattern = None
        self.patterns = []
        self.thread_safe_updater = ThreadSafeUIUpdater()
        
        # Services
        self.db_service = get_database_service()
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        
        # Load existing patterns
        self._load_patterns()
        
        logger.info("DrumCreationWidget initialized")
        self.initialization_completed.emit("DrumCreationWidget")
    
    def _setup_ui(self):
        """Set up the user interface"""
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # Header section
            header_layout = QHBoxLayout()
            self.title_label = QLabel("🎵 Professional Drum Creation Studio")
            self.title_label.setStyleSheet("""
                font-size: 20px; 
                font-weight: bold; 
                color: #2E86AB;
                padding: 10px;
            """)
            header_layout.addWidget(self.title_label)
            header_layout.addStretch()
            
            # Quick actions
            self.new_pattern_btn = QPushButton("🆕 New Pattern")
            self.new_pattern_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2E86AB;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1F5F7A;
                }
            """)
            header_layout.addWidget(self.new_pattern_btn)
            
            self.webdaw_btn = QPushButton("🎛️ Open Professional WebDAW")
            self.webdaw_btn.setStyleSheet("""
                QPushButton {
                    background-color: #A23B72;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #7A2B54;
                }
            """)
            header_layout.addWidget(self.webdaw_btn)
            
            main_layout.addLayout(header_layout)
            
            # Main content
            content_widget = self._create_main_content()
            main_layout.addWidget(content_widget)
            
            # Status bar
            status_layout = QHBoxLayout()
            self.status_label = QLabel("Ready for drum creation")
            self.status_label.setStyleSheet("color: #666666; font-style: italic;")
            status_layout.addWidget(self.status_label)
            status_layout.addStretch()
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setMaximumWidth(200)
            status_layout.addWidget(self.progress_bar)
            
            main_layout.addLayout(status_layout)
            
        except Exception as e:
            logger.error(f"Error setting up UI: {e}")
            traceback.print_exc()
    
    def _create_main_content(self):
        """Create the main content area"""
        tabs = QTabWidget()
        
        # Pattern Library Tab
        library_tab = self._create_pattern_library_tab()
        tabs.addTab(library_tab, "Pattern Library")
        
        # Drum Studio Tab
        studio_tab = self._create_drum_studio_tab()
        tabs.addTab(studio_tab, "Drum Studio")
        
        # WebDAW Integration Tab
        webdaw_tab = self._create_webdaw_integration_tab()
        tabs.addTab(webdaw_tab, "WebDAW Integration")
        
        return tabs
    
    def _create_pattern_library_tab(self):
        """Create the pattern library tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Search and filter
        search_layout = QHBoxLayout()
        self.pattern_search = QLineEdit()
        self.pattern_search.setPlaceholderText("Search patterns...")
        search_layout.addWidget(self.pattern_search)
        
        self.pattern_filter = QComboBox()
        self.pattern_filter.addItems(["All", "Rock", "Jazz", "Funk", "Electronic", "Recent"])
        search_layout.addWidget(self.pattern_filter)
        
        layout.addLayout(search_layout)
        
        # Patterns list
        self.patterns_list = QListWidget()
        self.patterns_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: #fafafa;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eeeeee;
            }
            QListWidget::item:selected {
                background-color: #2E86AB;
                color: white;
            }
        """)
        layout.addWidget(self.patterns_list)
        
        # Pattern actions
        actions_layout = QHBoxLayout()
        self.play_pattern_btn = QPushButton("▶️ Play")
        self.edit_pattern_btn = QPushButton("✏️ Edit")
        self.export_pattern_btn = QPushButton("💾 Export")
        self.delete_pattern_btn = QPushButton("🗑️ Delete")
        
        for btn in [self.play_pattern_btn, self.edit_pattern_btn, 
                   self.export_pattern_btn, self.delete_pattern_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    padding: 6px 12px;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    background-color: white;
                }
                QPushButton:hover {
                    background-color: #f0f0f0;
                }
            """)
            actions_layout.addWidget(btn)
        
        layout.addLayout(actions_layout)
        return widget
    
    def _create_drum_studio_tab(self):
        """Create the drum studio tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Studio controls
        controls_group = QGroupBox("Drum Studio Controls")
        controls_layout = QGridLayout(controls_group)
        
        # Style selection
        controls_layout.addWidget(QLabel("Style:"), 0, 0)
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Rock", "Jazz", "Funk", "Latin", "Electronic", "Metal"])
        controls_layout.addWidget(self.style_combo, 0, 1)
        
        # BPM control
        controls_layout.addWidget(QLabel("BPM:"), 0, 2)
        self.bpm_spin = QSpinBox()
        self.bpm_spin.setRange(60, 200)
        self.bpm_spin.setValue(120)
        controls_layout.addWidget(self.bpm_spin, 0, 3)
        
        # Complexity slider
        controls_layout.addWidget(QLabel("Complexity:"), 1, 0)
        self.complexity_slider = QSlider(Qt.Horizontal)
        self.complexity_slider.setRange(1, 100)
        self.complexity_slider.setValue(50)
        controls_layout.addWidget(self.complexity_slider, 1, 1, 1, 2)
        self.complexity_label = QLabel("50")
        controls_layout.addWidget(self.complexity_label, 1, 3)
        
        # Generate button
        self.generate_btn = QPushButton("🎵 Generate Pattern")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E86AB;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1F5F7A;
            }
        """)
        controls_layout.addWidget(self.generate_btn, 2, 0, 1, 4)
        
        layout.addWidget(controls_group)
        
        # Pattern visualization
        pattern_group = QGroupBox("Pattern Visualization")
        pattern_layout = QVBoxLayout(pattern_group)
        
        self.pattern_display = QTextEdit()
        self.pattern_display.setReadOnly(True)
        self.pattern_display.setMaximumHeight(200)
        self.pattern_display.setPlainText("Generate a pattern to see visualization...")
        pattern_layout.addWidget(self.pattern_display)
        
        layout.addWidget(pattern_group)
        return widget
    
    def _create_webdaw_integration_tab(self):
        """Create the WebDAW integration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Integration info
        info_label = QLabel("""
        <h3>Professional WebDAW Integration</h3>
        <p>Connect your drum patterns with the Professional WebDAW for advanced editing and mixing.</p>
        <ul>
        <li>🎛️ Professional mixer with multi-track controls</li>
        <li>📊 Real-time level meters and visualization</li>
        <li>🎵 Advanced pattern editing and arrangement</li>
        <li>🔧 Professional effects and processing</li>
        </ul>
        """)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # WebDAW controls
        webdaw_group = QGroupBox("WebDAW Controls")
        webdaw_layout = QVBoxLayout(webdaw_group)
        
        # Launch buttons
        buttons_layout = QHBoxLayout()
        
        launch_webdaw_btn = QPushButton("🚀 Launch Professional WebDAW")
        launch_webdaw_btn.setStyleSheet("""
            QPushButton {
                background-color: #2E86AB;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1F5F7A;
            }
        """)
        buttons_layout.addWidget(launch_webdaw_btn)
        
        sync_patterns_btn = QPushButton("🔄 Sync Patterns")
        sync_patterns_btn.setStyleSheet("""
            QPushButton {
                background-color: #A23B72;
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #7A2B54;
            }
        """)
        buttons_layout.addWidget(sync_patterns_btn)
        
        webdaw_layout.addLayout(buttons_layout)
        layout.addWidget(webdaw_group)
        
        layout.addStretch()
        return widget
    
    def _connect_signals(self):
        """Connect UI signals to slots"""
        try:
            # Button connections
            self.new_pattern_btn.clicked.connect(self._on_new_pattern)
            self.webdaw_btn.clicked.connect(self._on_open_webdaw)
            self.play_pattern_btn.clicked.connect(self._on_play_pattern)
            self.edit_pattern_btn.clicked.connect(self._on_edit_pattern)
            self.export_pattern_btn.clicked.connect(self._on_export_pattern)
            self.delete_pattern_btn.clicked.connect(self._on_delete_pattern)
            self.generate_btn.clicked.connect(self._on_generate_pattern)
            
            # List selection
            self.patterns_list.itemSelectionChanged.connect(self._on_pattern_selected)
            
            # Slider updates
            self.complexity_slider.valueChanged.connect(
                lambda v: self.complexity_label.setText(str(v))
            )
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            traceback.print_exc()
    
    def _load_patterns(self):
        """Load patterns from database"""
        try:
            # Mock patterns for demonstration
            mock_patterns = [
                {"id": "1", "name": "Rock Basic", "style": "Rock", "bpm": 120, "complexity": 30},
                {"id": "2", "name": "Jazz Swing", "style": "Jazz", "bpm": 140, "complexity": 70},
                {"id": "3", "name": "Funk Groove", "style": "Funk", "bpm": 110, "complexity": 60},
                {"id": "4", "name": "Electronic Beat", "style": "Electronic", "bpm": 128, "complexity": 50},
            ]
            
            self.patterns = mock_patterns
            self._populate_patterns_list()
            
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
            traceback.print_exc()
    
    def _populate_patterns_list(self):
        """Populate the patterns list widget"""
        try:
            self.patterns_list.clear()
            
            for pattern in self.patterns:
                item = QListWidgetItem()
                item.setText(f"{pattern['name']} ({pattern['style']}) - {pattern['bpm']} BPM")
                item.setData(Qt.UserRole, pattern)
                self.patterns_list.addItem(item)
                
        except Exception as e:
            logger.error(f"Error populating patterns list: {e}")
            traceback.print_exc()
    
    def _on_new_pattern(self):
        """Handle new pattern creation"""
        try:
            self.status_label.setText("Creating new pattern...")
            logger.info("Starting new pattern creation")
            
            QMessageBox.information(
                self,
                "New Pattern",
                "Professional WebDAW pattern creation will be integrated here.\n"
                "This will open the advanced drum creation interface."
            )
            
        except Exception as e:
            logger.error(f"Error creating new pattern: {e}")
            traceback.print_exc()
    
    def _on_open_webdaw(self):
        """Handle opening Professional WebDAW"""
        try:
            self.status_label.setText("Opening Professional WebDAW...")
            logger.info("Opening Professional WebDAW interface")
            
            # This would integrate with the web frontend
            import webbrowser
            webbrowser.open("http://localhost:3000")
            
            QMessageBox.information(
                self,
                "Professional WebDAW",
                "Opening Professional WebDAW in your browser.\n"
                "Navigate to ProStudioDAW for advanced drum creation."
            )
            
        except Exception as e:
            logger.error(f"Error opening WebDAW: {e}")
            traceback.print_exc()
    
    def _on_generate_pattern(self):
        """Handle pattern generation"""
        try:
            style = self.style_combo.currentText()
            bpm = self.bpm_spin.value()
            complexity = self.complexity_slider.value()
            
            self.status_label.setText(f"Generating {style} pattern at {bpm} BPM...")
            
            # Mock pattern generation
            pattern_text = f"""
Generated {style} Pattern:
BPM: {bpm}
Complexity: {complexity}%

Kick:  X . . . X . . .
Snare: . . X . . . X .
HiHat: X X X X X X X X
Crash: X . . . . . . .
            """
            
            self.pattern_display.setPlainText(pattern_text)
            self.status_label.setText("Pattern generated successfully!")
            
        except Exception as e:
            logger.error(f"Error generating pattern: {e}")
            traceback.print_exc()
    
    def _on_play_pattern(self):
        """Handle pattern playback"""
        try:
            selected_items = self.patterns_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Selection", "Please select a pattern first")
                return
            
            pattern = selected_items[0].data(Qt.UserRole)
            self.status_label.setText(f"Playing: {pattern['name']}")
            logger.info(f"Playing pattern: {pattern['name']}")
            
        except Exception as e:
            logger.error(f"Error playing pattern: {e}")
            traceback.print_exc()
    
    def _on_edit_pattern(self):
        """Handle pattern editing"""
        try:
            selected_items = self.patterns_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Selection", "Please select a pattern first")
                return
            
            pattern = selected_items[0].data(Qt.UserRole)
            self.status_label.setText(f"Editing: {pattern['name']}")
            
            QMessageBox.information(
                self,
                "Edit Pattern",
                f"Opening Professional WebDAW editor for:\n{pattern['name']}\n\n"
                "Advanced editing capabilities will be available here."
            )
            
        except Exception as e:
            logger.error(f"Error editing pattern: {e}")
            traceback.print_exc()
    
    def _on_export_pattern(self):
        """Handle pattern export"""
        try:
            selected_items = self.patterns_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Selection", "Please select a pattern first")
                return
            
            pattern = selected_items[0].data(Qt.UserRole)
            
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Drum Pattern",
                f"{pattern['name']}.mid",
                "MIDI Files (*.mid);;JSON Files (*.json);;All Files (*)"
            )
            
            if file_path:
                self.status_label.setText(f"Exporting: {pattern['name']}")
                logger.info(f"Exporting pattern to: {file_path}")
                self.pattern_exported.emit(file_path, pattern)
                
        except Exception as e:
            logger.error(f"Error exporting pattern: {e}")
            traceback.print_exc()
    
    def _on_delete_pattern(self):
        """Handle pattern deletion"""
        try:
            selected_items = self.patterns_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Selection", "Please select a pattern first")
                return
            
            pattern = selected_items[0].data(Qt.UserRole)
            
            reply = QMessageBox.question(
                self,
                "Delete Pattern",
                f"Are you sure you want to delete '{pattern['name']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.patterns = [p for p in self.patterns if p['id'] != pattern['id']]
                self._populate_patterns_list()
                self.status_label.setText(f"Deleted: {pattern['name']}")
                
        except Exception as e:
            logger.error(f"Error deleting pattern: {e}")
            traceback.print_exc()
    
    def _on_pattern_selected(self):
        """Handle pattern selection"""
        try:
            selected_items = self.patterns_list.selectedItems()
            if selected_items:
                pattern = selected_items[0].data(Qt.UserRole)
                self.current_pattern = pattern
                self.status_label.setText(f"Selected: {pattern['name']}")
                
        except Exception as e:
            logger.error(f"Error handling pattern selection: {e}")
            traceback.print_exc()
