"""
DrumBeatsWidget - Complete Fixed Version
=======================================
Enhanced widget for managing famous drum beat profiles and audio samples.
Handles the specific H:\DrumBeats file structure and integrates with database storage.
"""
import sys
import json
import logging
import os
import platform
import subprocess
import traceback
import uuid

from PySide6.QtWidgets import QApplication
from datetime import datetime
from admin.services.central_database_service import CentralDatabaseService
from PySide6.QtCore import Qt, QTimer, Signal, QObject, Slot, QSize, QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QMessageBox, QTabWidget,
    QFileDialog, QComboBox, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QGroupBox, QCheckBox, QProgressBar, QSpinBox, QButtonGroup, QRadioButton
)
from pathlib import Path
from typing import Optional, Dict, Any, List

# Import audio player widget with fallback handling
try:
    from .audio_player_tab import AudioPlayerTab
    AUDIO_PLAYER_AVAILABLE = True
except ImportError:
    logger.warning("AudioPlayerTab not available - audio playback will be limited")
    AUDIO_PLAYER_AVAILABLE = False
    # Create a dummy class for compatibility
    class AudioPlayerTab:
        def __init__(self, *args, **kwargs):
            pass

logger = logging.getLogger(__name__)

# Constants
DEFAULT_OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(os.getcwd(), "output"))
DRUMBEATS_DIR = r"H:\DrumBeats"
AUDIO_EXTENSIONS = ('.wav', '.mp3', '.flac', '.ogg', '.m4a')

class DrumBeatProfileDialog(QDialog):
    """Dialog for adding or editing drum beat profiles."""

    def __init__(self, parent=None, profile_data=None):
        super().__init__(parent)
        self.profile_data = profile_data or {}
        self.setWindowTitle("Add Drum Beat Profile" if not profile_data else "Edit Drum Beat Profile")
        self.setMinimumWidth(500)

        # Create form layout
        layout = QFormLayout(self)

        # Profile name
        self.name_edit = QLineEdit(self.profile_data.get("name", ""))
        layout.addRow("Name:", self.name_edit)

        # Artist
        self.artist_edit = QLineEdit(self.profile_data.get("artist", ""))
        layout.addRow("Artist:", self.artist_edit)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setText(self.profile_data.get("description", ""))
        self.description_edit.setAcceptRichText(False)
        self.description_edit.setMaximumHeight(100)
        layout.addRow("Description:", self.description_edit)

        # Source
        self.source_edit = QLineEdit(self.profile_data.get("source", ""))
        layout.addRow("Source:", self.source_edit)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_profile_data(self):
        """Get the profile data from the dialog fields."""
        profile_data = self.profile_data.copy() if self.profile_data else {}

        # Basic info
        profile_data["name"] = self.name_edit.text().strip()
        profile_data["artist"] = self.artist_edit.text().strip()
        profile_data["description"] = self.description_edit.toPlainText().strip()
        profile_data["source"] = self.source_edit.text().strip()

        # If this is a new profile, generate an ID and set creation date
        if not profile_data.get("id"):
            profile_data["id"] = str(uuid.uuid4())
            profile_data["created"] = datetime.now().isoformat()

        # Ensure samples list exists
        if "samples" not in profile_data:
            profile_data["samples"] = []

        return profile_data

class DrumBeatSampleDialog(QDialog):
    """Dialog for adding or editing drum beat samples."""

    def __init__(self, parent=None, sample_data=None):
        super().__init__(parent)
        self.sample_data = sample_data or {}
        self.setWindowTitle("Add Sample" if not sample_data else "Edit Sample")
        self.setMinimumWidth(500)

        # Create form layout
        layout = QFormLayout(self)

        # Sample title
        self.title_edit = QLineEdit(self.sample_data.get("title", ""))
        layout.addRow("Title:", self.title_edit)

        # YouTube ID (optional)
        self.youtube_id_edit = QLineEdit(self.sample_data.get("youtube_id", ""))
        layout.addRow("YouTube ID (optional):", self.youtube_id_edit)

        # Sample type
        self.type_combo = QComboBox()
        for sample_type in ["Original", "Drum", "Cover", "Tutorial", "Demonstration", "Other"]:
            self.type_combo.addItem(sample_type)

        # Set current type if editing
        current_type = self.sample_data.get("type", "Original")
        index = self.type_combo.findText(current_type)
        if index >= 0:
            self.type_combo.setCurrentIndex(index)

        layout.addRow("Type:", self.type_combo)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addRow(button_box)

    def get_sample_data(self):
        """Get the entered sample data."""
        # Start with existing data if editing
        data = self.sample_data.copy() if self.sample_data else {}

        # Update with new values
        data["title"] = self.title_edit.text().strip()
        data["youtube_id"] = self.youtube_id_edit.text().strip()
        data["type"] = self.type_combo.currentText()

        # Add or update metadata
        data["id"] = data.get("id", str(uuid.uuid4()))
        data["date_added"] = data.get("date_added", datetime.now().isoformat())
        data["date_modified"] = datetime.now().isoformat()

        return data

