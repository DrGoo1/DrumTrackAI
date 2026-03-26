"""
Drum Beats Widget
================
UI component for managing drum beats, including database operations,
audio playback, and integration with MVSep for stem separation.
"""
import logging
import os
import json
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Any

from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QProgressBar, QComboBox, QLineEdit, QGroupBox,
    QSplitter, QListWidget, QListWidgetItem
)

from admin.services.central_database_service import get_database_service
from admin.utils.thread_safe_ui_updater import ThreadSafeUIUpdater

logger = logging.getLogger(__name__)

class DrumBeatsWidget(QWidget):
    """Widget for managing drum beats and associated audio files"""
    
    # Signals
    beat_selected = Signal(dict)
    beat_processed = Signal(str, dict)  # beat_id, result_data
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DrumBeatsWidget")
        
        # Initialize state
        self.current_beat = None
        self.beats = []
        self.filtered_beats = []
        self.current_filter = ""
        self.thread_safe_updater = ThreadSafeUIUpdater()
        
        # Services
        self.db_service = get_database_service()
        self.batch_processor = None
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        
        # Load data
        self._initialize_database()
        self._load_data()
        
        logger.info("DrumBeatsWidget initialized")
    
    def _setup_ui(self):
        """Set up the user interface"""
        try:
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)
            
            # Header section
            header_layout = QHBoxLayout()
            self.title_label = QLabel("Drum Beats Library")
            self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
            header_layout.addWidget(self.title_label)
            header_layout.addStretch()
            
            # Search box
            self.search_box = QLineEdit()
            self.search_box.setPlaceholderText("Search drum beats...")
            self.search_box.setMaximumWidth(250)
            header_layout.addWidget(self.search_box)
            
            # Filter combo
            self.filter_combo = QComboBox()
            self.filter_combo.addItem("All Beats")
            self.filter_combo.addItem("By Complexity")
            self.filter_combo.addItem("By Energy")
            self.filter_combo.addItem("By BPM")
            header_layout.addWidget(self.filter_combo)
            
            main_layout.addLayout(header_layout)
            
            # Main content
            splitter = QSplitter(Qt.Horizontal)
            splitter.setHandleWidth(1)
            
            # Left panel - Beat list
            beats_group = QGroupBox("Available Beats")
            beats_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 1ex;
                    background-color: #f8f8f8;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #333333;
                }
            """)
            beats_layout = QVBoxLayout(beats_group)
            
            self.beats_table = QTableWidget()
            self.beats_table.setColumnCount(4)
            self.beats_table.setHorizontalHeaderLabels(["Name", "BPM", "Complexity", "Energy"])
            self.beats_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.beats_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.beats_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.beats_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.beats_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.beats_table.setSelectionMode(QTableWidget.SingleSelection)
            
            # Style the table for better readability
            self.beats_table.setStyleSheet("""
                QTableWidget {
                    background-color: white;
                    alternate-background-color: #f0f0f0;
                    color: #333333;
                    gridline-color: #d0d0d0;
                    selection-background-color: #4a90e2;
                    selection-color: white;
                }
                QTableWidget::item {
                    padding: 8px;
                    border-bottom: 1px solid #e0e0e0;
                }
                QTableWidget::item:selected {
                    background-color: #4a90e2;
                    color: white;
                }
                QHeaderView::section {
                    background-color: #e8e8e8;
                    color: #333333;
                    padding: 8px;
                    border: 1px solid #d0d0d0;
                    font-weight: bold;
                }
            """)
            self.beats_table.setAlternatingRowColors(True)
            beats_layout.addWidget(self.beats_table)
            
            # Buttons for beats management
            beats_buttons_layout = QHBoxLayout()
            
            self.add_beat_btn = QPushButton("Add Beat")
            self.edit_beat_btn = QPushButton("Edit")
            self.delete_beat_btn = QPushButton("Delete")
            self.play_beat_btn = QPushButton("Play")
            
            beats_buttons_layout.addWidget(self.add_beat_btn)
            beats_buttons_layout.addWidget(self.edit_beat_btn)
            beats_buttons_layout.addWidget(self.delete_beat_btn)
            beats_buttons_layout.addWidget(self.play_beat_btn)
            beats_buttons_layout.addStretch()
            
            beats_layout.addLayout(beats_buttons_layout)
            
            # Right panel - Beat details and processing
            details_group = QGroupBox("Beat Details & Processing")
            details_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 1ex;
                    background-color: #f8f8f8;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px 0 5px;
                    color: #333333;
                }
            """)
            details_layout = QVBoxLayout(details_group)
            
            # Details section
            details_form_layout = QVBoxLayout()
            self.beat_name_label = QLabel("Name: ")
            self.beat_details_label = QLabel("Details: Not selected")
            self.beat_path_label = QLabel("File: Not selected")
            
            # Style the detail labels for better readability
            label_style = """
                QLabel {
                    color: #333333;
                    font-size: 12px;
                    padding: 4px;
                    background-color: white;
                    border: 1px solid #e0e0e0;
                    border-radius: 3px;
                    margin: 2px;
                }
            """
            self.beat_name_label.setStyleSheet(label_style)
            self.beat_details_label.setStyleSheet(label_style)
            self.beat_path_label.setStyleSheet(label_style)
            
            details_form_layout.addWidget(self.beat_name_label)
            details_form_layout.addWidget(self.beat_details_label)
            details_form_layout.addWidget(self.beat_path_label)
            
            # Processing section
            processing_group = QGroupBox("MVSep Processing")
            processing_layout = QVBoxLayout(processing_group)
            
            self.process_btn = QPushButton("Process with MVSep")
            self.process_btn.setEnabled(False)
            
            self.progress_bar = QProgressBar()
            self.progress_bar.setValue(0)
            self.progress_label = QLabel("Ready")
            
            processing_layout.addWidget(self.process_btn)
            processing_layout.addWidget(self.progress_bar)
            processing_layout.addWidget(self.progress_label)
            
            details_form_layout.addWidget(processing_group)
            details_layout.addLayout(details_form_layout)
            
            # Results section
            results_group = QGroupBox("Processing Results")
            results_layout = QVBoxLayout(results_group)
            
            self.results_list = QListWidget()
            results_layout.addWidget(self.results_list)
            
            # Results buttons
            results_buttons_layout = QHBoxLayout()
            self.open_result_btn = QPushButton("Open Result")
            self.open_folder_btn = QPushButton("Open Folder")
            
            results_buttons_layout.addWidget(self.open_result_btn)
            results_buttons_layout.addWidget(self.open_folder_btn)
            results_buttons_layout.addStretch()
            
            results_layout.addLayout(results_buttons_layout)
            
            details_layout.addWidget(results_group)
            
            # Add both panels to splitter
            splitter.addWidget(beats_group)
            splitter.addWidget(details_group)
            splitter.setSizes([300, 400])
            
            main_layout.addWidget(splitter)
            
            # Update button states
            self._update_button_states()
            
        except Exception as e:
            logger.error(f"Error setting up UI: {e}")
            traceback.print_exc()
    
    def _connect_signals(self):
        """Connect UI signals to slots"""
        try:
            # Beats table
            self.beats_table.itemSelectionChanged.connect(self._on_beat_selected)
            self.beats_table.doubleClicked.connect(self._on_play_beat)
            
            # Buttons
            self.add_beat_btn.clicked.connect(self._on_add_beat)
            self.edit_beat_btn.clicked.connect(self._on_edit_beat)
            self.delete_beat_btn.clicked.connect(self._on_delete_beat)
            self.play_beat_btn.clicked.connect(self._on_play_beat)
            
            self.process_btn.clicked.connect(self._on_process_beat)
            self.open_result_btn.clicked.connect(self._on_open_result)
            self.open_folder_btn.clicked.connect(self._on_open_folder)
            
            # Search and filter
            self.search_box.textChanged.connect(self._on_search_changed)
            self.filter_combo.currentIndexChanged.connect(self._on_filter_changed)
            
            # Database service
            self.db_service.data_changed.connect(self._on_data_changed)
            self.db_service.database_error.connect(self._on_database_error)
            
            logger.debug("All signals connected")
            
        except Exception as e:
            logger.error(f"Error connecting signals: {e}")
            traceback.print_exc()
    
    def _initialize_database(self):
        """Initialize the database connection"""
        try:
            # Use the central database service (don't initialize with custom path)
            # The central database service will use its default path: drum_tracks.db
            success = self.db_service.initialize()
            if success:
                logger.info("Database connection established via central database service")
            else:
                logger.error("Failed to initialize database")
                QMessageBox.warning(
                    self, 
                    "Database Error", 
                    "Failed to initialize the database. Some features may not work correctly."
                )
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            traceback.print_exc()
            QMessageBox.critical(
                self,
                "Database Error",
                f"Failed to initialize database: {str(e)}"
            )
    
    def _load_data(self):
        """Load drum beats from database"""
        try:
            # Get all drum beats
            self.beats = self.db_service.get_drum_beats()
            
            # Apply current filter
            self._apply_filters()
            
            # Update the UI
            self._populate_beats_table()
            
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            traceback.print_exc()
    
    def _populate_beats_table(self):
        """Populate the beats table with current filtered data"""
        try:
            self.beats_table.setRowCount(0)
            
            for beat in self.filtered_beats:
                row = self.beats_table.rowCount()
                self.beats_table.insertRow(row)
                
                # Set name
                name_item = QTableWidgetItem(beat.get("name", "Unknown"))
                name_item.setData(Qt.UserRole, beat)
                self.beats_table.setItem(row, 0, name_item)
                
                # Set BPM
                bpm = beat.get("bpm", 0)
                bpm_item = QTableWidgetItem(f"{bpm}" if bpm else "-")
                self.beats_table.setItem(row, 1, bpm_item)
                
                # Set complexity
                complexity = beat.get("complexity", 0)
                complexity_item = QTableWidgetItem(f"{complexity:.1f}" if complexity else "-")
                self.beats_table.setItem(row, 2, complexity_item)
                
                # Set energy
                energy = beat.get("energy", 0)
                energy_item = QTableWidgetItem(f"{energy:.1f}" if energy else "-")
                self.beats_table.setItem(row, 3, energy_item)
            
            self._update_button_states()
            
        except Exception as e:
            logger.error(f"Error populating beats table: {e}")
            traceback.print_exc()
    
    def _apply_filters(self):
        """Apply current search and filter criteria"""
        try:
            search_text = self.current_filter.lower()
            filter_idx = self.filter_combo.currentIndex() if hasattr(self, 'filter_combo') else 0
            
            # Start with all beats
            filtered = self.beats.copy()
            
            # Apply text search if any
            if search_text:
                filtered = [
                    beat for beat in filtered
                    if search_text in beat.get("name", "").lower() or
                       search_text in beat.get("description", "").lower()
                ]
            
            # Apply type filter
            if filter_idx == 1:  # By Complexity
                filtered.sort(key=lambda x: x.get("complexity", 0) or 0, reverse=True)
            elif filter_idx == 2:  # By Energy
                filtered.sort(key=lambda x: x.get("energy", 0) or 0, reverse=True)
            elif filter_idx == 3:  # By BPM
                filtered.sort(key=lambda x: x.get("bpm", 0) or 0)
            
            self.filtered_beats = filtered
            
        except Exception as e:
            logger.error(f"Error applying filters: {e}")
            traceback.print_exc()
            self.filtered_beats = self.beats.copy()
    
    def _update_button_states(self):
        """Update button states based on selection"""
        try:
            has_beat_selected = self.current_beat is not None
            
            # Basic buttons
            self.edit_beat_btn.setEnabled(has_beat_selected)
            self.delete_beat_btn.setEnabled(has_beat_selected)
            self.play_beat_btn.setEnabled(has_beat_selected and 
                                         os.path.exists(self.current_beat.get("file_path", "")))
            
            # Processing buttons
            has_file = has_beat_selected and os.path.exists(self.current_beat.get("file_path", ""))
            self.process_btn.setEnabled(has_file and self.batch_processor is not None)
            
            # Results buttons
            has_results = False
            if has_beat_selected:
                # Check for results files
                beat_id = self.current_beat.get("id", "")
                output_dir = os.path.join(os.path.expanduser("~"), "DrumTracKAI", "processed", beat_id)
                has_results = os.path.exists(output_dir) and len(os.listdir(output_dir)) > 0
                
            self.open_result_btn.setEnabled(has_results)
            self.open_folder_btn.setEnabled(has_results)
            
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            traceback.print_exc()
    
    def _on_beat_selected(self):
        """Handle beat selection"""
        try:
            selected_items = self.beats_table.selectedItems()
            if not selected_items:
                self.current_beat = None
                self._update_beat_details(None)
                self._update_button_states()
                return
                
            # Get the beat data
            row = selected_items[0].row()
            name_item = self.beats_table.item(row, 0)
            beat_data = name_item.data(Qt.UserRole)
            
            # Update current beat
            self.current_beat = beat_data
            
            # Update UI
            self._update_beat_details(beat_data)
            self._update_button_states()
            
            # Emit signal
            self.beat_selected.emit(beat_data)
            
        except Exception as e:
            logger.error(f"Error handling beat selection: {e}")
            traceback.print_exc()
    
    def _update_beat_details(self, beat_data):
        """Update beat details panel"""
        try:
            if not beat_data:
                self.beat_name_label.setText("Name: Not selected")
                self.beat_details_label.setText("Details: Not selected")
                self.beat_path_label.setText("File: Not selected")
                return
                
            # Update labels
            self.beat_name_label.setText(f"Name: {beat_data.get('name', 'Unknown')}")
            
            # Build details text
            details = []
            if beat_data.get("bpm"):
                details.append(f"BPM: {beat_data['bpm']}")
            if beat_data.get("time_signature"):
                details.append(f"Time Sig: {beat_data['time_signature']}")
            if beat_data.get("complexity"):
                details.append(f"Complexity: {beat_data['complexity']:.1f}")
            if beat_data.get("energy"):
                details.append(f"Energy: {beat_data['energy']:.1f}")
            if beat_data.get("description"):
                details.append(f"Description: {beat_data['description']}")
                
            details_text = " | ".join(details) if details else "No details available"
            self.beat_details_label.setText(f"Details: {details_text}")
            
            # File path
            file_path = beat_data.get("file_path", "Not set")
            if file_path and os.path.exists(file_path):
                file_status = "File exists"
            elif file_path:
                file_status = "File missing"
            else:
                file_status = "No file"
                
            self.beat_path_label.setText(f"File: {os.path.basename(file_path)} ({file_status})")
            
            # Update results list
            self._update_results_list(beat_data.get("id", ""))
            
        except Exception as e:
            logger.error(f"Error updating beat details: {e}")
            traceback.print_exc()
    
    def _update_results_list(self, beat_id):
        """Update the processing results list for the current beat"""
        try:
            self.results_list.clear()
            
            if not beat_id:
                return
                
            # Check for results files
            output_dir = os.path.join(os.path.expanduser("~"), "DrumTracKAI", "processed", beat_id)
            if not os.path.exists(output_dir):
                return
                
            # List files in the output directory
            files = os.listdir(output_dir)
            for file in files:
                file_path = os.path.join(output_dir, file)
                if os.path.isfile(file_path):
                    item = QListWidgetItem(file)
                    item.setData(Qt.UserRole, file_path)
                    self.results_list.addItem(item)
            
        except Exception as e:
            logger.error(f"Error updating results list: {e}")
            traceback.print_exc()
    
    def _on_add_beat(self):
        """Handle add beat button click"""
        try:
            # First select audio file
            file_path, _ = QFileDialog.getOpenFileName(
                self, 
                "Select Audio File", 
                "", 
                "Audio Files (*.wav *.mp3 *.flac *.ogg);;All Files (*.*)"
            )
            
            if not file_path:
                return
                
            # Simple form for name and details
            beat_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # TODO: Replace with proper form dialog
            name, ok = QInputDialog.getText(
                self, 
                "Beat Name",
                "Enter name for the beat:",
                QLineEdit.Normal,
                beat_name
            )
            
            if not ok or not name:
                return
                
            # Add to database
            beat_id = self.db_service.add_drum_beat(
                name=name,
                file_path=file_path,
                metadata={
                    "description": "",
                    "bpm": 0,
                    "time_signature": "4/4",
                    "complexity": 0,
                    "energy": 0
                }
            )
            
            if beat_id:
                logger.info(f"Added new beat: {name} (ID: {beat_id})")
                self._load_data()
            else:
                QMessageBox.warning(self, "Add Beat Failed", "Failed to add beat to database")
            
        except Exception as e:
            logger.error(f"Error adding beat: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to add beat: {str(e)}")
    
    def _on_edit_beat(self):
        """Handle edit beat button click"""
        try:
            if not self.current_beat:
                return
                
            # TODO: Replace with proper form dialog
            QMessageBox.information(
                self,
                "Edit Beat",
                "Edit beat functionality not fully implemented yet"
            )
            
        except Exception as e:
            logger.error(f"Error editing beat: {e}")
            traceback.print_exc()
    
    def _on_delete_beat(self):
        """Handle delete beat button click"""
        try:
            if not self.current_beat:
                return
                
            beat_id = self.current_beat.get("id")
            beat_name = self.current_beat.get("name", "this beat")
            
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to delete '{beat_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
                
            # Delete from database
            if self.db_service.delete_drum_beat(beat_id):
                logger.info(f"Deleted beat: {beat_name} (ID: {beat_id})")
                self.current_beat = None
                self._load_data()
            else:
                QMessageBox.warning(self, "Delete Failed", "Failed to delete beat from database")
            
        except Exception as e:
            logger.error(f"Error deleting beat: {e}")
            traceback.print_exc()
    
    def _on_play_beat(self):
        """Play the selected beat"""
        try:
            if not self.current_beat:
                return
                
            file_path = self.current_beat.get("file_path")
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "Play Error", "Audio file not found")
                return
                
            # Use system default player
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
                
            logger.info(f"Playing audio file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error playing beat: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Play Error", f"Failed to play audio: {str(e)}")
    
    def _on_process_beat(self):
        """Process beat with MVSep"""
        try:
            if not self.current_beat:
                return
                
            if not self.batch_processor:
                QMessageBox.warning(
                    self,
                    "Processing Error",
                    "Batch processor not available. Cannot process audio."
                )
                return
                
            beat_id = self.current_beat.get("id")
            file_path = self.current_beat.get("file_path")
            
            if not file_path or not os.path.exists(file_path):
                QMessageBox.warning(self, "Processing Error", "Audio file not found")
                return
                
            # Create output directory
            output_dir = os.path.join(os.path.expanduser("~"), "DrumTracKAI", "processed", beat_id)
            os.makedirs(output_dir, exist_ok=True)
            
            # Add to batch processor
            try:
                # Get API key
                from os import environ
                api_key = environ.get("MVSEP_API_KEY")
                
                if api_key:
                    self.batch_processor.set_api_key(api_key)
                else:
                    QMessageBox.warning(
                        self, 
                        "API Key Missing",
                        "MVSEP_API_KEY not found in environment variables. Processing may fail."
                    )
                
                # Add job to queue
                self.batch_processor.add_to_queue(
                    file_path, 
                    output_dir,
                    {"beat_id": beat_id}
                )
                
                # Start processing
                self.batch_processor.start_processing(
                    keep_original_mix=True,
                    keep_drum_stem=True
                )
                
                # Update UI
                self.progress_bar.setValue(0)
                self.progress_label.setText("Processing started...")
                
                QMessageBox.information(
                    self,
                    "Processing Started",
                    "Audio processing has started. Check the Batch Processing tab for details."
                )
                
            except Exception as e:
                logger.error(f"Error adding to batch processor: {e}")
                traceback.print_exc()
                QMessageBox.critical(
                    self,
                    "Processing Error",
                    f"Failed to start processing: {str(e)}"
                )
            
        except Exception as e:
            logger.error(f"Error processing beat: {e}")
            traceback.print_exc()
    
    def _on_open_result(self):
        """Open the selected result file"""
        try:
            selected_items = self.results_list.selectedItems()
            if not selected_items:
                QMessageBox.information(self, "Selection", "Please select a result file first")
                return
                
            file_path = selected_items[0].data(Qt.UserRole)
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "File Error", "Result file not found")
                return
                
            # Use system default player
            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", file_path])
            else:  # Linux
                subprocess.call(["xdg-open", file_path])
                
            logger.info(f"Opened result file: {file_path}")
            
        except Exception as e:
            logger.error(f"Error opening result: {e}")
            traceback.print_exc()
    
    def _on_open_folder(self):
        """Open the results folder"""
        try:
            if not self.current_beat:
                return
                
            beat_id = self.current_beat.get("id", "")
            output_dir = os.path.join(os.path.expanduser("~"), "DrumTracKAI", "processed", beat_id)
            
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            # Use system file explorer
            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Darwin":  # macOS
                subprocess.call(["open", output_dir])
            else:  # Linux
                subprocess.call(["xdg-open", output_dir])
                
            logger.info(f"Opened results folder: {output_dir}")
            
        except Exception as e:
            logger.error(f"Error opening folder: {e}")
            traceback.print_exc()
    
    def _on_search_changed(self, text):
        """Handle search text change"""
        try:
            self.current_filter = text
            self._apply_filters()
            self._populate_beats_table()
            
        except Exception as e:
            logger.error(f"Error handling search: {e}")
            traceback.print_exc()
    
    def _on_filter_changed(self, index):
        """Handle filter combo change"""
        try:
            self._apply_filters()
            self._populate_beats_table()
            
        except Exception as e:
            logger.error(f"Error handling filter change: {e}")
            traceback.print_exc()
    
    def _on_data_changed(self, table_name, operation):
        """Handle database data changes"""
        try:
            if table_name == "drum_beats":
                logger.info(f"Drum beats data changed ({operation}), reloading")
                self._load_data()
                
        except Exception as e:
            logger.error(f"Error handling data change: {e}")
            traceback.print_exc()
    
    def _on_database_error(self, error_message):
        """Handle database errors"""
        logger.error(f"Database error: {error_message}")
        # Only show critical errors to the user
        if "CRITICAL" in error_message:
            QMessageBox.critical(self, "Database Error", error_message)
    
    def set_batch_processor(self, batch_processor):
        """Set the batch processor for MVSep processing"""
        self.batch_processor = batch_processor
        self._update_button_states()
        logger.info("Batch processor connected to DrumBeatsWidget")