class MVSepProcessingDialog(QDialog):
    """Dialog for selecting MVSep processing options."""

    def __init__(self, parent=None, sample_data=None):
        super().__init__(parent)
        self.sample_data = sample_data
        self.setWindowTitle("MVSep Processing Options")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        # Sample info
        if sample_data:
            info_label = QLabel(f"Sample: {sample_data.get('title', 'Unknown')}")
            info_label.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
            layout.addWidget(info_label)

        # Processing type selection
        processing_group = QGroupBox("Processing Type")
        processing_layout = QVBoxLayout(processing_group)

        self.processing_type_group = QButtonGroup()

        # Auto-detect option (default)
        self.auto_radio = QRadioButton("Auto-detect (recommended)")
        self.auto_radio.setChecked(True)
        self.auto_radio.setToolTip("Automatically determine the best processing based on file content")
        self.processing_type_group.addButton(self.auto_radio, 0)
        processing_layout.addWidget(self.auto_radio)

        # Full song processing
        self.full_song_radio = QRadioButton("Full Song Separation")
        self.full_song_radio.setToolTip("Use HDemucs for complete instrument separation")
        self.processing_type_group.addButton(self.full_song_radio, 1)
        processing_layout.addWidget(self.full_song_radio)

        # Drum-only processing
        self.drum_only_radio = QRadioButton("Drum-Only Processing")
        self.drum_only_radio.setToolTip("Use DrumSep for drum component separation")
        self.processing_type_group.addButton(self.drum_only_radio, 2)
        processing_layout.addWidget(self.drum_only_radio)

        # Set the appropriate default based on sample data
        if sample_data:
            filename = sample_data.get('title', '').lower()
            sample_type = sample_data.get('type', '').lower()

            # Auto-select the appropriate processing type
            if '_drum' in filename or sample_type == 'drum':
                self.drum_only_radio.setChecked(True)
            elif '_original' in filename or sample_type == 'original':
                self.full_song_radio.setChecked(True)

        layout.addWidget(processing_group)

        # Output options
        output_group = QGroupBox("Output Options")
        output_layout = QVBoxLayout(output_group)

        # Add output directory selection
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("Base Output Directory:")
        self.output_dir_field = QLineEdit()
        self.output_dir_field.setReadOnly(True)

        # Default to database location for drum analysis
        default_output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                                         "database", "processed_stems")
        os.makedirs(default_output_dir, exist_ok=True)
        self.output_dir_field.setText(default_output_dir)

        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._browse_output_dir)
        output_dir_layout.addWidget(output_dir_label, 1)
        output_dir_layout.addWidget(self.output_dir_field, 3)
        output_dir_layout.addWidget(browse_button, 1)
        output_layout.addLayout(output_dir_layout)

        # Folder organization options
        folder_group = QGroupBox("Folder Organization")
        folder_layout = QVBoxLayout(folder_group)

        self.folder_organization_group = QButtonGroup()

        # Create subfolder per file
        self.create_subfolder_radio = QRadioButton("Create subfolder for each file (recommended)")
        self.create_subfolder_radio.setChecked(True)
        self.create_subfolder_radio.setToolTip("Create a separate subfolder for each processed file")
        self.folder_organization_group.addButton(self.create_subfolder_radio, 0)
        folder_layout.addWidget(self.create_subfolder_radio)

        # Use date-based folders
        self.date_folder_radio = QRadioButton("Use date-based folders")
        self.date_folder_radio.setToolTip("Group files processed on the same date")
        self.folder_organization_group.addButton(self.date_folder_radio, 1)
        folder_layout.addWidget(self.date_folder_radio)

        # Use processing type folders
        self.type_folder_radio = QRadioButton("Group by processing type")
        self.type_folder_radio.setToolTip("Separate files by their processing type (full or drums)")
        self.folder_organization_group.addButton(self.type_folder_radio, 2)
        folder_layout.addWidget(self.type_folder_radio)

        # No subfolders
        self.no_subfolder_radio = QRadioButton("No subfolders (flat structure)")
        self.no_subfolder_radio.setToolTip("Save all files directly in the output directory")
        self.folder_organization_group.addButton(self.no_subfolder_radio, 3)
        folder_layout.addWidget(self.no_subfolder_radio)

        output_layout.addWidget(folder_group)

        # Keep original/analyze options
        self.keep_original_check = QCheckBox("Keep original file in output")
        self.keep_original_check.setChecked(True)
        output_layout.addWidget(self.keep_original_check)

        self.auto_analyze_check = QCheckBox("Automatically analyze drums after processing")
        self.auto_analyze_check.setChecked(True)
        output_layout.addWidget(self.auto_analyze_check)

        layout.addWidget(output_group)

        # Auto-detect explanation
        if sample_data:
            explanation = self._get_auto_detect_explanation()
            explanation_label = QLabel(explanation)
            explanation_label.setWordWrap(True)
            explanation_label.setStyleSheet("color: #666; font-style: italic; margin: 10px 0;")
            layout.addWidget(explanation_label)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _get_auto_detect_explanation(self):
        """Get explanation of what auto-detect will do."""
        if not self.sample_data:
            return "Auto-detect will choose the best processing method."

        filename = self.sample_data.get("title", "")
        file_path = self.sample_data.get("file_path", "")

        if file_path:
            filename = os.path.basename(file_path)

        if "_drum" in filename.lower():
            return "Auto-detect: Will use Drum-Only Processing (DrumSep) based on '_drum' in filename."
        elif "_original" in filename.lower():
            return "Auto-detect: Will use Full Song Separation (HDemucs) based on '_original' in filename."
        else:
            return "Auto-detect: Will use Full Song Separation (HDemucs) as default for unknown file type."

    def _browse_output_dir(self):
        """Open a directory browser dialog to select the output directory"""
        try:
            directory = QFileDialog.getExistingDirectory(
                self, "Select Output Directory", self.output_dir_field.text(),
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )

            if directory:  # Only update if a directory was selected (not canceled)
                self.output_dir_field.setText(directory)
                logger.debug(f"Output directory set to: {directory}")
        except Exception as e:
            logger.error(f"Error browsing for output directory: {e}")

    def get_processing_options(self):
        """Get the selected processing options."""
        selected_id = self.processing_type_group.checkedId()

        processing_types = {
            0: "auto",
            1: "full_song",
            2: "drum_only"
        }

        folder_id = self.folder_organization_group.checkedId()
        folder_types = {
            0: "subfolder_per_file",
            1: "date_based",
            2: "processing_type",
            3: "flat"
        }

        return {
            "processing_type": processing_types.get(selected_id, "auto"),
            "keep_original": self.keep_original_check.isChecked(),
            "auto_analyze": self.auto_analyze_check.isChecked(),
            "output_dir": self.output_dir_field.text().strip(),
            "folder_organization": folder_types.get(folder_id, "subfolder_per_file")
        }

class DrumBeatsWidget(QWidget):
    """Enhanced widget for managing drum beat profiles and audio samples."""

    # Signals
    status_updated = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Initialize core state
        self._initialization_complete = False
        self._is_downloading = False

        # Initialize data structures
        self.drumbeats = []
        self.current_drumbeat = None
        self.current_sample = None
        self.download_queue = []
        self.event_bus = None

        # Database reference (will be set later)
        self.db = None

        # Create directories if they don't exist
        os.makedirs(DRUMBEATS_DIR, exist_ok=True)

        # Initialize YouTube service (placeholder)
        self.youtube_service = None

        # Set up the UI
        self.setup_ui()

        # Load drum beat profiles
        self.load_drumbeat_profiles()

        # Initialize database connection
        self._initialize_database()

        # Mark initialization as complete
        self._initialization_complete = True
        logger.info("DrumBeats widget initialized successfully")

    def _initialize_database(self):
        """Initialize database connection for storing drumbeat data."""
        try:
            # Try to get the database service
            self.db = CentralDatabaseService.get_instance()
            logger.info("Database service connected for DrumBeats widget")
        except Exception as e:
            logger.warning(f"Could not connect to database service: {e}")
            self.db = None

    def setup_ui(self):
        """Set up the user interface."""
        # Create main layout
        main_layout = QHBoxLayout(self)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # Left panel - Drum beat list
        left_panel = self._create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel - Details
        right_panel = self._create_right_panel()
        splitter.addWidget(right_panel)

        # Set initial splitter sizes
        splitter.setSizes([300, 700])

        # Update button states
        self.update_button_states()

    def _create_left_panel(self):
        """Create the left panel with drumbeat list and controls."""
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Header label
        header_label = QLabel("Famous Drum Beats")
        header_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        left_layout.addWidget(header_label)

        # Drum beat list
        self.drumbeat_list = QListWidget()
        self.drumbeat_list.setMinimumWidth(200)
        self.drumbeat_list.currentItemChanged.connect(self.on_drumbeat_selected)
        left_layout.addWidget(self.drumbeat_list)

        # Control buttons
        button_layout = QVBoxLayout()

        self.add_drumbeat_button = QPushButton("Add DrumBeat")
        self.add_drumbeat_button.clicked.connect(self.on_add_drumbeat)
        button_layout.addWidget(self.add_drumbeat_button)

        self.edit_drumbeat_button = QPushButton("Edit DrumBeat")
        self.edit_drumbeat_button.clicked.connect(self.on_edit_drumbeat)
        button_layout.addWidget(self.edit_drumbeat_button)

        self.delete_drumbeat_button = QPushButton("Delete DrumBeat")
        self.delete_drumbeat_button.clicked.connect(self.on_delete_drumbeat)
        button_layout.addWidget(self.delete_drumbeat_button)

        # Scan button
        self.scan_directory_button = QPushButton("Scan H:\\DrumBeats")
        self.scan_directory_button.clicked.connect(self.on_scan_directory)
        button_layout.addWidget(self.scan_directory_button)

        left_layout.addLayout(button_layout)

        return left_panel

    def _create_right_panel(self):
        """Create the right panel with detailed views."""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Tab widget for details
        self.details_tabs = QTabWidget()
        right_layout.addWidget(self.details_tabs)

        # Profile tab
        self._create_profile_tab()

        # Samples tab
        self._create_samples_tab()

        # Audio player tab
        self._create_audio_player_tab()

        # MVSep tab
        self._create_mvsep_tab()

        return right_panel

    def _create_profile_tab(self):
        """Create the profile information tab."""
        profile_tab = QWidget()
        profile_layout = QVBoxLayout(profile_tab)

        self.profile_text = QTextEdit()
        self.profile_text.setReadOnly(True)
        profile_layout.addWidget(self.profile_text)

        self.details_tabs.addTab(profile_tab, "Profile")

    def _create_samples_tab(self):
        """Create the samples management tab."""
        samples_tab = QWidget()
        samples_layout = QVBoxLayout(samples_tab)

        # Sample list controls
        samples_ctrl_layout = QHBoxLayout()
        self.add_sample_button = QPushButton("Add Sample")
        self.add_sample_button.clicked.connect(self.on_add_sample)
        self.edit_sample_button = QPushButton("Edit Sample")
        self.edit_sample_button.clicked.connect(self.on_edit_sample)
        self.delete_sample_button = QPushButton("Delete Sample")
        self.delete_sample_button.clicked.connect(self.on_delete_sample)

        samples_ctrl_layout.addWidget(self.add_sample_button)
        samples_ctrl_layout.addWidget(self.edit_sample_button)
        samples_ctrl_layout.addWidget(self.delete_sample_button)
        samples_ctrl_layout.addStretch(1)

        # Sample list
        self.samples_list = QListWidget()
        self.samples_list.setSelectionMode(QListWidget.SingleSelection)
        self.samples_list.itemSelectionChanged.connect(self.on_sample_selected)

        samples_layout.addLayout(samples_ctrl_layout)
        samples_layout.addWidget(QLabel("Available Samples:"))
        samples_layout.addWidget(self.samples_list)

        # Sample action controls
        action_ctrl_layout = QHBoxLayout()
        self.play_audio_button = QPushButton("Play Audio")
        self.play_audio_button.clicked.connect(self.on_play_audio)

        self.send_to_audio_tab_button = QPushButton("Send to Audio Tab")
        self.send_to_audio_tab_button.clicked.connect(self.on_send_to_audio_tab)

        action_ctrl_layout.addWidget(self.play_audio_button)
        action_ctrl_layout.addWidget(self.send_to_audio_tab_button)
        action_ctrl_layout.addStretch(1)

        samples_layout.addLayout(action_ctrl_layout)

        self.details_tabs.addTab(samples_tab, "Samples")

    def _create_audio_player_tab(self):
        """Create the audio player tab."""
        if AUDIO_PLAYER_AVAILABLE:
            try:
                self.audio_player = AudioPlayerTab()
                self.details_tabs.addTab(self.audio_player, "Audio Player")
            except Exception as e:
                logger.error(f"Error creating audio player: {e}")
                self._create_placeholder_audio_tab()
        else:
            self._create_placeholder_audio_tab()

    def _create_placeholder_audio_tab(self):
        """Create a placeholder audio tab."""
        placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_widget)

        placeholder_label = QLabel("Audio player not available")
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_layout.addWidget(placeholder_label)

        self.details_tabs.addTab(placeholder_widget, "Audio Player")

    def _create_mvsep_tab(self):
        """Create the MVSep integration tab."""
        mvsep_tab = QWidget()
        mvsep_layout = QVBoxLayout(mvsep_tab)

        # Instructions
        instructions = QLabel("""
        <h3>MVSep Integration</h3>
        <p>Send drum beat samples to MVSep for separation processing.</p>
        <p>The system will automatically detect the best processing method based on the filename:</p>
        <ul>
        <li><b>Files with "_original":</b> Full song separation (HDemucs)</li>
        <li><b>Files with "_drum":</b> Drum-only processing (DrumSep)</li>
        <li><b>Other files:</b> User can choose processing type</li>
        </ul>
        """)
        instructions.setTextFormat(Qt.TextFormat.RichText)
        instructions.setWordWrap(True)
        mvsep_layout.addWidget(instructions)

        # Current sample info
        self.current_sample_info = QGroupBox("Current Sample")
        sample_info_layout = QVBoxLayout(self.current_sample_info)

        self.sample_title_label = QLabel("No sample selected")
        self.sample_title_label.setStyleSheet("font-weight: bold;")
        sample_info_layout.addWidget(self.sample_title_label)

        self.sample_path_label = QLabel("")
        self.sample_path_label.setStyleSheet("color: #666; font-size: 10px;")
        self.sample_path_label.setWordWrap(True)
        sample_info_layout.addWidget(self.sample_path_label)

        self.processing_strategy_label = QLabel("")
        self.processing_strategy_label.setStyleSheet("color: #0066cc;")
        self.processing_strategy_label.setWordWrap(True)
        sample_info_layout.addWidget(self.processing_strategy_label)

        mvsep_layout.addWidget(self.current_sample_info)

        # MVSep buttons
        mvsep_buttons_layout = QHBoxLayout()

        self.add_to_mvsep_button = QPushButton("Send to MVSep")
        self.add_to_mvsep_button.clicked.connect(self.on_add_to_mvsep)
        self.add_to_mvsep_button.setStyleSheet("""
        QPushButton {
            background-color: #4CAF50;
            color: white;
            font-weight: bold;
            padding: 8px;
            border: none;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:disabled {
            background-color: #cccccc;
            color: #666666;
        }
        """)
        mvsep_buttons_layout.addWidget(self.add_to_mvsep_button)

        mvsep_layout.addLayout(mvsep_buttons_layout)

        # Status display
        self.mvsep_status = QLabel("Ready for processing")
        self.mvsep_status.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        mvsep_layout.addWidget(self.mvsep_status)

        mvsep_layout.addStretch()

        self.details_tabs.addTab(mvsep_tab, "MVSep Processing")

    def load_drumbeat_profiles(self):
        """Load drum beat profiles from the H:\DrumBeats directory."""
        try:
            logger.info("Loading drumbeat profiles from H:\\DrumBeats directory...")

            # Clear existing drumbeats
            self.drumbeats = []

            if not os.path.exists(DRUMBEATS_DIR):
                logger.warning(f"DrumBeats directory not found: {DRUMBEATS_DIR}")
                self._create_empty_profile()
                return

            # Scan for audio files
            audio_files = self._scan_audio_files()

            if not audio_files:
                logger.info("No audio files found, creating empty profile")
                self._create_empty_profile()
            else:
                # Group files by base name (removing _original and _drum suffixes)
                grouped_files = self._group_audio_files(audio_files)

                # Create drumbeat profiles
                self._create_drumbeat_profiles(grouped_files)

            # Update UI
            self.populate_drumbeat_list()

            # Select first drumbeat if available
            if self.drumbeats and self.drumbeat_list.count() > 0:
                self.drumbeat_list.setCurrentRow(0)

            logger.info(f"Loaded {len(self.drumbeats)} drumbeat profiles")

        except Exception as e:
            logger.error(f"Error loading drumbeat profiles: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error Loading Drumbeats", str(e), QMessageBox.Critical)
            self._create_empty_profile()

    def _scan_audio_files(self):
        """Scan the DrumBeats directory for audio files."""
        audio_files = []

        try:
            # Scan directly in the root directory (as specified in requirements)
            for file_path in Path(DRUMBEATS_DIR).iterdir():
                if file_path.is_file() and file_path.suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(file_path)
                    logger.debug(f"Found audio file: {file_path}")
        except Exception as e:
            logger.error(f"Error scanning audio files: {e}")

        return audio_files

    def _group_audio_files(self, audio_files):
        """Group audio files by base name (song_name_original.wav and song_name_drum.wav)."""
        grouped = {}

        for file_path in audio_files:
            # Get the file name without extension
            base_name = file_path.stem

            # Determine if this is an original or drum version
            if base_name.endswith('_original'):
                key = base_name[:-9]  # Remove '_original'
                file_type = 'original'
            elif base_name.endswith('_drum'):
                key = base_name[:-5]  # Remove '_drum'
                file_type = 'drum'
            else:
                # File doesn't follow the expected naming convention
                key = base_name
                file_type = 'unknown'

            if key not in grouped:
                grouped[key] = {}

            grouped[key][file_type] = file_path

        return grouped

    def _create_drumbeat_profiles(self, grouped_files):
        """Create drumbeat profiles from grouped files."""
        for base_name, files in grouped_files.items():
            # Create a profile for this group
            profile = {
                "id": str(uuid.uuid4()),
                "name": base_name.replace('_', ' ').title(),
                "artist": "Unknown Artist",  # Could be extracted from filename later
                "description": f"Drum beat collection for {base_name}",
                "source": "H:\\DrumBeats",
                "date_added": datetime.now().isoformat(),
                "date_modified": datetime.now().isoformat(),
                "samples": []
            }

            # Add samples for each file type
            for file_type, file_path in files.items():
                sample = {
                    "id": str(uuid.uuid4()),
                    "title": f"{base_name} ({file_type})",
                    "type": file_type.title(),
                    "file_path": str(file_path),
                    "file_size": file_path.stat().st_size,
                    "downloaded": True,
                    "date_added": datetime.now().isoformat(),
                    "description": f"{file_type.title()} version of {base_name}"
                }
                profile["samples"].append(sample)

            self.drumbeats.append(profile)
            logger.debug(f"Created profile: {profile['name']} with {len(profile['samples'])} samples")

            # Store in database if available
            if self.db:
                self._store_profile_in_database(profile)

    def _store_profile_in_database(self, profile):
        """Store drumbeat profile in the database."""
        try:
            # Store the profile in the drumbeats table
            profile_data = {
                "id": profile["id"],
                "name": profile["name"],
                "artist": profile.get("artist", ""),
                "description": profile.get("description", ""),
                "source": profile.get("source", ""),
                "metadata": json.dumps(profile),
                "date_created": profile.get("date_added", datetime.now().isoformat()),
                "date_modified": profile.get("date_modified", datetime.now().isoformat())
            }

            # Check if profile already exists
            existing = self.db.query("SELECT id FROM drumbeats WHERE id = ?", (profile["id"],))

            if existing:
                # Update existing profile
                self.db.execute(
                    "UPDATE drumbeats SET name=?, artist=?, description=?, source=?, metadata=?, date_modified=? WHERE id=?",
                    (profile_data["name"], profile_data["artist"], profile_data["description"],
                     profile_data["source"], profile_data["metadata"], profile_data["date_modified"], profile["id"])
                )
            else:
                # Insert new profile
                self.db.execute(
                    "INSERT INTO drumbeats (id, name, artist, description, source, metadata, date_created, date_modified) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (profile_data["id"], profile_data["name"], profile_data["artist"], profile_data["description"],
                     profile_data["source"], profile_data["metadata"], profile_data["date_created"], profile_data["date_modified"])
                )

            # Store samples
            for sample in profile["samples"]:
                self._store_sample_in_database(sample, profile["id"])

            logger.debug(f"Stored profile {profile['name']} in database")

        except Exception as e:
            logger.error(f"Error storing profile in database: {e}")

    def _store_sample_in_database(self, sample, drumbeat_id):
        """Store a sample in the database."""
        try:
            sample_data = {
                "id": sample["id"],
                "drumbeat_id": drumbeat_id,
                "title": sample["title"],
                "file_path": sample["file_path"],
                "file_size": sample.get("file_size", 0),
                "sample_type": sample.get("type", "Unknown"),
                "downloaded": sample.get("downloaded", False),
                "metadata": json.dumps(sample),
                "date_added": sample.get("date_added", datetime.now().isoformat())
            }

            # Check if sample already exists
            existing = self.db.query("SELECT id FROM drumbeat_samples WHERE id = ?", (sample["id"],))

            if existing:
                # Update existing sample
                self.db.execute(
                    "UPDATE drumbeat_samples SET title=?, file_path=?, file_size=?, sample_type=?, downloaded=?, metadata=? WHERE id=?",
                    (sample_data["title"], sample_data["file_path"], sample_data["file_size"],
                     sample_data["sample_type"], sample_data["downloaded"], sample_data["metadata"], sample["id"])
                )
            else:
                # Insert new sample
                self.db.execute(
                    "INSERT INTO drumbeat_samples (id, drumbeat_id, title, file_path, file_size, sample_type, downloaded, metadata, date_added) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (sample_data["id"], sample_data["drumbeat_id"], sample_data["title"], sample_data["file_path"],
                     sample_data["file_size"], sample_data["sample_type"], sample_data["downloaded"], sample_data["metadata"], sample_data["date_added"])
                )

        except Exception as e:
            logger.error(f"Error storing sample in database: {e}")

    def _create_empty_profile(self):
        """Create an empty default profile."""
        default_profile = {
            "id": str(uuid.uuid4()),
            "name": "Default Profile",
            "artist": "",
            "description": "No audio files found in H:\\DrumBeats",
            "source": "Default",
            "date_added": datetime.now().isoformat(),
            "date_modified": datetime.now().isoformat(),
            "samples": []
        }
        self.drumbeats.append(default_profile)

    def populate_drumbeat_list(self):
        """Populate the drumbeat list with available profiles."""
        try:
            self.drumbeat_list.clear()

            for i, drumbeat in enumerate(self.drumbeats):
                item_name = drumbeat.get('name', f'Drumbeat {i+1}')
                item = QListWidgetItem(item_name)
                item.setData(Qt.UserRole, i)  # Store index for easy retrieval
                self.drumbeat_list.addItem(item)

            logger.info(f"Populated drumbeat list with {len(self.drumbeats)} profiles")

        except Exception as e:
            logger.error(f"Error populating drumbeat list: {e}")
            logger.error(traceback.format_exc())

    def populate_samples_list(self):
        """Populate the samples list with samples from the selected drumbeat."""
        try:
            self.samples_list.clear()
            self.current_sample = None

            if not self.current_drumbeat:
                return

            samples = self.current_drumbeat.get("samples", [])
            if not samples:
                logger.info(f"No samples found for drumbeat {self.current_drumbeat.get('name')}")
                return

            for i, sample in enumerate(samples):
                title = sample.get("title", "Untitled Sample")
                file_path = sample.get("file_path", "")
                downloaded = sample.get("downloaded", False) and os.path.exists(file_path)

                # Status indicator
                status = "[+] " if downloaded else "[-] "
                display_text = f"{status}{title}"

                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, i)  # Store sample index

                # Set color based on availability
                if not downloaded:
                    item.setForeground(Qt.gray)

                # Set tooltip
                tooltip = f"Title: {title}\n"
                if sample.get("type"):
                    tooltip += f"Type: {sample.get('type')}\n"
                if file_path:
                    tooltip += f"File: {file_path}\n"
                tooltip += f"Exists: {'Yes' if os.path.exists(file_path) else 'No'}\n"
                if sample.get("file_size"):
                    size_mb = sample.get("file_size", 0) / (1024 * 1024)
                    tooltip += f"Size: {size_mb:.1f} MB\n"
                item.setToolTip(tooltip)

                self.samples_list.addItem(item)

            logger.info(f"Populated samples list with {len(samples)} samples")

        except Exception as e:
            logger.error(f"Error populating samples list: {e}")
            logger.error(traceback.format_exc())

    def update_button_states(self):
        """Update the enabled/disabled state of buttons based on current selection."""
        try:
            # Check if we have selections
            has_drumbeat = self.current_drumbeat is not None
            has_sample = self._get_current_sample_data() is not None
            sample_data = self._get_current_sample_data()
            
            # Ensure has_audio_file is always a boolean
            has_audio_file = False
            if sample_data:
                file_path = sample_data.get("file_path")
                if file_path and os.path.exists(file_path):
                    has_audio_file = True

            # Drumbeat buttons
            self.edit_drumbeat_button.setEnabled(has_drumbeat)
            self.delete_drumbeat_button.setEnabled(has_drumbeat)

            # Sample buttons
            self.add_sample_button.setEnabled(has_drumbeat)
            self.edit_sample_button.setEnabled(has_sample)
            self.delete_sample_button.setEnabled(has_sample)

            # Audio/playback buttons
            self.play_audio_button.setEnabled(has_audio_file)
            self.send_to_audio_tab_button.setEnabled(has_audio_file)

            # MVSep buttons
            self.add_to_mvsep_button.setEnabled(has_audio_file)

            # Update current sample info in MVSep tab
            self._update_current_sample_info()

        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            logger.error(traceback.format_exc())

    def _get_current_sample_data(self):
        """Get the data for the currently selected sample."""
        try:
            if not self.current_drumbeat or not self.samples_list.currentItem():
                return None

            # Get sample index from the current item
            sample_index = self.samples_list.currentItem().data(Qt.UserRole)
            if sample_index is None:
                return None

            samples = self.current_drumbeat.get("samples", [])
            if 0 <= sample_index < len(samples):
                return samples[sample_index]

            return None

        except Exception as e:
            logger.error(f"Error getting current sample data: {e}")
            return None

    def _update_current_sample_info(self):
        """Update the current sample information display."""
        try:
            sample_data = self._get_current_sample_data()

            if not sample_data:
                self.sample_title_label.setText("No sample selected")
                self.sample_path_label.setText("")
                self.processing_strategy_label.setText("")
                return

            # Sample title
            self.sample_title_label.setText(sample_data.get("title", "Unknown Sample"))

            # File path
            file_path = sample_data.get("file_path", "")
            if file_path:
                self.sample_path_label.setText(f"Path: {file_path}")
            else:
                self.sample_path_label.setText("No file path")

            # Processing strategy
            if sample_data.get("downloaded") and file_path and os.path.exists(file_path):
                strategy = self._determine_processing_strategy(sample_data)
                self.processing_strategy_label.setText(f"Recommended: {strategy['description']}")
            else:
                self.processing_strategy_label.setText("File not available for processing")

        except Exception as e:
            logger.error(f"Error updating current sample info: {e}")

    def _determine_processing_strategy(self, sample_data):
        """Determine the recommended processing strategy for a sample."""
        try:
            file_path = sample_data.get("file_path", "")
            sample_type = sample_data.get("type", "").lower()

            if not file_path:
                return {"description": "No file available", "type": "none"}

            filename = os.path.basename(file_path).lower()

            # Enhanced detection of drum samples
            is_drum_file = False
            drum_keywords = ["_drum", "drum_", "drums_", "_drums", "drum.", ".drum"]

            for keyword in drum_keywords:
                if keyword in filename:
                    is_drum_file = True
                    break

            # Check filename patterns
            if is_drum_file or sample_type == "drum":
                logger.info(f"Detected drum file: {filename}, using drum-only processing")
                return {
                    "description": "Drum-Only Processing (DrumSep) - for drum component separation",
                    "type": "drum_only",
                    "model": "DrumSep"
                }
            elif "_original" in filename or sample_type == "original":
                logger.info(f"Detected original file: {filename}, using full song processing")
                return {
                    "description": "Full Song Separation (HDemucs) - for complete instrument separation",
                    "type": "full_song",
                    "model": "HDemucs"
                }
            else:
                logger.info(f"No specific pattern detected in: {filename}, using auto-detection")
                return {
                    "description": "Auto-detect - will choose best method based on content",
                    "type": "auto",
                    "model": "Auto"
                }

        except Exception as e:
            logger.error(f"Error determining processing strategy: {e}")
            return {"description": "Error determining strategy", "type": "auto"}

    def _show_message(self, title, message, icon=QMessageBox.Information):
        """Show a message box with the given title and message."""
        try:
            QMessageBox(icon, title, message, QMessageBox.Ok, self).exec()
        except Exception as e:
            logger.error(f"Error showing message box: {e}")
            print(f"ERROR: {title} - {message}")

    # Event handlers
    def on_drumbeat_selected(self, current, previous):
        """Handle selection change in the drumbeat list."""
        try:
            # Reset current selection if no item selected
            if not current:
                self.current_drumbeat = None
                self.current_sample = None
                self.samples_list.clear()
                self.update_drumbeat_details()
                self.update_button_states()
                return

            # Get the selected drumbeat index
            selected_row = self.drumbeat_list.currentRow()
            if 0 <= selected_row < len(self.drumbeats):
                # Set the current drumbeat
                self.current_drumbeat = self.drumbeats[selected_row]
                logger.info(f"Selected drumbeat: {self.current_drumbeat.get('name')}")

                # Update the UI
                self.update_drumbeat_details()
                self.populate_samples_list()
                self.update_button_states()
            else:
                logger.error(f"Invalid drumbeat selection index: {selected_row}, total drumbeats: {len(self.drumbeats)}")
        except Exception as e:
            logger.error(f"Error selecting drumbeat: {e}")
            logger.error(traceback.format_exc())

    def on_sample_selected(self):
        """Handle selection change in the samples list."""
        try:
            # Reset current sample selection if nothing is selected
            if not self.samples_list.selectedItems():
                self.current_sample = None
                self.update_button_states()
                return

            # Get the sample data
            sample_data = self._get_current_sample_data()
            if sample_data:
                self.current_sample = sample_data
                logger.info(f"Selected sample: {sample_data.get('title')}")

                # Update UI
                self.update_button_states()
            else:
                self.current_sample = None
                self.update_button_states()

        except Exception as e:
            logger.error(f"Error selecting sample: {e}")
            logger.error(traceback.format_exc())

    def update_drumbeat_details(self):
        """Update the drumbeat details display with the current drumbeat information."""
        try:
            if not self.current_drumbeat:
                self.profile_text.clear()
                return

            # Create HTML display of drumbeat details
            profile_text = f"<h2>{self.current_drumbeat.get('name', 'Unknown Drumbeat')}</h2>\n"

            # Artist
            if self.current_drumbeat.get("artist"):
                profile_text += f"<p><b>Artist:</b> {self.current_drumbeat.get('artist')}</p>\n"

            # Description
            if self.current_drumbeat.get("description"):
                profile_text += f"<p><b>Description:</b> {self.current_drumbeat.get('description')}</p>\n"

            # Add sample count
            sample_count = len(self.current_drumbeat.get("samples", []))
            profile_text += f"<p><b>Samples:</b> {sample_count}</p>\n"

            # Add source
            if self.current_drumbeat.get("source"):
                profile_text += f"<p><b>Source:</b> {self.current_drumbeat.get('source')}</p>\n"

            # Add creation date if available
            if self.current_drumbeat.get("created"):
                profile_text += f"<p><b>Created:</b> {self.current_drumbeat.get('created')}</p>\n"

            self.profile_text.setHtml(profile_text)

        except Exception as e:
            logger.error(f"Error updating drumbeat details: {e}")
            logger.error(traceback.format_exc())

    def on_add_drumbeat(self):
        """Handle adding a new drumbeat profile."""
        try:
            dialog = DrumBeatProfileDialog(self)
            if dialog.exec() == QDialog.Accepted:
                profile_data = dialog.get_profile_data()

                if not profile_data.get("name"):
                    self._show_message("Missing Information", "Please provide a name for the drumbeat profile.", QMessageBox.Warning)
                    return

                # Add the profile to the list
                self.drumbeats.append(profile_data)

                # Store in database if available
                if self.db:
                    self._store_profile_in_database(profile_data)

                # Refresh the UI
                self.populate_drumbeat_list()

                # Select the new profile
                self.drumbeat_list.setCurrentRow(len(self.drumbeats) - 1)

                logger.info(f"Added new drumbeat profile: {profile_data.get('name')}")

        except Exception as e:
            logger.error(f"Error adding drumbeat: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to add drumbeat profile: {str(e)}", QMessageBox.Critical)

    def on_edit_drumbeat(self):
        """Handle editing the selected drumbeat profile."""
        try:
            if not self.current_drumbeat:
                self._show_message("No Selection", "Please select a drumbeat profile first.", QMessageBox.Information)
                return

            dialog = DrumBeatProfileDialog(self, self.current_drumbeat)
            if dialog.exec() == QDialog.Accepted:
                profile_data = dialog.get_profile_data()

                if not profile_data.get("name"):
                    self._show_message("Missing Information", "Please provide a name for the drumbeat profile.", QMessageBox.Warning)
                    return

                # Update the profile in the list
                selected_row = self.drumbeat_list.currentRow()
                if 0 <= selected_row < len(self.drumbeats):
                    self.drumbeats[selected_row] = profile_data
                    self.current_drumbeat = profile_data

                    # Store in database if available
                    if self.db:
                        self._store_profile_in_database(profile_data)

                    # Refresh the UI
                    self.populate_drumbeat_list()
                    self.drumbeat_list.setCurrentRow(selected_row)
                    self.update_drumbeat_details()

                    logger.info(f"Updated drumbeat profile: {profile_data.get('name')}")

        except Exception as e:
            logger.error(f"Error editing drumbeat: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to edit drumbeat profile: {str(e)}", QMessageBox.Critical)

    def on_delete_drumbeat(self):
        """Handle deleting the selected drumbeat profile."""
        try:
            if not self.current_drumbeat:
                self._show_message("No Selection", "Please select a drumbeat profile first.", QMessageBox.Information)
                return

            # Ask for confirmation
            profile_name = self.current_drumbeat.get("name", "Unknown")
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                         f"Are you sure you want to delete the drumbeat profile '{profile_name}'?",
                                         QMessageBox.Yes | QMessageBox.No)

            if confirm == QMessageBox.Yes:
                # Remove from database if available
                if self.db:
                    try:
                        profile_id = self.current_drumbeat.get("id")
                        self.db.execute("DELETE FROM drumbeat_samples WHERE drumbeat_id = ?", (profile_id,))
                        self.db.execute("DELETE FROM drumbeats WHERE id = ?", (profile_id,))
                    except Exception as db_error:
                        logger.error(f"Error deleting from database: {db_error}")

                # Remove the profile from the list
                selected_row = self.drumbeat_list.currentRow()
                if 0 <= selected_row < len(self.drumbeats):
                    del self.drumbeats[selected_row]

                    # Reset selection
                    self.current_drumbeat = None
                    self.current_sample = None

                    # Refresh the UI
                    self.populate_drumbeat_list()
                    self.samples_list.clear()
                    self.update_drumbeat_details()
                    self.update_button_states()

                    logger.info(f"Deleted drumbeat profile: {profile_name}")

        except Exception as e:
            logger.error(f"Error deleting drumbeat: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to delete drumbeat profile: {str(e)}", QMessageBox.Critical)

    def on_add_sample(self):
        """Handle adding a new sample to the current drumbeat profile."""
        try:
            if not self.current_drumbeat:
                self._show_message("No Profile Selected", "Please select a drumbeat profile first.", QMessageBox.Information)
                return

            dialog = DrumBeatSampleDialog(self)
            if dialog.exec() == QDialog.Accepted:
                sample_data = dialog.get_sample_data()

                if not sample_data.get("title"):
                    self._show_message("Missing Information", "Please provide a title for the sample.", QMessageBox.Warning)
                    return

                # Add the sample to the current drumbeat
                if "samples" not in self.current_drumbeat:
                    self.current_drumbeat["samples"] = []

                self.current_drumbeat["samples"].append(sample_data)

                # Store in database if available
                if self.db:
                    self._store_sample_in_database(sample_data, self.current_drumbeat.get("id"))
                    self._store_profile_in_database(self.current_drumbeat)  # Update profile

                # Refresh the UI
                self.populate_samples_list()

                logger.info(f"Added new sample: {sample_data.get('title')} to {self.current_drumbeat.get('name')}")

        except Exception as e:
            logger.error(f"Error adding sample: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to add sample: {str(e)}", QMessageBox.Critical)

    def on_edit_sample(self):
        """Handle editing the selected sample."""
        try:
            sample_data = self._get_current_sample_data()
            if not sample_data:
                self._show_message("No Sample Selected", "Please select a sample first.", QMessageBox.Information)
                return

            dialog = DrumBeatSampleDialog(self, sample_data)
            if dialog.exec() == QDialog.Accepted:
                updated_sample = dialog.get_sample_data()

                if not updated_sample.get("title"):
                    self._show_message("Missing Information", "Please provide a title for the sample.", QMessageBox.Warning)
                    return

                # Update the sample in the current drumbeat
                sample_index = self.samples_list.currentItem().data(Qt.UserRole)
                if 0 <= sample_index < len(self.current_drumbeat.get("samples", [])):
                    self.current_drumbeat["samples"][sample_index] = updated_sample

                    # Store in database if available
                    if self.db:
                        self._store_sample_in_database(updated_sample, self.current_drumbeat.get("id"))
                        self._store_profile_in_database(self.current_drumbeat)  # Update profile

                    # Refresh the UI
                    self.populate_samples_list()

                    # Re-select the edited sample
                    self.samples_list.setCurrentRow(sample_index)

                    logger.info(f"Updated sample: {updated_sample.get('title')}")

        except Exception as e:
            logger.error(f"Error editing sample: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to edit sample: {str(e)}", QMessageBox.Critical)

    def on_delete_sample(self):
        """Handle deleting the selected sample."""
        try:
            sample_data = self._get_current_sample_data()
            if not sample_data:
                self._show_message("No Sample Selected", "Please select a sample first.", QMessageBox.Information)
                return

            # Ask for confirmation
            sample_title = sample_data.get("title", "Unknown Sample")
            confirm = QMessageBox.question(self, "Confirm Deletion",
                                         f"Are you sure you want to delete the sample '{sample_title}'?",
                                         QMessageBox.Yes | QMessageBox.No)

            if confirm == QMessageBox.Yes:
                # Remove from database if available
                if self.db:
                    try:
                        sample_id = sample_data.get("id")
                        self.db.execute("DELETE FROM drumbeat_samples WHERE id = ?", (sample_id,))
                    except Exception as db_error:
                        logger.error(f"Error deleting sample from database: {db_error}")

                # Remove the sample from the current drumbeat
                sample_index = self.samples_list.currentItem().data(Qt.UserRole)
                if 0 <= sample_index < len(self.current_drumbeat.get("samples", [])):
                    del self.current_drumbeat["samples"][sample_index]

                    # Store updated profile in database
                    if self.db:
                        self._store_profile_in_database(self.current_drumbeat)

                    # Reset current sample
                    self.current_sample = None

                    # Refresh the UI
                    self.populate_samples_list()
                    self.update_button_states()

                    logger.info(f"Deleted sample: {sample_title}")

        except Exception as e:
            logger.error(f"Error deleting sample: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to delete sample: {str(e)}", QMessageBox.Critical)

    def on_scan_directory(self):
        """Handle scanning the H:\DrumBeats directory for new files."""
        try:
            # Ask for confirmation
            confirm = QMessageBox.question(self, "Scan Directory",
                                         "Scan H:\\DrumBeats directory for new audio files?\n\nThis will reload all drumbeat profiles.",
                                         QMessageBox.Yes | QMessageBox.No)

            if confirm == QMessageBox.Yes:
                # Reload drumbeat profiles
                self.load_drumbeat_profiles()
                self._show_message("Scan Complete", "Directory scan completed successfully.", QMessageBox.Information)

        except Exception as e:
            logger.error(f"Error scanning directory: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to scan directory: {str(e)}", QMessageBox.Critical)

    def on_play_audio(self):
        """Play the selected audio sample using integrated audio player or system default."""
        try:
            sample_data = self._get_current_sample_data()
            if not sample_data:
                self._show_message("No sample selected", "Please select an audio sample first.", QMessageBox.Warning)
                return

            file_path = sample_data.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                self._show_message("File not available",
                                 "The audio file is not available or does not exist.",
                                 QMessageBox.Warning)
                return

            # Try to use the audio player tab if available
            if hasattr(self, 'audio_player') and self.audio_player:
                try:
                    self.audio_player.load_file(file_path)
                    self.audio_player.play()
                    logger.info(f"Playing audio file with integrated player: {file_path}")
                    self.status_updated.emit(f"Playing: {sample_data.get('title', 'Unknown')}")
                    return
                except Exception as e:
                    logger.warning(f"Audio player failed, falling back to system player: {e}")

            # Fallback: use system default player
            try:
                system = platform.system()
                if system == "Windows":
                    os.startfile(file_path)
                elif system == "Darwin":  # macOS
                    subprocess.call(["open", file_path])
                else:  # Linux and other Unix
                    subprocess.call(["xdg-open", file_path])
                    
                logger.info(f"Playing audio file with system player: {file_path}")
                self.status_updated.emit(f"Opened: {sample_data.get('title', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Failed to open audio file: {e}")
                self._show_message("Playback Error", 
                                 f"Failed to play audio file: {str(e)}", 
                                 QMessageBox.Critical)

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            self._show_message("Playback Error", f"Could not play audio file: {str(e)}", QMessageBox.Critical)

    def on_send_to_audio_tab(self):
        """Send the selected audio sample to the main audio player tab."""
        try:
            sample_data = self._get_current_sample_data()
            if not sample_data:
                self._show_message("No sample selected", "Please select an audio sample first.", QMessageBox.Warning)
                return

            file_path = sample_data.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                self._show_message("File not available",
                                 "The audio file is not available or does not exist.",
                                 QMessageBox.Warning)
                return

            # Try to get the main audio player tab
            main_window = self.window()
            audio_player = None

            # Look for the audio player tab in the main window
            if hasattr(main_window, 'tab_widget'):
                for i in range(main_window.tab_widget.count()):
                    tab_text = main_window.tab_widget.tabText(i)
                    if "audio player" in tab_text.lower():
                        audio_player = main_window.tab_widget.widget(i)
                        main_window.tab_widget.setCurrentIndex(i)  # Switch to the tab
                        break

            if audio_player and hasattr(audio_player, 'load_file'):
                # Load the file in the audio player
                audio_player.load_file(file_path)
                self._show_message("Audio Sent", f"Sent '{sample_data.get('title')}' to Audio Player tab.", QMessageBox.Information)
                logger.info(f"Sent audio file to player: {file_path}")
            else:
                # Fallback: load in local audio player if available
                if AUDIO_PLAYER_AVAILABLE and hasattr(self, 'audio_player'):
                    self.audio_player.load_file(file_path)
                    self.details_tabs.setCurrentWidget(self.audio_player)
                    logger.info(f"Loaded audio file in local player: {file_path}")
                else:
                    self._show_message("Audio Player Not Available",
                                     "Could not find the main audio player tab.",
                                     QMessageBox.Warning)

        except Exception as e:
            logger.error(f"Error sending to audio tab: {e}")
            self._show_message("Error", f"Failed to send audio to player: {str(e)}", QMessageBox.Critical)

    def on_add_to_mvsep(self):
        """Add current sample to MVSep batch processor queue with processing options."""
        try:
            sample_data = self._get_current_sample_data()
            if not sample_data:
                self._show_message("No sample selected", "Please select a sample first.", QMessageBox.Warning)
                return

            file_path = sample_data.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                self._show_message("File not available",
                                 "The audio file is not available or does not exist.",
                                 QMessageBox.Warning)
                return

            # Show processing options dialog
            processing_dialog = MVSepProcessingDialog(self, sample_data)
            if processing_dialog.exec() != QDialog.Accepted:
                return

            options = processing_dialog.get_processing_options()

            # Determine processing strategy
            if options["processing_type"] == "auto":
                strategy = self._determine_processing_strategy(sample_data)
                processing_type = strategy["type"]
            else:
                processing_type = options["processing_type"]

            # Create the appropriate output directory structure based on folder organization
            base_output_dir = options.get("output_dir")
            folder_organization = options.get("folder_organization", "subfolder_per_file")

            # Get the filename without extension for use in subfolder naming
            filename = os.path.basename(file_path)
            file_base_name = os.path.splitext(filename)[0]

            # Create the organized output directory
            if folder_organization == "subfolder_per_file":
                # Create a subfolder with the sample name
                output_dir = os.path.join(base_output_dir, file_base_name)
            elif folder_organization == "date_based":
                # Use current date for folder organization
                current_date = datetime.now().strftime("%Y-%m-%d")
                output_dir = os.path.join(base_output_dir, current_date)
            elif folder_organization == "processing_type":
                # Group by processing type
                type_folder = "drums" if processing_type == "drum_only" else "full_song"
                output_dir = os.path.join(base_output_dir, type_folder)
            else:  # flat structure
                output_dir = base_output_dir

            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            logger.info(f"Created output directory: {output_dir}")

            # Robust MainWindow detection for MVSep integration
            main_window = None
            batch_processor = None
            
            logger.info("Starting MainWindow detection for MVSep integration...")
            
            # Method 1: Check if current window() is already the MainWindow
            current_window = self.window()
            if hasattr(current_window, 'tab_widget') and 'MainWindow' in type(current_window).__name__:
                main_window = current_window
                logger.info(f"Found MainWindow directly: {type(main_window).__name__}")
            else:
                logger.info(f"Current window {type(current_window).__name__} is not MainWindow, searching...")
                
                # Method 2: Search parent hierarchy thoroughly
                parent = self.parent()
                level = 0
                while parent and level < 10:  # Increased search depth
                    level += 1
                    logger.debug(f"Checking parent level {level}: {type(parent).__name__}")
                    
                    if (hasattr(parent, 'tab_widget') and 
                        ('MainWindow' in type(parent).__name__ or 
                         hasattr(parent, 'tab_widgets'))):
                        main_window = parent
                        logger.info(f"Found MainWindow at parent level {level}: {type(main_window).__name__}")
                        break
                    parent = parent.parent()
                
                # Method 3: QApplication comprehensive search
                if not main_window:
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        logger.info("Searching all application widgets for MainWindow...")
                        for widget in app.allWidgets():
                            # Multiple criteria for MainWindow detection
                            is_main_window = (
                                hasattr(widget, 'tab_widget') and
                                (
                                    'MainWindow' in type(widget).__name__ or
                                    hasattr(widget, 'tab_widgets') or
                                    (hasattr(widget, 'windowTitle') and 'DrumTracKAI' in widget.windowTitle())
                                )
                            )
                            
                            if is_main_window:
                                main_window = widget
                                logger.info(f"Found MainWindow via QApplication: {type(main_window).__name__}")
                                break
            
            # Final validation
            if not main_window or not hasattr(main_window, 'tab_widget'):
                error_msg = f"Cannot find MainWindow with tab_widget. Searched current window: {type(current_window).__name__}"
                logger.error(error_msg)
                QMessageBox.warning(self, "MVSep Integration Error", 
                                  "Cannot find batch processor tab. Please ensure the Batch Processing tab is loaded.")
                return
            
            logger.info(f"Successfully found MainWindow: {type(main_window).__name__} with {main_window.tab_widget.count()} tabs")

            # Look for batch processor or MVSep tab
            if hasattr(main_window, 'tab_widget'):
                for i in range(main_window.tab_widget.count()):
                    tab_text = main_window.tab_widget.tabText(i).lower()
                    logger.info(f"Checking tab {i}: '{main_window.tab_widget.tabText(i)}' (lowercase: '{tab_text}')")
                    if "mvsep" in tab_text or "batch" in tab_text:
                        tab_widget = main_window.tab_widget.widget(i)
                        logger.info(f"Found potential tab: {tab_text}, widget type: {type(tab_widget).__name__}")
                        # Check if this widget has add_file or similar method
                        if hasattr(tab_widget, 'add_file') or hasattr(tab_widget, 'add_to_queue'):
                            batch_processor = tab_widget
                            logger.info(f"Using tab '{main_window.tab_widget.tabText(i)}' as batch processor")
                            break

            if batch_processor:
                # Prepare metadata for the batch processor
                metadata = {
                    "title": sample_data.get("title", "Unknown Sample"),
                    "source": "DrumBeats",
                    "drumbeat_id": self.current_drumbeat.get("id", ""),
                    "drumbeat_name": self.current_drumbeat.get("name", "Unknown Drumbeat"),
                    "processing_type": processing_type,
                    "keep_original": options["keep_original"],
                    "auto_analyze": options["auto_analyze"],
                    "folder_organization": folder_organization,
                    # Critical: Set skip_first_stage flag for drum-only processing
                    "skip_first_stage": True if processing_type == "drum_only" else False
                }

                logger.info(f"Processing type: {processing_type}, Skip first stage: {metadata.get('skip_first_stage', False)}")

                # Add to batch processor
                try:
                    if hasattr(batch_processor, 'add_file'):
                        batch_processor.add_file(file_path, metadata=metadata)
                    elif hasattr(batch_processor, 'add_to_queue'):
                        # Use the organized output directory
                        batch_processor.add_to_queue(file_path, output_dir, metadata)
                    else:
                        # Try other common method names
                        for method_name in ['add_item', 'queue_file', 'add_audio_file']:
                            if hasattr(batch_processor, method_name):
                                getattr(batch_processor, method_name)(file_path, metadata)
                                break
                        else:
                            raise AttributeError("No suitable method found to add file to batch processor")

                    self._show_message("Added to MVSep",
                                     f"Added '{sample_data.get('title')}' to MVSep processing queue.\n"
                                     f"Processing type: {processing_type.replace('_', ' ').title()}\n"
                                     f"Output folder: {output_dir}",
                                     QMessageBox.Information)

                    logger.info(f"Added sample to MVSep queue: {file_path} with processing type: {processing_type}")
                    logger.info(f"Output directory: {output_dir}")

                except Exception as add_error:
                    logger.error(f"Error adding to batch processor: {add_error}")
                    self._show_message("Error", f"Failed to add to batch processor: {str(add_error)}", QMessageBox.Critical)
            else:
                self._show_message("MVSep Not Available",
                                 "Could not find the MVSep or Batch Processing tab.",
                                 QMessageBox.Warning)

        except Exception as e:
            logger.error(f"Error adding to MVSep: {e}")
            logger.error(traceback.format_exc())
            self._show_message("Error", f"Failed to add sample to MVSep: {str(e)}", QMessageBox.Critical)

    def set_event_bus(self, event_bus):
        """Set the event bus for communication with other components."""
        self.event_bus = event_bus
        logger.info("Event bus connected to DrumBeats widget")

        # Subscribe to relevant events if needed
        if self.event_bus:
            try:
                # Subscribe to file processing completion events
                self.event_bus.subscribe(self._on_processing_complete, event_type="processing_complete")
                # Subscribe to database update events
                self.event_bus.subscribe(self._on_database_updated, event_type="database_updated")
            except Exception as e:
                logger.warning(f"Could not subscribe to event bus events: {e}")

    def _on_processing_complete(self, event):
        """Handle processing completion events from MVSep."""
        try:
            if event.data and isinstance(event.data, dict):
                source_file = event.data.get("source_file", "")
                output_files = event.data.get("output_files", {})

                # Check if this was one of our drumbeat samples
                for drumbeat in self.drumbeats:
                    for sample in drumbeat.get("samples", []):
                        if sample.get("file_path") == source_file:
                            # Update sample with processing results
                            sample["processed"] = True
                            sample["output_files"] = output_files
                            sample["date_processed"] = datetime.now().isoformat()

                            # Store in database if available
                            if self.db:
                                self._store_sample_in_database(sample, drumbeat.get("id"))

                            logger.info(f"Updated sample with processing results: {sample.get('title')}")

                            # Refresh UI if this is the current sample
                            if self.current_sample and self.current_sample.get("id") == sample.get("id"):
                                self.update_button_states()

                            break
                    else:
                        continue
                    break

        except Exception as e:
            logger.error(f"Error handling processing complete event: {e}")

    def _on_database_updated(self, event):
        """Handle database update events."""
        try:
            # Refresh our data if the database was updated by another component
            if event.data and event.data.get("table") in ["drumbeats", "drumbeat_samples"]:
                logger.info("Database updated, refreshing drumbeat data")
                # Could implement a more sophisticated refresh here
                pass
        except Exception as e:
            logger.error(f"Error handling database update event: {e}")

    def on_play_beat(self):
        """Play the currently selected drum beat sample."""
        try:
            sample_data = self._get_current_sample_data()
            if not sample_data:
                self._show_message("No sample selected", "Please select a sample first.", QMessageBox.Warning)
                return

            file_path = sample_data.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                self._show_message("File not available",
                                 "The audio file is not available or does not exist.",
                                 QMessageBox.Warning)
                return

            # Try to use the audio player tab if available
            if hasattr(self, 'audio_player') and self.audio_player:
                try:
                    self.audio_player.load_file(file_path)
                    self.audio_player.play()
                    logger.info(f"Playing audio file: {file_path}")
                    self.status_updated.emit(f"Playing: {sample_data.get('title', 'Unknown')}")
                    return
                except Exception as e:
                    logger.warning(f"Audio player failed: {e}")

            # Fallback: use system default player
            try:
                if platform.system() == "Windows":
                    os.startfile(file_path)
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", file_path])
                else:  # Linux
                    subprocess.run(["xdg-open", file_path])
                    
                logger.info(f"Opened audio file with system player: {file_path}")
                self.status_updated.emit(f"Opened: {sample_data.get('title', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Failed to open audio file: {e}")
                self._show_message("Playback Error", 
                                 f"Failed to play audio file: {str(e)}", 
                                 QMessageBox.Critical)

        except Exception as e:
            logger.error(f"Error playing beat: {e}")
            self._show_message("Error", f"Failed to play beat: {str(e)}", QMessageBox.Critical)

    def on_download_beat(self):
        """Download the currently selected drum beat sample to a chosen location."""
        try:
            sample_data = self._get_current_sample_data()
            if not sample_data:
                self._show_message("No sample selected", "Please select a sample first.", QMessageBox.Warning)
                return

            file_path = sample_data.get('file_path', '')
            if not file_path or not os.path.exists(file_path):
                self._show_message("File not available",
                                 "The audio file is not available or does not exist.",
                                 QMessageBox.Warning)
                return

            # Get the original filename
            original_filename = os.path.basename(file_path)
            sample_title = sample_data.get('title', 'Unknown')
            
            # Open file dialog to choose destination
            destination, _ = QFileDialog.getSaveFileName(
                self,
                f"Save {sample_title}",
                original_filename,
                "Audio Files (*.wav *.mp3 *.flac *.ogg *.m4a);;All Files (*)"
            )
            
            if not destination:
                return  # User cancelled
            
            # Copy the file
            import shutil
            try:
                shutil.copy2(file_path, destination)
                logger.info(f"Downloaded file from {file_path} to {destination}")
                self.status_updated.emit(f"Downloaded: {sample_title}")
                self._show_message("Download Complete", 
                                 f"Successfully downloaded {sample_title} to:\n{destination}", 
                                 QMessageBox.Information)
                
            except Exception as e:
                logger.error(f"Failed to copy file: {e}")
                self._show_message("Download Error", 
                                 f"Failed to download file: {str(e)}", 
                                 QMessageBox.Critical)

        except Exception as e:
            logger.error(f"Error downloading beat: {e}")
            self._show_message("Error", f"Failed to download beat: {str(e)}", QMessageBox.Critical)

    def _show_message(self, title, message, icon_type=QMessageBox.Information):
        """Show a message box with the given title, message, and icon type."""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setIcon(icon_type)
        msg_box.exec()


# Utility functions for external integration
def create_drumbeats_widget(parent=None):
    """
    Factory function to create a DrumBeats widget with error handling.

    Args:
        parent: Parent widget

    Returns:
        DrumBeatsWidget instance or None if creation fails
    """
    try:
        widget = DrumBeatsWidget(parent)
        logger.info("DrumBeats widget created successfully")
        return widget
    except Exception as e:
        logger.error(f"Failed to create DrumBeats widget: {e}")
        logger.error(traceback.format_exc())
        return None


def apply_drumbeats_integration_fix(drumbeats_widget):
    """
    Apply integration fixes to an existing DrumBeats widget.
    This function can be called to retrofit existing widgets with enhanced functionality.

    Args:
        drumbeats_widget: Existing DrumBeats widget instance

    Returns:
        bool: True if fixes were applied successfully
    """
    try:
        if not drumbeats_widget:
            logger.error("Cannot apply integration fix: widget is None")
            return False

        # Check if widget already has enhanced integration
        if hasattr(drumbeats_widget, '_integration_fix_applied'):
            logger.info("Integration fix already applied to this widget")
            return True

        # Mark as fixed
        drumbeats_widget._integration_fix_applied = True

        # Ensure all required methods exist
        required_methods = [
            'update_button_states',
            '_get_current_sample_data',
            '_update_current_sample_info',
            '_determine_processing_strategy'
        ]

        for method_name in required_methods:
            if not hasattr(drumbeats_widget, method_name):
                logger.warning(f"DrumBeats widget missing method: {method_name}")

        # Refresh the widget's data
        if hasattr(drumbeats_widget, 'load_drumbeat_profiles'):
            drumbeats_widget.load_drumbeat_profiles()

        logger.info("DrumBeats widget integration fix applied successfully")
        return True

    except Exception as e:
        logger.error(f"Error applying DrumBeats widget integration fix: {e}")
        logger.error(traceback.format_exc())
        return False


def get_drumbeats_widget_status():
    """
    Get status information about the DrumBeats widget functionality.

    Returns:
        dict: Status information
    """
    status = {
        "audio_player_available": AUDIO_PLAYER_AVAILABLE,
        "drumbeats_directory": DRUMBEATS_DIR,
        "directory_exists": os.path.exists(DRUMBEATS_DIR),
        "supported_formats": AUDIO_EXTENSIONS
    }

    # Check for files in the directory
    if status["directory_exists"]:
        try:
            files = list(Path(DRUMBEATS_DIR).glob("*"))
            audio_files = [f for f in files if f.suffix.lower() in AUDIO_EXTENSIONS]
            status["total_files"] = len(files)
            status["audio_files"] = len(audio_files)

            # Check for expected naming pattern
            original_files = [f for f in audio_files if "_original" in f.name.lower()]
            drum_files = [f for f in audio_files if "_drum" in f.name.lower()]
            status["original_files"] = len(original_files)
            status["drum_files"] = len(drum_files)

        except Exception as e:
            status["scan_error"] = str(e)

    return status


# Example usage and testing
if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create application
    app = QApplication(sys.argv)

    # Create widget
    widget = create_drumbeats_widget()

    if widget:
        widget.show()
        widget.resize(1200, 800)

        # Connect status updates
        widget.status_updated.connect(lambda msg: print(f"Status: {msg}"))

        # Print status information
        status = get_drumbeats_widget_status()
        print("DrumBeats Widget Status:")
        for key, value in status.items():
            print(f"  {key}: {value}")

        logger.info("DrumBeats widget test application started")

        # Run application
        sys.exit(app.exec())
    else:
        print("Failed to create DrumBeats widget")
        sys.exit(1)